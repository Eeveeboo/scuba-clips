"""Vercel entry point for `GET /api/scad`.

Vercel runs the `handler` class for the `/api/scad` route. This file holds only
the HTTP plumbing; `api.support.service.scad_response` holds the answer.
"""

from __future__ import annotations

import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Vercel runs this file with the repo root as the working directory but not on
# sys.path, so add the root before the `api.support` import.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.support.service import Response, scad_response


class handler(BaseHTTPRequestHandler):
    """Answer the SCAD route."""

    def do_GET(self) -> None:
        query = parse_qs(urlparse(self.path).query)
        _write(self, scad_response(query))


def _write(request: BaseHTTPRequestHandler, response: Response) -> None:
    """Write one `Response` to the open request."""
    body = response.body
    encoded = body.encode("utf-8") if isinstance(body, str) else body
    request.send_response(response.status)
    request.send_header("Content-Type", response.content_type)
    request.send_header("Content-Length", str(len(encoded)))
    request.end_headers()
    request.wfile.write(encoded)
