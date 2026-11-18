"""Loopback HTTP transport for the archive viewer and optional live MicroWorld."""

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from threading import Thread
from urllib.parse import parse_qsl, urlsplit
import webbrowser

from . import SCHEMA
from .archive import json_bytes
from .cli import ERRORS
from .locale import CHINESE
from .live import save_details


STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/viewer.css": ("viewer.css", "text/css; charset=utf-8"),
    "/viewer.js": ("viewer.js", "text/javascript; charset=utf-8"),
    "/live.js": ("live.js", "text/javascript; charset=utf-8"),
    "/live_motion.js": ("live_motion.js", "text/javascript; charset=utf-8"),
    "/nest_view.js": ("nest_view.js", "text/javascript; charset=utf-8"),
    "/observatory.js": ("observatory.js", "text/javascript; charset=utf-8"),
}
LIVE = "/api/v1/live/"


def bind(api, port, live=None):
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
            try:
                self.end_headers()
                self.wfile.write(payload)
            except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                pass

        def as_json(self, status, payload):
            self.send_content(status, "application/json; charset=utf-8", json_bytes(payload))

        def local_host(self):
            host = self.headers.get("Host")
            return host in (f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}")

        def do_GET(self):
            if not self.local_host():
                self.as_json(HTTPStatus.FORBIDDEN, dict(schema=SCHEMA, error="This viewer serves only the local host"))
                return
            url = urlsplit(self.path)
            path = url.path
            if path == "/locale/zh-CN.json":
                self.send_content(HTTPStatus.OK, "application/json; charset=utf-8", CHINESE.read_bytes())
            elif path in STATIC:
                file, media = STATIC[path]
                self.send_content(HTTPStatus.OK, media, (root / file).read_bytes())
            elif path.startswith(LIVE):
                try:
                    resource = path.removeprefix(LIVE)
                    if live is not None:
                        data = live.read(resource, dict(parse_qsl(url.query, max_num_fields=12)))
                    elif resource == "status":
                        data = dict(enabled=False)
                    else:
                        raise ValueError("Live MicroWorld is disabled")
                    self.as_json(HTTPStatus.OK, dict(schema=SCHEMA, data=data))
                except ERRORS as err:
                    self.as_json(HTTPStatus.BAD_REQUEST, dict(schema=SCHEMA, error=str(err)))
            elif path.startswith("/api/"):
                try:
                    self.as_json(HTTPStatus.OK, api.dispatch(self.path))
                except ERRORS as err:
                    self.as_json(HTTPStatus.BAD_REQUEST, dict(schema=SCHEMA, error=str(err)))
            else:
                self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self):
            path = urlsplit(self.path).path
            if live is None or not path.startswith(LIVE):
                self.send_error(HTTPStatus.NOT_IMPLEMENTED, "Unsupported method ('POST')")
                return
            try:
                resource = path.removeprefix(LIVE)
                size = int(self.headers.get("Content-Length", "0"))
                # Windows may reset the connection if we close it with unread request bytes.
                self.connection.settimeout(5)
                body = self.rfile.read(size) if 0 < size <= 2048 else b""
                if not self.local_host() or self.headers.get("Origin") != "http://" + self.headers["Host"]:
                    self.as_json(HTTPStatus.FORBIDDEN, dict(schema=SCHEMA, error="Live commands require the local viewer origin"))
                    return
                if (resource not in {"new", "nursery", "habitat", "observatory", "single-nest", "clock", "seek", "save", "load", "folder", "replay"}
                        or len(body) < 2 or len(body) != size or
                        self.headers.get_content_type() != "application/json"):
                    raise ValueError("Invalid live command request")
                data = json.loads(body)
                if not isinstance(data, dict):
                    raise ValueError("A live command needs a JSON object")
                if resource == "replay":
                    with live.lock:
                        saved = live.name_path(data.get("name"))
                        save_details(saved)
                        result = {"archive": api.catalog.register(saved)}
                else:
                    result = live.write(resource, data)
                self.as_json(HTTPStatus.OK, dict(schema=SCHEMA, data=result))
            except ERRORS as err:
                self.as_json(HTTPStatus.BAD_REQUEST, dict(schema=SCHEMA, error=str(err)))

        def log_message(self, fmt, *args):
            if not fmt.startswith('"%s" %s %s') or (len(args) > 1 and str(args[1]) not in ("200", "404")):
                super().log_message(fmt, *args)

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def serve(api, port, open_browser, live=None):
    with bind(api, port, live) as server:
        address = f"http://127.0.0.1:{server.server_port}/"
        print(f"AntWorld OP0 is running at {address}", flush=True)
        print("Leave this terminal open while viewing. Press Ctrl+C to stop.", flush=True)
        if open_browser:
            Thread(target=webbrowser.open, args=(address,), daemon=True).start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nOP0 closed.", file=sys.stderr)
