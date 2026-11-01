"""Allowlist static server for the mock exam site.

Serves only the public site files: the 3 pages, catalog.json, assets/ and exams/.
Everything else (.env, sources/ with personal notes, scripts, .git) returns 404, and
directory listings are disabled.

Usage: python serve.py [port]   (binds 127.0.0.1 only; expose with Tailscale Funnel)
"""
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
PAGES = {"/": "/index.html", "/index.html": None, "/subject.html": None, "/exam.html": None, "/catalog.json": None}
PREFIXES = ("/assets/", "/exams/")


class Handler(SimpleHTTPRequestHandler):
    def _allowed(self):
        path = unquote(urlsplit(self.path).path)
        if any(part.startswith(".") for part in path.split("/") if part):
            return None
        if path in PAGES:
            return PAGES[path] or path
        if path.startswith(PREFIXES) and not path.endswith("/"):
            return path
        return None

    def _guard(self):
        target = self._allowed()
        if target is None:
            self.send_error(404)
            return False
        query = urlsplit(self.path).query
        self.path = target + (f"?{query}" if query else "")
        return True

    def do_GET(self):
        if self._guard():
            super().do_GET()

    def do_HEAD(self):
        if self._guard():
            super().do_HEAD()

    def list_directory(self, path):
        self.send_error(404)
        return None

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8787
    server = ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, directory=str(ROOT)))
    print(f"serving {ROOT} on http://127.0.0.1:{port}")
    server.serve_forever()
