"""Tests for the request parsing that feeds generation."""

from __future__ import annotations

from web.service import scad_response, schema_response

MODEL = "upper_inflator_retaining_clip"


def test_scad_response__reads_a_comma_separated_webbing_list() -> None:
    """The editor sends a webbing size as two comma-separated numbers.

    The value must reach the model as two floats and change the geometry, so the
    list form in the URL is usable.

    If this test fails, then the list value did not parse or did not reach the
    source.
    """
    default = scad_response({"model": [MODEL]})
    changed = scad_response(
        {"model": [MODEL], "hardware.webbing_shoulder_size": ["60.0,4.0"]}
    )
    assert changed.status == 200, "Expected a comma-separated list to be accepted."
    assert changed.body != default.body, (
        "Expected a changed webbing size to change the SCAD source."
    )


def test_scad_response__rejects_an_unknown_model_field_or_value() -> None:
    """Three bad requests arrive: a model that does not exist, a field that does not exist, and a number that is not a number.

    Each request must answer 400 with a short message, and none may answer with
    a wrong clip. A wrong result would ship the wrong STL to a user who made a
    typo.

    If this test fails, then a bad request returned a part or leaked an
    internal detail.
    """
    cases = [
        ({"model": ["no_such_model"]}, "unknown model"),
        ({"model": [MODEL], "bogus.field": ["1"]}, "unknown field"),
        ({"model": [MODEL], "hardware.inflator_tube_diameter": ["abc"]}, "bad value"),
    ]
    for query, fragment in cases:
        response = scad_response(query)
        assert response.status == 400, (
            f"Expected a bad request {query!r} to answer 400, got {response.status}."
        )
        assert fragment in response.body, (
            f"Expected the answer to explain {fragment!r}, got {response.body!r}."
        )
        assert "Traceback" not in response.body, (
            "Expected the answer to hide the stack trace."
        )


def test_schema_response__lists_the_models_and_fields_as_json() -> None:
    """The client asks for the schema, because it must not hard-code the fields.

    The answer must be JSON with a status of 200, one entry per real model, and
    a section for every config group.

    If this test fails, then the client cannot build the form from the server.
    """
    response = schema_response()
    assert response.status == 200, "Expected the schema request to answer 200."
    assert response.content_type.startswith("application/json"), (
        "Expected the schema to answer as JSON."
    )
    assert '"models"' in response.body and '"sections"' in response.body, (
        "Expected the schema body to hold the models and the sections."
    )
