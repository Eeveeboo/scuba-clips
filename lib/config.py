"""Configuration for the scuba-clips kit.

Every number the parts use lives here, with a default. To fit your own kit,
copy `config.example.toml` to `config.toml` in the repo root and edit the
values you want to override. `config.toml` is gitignored, and a key you leave
out keeps its default. An unknown key stops the load, so a typo cannot pass
quietly.

This module also holds the clip-envelope formulas: they turn a hose diameter
and the clip walls into the inner and outer diameters of the clip.

Importing this module reads `config.toml` once and builds `CONFIG`. Every
builder reads that one `CONFIG`, so one file sets the numbers for the whole kit.

Write the example file that lists every default:

    uv run python -m lib.config --example

Check that the committed example still matches the defaults:

    uv run python -m lib.config --check
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any, Final, TypeVar, get_origin, get_type_hints

import click

ROOT: Final = Path(__file__).resolve().parents[1]
CONFIG_PATH: Final = ROOT / "config.toml"
EXAMPLE_PATH: Final = ROOT / "config.example.toml"


def _field(default: Any, comment: str) -> Any:
    """A dataclass field, with the comment the example file prints."""
    return field(default=default, metadata={"comment": comment})


@dataclass(frozen=True)
class LibraryConfig:
    """Fit defaults shared by the geometry builders in lib/."""

    tessellation_resolution: int = _field(
        100, "Tessellation detail for cylinders; 100 is the old $fn = 100."
    )
    dimensional_resolution: float = _field(
        0.01, "Small length used as a lower bound in a shape check."
    )
    clip_tongue_wall_thickness: float = _field(
        2.0, "Flexible tongue wall thickness of a hose clip."
    )
    clip_radial_gap: float = _field(
        2.0, "Radial gap between the tongue and the outer wall."
    )
    clip_backbone_wall_thickness: float = _field(
        3.0, "Structural outer wall thickness of a hose clip."
    )


@dataclass(frozen=True)
class HardwareConfig:
    """The hoses, the fitting and the webbing this kit fits, and the hose-clip
    opening angles. Lengths are in millimetres, angles in degrees.

    A hose only has a high pressure or a low pressure. Each hose type still
    needs its own diameter: a size up or down changes how hard the clip lets
    the hose go.
    """

    inflator_tube_diameter: float = _field(
        27.0, "BCD inflator tube, held by the combo clip."
    )
    lp_inflator_hose_diameter: float = _field(
        12.5, "LP hose, first stage to the BCD inflator."
    )
    spg_hose_diameter: float = _field(8.0, "HP hose, first stage to the SPG.")
    regulator_fitting_diameter: float = _field(
        18.5, "LP hose fitting at the second stage, held by the octi clip."
    )
    regulator_fitting_length: float = _field(
        15.0, "Length of that fitting; the octi clip grips this length."
    )
    regulator_hose_diameter: float = _field(
        12.5, "LP hose, first stage to the second stage."
    )
    side_clip_hose_diameter: float = _field(
        12.5, "LP hose held by the lower octopus retaining clip."
    )
    tongue_back_angle: float = _field(
        60.0, "Tongue opening at the back (closed side) of a hose clip, in degrees."
    )
    backbone_front_angle: float = _field(
        90.0, "Opening at the front (open side) of a hose clip, in degrees."
    )
    opening_angle_offset: float = _field(
        15.0,
        "Extra front opening angle of the clip and of the relief cut, in degrees.",
    )
    webbing_shoulder_size: tuple[float, float] = _field(
        (50.0, 3.0), "Shoulder webbing [width, thickness]."
    )
    webbing_hip_size: tuple[float, float] = _field(
        (37.5, 5.0), "Hip webbing [width, thickness]."
    )


@dataclass(frozen=True)
class ComboClipConfig:
    """Tuning of the inflator + SPG combo clip."""

    clip_grip_length: float = _field(
        10.0, "Length of hose each clip grips, along the clip axis."
    )
    hp_spg_clip_distance: float = _field(
        22.5, "Clip centre distance, inflator clip to HP/SPG clip."
    )
    lpi_clip_distance: float = _field(
        30.0, "Clip centre distance, inflator clip to LPI clip."
    )
    hp_spg_lpi_clip_distance: float = _field(
        24.0, "Clip centre distance, HP/SPG clip to LPI clip; sets the triangle."
    )
    standoff_flare_percent: float = _field(
        100.0,
        "Standoff arm flare, percent: 0 is a straight arm, 100 reaches the "
        "inflator clip edge.",
    )


@dataclass(frozen=True)
class OctiClipConfig:
    """Tuning of the upper octopus retaining clip."""

    strap_block_height: float = _field(50.0, "Height of the webbing strap block.")
    slit_tightness: float = _field(
        4.5,
        "Clearance of the webbing slit over the webbing thickness.",
    )
    slit_flare_start: float = _field(
        5.0, "Z distance from the block centre where the slit flare begins."
    )
    regulator_clip_standoff: float = _field(
        18.0, "Regulator-fitting clip distance from the webbing."
    )
    hose_clip_grip_length: float = _field(
        10.0, "Length of hose the LP regulator-hose clip grips."
    )
    hose_clip_standoff: float = _field(
        0.0, "LP regulator-hose clip distance from the webbing."
    )
    standoff_offset: float = _field(
        6.0, "X displacement outwards of each standoff from the strap block edge."
    )


@dataclass(frozen=True)
class UpperInflatorRetainingClipConfig:
    """Tuning of the upper inflator retaining clip."""

    strap_block_height: float = _field(50.0, "Height of the webbing strap block.")
    slit_tightness: float = _field(
        4.5, "Clearance of the webbing slit over the webbing thickness."
    )
    slit_flare_start: float = _field(
        5.0, "Z distance from the block centre where the slit flare begins."
    )
    clip_grip_length: float = _field(20.0, "Length of inflator tube the clip grips.")


@dataclass(frozen=True)
class LowerOctiRetainingClipConfig:
    """Tuning of the lower octopus retaining clip."""

    block_height: float = _field(20.0, "Height of the webbing block.")
    webbing_clearance: float = _field(0.5, "Clearance, so the webbing slides in.")
    clip_grip_length: float = _field(
        10.0, "Length of hose each of the two clips grips."
    )


@dataclass(frozen=True)
class Config:
    """Every default, grouped by the section it is written under in TOML."""

    library: LibraryConfig = field(default_factory=LibraryConfig)
    hardware: HardwareConfig = field(default_factory=HardwareConfig)
    inflator_spg_combo_clip: ComboClipConfig = field(default_factory=ComboClipConfig)
    upper_octi_retaining_clip: OctiClipConfig = field(default_factory=OctiClipConfig)
    upper_inflator_retaining_clip: UpperInflatorRetainingClipConfig = field(
        default_factory=UpperInflatorRetainingClipConfig
    )
    lower_octi_retaining_clip: LowerOctiRetainingClipConfig = field(
        default_factory=LowerOctiRetainingClipConfig
    )


ConfigT = TypeVar("ConfigT")


def _value(raw: Any, annotation: Any, where: str) -> Any:
    """One TOML value, checked and converted to the type of its field."""
    if annotation is int:
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise TypeError(f"config.toml: {where} must be a whole number, got {raw!r}")
        return raw
    if annotation is float:
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise TypeError(f"config.toml: {where} must be a number, got {raw!r}")
        return float(raw)
    if get_origin(annotation) is tuple:
        ok = (
            isinstance(raw, (list, tuple))
            and len(raw) == 2
            and all(
                not isinstance(item, bool) and isinstance(item, (int, float))
                for item in raw
            )
        )
        if not ok:
            raise TypeError(
                f"config.toml: {where} must be [width, thickness], got {raw!r}"
            )
        return (float(raw[0]), float(raw[1]))
    raise TypeError(f"config.toml: {where} has an unsupported type {annotation!r}")


def _build(cls: type[ConfigT], data: dict[str, Any], name: str) -> ConfigT:
    """Build one frozen config dataclass from its TOML table and the defaults.

    The fields come from the dataclass itself: a new field needs no parser. A key
    the dataclass does not define stops the build, so a typo cannot pass quietly.
    """
    hints = get_type_hints(cls)
    unknown = sorted(set(data) - set(hints))
    if unknown:
        raise ValueError(
            f"config.toml: unknown key(s) in [{name}]: {', '.join(unknown)}"
        )

    defaults = cls()
    obj = cls.__new__(cls)
    for item, annotation in hints.items():
        if item not in data:
            value = getattr(defaults, item)
        elif is_dataclass(annotation):
            raw = data[item]
            if not isinstance(raw, dict):
                raise TypeError(f"config.toml: [{item}] must be a table")
            value = _build(annotation, raw, item)
        else:
            value = _value(data[item], annotation, f"{name}.{item}")
        # The dataclass is frozen, so set each field directly.
        object.__setattr__(obj, item, value)
    return obj


def load_config(path: Path | None = None) -> Config:
    """The defaults, with the values in `path` (default `config.toml`) applied."""
    if path is None:
        path = CONFIG_PATH
    raw: dict[str, Any] = {}
    if path.is_file():
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    return _build(Config, raw, "config")


CONFIG: Final = load_config()


def set_config(config: Config) -> None:
    """Replace the process-wide `CONFIG`.

    The web server is stateless: it calls this before it builds one model for
    one request. Every model module reads `CONFIG` at import time, so the caller
    must also drop the cached `lib.*` and `models.*` modules, as
    `tools/render.py` does. The module attribute is written through `globals()`,
    because `Final` forbids a typed reassignment.
    """
    globals()["CONFIG"] = config


def build_config(values: dict[str, Any]) -> Config:
    """A validated `Config` from a nested `section -> field -> value` mapping.

    A key the dataclass does not define stops the build, so a bad request cannot
    pass quietly. `_build` holds the one copy of that rule.
    """
    return _build(Config, values, "config")


MODELS_DIR: Final = ROOT / "models"


def model_names() -> list[str]:
    """The real clip model names: `all` and everything under `models/dev/` are
    left out."""
    names = []
    for path in sorted(MODELS_DIR.glob("*.py")):
        if path.stem in {"__init__", "all"}:
            continue
        names.append(path.stem)
    return names


def _display_label(name: str) -> str:
    """A human form of a field or model name: words, sentence case."""
    words = name.replace("_", " ").strip()
    if not words:
        return name
    return words[0].upper() + words[1:]


def _schema_type(annotation: Any) -> str:
    """The schema type name for one dataclass field annotation."""
    if annotation is int:
        return "int"
    if annotation is float:
        return "float"
    if get_origin(annotation) is tuple:
        return "float_list"
    raise TypeError(f"config: no schema type for {annotation!r}")


def _schema_default(value: Any) -> Any:
    """A dataclass default as a JSON value: a tuple becomes a list."""
    if isinstance(value, tuple):
        return [float(item) for item in value]
    return value


def config_schema() -> dict[str, Any]:
    """The editor schema: the real models and every config field, by reflection.

    The defaults come from `Config()`, not from a loaded `config.toml`, so the
    editor starts from the same numbers as `config.example.toml`.
    """
    config = Config()
    sections = []
    for section_field in fields(config):
        section = getattr(config, section_field.name)
        hints = get_type_hints(type(section))
        section_fields = []
        for item in fields(section):
            value = getattr(section, item.name)
            section_fields.append(
                {
                    "key": f"{section_field.name}.{item.name}",
                    "label": _display_label(item.name),
                    "type": _schema_type(hints[item.name]),
                    "default": _schema_default(value),
                    "comment": item.metadata.get("comment", ""),
                }
            )
        sections.append(
            {
                "name": section_field.name,
                "label": _display_label(section_field.name),
                "fields": section_fields,
            }
        )
    models = [{"name": name, "label": _display_label(name)} for name in model_names()]
    return {"models": models, "sections": sections}


def hose_clip_total_diameter(
    hose_diameter: float,
    backbone_wall_thickness: float | None = None,
    radial_gap: float | None = None,
    tongue_wall_thickness: float | None = None,
) -> float:
    """Outside diameter of an assembled clip: the flexible tongue, the radial
    gap and the structural outer wall.

    A wall left as `None` comes from the `[library]` config section at call
    time, not at import time, so the web server can change the wall for one
    request. A default of `CONFIG.library.*` would freeze the values when this
    module loads.
    """
    if backbone_wall_thickness is None:
        backbone_wall_thickness = CONFIG.library.clip_backbone_wall_thickness
    if radial_gap is None:
        radial_gap = CONFIG.library.clip_radial_gap
    if tongue_wall_thickness is None:
        tongue_wall_thickness = CONFIG.library.clip_tongue_wall_thickness
    return (
        hose_diameter + tongue_wall_thickness / 2 + radial_gap + backbone_wall_thickness
    )


def hose_clip_base_diameter(
    hose_diameter: float, tongue_wall_thickness: float
) -> float:
    """Outside diameter of the inner C, the flexible tongue: the hose plus half
    the tongue wall, so the tongue wall lies half inside and half outside the
    hose surface."""
    return hose_diameter + tongue_wall_thickness / 2


EXAMPLE_HEADER = """\
# scuba-clips configuration example.
#
# Copy this file to config.toml in the repo root and edit your own values.
# config.toml is gitignored. Every key below has this value as its default,
# so a key you leave out keeps that value.
# 
# All values are either in millimeters or degrees.
"""


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, tuple):
        return "[" + ", ".join(repr(item) for item in value) + "]"
    raise TypeError(f"cannot write {value!r} to TOML")


def render_example() -> str:
    """The example TOML text, from the defaults in this module."""
    config = Config()
    blocks = []
    for section_field in fields(config):
        section = getattr(config, section_field.name)
        lines = [f"[{section_field.name}]"]
        for item in fields(section):
            value = _toml_value(getattr(section, item.name))
            line = f"{item.name} = {value}"
            comment = item.metadata.get("comment")
            if comment:
                line += f"  # {comment}"
            lines.append(line)
        blocks.append("\n".join(lines))
    return EXAMPLE_HEADER + "\n" + "\n\n".join(blocks) + "\n"


def write_example(path: Path | None = None) -> Path:
    """Write the example file, default `config.example.toml` in the repo root."""
    if path is None:
        path = EXAMPLE_PATH
    path.write_text(render_example(), encoding="utf-8")
    return path


@click.command()
@click.option(
    "--example",
    is_flag=True,
    help="Write config.example.toml from the defaults in this module.",
)
@click.option(
    "--check",
    is_flag=True,
    help="Fail if config.example.toml does not match the defaults in this module.",
)
def main(example: bool, check: bool) -> None:
    """Write the example TOML that lists every default.

    Copy the example to config.toml and edit your own values.
    """
    if check:
        expected = render_example()
        current = (
            EXAMPLE_PATH.read_text(encoding="utf-8") if EXAMPLE_PATH.exists() else ""
        )
        if current != expected:
            raise click.ClickException(
                f"{EXAMPLE_PATH.name} is stale. Run `uv run cli config-example` and commit the result."
            )
        click.echo(f"config.py: {EXAMPLE_PATH.name} is up to date")
        return
    if not example:
        raise click.UsageError("pass --example to write config.example.toml")
    path = write_example()
    click.echo(f"config.py: wrote {path}")


if __name__ == "__main__":
    main()
