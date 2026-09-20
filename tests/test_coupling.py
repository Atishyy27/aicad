import math

import pytest

from aicad.joints import REGISTRY, flange_coupling, parts_of
from aicad.parse import parse_rules

J = flange_coupling


def test_torque_from_power_and_speed():
    d = J.design(power_kw=20, speed_rpm=1440)
    assert d.dims["torque_nmm"] == pytest.approx(9.5493e6 * 20 / 1440, rel=1e-6)
    assert any("Torque from power and speed" in n for n in d.notes)


def test_shaft_from_torsion_then_rounded_up():
    d = J.design(torque_nm=500, design_factor=1.0)
    raw = (16 * 500_000 / (math.pi * 60)) ** (1 / 3)
    assert d.raw["shaft_torsion"] == pytest.approx(raw)
    assert d.dims["d"] >= raw and d.dims["d"] in J.DATA["preferred_diameters_mm"]


@pytest.mark.parametrize("nm", [50, 100, 250, 500, 1000, 2000, 3000, 5000])
def test_every_check_passes_across_torques(nm):
    d = J.design(torque_nm=nm)
    assert d.all_passed, [c.name for c in d.checks if not c.passed]
    assert d.dims["n_bolts"] in (3, 4, 6)
    assert d.dims["d_bolt"] in J.BOLT_SIZES


def test_bolt_count_follows_the_shaft_size_rule():
    assert (J.bolt_count(30), J.bolt_count(40), J.bolt_count(41), J.bolt_count(100), J.bolt_count(120)) == (3, 3, 4, 4, 6)


def test_parts_list_follows_the_bolt_count():
    d = J.design(torque_nm=3000)
    names = parts_of(J, d.dims)
    n = int(d.dims["n_bolts"])
    assert names.count("flange_left") == 1
    assert len([x for x in names if x.startswith("bolt_")]) == n
    assert len([x for x in names if x.startswith("nut_")]) == n
    assert set(J.build_parts(d.dims)) == set(names)


def test_given_shaft_too_small_is_reported():
    d = J.design(torque_nm=3000, rod_diameter_mm=25)
    assert not d.all_passed or any("too small" in n for n in d.notes)


def test_missing_input_is_rejected():
    with pytest.raises(ValueError):
        J.design()


def test_parser_reads_torque_power_and_speed():
    assert parse_rules("flange coupling for 500 N-m torque").torque_nm == 500
    s = parse_rules("a coupling to transmit 20 kW at 1440 rpm")
    assert (s.joint, s.power_kw, s.speed_rpm) == ("flange_coupling", 20, 1440)
    assert parse_rules("coupling for 2.5 kNm").torque_nm == 2500
    assert parse_rules("flange coupling").missing() == ["torque, or power and speed, or shaft diameter"]


def test_registry_knows_the_coupling():
    assert REGISTRY["flange_coupling"] is J
