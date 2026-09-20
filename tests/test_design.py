import math

import pytest

from aicad.joints import REGISTRY, cotter, knuckle, nut_bolt
from conftest import SIZING, SWEEP, cases

LOADS_KN = [1, 2, 5, 10, 20, 50, 100, 150, 200, 300]


# ---------------------------------------------------------------- knuckle

def test_knuckle_50kn_rod_from_tension():
    r = knuckle.design(load_n=50_000, design_factor=1.0)
    assert r.raw["rod_tension"] == pytest.approx(math.sqrt(4 * 50_000 / (math.pi * 75)))
    assert r.raw["rod_tension"] == pytest.approx(29.13, abs=0.01)
    assert r.dims["D"] == 30


def test_knuckle_50kn_pin_is_raised_for_bending():
    r = knuckle.design(load_n=50_000, design_factor=1.0)
    # sigma_b = 16P(0.75/3 + 1.25/4)/(pi d^2) <= 75  ->  d >= 43.70 -> preferred 45
    assert r.raw["pin_bending"] == pytest.approx(43.70, abs=0.01)
    assert r.dims["d"] == 45
    assert r.dims["d2"] == 90 and r.dims["t"] == 56.25 and r.dims["t1"] == 33.75
    assert "governed by pin bending" == r.rules["d"]
    assert any("bending" in n for n in r.notes)


def test_knuckle_check_only_mode_keeps_pin_equal_to_rod_and_reports_bending_fail():
    r = knuckle.design(load_n=50_000, bending_mode="check_only", design_factor=1.0)
    assert r.dims["d"] == 30
    bending = next(c for c in r.checks if c.name == "pin bending")
    assert not bending.passed
    assert all(c.passed for c in r.checks if c.name != "pin bending")


def test_knuckle_low_shear_stress_makes_shear_govern_over_rod():
    r = knuckle.design(load_n=50_000, shear_mpa=20, bending_mode="check_only", design_factor=1.0)
    assert r.dims["D"] == 30 and r.dims["d"] == 40


def test_knuckle_diameter_only_skips_checks():
    r = knuckle.design(rod_diameter_mm=30)
    assert r.dims["d"] == 30 and r.dims["d2"] == 60 and r.checks == []


def test_knuckle_given_small_rod_fails_rod_tension():
    r = knuckle.design(load_n=50_000, rod_diameter_mm=16)
    assert "rod tension" in [c.name for c in r.checks if not c.passed]


# ---------------------------------------------------------------- cotter

def test_cotter_50kn_rod_and_proportions():
    r = cotter.design(load_n=50_000, design_factor=1.0)
    assert r.dims["d"] == 30
    # proportions are rounded up to whole mm before any adjustment
    assert r.dims["b"] >= math.ceil(1.6 * 30)
    assert r.dims["t"] >= math.ceil(0.31 * 30)
    assert r.all_passed


def test_cotter_walls_are_real():
    for kn in LOADS_KN:
        d = cotter.design(load_n=kn * 1000).dims
        assert d["d2"] >= d["d1"] + 4 and d["d4"] >= d["d2"] + 4 and d["d3"] >= d["d1"] + 4


def test_cotter_adjustments_are_explained():
    r = cotter.design(load_n=50_000, crushing_mpa=90)
    assert r.all_passed
    assert any("raised from" in n for n in r.notes)


# ---------------------------------------------------------------- nut bolt

def test_bolt_size_from_load_is_smallest_that_passes():
    r = nut_bolt.design(load_n=20_000, design_factor=1.0)
    # needs 20000/80 = 250 mm^2; M20 has 245 (too small), M24 has 353
    assert r.raw["stress_area_needed"] == pytest.approx(250)
    assert r.dims["d"] == 24
    assert r.all_passed


def test_bolt_given_size_uses_table_values():
    r = nut_bolt.design(bolt_size=12)
    assert (r.dims["s"], r.dims["k"], r.dims["m"]) == (18, 7.5, 10.8)
    assert r.dims["grip"] == 24  # default 2 x d
    assert r.dims["L"] % 5 == 0 and r.dims["L"] >= 24 + 2.5 + 10.8 + 2 * 1.75


def test_bolt_unknown_size_is_rejected():
    with pytest.raises(ValueError):
        nut_bolt.design(bolt_size=11)


def test_bolt_too_big_load_is_rejected_with_advice():
    with pytest.raises(ValueError, match="at least 2 bolts"):
        nut_bolt.design(load_n=100_000)


# ---------------------------------------------------------------- all joints

@pytest.mark.parametrize("name,kw", cases(REGISTRY))
def test_every_check_passes_for_every_tool_sized_design(name, kw):
    r = REGISTRY[name].design(**kw)
    failing = [f"{c.name} {c.stress_mpa:.1f}>{c.allowable_mpa}" for c in r.checks if not c.passed]
    assert not failing, failing


@pytest.mark.parametrize("name", list(REGISTRY))
@pytest.mark.parametrize("bad", [0, -5])
def test_non_positive_input_is_rejected(name, bad):
    field = "torque_nm" if name == "flange_coupling" else "load_n"
    with pytest.raises(ValueError):
        REGISTRY[name].design(**{field: bad})


@pytest.mark.parametrize("name", list(REGISTRY))
def test_nothing_given_is_rejected(name):
    with pytest.raises(ValueError):
        REGISTRY[name].design()


@pytest.mark.parametrize("name", list(REGISTRY))
def test_unverified_flag_is_carried(name):
    r = REGISTRY[name].design(**SIZING[name])
    assert r.verified_against_book is False


# ---------------------------------------------------------------- design margin

@pytest.mark.parametrize("name", list(REGISTRY))
def test_margin_leaves_the_checks_below_their_limits(name):
    """Without margin the tool sizes right up to the allowed stress, which is why every part
    looked red. The default 1.25 factor sizes for a bigger load and reports at the real one."""
    from conftest import SIZING
    tight = REGISTRY[name].design(**SIZING[name], design_factor=1.0)
    safe = REGISTRY[name].design(**SIZING[name])
    worst = lambda d: max((c.stress_mpa / c.allowable_mpa for c in d.checks), default=0)
    assert safe.design_factor == 1.25
    assert worst(safe) <= worst(tight) + 1e-9
    assert worst(safe) <= 0.85 or name == "nut_bolt"   # bolts jump in standard steps
    assert all(c.passed for c in safe.checks)


def test_margin_is_explained_in_the_notes():
    d = REGISTRY["knuckle"].design(load_n=50_000)
    assert any("Sized for 1.25 x the given load" in n for n in d.notes)


@pytest.mark.parametrize("factor", [1.0, 1.5, 2.0])
def test_bigger_factor_means_bigger_parts(factor):
    d = REGISTRY["knuckle"].design(load_n=50_000, design_factor=factor)
    base = REGISTRY["knuckle"].design(load_n=50_000, design_factor=1.0)
    assert d.dims["d"] >= base.dims["d"]
