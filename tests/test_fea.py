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


def test_every_fea_case_names_dimensions_that_really_exist():
    """A face rule that refers to a dimension by the wrong name fails deep inside FreeCAD,
    minutes into a run. This catches it in milliseconds."""
    from aicad.fea import CASES
    from aicad.joints import REGISTRY
    from conftest import SIZING
    for joint, case in CASES.items():
        dims = REGISTRY[joint].design(**SIZING[joint]).dims
        for rule in (case["fix"], case["load"]):
            for key in list(rule.get("at", {})) + ([rule["dia"]] if rule.get("dia") else []):
                assert key in dims, f"{joint}: face rule names {key}, which is not a dimension"


def test_the_gib_joint_is_held_at_the_wall_the_shear_check_is_about():
    """The rod is clamped at the far wall of the slot, which is the metal the rod-end shear
    check says could tear out. If that moved, the run would be measuring something else."""
    from aicad.fea import CASES
    from aicad.joints import REGISTRY
    case = CASES["gib_and_cotter"]
    dims = REGISTRY["gib_and_cotter"].design(load_n=50_000).dims
    target = sum(dims[k] * w for k, w in case["fix"]["at"].items())
    assert target == dims["xs"] + dims["b"] / 2
    assert dims["rod_end_len"] - target == dims["a"]
