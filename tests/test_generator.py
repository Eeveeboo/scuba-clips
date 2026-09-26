"""Tests for stateless SCAD generation."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from api.support.generator import render_scad
from lib.config import Config, build_config, hose_clip_total_diameter, set_config

MODEL = "upper_inflator_retaining_clip"


def test_render_scad__changed_values_change_the_source_and_defaults_repeat() -> None:
    """The editor asks for the default part, then a wider inflator tube, then the default again.

    A changed value must reach the geometry, so the source must differ. Asking
    for the defaults again must reproduce the first source, so one request
    cannot leave a value behind for the next one.

    If this test fails, then a value did not reach the model, or a later request
    returned an earlier request's source.
    """
    default_first = render_scad(MODEL, {})
    changed = render_scad(MODEL, {"hardware": {"inflator_tube_diameter": 30.0}})
    default_again = render_scad(MODEL, {})

    assert changed != default_first, (
        "Expected a changed inflator tube diameter to change the SCAD source."
    )
    assert default_again == default_first, (
        "Expected the same defaults to reproduce the same SCAD source."
    )


def test_render_scad__concurrent_values_do_not_collide() -> None:
    """Eight threads ask for eight different inflator tube diameters at the same time.

    Generation shares one process-wide config and one model import cache, so
    without the lock the threads would overwrite each other's config. Each
    answer must equal the same answer generated alone.

    If this test fails, then a concurrent request returned another request's
    source.
    """
    values = [
        {"hardware": {"inflator_tube_diameter": 20.0 + index}} for index in range(8)
    ]
    expected = [render_scad(MODEL, item) for item in values]

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda item: render_scad(MODEL, item), values))

    for index, (got, want) in enumerate(zip(results, expected)):
        assert got == want, (
            f"Expected concurrent request {index} to return its own source; "
            "another thread's value leaked in."
        )


def test_hose_clip_total_diameter__reads_changed_library_wall_at_call_time() -> None:
    """An operator sets a thicker backbone wall in the library section, then builds a clip.

    The total diameter must use the current `[library]` wall, not the wall that
    was bound when `lib/config.py` first loaded. The web server changes that
    wall for one request.

    If this test fails, then the wall was frozen at import time and a library
    change does not reach the diameter.
    """
    set_config(build_config({"library": {"clip_backbone_wall_thickness": 5.0}}))
    try:
        expected = 27.0 + 2.0 / 2 + 2.0 + 5.0
        assert hose_clip_total_diameter(27.0) == expected, (
            "Expected the backbone wall to come from the current CONFIG at call time."
        )
    finally:
        set_config(Config())
