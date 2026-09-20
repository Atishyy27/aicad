"""Finite-element checks. Skipped where FreeCAD is missing; slow (meshing and solving)."""
import math

import pytest

from aicad import fea
from aicad.export import export_all
from aicad.joints import REGISTRY

pytestmark = pytest.mark.skipif(not fea.available(), reason="FreeCAD not installed")


def test_solver_reproduces_a_bar_in_tension(tmp_path):
    """Validation: a bar pulled by a known force must give load over area."""
    import cadquery as cq
    d, L, P = 20.0, 100.0, 10_000.0
    (tmp_path / "parts").mkdir()
    bar = cq.Workplane("XY").circle(d / 2).extrude(L)
    cq.exporters.export(bar, str(tmp_path / "parts" / "bar.step"))

    class FakeJoint:
        NAME = "bar_test"

    class FakeCheck:
        name = "rod tension"
        stress_mpa = P / (math.pi * (d / 2) ** 2)
        allowable_mpa = 75.0

    class FakeDesign:
        dims = {"d": d, "D": d}
        checks = [FakeCheck()]
        load_n = P

    fea.CASES["bar_test"] = {
        "part": "bar", "fix": {"kind": "plane_normal", "axis": "z", "pick": "min"},
        "load": {"kind": "plane_end", "axis": "z", "pick": "max"}, "direction": [0, 0, 1],
        "compare": "rod tension", "note": "validation bar",
    }
    try:
        r = fea.run(FakeJoint, FakeDesign, tmp_path)
    finally:
        fea.CASES.pop("bar_test")
    assert r["ok"], r
    assert r["mesh_nodes"] > 200
    assert r["max_von_mises"] == pytest.approx(FakeCheck.stress_mpa, rel=0.05), r


@pytest.mark.parametrize("name,kw", [("knuckle", {"load_n": 50_000})])
def test_real_part_is_in_the_same_range_as_the_hand_calculation(name, kw, tmp_path):
    joint = REGISTRY[name]
    design = joint.design(**kw)
    export_all(joint.build_parts(design.dims), design, joint, tmp_path, "fea test")
    r = fea.run(joint, design, tmp_path)
    assert r["ok"], r
    # the formula ignores the stress concentration at the bore, so the finite element
    # answer should be higher, but not wildly so
    assert 0 < r["difference_pct"] < 60, r
    assert r["hand_check"] == "rod tension"


def test_unknown_joint_says_so():
    class J:
        NAME = "nothing_like_this"
    assert fea.run(J, None, ".")["ok"] is False
