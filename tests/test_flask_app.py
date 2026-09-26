"""Tests for the Flask entrypoint that serves the editor and the API."""

from __future__ import annotations

import json

from main import app

MODEL = "upper_inflator_retaining_clip"


def test_schema_route__returns_the_frozen_json_shape() -> None:
    """The client loads the editor and asks the server for the schema.

    The answer must be 200 JSON whose top level holds exactly `models` and
    `sections`, so the client can build the form and the model picker from two
    known keys.

    If this test fails, then the schema route changed status, content type or
    shape, and the client cannot load the editor.
    """
    response = app.test_client().get("/api/schema")
    assert response.status_code == 200, (
        "Expected the schema route to answer 200."
    )
    assert response.content_type.startswith("application/json"), (
        "Expected the schema route to answer as JSON."
    )
    payload = json.loads(response.get_data(as_text=True))
    assert set(payload) == {"models", "sections"}, (
        "Expected the schema top level to hold only the models and the sections."
    )
    assert payload["models"], "Expected at least one real model in the schema."
    assert {"name", "label"} <= set(payload["models"][0]), (
        "Expected each model entry to hold a name and a label."
    )
    assert {"name", "label", "fields"} <= set(payload["sections"][0]), (
        "Expected each section entry to hold a name, a label and its fields."
    )


def test_scad_route__returns_plain_scad_for_a_model() -> None:
    """The editor asks for the source of the chosen clip.

    The answer must be 200 `text/plain` OpenSCAD source, because the browser
    compiles that source into the STL and the preview.

    If this test fails, then the SCAD route changed status, content type or
    stopped returning source.
    """
    response = app.test_client().get(f"/api/scad?model={MODEL}")
    assert response.status_code == 200, (
        "Expected a known model to answer 200."
    )
    assert response.content_type.startswith("text/plain"), (
        "Expected the SCAD route to answer as plain text."
    )
    assert response.get_data(as_text=True).strip(), (
        "Expected the SCAD route to answer with source, not an empty body."
    )


def test_scad_route__drops_a_blank_query_pair() -> None:
    """A user clears a form field, so the client sends the key with a blank value.

    The answer must be the same 200 source as when the key is absent, because
    the field takes its default. An empty `model=` must answer 400 `missing
    model`, because a blank pair does not hold a value.

    If this test fails, then a blank query pair reached the service, and a
    cleared field changed the clip or the error message.
    """
    client = app.test_client()
    default = client.get(f"/api/scad?model={MODEL}")
    blank = client.get(f"/api/scad?model={MODEL}&hardware.webbing_shoulder_size=")
    assert blank.status_code == 200, (
        "Expected a blank field value to answer 200."
    )
    assert blank.get_data() == default.get_data(), (
        "Expected a blank field value to use the field default."
    )
    missing = client.get("/api/scad?model=")
    assert missing.status_code == 400, (
        "Expected an empty model to answer 400."
    )
    assert "missing model" in missing.get_data(as_text=True), (
        "Expected an empty model to report the missing model."
    )


def test_scad_route__rejects_a_bad_value() -> None:
    """A user edits the URL and types a word where the field wants a number.

    The answer must be 400 with a short message, not a wrong clip or a stack
    trace, because a wrong result would ship the wrong part.

    If this test fails, then the SCAD route accepted a bad value or leaked an
    internal detail.
    """
    response = app.test_client().get(
        f"/api/scad?model={MODEL}&hardware.inflator_tube_diameter=abc"
    )
    assert response.status_code == 400, (
        "Expected a bad value to answer 400."
    )
    body = response.get_data(as_text=True)
    assert "bad value" in body, "Expected the answer to explain the bad value."
    assert "Traceback" not in body, "Expected the answer to hide the stack trace."


def test_static_route__serves_a_client_file() -> None:
    """The browser loads the editor script from the public folder.

    The answer must be 200 with the file bytes, because the editor cannot run
    without its script.

    If this test fails, then the static route does not serve the public folder.
    """
    response = app.test_client().get("/app.js")
    assert response.status_code == 200, (
        "Expected the editor script to answer 200."
    )
    assert response.get_data(), "Expected the static route to return file bytes."
