"""Vercel entry point for `GET /api/schema`.

Vercel runs the `handler` class for the `/api/schema` route. This file holds
only the HTTP plumbing; `web.service.schema_response` holds the answer.
"""

from __future__ import annotations

import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

# Vercel runs this file with the repo root as the working directory but not on
# sys.path, so add the root before the `web` import.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from web.service import Response, schema_response


class handler(BaseHTTPRequestHandler):
    """Answer the schema route."""

    def do_GET(self) -> None:
        _write(self, schema_response())


def _write(request: BaseHTTPRequestHandler, response: Response) -> None:
    """Write one `Response` to the open request."""
    body = response.body.encode("utf-8")
    request.send_response(response.status)
    request.send_header("Content-Type", response.content_type)
    request.send_header("Content-Length", str(len(body)))
    request.end_headers()
    request.wfile.write(body)
