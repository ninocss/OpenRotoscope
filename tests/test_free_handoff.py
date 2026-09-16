from __future__ import annotations

from pathlib import Path

from openroto.free_handoff import FREE_EXPORT_RE, fusion_comp_text


def test_free_export_filename_contract():
    match = FREE_EXPORT_RE.match(
        "OpenRotoFree_clipABC-7_n42_w1920_h1080_f25000_00000000.png"
    )
    assert match is not None
    assert match.group("session") == "clipABC-7"
    assert int(match.group("count")) == 42
    assert int(match.group("width")) == 1920
    assert int(match.group("height")) == 1080
    assert int(match.group("fps")) == 25000


def test_free_comp_points_loader_at_final_matte_sequence(tmp_path: Path):
    first_mask = tmp_path / "matte" / "final" / "matte_00000000.png"
    text = fusion_comp_text(first_mask, frame_count=12, width=1280, height=720)
    assert "Composition {" in text
    assert "OpenRotoMask = Loader" in text
    assert str(first_mask).replace("\\", "\\\\") in text
    assert "Length = 12" in text
    assert "GlobalEnd = 11" in text
    assert "Width = Input { Value = 1280 }" in text
    assert "Height = Input { Value = 720 }" in text
    assert 'EffectMask = Input { SourceOp = "OpenRotoMask", Source = "Output" }' in text
