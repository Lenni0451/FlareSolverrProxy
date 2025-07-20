# FlareSolverrProxy
Simple docker service to redirect HTTP requests to FlareSolverr using a regular HTTP proxy intended for RSS feed readers.

This project was generated using Google Gemini in Canvas mode.

The main purpose of this project is to access RSS feeds protected by CloudFlare. I've only tested it with Miniflux, but it should also work with other RSS feed readers.

Below are the recommended settings for using this proxy with Miniflux:
| Setting                                   | Value                     |
| ----------------------------------------- | ------------------------- |
| Allow self-signed or invalid certificates | true                      |
| Disable HTTP/2 to avoid fingerprinting    | true                      |
| Proxy URL                                 | http://192.168.178.2:8888 |
