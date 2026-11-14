"""Loopback HTTP transport for the observation API and bundled viewer."""

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from threading import Thread
from urllib.parse import urlsplit
import webbrowser

from . import SCHEMA
from .archive import json_bytes
from .cli import ERRORS
from .locale import CHINESE


STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/viewer.css": ("viewer.css", "text/css; charset=utf-8"),
    "/viewer.js": ("viewer.js", "text/javascript; charset=utf-8"),
}


def bind(api, port):
    root = Path(__file__).with_name("web")

    class Handler(BaseHTTPRequestHandler):
        server_version = "AntWorldOP0/1"

        def send_content(self, status, media, payload):
            self.send_response(status)
            self.send_header("Content-Type", media)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; "
                             "style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            try:
                self.wfile.write(payload)
            except (ConnectionResetError, BrokenPipeError):
                pass

        def as_json(self, status, payload):
            self.send_content(status, "application/json; charset=utf-8", json_bytes(payload))

        def do_GET(self):
            host = self.headers.get("Host")
            if host not in (f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"):
                self.as_json(HTTPStatus.FORBIDDEN, dict(schema=SCHEMA, error="This viewer serves only the local host"))
                return
            path = urlsplit(self.path).path
            if path == "/locale/zh-CN.json":
                self.send_content(HTTPStatus.OK, "application/json; charset=utf-8", CHINESE.read_bytes())
            elif path in STATIC:
                file, media = STATIC[path]
                self.send_content(HTTPStatus.OK, media, (root / file).read_bytes())
            elif path.startswith("/api/"):
                try:
                    self.as_json(HTTPStatus.OK, api.dispatch(self.path))
                except ERRORS as err:
                    self.as_json(HTTPStatus.BAD_REQUEST, dict(schema=SCHEMA, error=str(err)))
            else:
                self.send_error(HTTPStatus.NOT_FOUND)

        def log_message(self, fmt, *args):
            if not fmt.startswith('"%s" %s %s') or (len(args) > 1 and str(args[1]) not in ("200", "404")):
                super().log_message(fmt, *args)

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def serve(api, port, open_browser):
    with bind(api, port) as server:
        address = f"http://127.0.0.1:{server.server_port}/"
        print(f"AntWorld OP0 is running at {address}", flush=True)
        print("Leave this terminal open while viewing. Press Ctrl+C to stop.", flush=True)
        if open_browser:
            Thread(target=webbrowser.open, args=(address,), daemon=True).start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nOP0 closed.", file=sys.stderr)
