"""A dependency-free local server for the editor.

It answers `/api/schema` and `/api/scad` through `web.service`, and serves
`web/public/` as static files when that folder exists. Run it with:

    uv run python -m web.dev_server

The port comes from `PORT`, default 8000.
"""

from __future__ import annotations

import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from web.service import Response, scad_response, schema_response

PUBLIC_DIR = Path(__file__).resolve().parent / "public"
HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def _not_found() -> Response:
    return Response(
        status=404, content_type="text/plain; charset=utf-8", body="not found\n"
    )


def _static_response(url_path: str) -> Response:
    """The file under `PUBLIC_DIR`, or 404 when it is absent or escapes it."""
    if not PUBLIC_DIR.is_dir():
        return _not_found()
    relative = unquote(url_path).lstrip("/") or "index.html"
    candidate = (PUBLIC_DIR / relative).resolve()
    if PUBLIC_DIR.resolve() not in candidate.parents or not candidate.is_file():
        return _not_found()
    content_type, _ = mimetypes.guess_type(candidate.name)
    body = candidate.read_bytes()
    return Response(
        status=200, content_type=content_type or "application/octet-stream", body=body
    )


class Handler(BaseHTTPRequestHandler):
    """Route the two API paths and the static files."""

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/schema":
            response = schema_response()
        elif parsed.path == "/api/scad":
            response = scad_response(parse_qs(parsed.query))
        else:
            response = _static_response(parsed.path)
        body = response.body
        encoded = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main() -> None:
    """Start the server and print its address."""
    port = int(os.environ.get("PORT", DEFAULT_PORT))
    server = ThreadingHTTPServer((HOST, port), Handler)
    print(f"web.dev_server: http://{HOST}:{server.server_port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
