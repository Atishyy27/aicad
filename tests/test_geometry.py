import itertools

import cadquery as cq
import pytest

from aicad.export import export_all
from aicad.joints import REGISTRY, knuckle, parts_of

from conftest import SIZING as CASES
from conftest import SMALL


@pytest.fixture(scope="module", params=list(CASES))
def built(request):
    joint = REGISTRY[request.param]
    design = joint.design(**CASES[request.param])
    return joint, design, joint.build_parts(design.dims)


def test_parts_match_the_data_file(built):
    joint, design, parts = built
    assert list(parts) == parts_of(joint, design.dims)


def test_each_part_is_one_valid_solid(built):
    _, _, parts = built
    for name, wp in parts.items():
        solids = wp.solids().vals()
        assert len(solids) == 1, f"{name} has {len(solids)} solids"
        assert solids[0].isValid(), name
        assert solids[0].Volume() > 0, name


def test_no_two_parts_overlap(built):
    _, _, parts = built
    for (a, wa), (b, wb) in itertools.combinations(parts.items(), 2):
        va, vb = wa.val(), wb.val()
        common = va.intersect(vb)
        overlap = common.Volume() if common.Solids() else 0.0
        assert overlap < 1e-4 * min(va.Volume(), vb.Volume()), f"{a} and {b} overlap by {overlap:.3f} mm^3"


def test_overlap_check_can_fail():
    """Mutation guard: a pin pushed 1 mm sideways must be caught."""
    parts = knuckle.build_parts(knuckle.design(load_n=50_000).dims)
    moved = parts["knuckle_pin"].val().translate((1, 0, 0))
    assert moved.intersect(parts["fork"].val()).Volume() > 100


def test_knuckle_eye_can_swing():
    design = knuckle.design(load_n=50_000)
    dims = design.dims
    parts = knuckle.build_parts(dims)
    assert parts["single_eye_rod"].val().BoundingBox().xmax == pytest.approx(dims["d2"] / 2, abs=1e-3)
    probe = cq.Workplane().box(dims["clearance"] * 0.9, 1, 1).translate(
        (dims["d2"] / 2 + dims["clearance"] * 0.45, 0, 0)).val()
    assert probe.intersect(parts["fork"].val()).Volume() < 1e-6


def test_cotter_sits_in_both_slots():
    design = REGISTRY["cotter"].design(load_n=50_000)
    parts = REGISTRY["cotter"].build_parts(design.dims)
    cot = parts["cotter"].val().BoundingBox()
    d4 = design.dims["d4"]
    assert cot.zmax > d4 / 2 and cot.zmin < -d4 / 2  # passes right through the socket collar
    assert cot.ylen == pytest.approx(design.dims["t"], abs=1e-3)


def test_bolt_stack_order():
    design = REGISTRY["nut_bolt"].design(bolt_size=12, grip_mm=40)
    parts = REGISTRY["nut_bolt"].build_parts(design.dims)
    washer = parts["washer"].val().BoundingBox()
    nut = parts["nut"].val().BoundingBox()
    bolt = parts["bolt"].val().BoundingBox()
    assert washer.zmin == pytest.approx(40) and nut.zmin == pytest.approx(washer.zmax)
    assert bolt.zmax > nut.zmax  # thread sticks out past the nut


@pytest.mark.parametrize("name", list(CASES))
def test_small_design_builds(name):
    joint = REGISTRY[name]
    design = joint.design(**SMALL[name])
    assert all(p.val().isValid() for p in joint.build_parts(design.dims).values())


def test_export_writes_everything_and_assembly_keeps_parts_separate(built, tmp_path):
    joint, design, parts = built
    out = export_all(parts, design, joint, tmp_path, request="test request")
    names = parts_of(joint, design.dims)
    for name in names:
        again = cq.importers.importStep(str(out / "parts" / f"{name}.step"))
        assert len(again.solids().vals()) == 1
    assy = cq.importers.importStep(str(out / "assembly.step"))
    assert len(assy.solids().vals()) == len(names)
    html = (out / "viewer.html").read_text()
    assert "data:model/gltf-binary;base64," in html
    assert "<script type=\"module\" src=" not in html, "viewer must not load its script from the internet"
    assert "UNVERIFIED" in (out / "report.md").read_text()


def test_sleeve_cotters_pass_through_sleeve_and_both_rods():
    joint = REGISTRY["sleeve_and_cotter"]
    design = joint.design(load_n=50_000)
    parts = joint.build_parts(design.dims)
    d1 = design.dims["d1"]
    for side in ("cotter_left", "cotter_right"):
        bb = parts[side].val().BoundingBox()
        assert bb.zmax > d1 / 2 and bb.zmin < -d1 / 2, side
    left, right = parts["rod_left"].val().BoundingBox(), parts["rod_right"].val().BoundingBox()
    assert left.xmax < 0 < right.xmin  # rod ends do not touch: there is a gap in the middle


@pytest.mark.parametrize("name", list(CASES))
def test_every_joint_has_drawing_dimensions_on_real_views(name):
    joint = REGISTRY[name]
    specs = joint.drawing_dims(joint.design(**CASES[name]).dims)
    assert len(specs) >= 4
    assert {s["view"] for s in specs} <= {"FRONT VIEW", "LEFT SIDE VIEW", "TOP VIEW (PLAN)"}
    for s in specs:
        assert s["orient"] in ("h", "v") and s["text"]


@pytest.mark.parametrize("name", list(CASES))
def test_exploded_view_separates_every_part(name):
    joint = REGISTRY[name]
    design = joint.design(**CASES[name])
    parts = joint.build_parts(design.dims)
    moves = joint.explode(design.dims)
    assert set(moves) == set(parts)
    moved = {n: p.val().translate(moves[n]) for n, p in parts.items()}
    for (a, va), (b, vb) in itertools.combinations(moved.items(), 2):
        common = va.intersect(vb)
        assert (common.Volume() if common.Solids() else 0.0) < 1e-6, f"{a} and {b} still touch when exploded"
