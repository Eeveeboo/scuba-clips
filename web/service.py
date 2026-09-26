"""The schema and SCAD answers, as plain `Response` values.

The two Vercel entry points and the local dev server share this module, so each
transport keeps only its own plumbing. No function here touches a socket.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from lib.config import config_schema, model_names
from web.generator import render_scad

TEXT = "text/plain; charset=utf-8"
JSON = "application/json; charset=utf-8"


@dataclass(frozen=True)
class Response:
    """One HTTP answer: status, content type and body text or bytes."""

    status: int
    content_type: str
    body: str | bytes


def _error(message: str) -> Response:
    """A short 400 answer. It never holds a path or a stack trace."""
    return Response(status=400, content_type=TEXT, body=f"{message}\n")


def schema_response() -> Response:
    """The editor schema as JSON: every real model and every config field."""
    return Response(status=200, content_type=JSON, body=json.dumps(config_schema()))


def _field_types() -> dict[str, str]:
    """A flat map of `<section>.<field>` to its schema type name."""
    types: dict[str, str] = {}
    for section in config_schema()["sections"]:
        for item in section["fields"]:
            types[item["key"]] = item["type"]
    return types


def _parse_value(key: str, raw: str, type_name: str) -> Any:
    """One query string as the Python value of its field type."""
    if type_name == "int":
        try:
            return int(raw)
        except ValueError:
            raise ValueError(f"bad value for {key}: {raw}") from None
    if type_name == "float":
        try:
            return float(raw)
        except ValueError:
            raise ValueError(f"bad value for {key}: {raw}") from None
    if type_name == "float_list":
        parts = raw.split(",")
        if len(parts) != 2:
            raise ValueError(f"bad value for {key}: {raw}")
        try:
            return [float(part) for part in parts]
        except ValueError:
            raise ValueError(f"bad value for {key}: {raw}") from None
    raise ValueError(f"bad value for {key}: {raw}")


def _parse_values(query: Mapping[str, Sequence[str]]) -> tuple[str, dict[str, Any]]:
    """The model name and the nested values mapping from the query keys.

    An unknown model or an unknown field is a `ValueError`, so the answer stays
    a short 400 and never a wrong result.
    """
    model_values = query.get("model")
    if not model_values:
        raise ValueError("missing model")
    model_name = model_values[0]
    if model_name not in model_names():
        raise ValueError(f"unknown model: {model_name}")

    types = _field_types()
    values: dict[str, Any] = {}
    for key, raw_values in query.items():
        if key == "model":
            continue
        type_name = types.get(key)
        if type_name is None:
            raise ValueError(f"unknown field: {key}")
        value = _parse_value(key=key, raw=raw_values[0], type_name=type_name)
        section, field = key.split(".", 1)
        section_values = values.setdefault(section, {})
        section_values[field] = value
    return model_name, values


def scad_response(query: Mapping[str, Sequence[str]]) -> Response:
    """The SCAD source for one model request.

    The query holds `model` and zero or more `<section>.<field>=<value>` keys.
    An unknown model, an unknown field or a bad value is a 400. An omitted key
    takes the default.
    """
    try:
        model_name, values = _parse_values(query)
        body = render_scad(model_name=model_name, values=values)
    except (ValueError, TypeError) as exc:
        return _error(str(exc))
    return Response(status=200, content_type=TEXT, body=body)
