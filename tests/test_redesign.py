import pytest

from aicad.joints import REGISTRY
from aicad.optimise import compare
from aicad.parse import Spec
from aicad.redesign import follow_up, max_load

CASES = {"knuckle": Spec(joint="knuckle", load_n=50_000), "cotter": Spec(joint="cotter", load_n=35_000),
         "sleeve_and_cotter": Spec(joint="sleeve_and_cotter", load_n=50_000),
         "nut_bolt": Spec(joint="nut_bolt", load_n=20_000)}


@pytest.mark.parametrize("name", list(CASES))
def test_max_load_is_exactly_the_limit(name):
    joint = REGISTRY[name]
    design = joint.design(**CASES[name].design_kwargs())
    P, governing = max_load(joint, design)
    at = joint._checks(P * 0.999, design.dims, design.stresses)
    over = joint._checks(P * 1.01, design.dims, design.stresses)
    assert all(c.passed for c in at)
    assert any(not c.passed for c in over)
    assert governing in [c.name for c in over if not c.passed]


def test_limit_question_on_a_design():
    r = follow_up(CASES["knuckle"], "how much load can this take", mode="rules")
    # eye shear binds first now: the eye is grown to the smallest size that passes, so it sits
    # closest to its allowable of any check
    assert r.kind == "limit" and r.governing == "eye shear"
    # the design carries more than the load it was sized for: that headroom is the design margin
    assert r.value > 50_000 and r.value < 50_000 * 1.6


def test_change_load_moves_dimensions_and_reports_them():
    before = REGISTRY["knuckle"].design(**CASES["knuckle"].design_kwargs())
    r = follow_up(CASES["knuckle"], "make it 80 kN", mode="rules")
    assert r.kind == "change" and r.spec.load_n == 80_000
    after = REGISTRY["knuckle"].design(**r.spec.design_kwargs())
    assert after.dims["D"] > before.dims["D"]
    assert any(c.startswith(f"D: {before.dims['D']:g} -> {after.dims['D']:g}") for c in r.changes)


def test_change_stress_only_changes_that_stress():
    r = follow_up(CASES["knuckle"], "use shear 50 MPa", mode="rules")
    assert r.kind == "change" and r.spec.shear_mpa == 50 and r.spec.load_n == 50_000


def test_change_that_needs_no_new_sizes_says_so():
    # crushing is nowhere near governing on this joint, so lowering it changes nothing.
    # shear would: it drives the eye, which is sized right down to its limit.
    r = follow_up(CASES["knuckle"], "use crushing 120 MPa", mode="rules")
    assert "No dimension had to change" in r.message


def test_switching_joint_keeps_the_load():
    r = follow_up(CASES["knuckle"], "change it to a cotter joint", mode="rules")
    assert r.spec.joint == "cotter" and r.spec.load_n == 50_000


def test_joint_word_alone_does_not_switch_the_joint():
    r = follow_up(CASES["knuckle"], "what load can a cotter joint take", mode="rules")
    assert r.kind == "limit"


def test_why_question_explains():
    r = follow_up(CASES["knuckle"], "why is the pin 45 mm", mode="rules")
    assert r.kind == "explain" and "bending" in r.message


def test_nonsense_is_unclear_not_a_crash():
    assert follow_up(CASES["knuckle"], "blah blah", mode="rules").kind == "unclear"


def test_margin_request_lowers_utilisation():
    before = REGISTRY["knuckle"].design(load_n=50_000, design_factor=1.0)
    r = follow_up(Spec(joint="knuckle", load_n=50_000, design_factor=1.0), "add more margin", mode="rules")
    assert r.kind == "change" and r.spec.design_factor > 1
    after = REGISTRY["knuckle"].design(**r.spec.design_kwargs())
    worst = lambda d: max(c.stress_mpa / c.allowable_mpa for c in d.checks)
    assert worst(after) < worst(before) - 0.1


def test_too_small_bolt_says_what_to_use_instead():
    d = REGISTRY["nut_bolt"].design(load_n=80_000, bolt_size=12)
    assert not d.all_passed
    assert any("too small" in n and ("M36" in n or "bolts" in n) for n in d.notes), d.notes


def test_optimise_picks_a_passing_material_with_nothing_lighter():
    rows = [r for r in compare(CASES["cotter"]) if r.get("ok")]
    r = follow_up(CASES["cotter"], "make it lighter", mode="rules")
    assert r.kind == "change"
    best = min(rows, key=lambda x: x["mass_kg"])
    assert best["material"] in r.message
    new = REGISTRY["cotter"].design(**r.spec.design_kwargs())
    assert new.all_passed


def test_cheapest_uses_cost_not_mass():
    rows = [r for r in compare(CASES["cotter"]) if r.get("ok")]
    r = follow_up(CASES["cotter"], "cheapest material please", mode="rules")
    assert min(rows, key=lambda x: x["cost_inr"])["material"] in r.message
