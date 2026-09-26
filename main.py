"""The Flask entrypoint for the editor.

One WSGI app holds the HTTP plumbing for both the local server and the Vercel
deploy. It answers `/api/schema` and `/api/scad` through
`api.support.service`, and serves the repository's `public/` as static files.

Run it locally with:

    uv run flask --app main run
"""

from __future__ import annotations

from flask import Flask, Response, request

from api.support.service import Response as ServiceResponse
from api.support.service import scad_response, schema_response

app = Flask(__name__, static_folder="public", static_url_path="")


def _answer(response: ServiceResponse) -> Response:
    """One Flask answer from the service's plain `Response` record."""
    return Response(
        response.body, status=response.status, content_type=response.content_type
    )


@app.get("/api/schema")
def schema() -> Response:
    """The editor schema as JSON."""
    return _answer(schema_response())


@app.get("/api/scad")
def scad() -> Response:
    """The SCAD source for one model request."""
    return _answer(scad_response(request.args.to_dict(flat=False)))


@app.get("/")
def index() -> Response:
    """The editor page."""
    return app.send_static_file("index.html")
