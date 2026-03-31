#!/usr/bin/env python3
"""Start ADSRECON frontend HTTP server"""
import http.server
import socketserver
import os
from pathlib import Path

BASE = Path(__file__).parent
PORT = 3000
DIRECTORY = BASE / "frontend"
os.chdir(DIRECTORY)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)


print(f"ADSRECON Frontend -> http://localhost:{PORT}")
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    httpd.serve_forever()
