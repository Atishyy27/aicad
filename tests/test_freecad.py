"""Runs FreeCAD headless. Skipped automatically where FreeCAD is not installed."""
import json
import re

import pytest

from aicad.export import export_all
from aicad.freecad_pack import find_freecadcmd, run_pack
from aicad.joints import REGISTRY

pytestmark = pytest.mark.skipif(find_freecadcmd() is None, reason="FreeCAD not installed")


@pytest.mark.parametrize("name,kw", [("knuckle", {"load_n": 50_000}), ("sleeve_and_cotter", {"load_n": 50_000}),
                                     ("nut_bolt", {"bolt_size": 12})])
def test_freecad_pack(name, kw, tmp_path):
    joint = REGISTRY[name]
    design = joint.design(**kw)
    out = export_all(joint.build_parts(design.dims), design, joint, tmp_path, "test")
    r = run_pack(out, joint, design, "test")
    assert r["ok"], r
    assert r["parts"] == sorted(joint.PARTS)
    assert (out / f"{name}.FCStd").stat().st_size > 1000
    sheet = (out / "drawing.svg").read_text()
    for label in ("FRONT VIEW", "LEFT SIDE VIEW", "TOP VIEW (PLAN)", "ISOMETRIC", "FIRST ANGLE", joint.TITLE.upper()):
        assert label in sheet, label
    assert len(re.findall(r"<path", sheet)) > 20
    assert len(re.findall(r"<polygon", sheet)) >= 8, "dimension arrowheads missing"
    assert json.loads((out / "freecad_result.json").read_text())["ok"]
