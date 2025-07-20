import os
import json
import requests
import ssl
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# --- Configuration ---
PROXY_PORT = int(os.environ.get('PROXY_PORT', 8888))
FLARESOLVERR_URL = os.environ.get('FLARESOLVERR_URL', 'http://localhost:8191/v1')
FLARESOLVERR_TIMEOUT = int(os.environ.get('FLARESOLVERR_TIMEOUT', 120000))
CERT_FILE = 'cert.pem'
KEY_FILE = 'key.pem'

class FlareSolverrProxyHandler(BaseHTTPRequestHandler):
    """
    This handler receives standard HTTP proxy requests, including CONNECT for HTTPS,
    translates them into FlareSolverr API calls, and returns the result.
    """

    def do_CONNECT(self):
        """
        Handles CONNECT requests to establish a tunnel for HTTPS traffic.
        This implements a Man-in-the-Middle (MitM) approach to decrypt the traffic.
        """
        self.send_response(200, 'Connection Established')
        self.end_headers()

        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.set_alpn_protocols(['http/1.1'])
            context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
            self.connection = context.wrap_socket(self.connection, server_side=True)
            self.rfile = self.connection.makefile('rb', self.rbufsize)
            self.wfile = self.connection.makefile('wb', self.wbufsize)
            self.handle_one_request()

        except ssl.SSLEOFError:
            print("\n--- SSL EOF Error: Client closed connection unexpectedly. ---")
            print("This is often caused by the client application rejecting the proxy's self-signed certificate.")
            print("ACTION: Ensure your client is configured to trust the proxy's certificate or ignore SSL/TLS errors.\n")
        except Exception as e:
            print(f"Error handling CONNECT request: {e}")

    def do_GET(self):
        """Handles GET requests for both HTTP and HTTPS."""
        self.handle_method('request.get')

    def do_POST(self):
        """Handles POST requests for both HTTP and HTTPS."""
        self.handle_method('request.post')

    def handle_method(self, flare_command):
        """Core logic to construct the target URL and forward to FlareSolverr."""
        if self.command == 'CONNECT':
            return

        try:
            if isinstance(self.connection, ssl.SSLSocket):
                target_url = f"https://{self.headers['host']}{self.path}"
            else:
                target_url = self.path
            self.handle_request(flare_command, target_url)
        except Exception as e:
            print(f"Error in handle_method: {e}")
            self.send_error(500, f"Error processing request: {e}")

    def handle_request(self, flare_command, target_url):
        """Constructs the payload and sends the request to FlareSolverr."""
        print(f"Received {self.command} request for: {target_url}")

        if not urlparse(target_url).scheme in ['http', 'https']:
             self.send_error(400, "Invalid URL. The proxy expects absolute URLs (e.g., http://example.com).")
             return

        payload = {'cmd': flare_command, 'url': target_url, 'maxTimeout': FLARESOLVERR_TIMEOUT}

        if self.command == 'POST':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length).decode('utf-8')
                payload['postData'] = post_data
                if 'Content-Type' in self.headers:
                    payload['headers'] = {'Content-Type': self.headers['Content-Type']}
            except Exception as e:
                self.send_error(400, f"Error reading POST data: {e}")
                return

        print(f"Forwarding to FlareSolverr: {json.dumps(payload, indent=2)}")

        try:
            response = requests.post(FLARESOLVERR_URL, json=payload, timeout=(FLARESOLVERR_TIMEOUT / 1000 + 10))
            response.raise_for_status()
            data = response.json()

            if data.get('status') == 'ok':
                solution = data.get('solution', {})
                response_body = solution.get('response', '')
                
                # --- REVISED: XML/RSS Feed Correction Logic using direct content inspection ---
                # This is more robust than checking headers, which FlareSolverr may not preserve.
                print("Checking response body for browser-rendered XML wrapper...")
                try:
                    soup = BeautifulSoup(response_body, 'lxml')
                    pre_tag = soup.find('pre')
                    
                    # A browser rendering raw XML often wraps it in a <pre> tag.
                    # We check if this tag exists and if its content looks like XML.
                    if pre_tag:
                        extracted_text = pre_tag.get_text().strip()
                        if extracted_text.startswith('<?xml'):
                            response_body = extracted_text
                            print("Successfully extracted XML from <pre> tag wrapper.")
                        else:
                            print("Found <pre> tag, but content does not appear to be XML. Using original body.")
                    else:
                        # This is the expected path for normal HTML pages.
                        print("No <pre> tag wrapper found. Assuming standard HTML response.")
                except Exception as e:
                    # If parsing fails for any reason, fall back to the original body.
                    print(f"Could not parse response with BeautifulSoup, using original body. Error: {e}")
                # --- End of revised logic ---

                self.send_response(solution.get('status', 500))
                
                for key, value in solution.get('headers', {}).items():
                    if key.lower() not in ['content-encoding', 'transfer-encoding', 'connection', 'date', 'server', 'content-length']:
                        self.send_header(key, value)
                self.end_headers()
                
                self.wfile.write(response_body.encode('utf-8'))
                print(f"Successfully returned content for {target_url}")
            else:
                error_message = data.get('message', 'Unknown FlareSolverr error')
                print(f"FlareSolverr Error: {error_message}")
                self.send_error(502, f"FlareSolverr failed: {error_message}")

        except requests.exceptions.RequestException as e:
            print(f"Error connecting to FlareSolverr: {e}")
            self.send_error(502, f"Bad Gateway: Could not connect to FlareSolverr. Error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            self.send_error(500, f"Internal Server Error: {e}")

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    address_family = socket.AF_INET6
    daemon_threads = True

if __name__ == '__main__':
    if not os.path.exists(CERT_FILE) or not os.path.exists(KEY_FILE):
        print("Error: Certificate (cert.pem) or key (key.pem) not found.")
        print("Please ensure the entrypoint.sh script has run correctly to generate them.")
        exit(1)

    server_address = ('', PROXY_PORT)
    httpd = ThreadingHTTPServer(server_address, FlareSolverrProxyHandler)
    print(f"Starting HTTP/S Proxy Server on port {PROXY_PORT}")
    print(f"Forwarding requests to FlareSolverr at: {FLARESOLVERR_URL}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        print("Server stopped.")

