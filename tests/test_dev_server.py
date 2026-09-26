"""Tests for the static file answers of the local dev server."""

from __future__ import annotations

from pathlib import Path

from api.support import dev_server


def test_static_response__returns_raw_bytes_for_a_non_utf8_file(
    tmp_path: Path, monkeypatch
) -> None:
    """A vendored binary file holds bytes that are not valid UTF-8.

    The static answer must hold those bytes unchanged, because the browser
    needs the exact file to render the STL, and a replaced byte makes the file
    useless.

    If this test fails, then the static answer changed the file bytes.
    """
    payload = b"\x00\xff\xfe\x80\x01 wasm"
    (tmp_path / "vendor.bin").write_bytes(payload)
    monkeypatch.setattr(dev_server, "PUBLIC_DIR", tmp_path)
    response = dev_server._static_response("/vendor.bin")
    assert response.status == 200, "Expected the file to answer 200."
    assert isinstance(response.body, bytes), (
        "Expected a binary body for a binary file."
    )
    assert response.body == payload, (
        "Expected the served bytes to equal the file bytes."
    )
