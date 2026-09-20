import pytest

from aicad.explain import explain_check, explain_dim, find_symbol, substitute, utilisation, utilisation_colour
from aicad.joints import REGISTRY, parts_of

from conftest import SIZING as CASES


def test_substitute_puts_numbers_into_the_formula():
    assert substitute("4P / (pi D^2)", {"P": 50000, "D": 30}) == "4 × 50,000 / (π × 30²)"
    assert substitute("P / ((d2 - d) 2 t1)", {"P": 50000, "d2": 90, "d": 45, "t1": 33.75}) == \
        "50,000 / ((90 - 45) × 2 × 33.75)"


@pytest.mark.parametrize("name", list(CASES))
def test_every_dimension_of_every_joint_can_be_explained(name):
    joint = REGISTRY[name]
    d = joint.design(**CASES[name])
    for key in d.dims:
        text = explain_dim(d, joint, key)
        assert text.startswith(f"{key} (") and f"{d.dims[key]:g}" in text


@pytest.mark.parametrize("name", list(CASES))
def test_check_explanation_shows_the_numbers_and_the_verdict(name):
    joint = REGISTRY[name]
    d = joint.design(**CASES[name])
    for c in d.checks:
        text = explain_check(d, c)
        assert f"{c.stress_mpa:.1f} MPa" in text and ("pass" in text or "FAIL" in text)
        assert "×" in text or "/" in text


def test_knuckle_pin_explanation_names_bending_as_the_reason():
    joint = REGISTRY["knuckle"]
    d = joint.design(load_n=50_000, design_factor=1.0)
    text = explain_dim(d, joint, "d")
    assert "43.70" in text and "bending" in text


@pytest.mark.parametrize("question,key", [
    ("why is the pin 45 mm", "d"), ("explain d2", "d2"), ("why is the eye so thick", "t"),
    ("why is the pin head that wide", "d3"), ("what decides the rod diameter", "D"),
])
def test_questions_map_to_the_right_dimension(question, key):
    joint = REGISTRY["knuckle"]
    assert find_symbol(question, joint.design(load_n=50_000), joint) == key


@pytest.mark.parametrize("name", list(CASES))
def test_every_check_maps_to_real_parts(name):
    joint = REGISTRY[name]
    d = joint.design(**CASES[name])
    here = set(parts_of(joint, d.dims))
    for c in d.checks:
        parts = joint.CHECK_PARTS.get(c.name)
        assert parts, f"{c.name} is not mapped to any part"
        # a mapping may name parts a bigger design would have (the coupling lists six bolts),
        # but at least one named part must exist in this design
        assert here & set(parts), f"{c.name} maps to no part of this design"


def test_utilisation_names_the_governing_check():
    joint = REGISTRY["knuckle"]
    u = utilisation(joint.design(load_n=50_000), joint)
    assert u["knuckle_pin"][1] in ("pin bending", "pin double shear")
    assert u["collar"] == (None, None)


def test_colour_scale_runs_green_to_red():
    g, r = utilisation_colour(0.1), utilisation_colour(1.0)
    assert g[1] > g[0] and r[0] > r[1]
    assert utilisation_colour(None) == (0.62, 0.64, 0.68)   # grey: not checked


def test_utilisation_ignores_parts_this_design_does_not_have():
    """The coupling's checks name up to six bolts; a three-bolt design must still work."""
    joint = REGISTRY["flange_coupling"]
    d = joint.design(torque_nm=500)
    u = utilisation(d, joint)
    assert int(d.dims["n_bolts"]) == 3
    assert set(u) == set(parts_of(joint, d.dims))
    assert u["bolt_1"][1] in ("bolt shear", "bolt crushing")
