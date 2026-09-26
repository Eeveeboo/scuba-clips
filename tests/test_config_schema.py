"""Tests for the editor schema built from the config dataclasses."""

from __future__ import annotations

import tomllib
from dataclasses import fields

from lib.config import Config, config_schema, model_names, render_example


def test_config_schema__covers_every_dataclass_field_with_example_defaults() -> None:
    """The schema is built from the dataclasses, and the example TOML is built from the same defaults.

    Every field must appear under its own section, in declaration order, and
    each schema default must equal the value in `render_example()`. The example
    file is the committed record of the defaults, so a schema that disagrees
    would show the editor a different starting number.

    If this test fails, then a dataclass field is missing from the schema, or a
    schema default disagrees with config.example.toml.
    """
    example = tomllib.loads(render_example())
    schema = config_schema()
    by_name = {section["name"]: section for section in schema["sections"]}

    config = Config()
    for section_field in fields(config):
        section = by_name[section_field.name]
        declared = [item.name for item in fields(getattr(config, section_field.name))]
        keys = [item["key"].split(".", 1)[1] for item in section["fields"]]
        assert keys == declared, (
            f"Expected schema section {section_field.name!r} to list every field "
            f"in declaration order, got {keys}."
        )
        for item in section["fields"]:
            field_name = item["key"].split(".", 1)[1]
            assert item["default"] == example[section_field.name][field_name], (
                f"Expected the {item['key']} default to match config.example.toml."
            )


def test_model_names__excludes_the_plate_and_the_dev_models() -> None:
    """The editor offers one real clip at a time, not the plate or the dev tools.

    The plate and `models/dev/` are print and test aids, and the client cannot
    render them as a single clip. The list must hold the four real parts.

    If this test fails, then a dev model or the plate leaked into the editor, or
    a real part is missing.
    """
    names = model_names()
    assert "all" not in names, "Expected the print plate to stay out of the model list."
    assert "dev" not in " ".join(names), (
        "Expected no model under models/dev/ to appear in the model list."
    )
    assert "upper_inflator_retaining_clip" in names, (
        "Expected the real clip models to appear in the model list."
    )
