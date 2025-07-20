#!/bin/bash

# Set the path for the certificate and key
CERT_FILE="/app/cert.pem"
KEY_FILE="/app/key.pem"

# Check if the certificate and key files already exist
if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
  echo "Certificate not found. Generating a new self-signed certificate..."
  # Generate a new self-signed certificate and key
  openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout "$KEY_FILE" \
    -out "$CERT_FILE" \
    -days 3650 \
    -subj "/C=US/ST=State/L=City/O=Organization/OU=OrgUnit/CN=localhost"
  echo "Certificate generated successfully."
else
  echo "Existing certificate found."
fi

# Execute the main python application
echo "Starting FlareSolverr Proxy..."
exec python flaresolverr_proxy.py
