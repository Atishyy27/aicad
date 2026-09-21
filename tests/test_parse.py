import json
import os
import subprocess

import pytest

from aicad import parse as P
from aicad.parse import parse, parse_rules, spec_from_ai_json

# ---------------------------------------------------------------- rules


def test_plain_english_with_kn():
    s = parse_rules("knuckle joint for 50 kN")
    assert (s.joint, s.load_n, s.missing()) == ("knuckle", 50_000, [])


def test_newtons_with_load_first():
    s = parse_rules("load of 5000 N on a knuckle joint")
    assert s.joint == "knuckle" and s.load_n == pytest.approx(5_000)


def test_rod_diameter_only():
    s = parse_rules("knuckle joint with 30 mm rod")
    assert s.rod_diameter_mm == 30 and s.load_n is None and s.missing() == []


def test_bare_joint_name_reports_what_is_missing():
    assert parse_rules("knuckle joint").missing() == ["load or rod diameter"]


def test_no_joint_named():
    s = parse_rules("make me something for 20 kN")
    assert s.joint is None and "joint type" in s.missing()


def test_cotter_and_socket_spigot_words():
    assert parse_rules("cotter joint 20 kN").joint == "cotter"
    assert parse_rules("socket and spigot joint for 20 kN").joint == "cotter"


def test_both_cotter_variants_are_recognised_and_built():
    s = parse_rules("sleeve and cotter joint 10 kN")
    assert s.joint == "sleeve_and_cotter" and s.supported()
    g = parse_rules("gib and cotter joint 10 kN")
    assert g.joint == "gib_and_cotter" and g.supported()
    # "gib" must win over the bare word cotter, or every gib request builds a plain cotter
    assert parse_rules("gib and cotter joint 10 kN").joint != "cotter"


def test_bolt_size_and_grip():
    s = parse_rules("M12 bolt with 40 mm grip")
    assert (s.joint, s.bolt_size, s.grip_mm, s.rod_diameter_mm) == ("nut_bolt", 12, 40, None)
    assert s.missing() == []


def test_bolt_needs_load_or_size():
    assert parse_rules("I need a nut bolt").missing() == ["load or bolt size"]


def test_tonnes_convert_to_newtons():
    assert parse_rules("knuckle joint 2 tonne").load_n == pytest.approx(2 * 1000 * 9.80665)


def test_design_stresses_are_picked_up():
    s = parse_rules("knuckle joint 50kN, tensile 80 MPa, shear 50 MPa, crushing 120 MPa")
    assert (s.tension_mpa, s.shear_mpa, s.crushing_mpa) == (80, 50, 120)


def test_decimal_load_and_misspelling():
    assert parse_rules("knukle joint for 12.5 kN").load_n == pytest.approx(12_500)
    assert parse_rules("knukle joint 10 kN").joint == "knuckle"


# ---------------------------------------------------------------- AI guard

def test_ai_values_traceable_to_the_sentence_are_kept():
    s = spec_from_ai_json({"joint": "knuckle", "load_n": 19613.3}, "a two tonne knuckle joint", "x")
    assert s.load_n == pytest.approx(19613.3) and not s.notes


def test_ai_invented_number_is_dropped():
    s = spec_from_ai_json({"joint": "knuckle", "load_n": 30000}, "I need a knuckle joint", "x")
    assert s.load_n is None
    assert any("not in the request" in n for n in s.notes)
    assert s.missing() == ["load or rod diameter"]


def test_ai_unknown_joint_becomes_none():
    assert spec_from_ai_json({"joint": "universal"}, "universal joint 5 kN", "x").joint is None


def test_ai_negative_value_is_dropped():
    s = spec_from_ai_json({"joint": "knuckle", "load_n": -5}, "knuckle 5 kN", "x")
    assert s.load_n is None


# ---------------------------------------------------------------- Claude Code path (fake CLI)

def _fake_runner(payload, returncode=0):
    def run(cmd, **kw):
        assert os.path.basename(cmd[0]).lower().startswith("claude") and "-p" in cmd and "--json-schema" in cmd
        assert cmd[cmd.index("--tools") + 1] == ""
        assert cmd[cmd.index("--setting-sources") + 1] == "local"
        return subprocess.CompletedProcess(cmd, returncode, stdout=json.dumps(payload), stderr="boom")
    return run


def test_claude_code_structured_output_is_used(monkeypatch):
    monkeypatch.setattr(P, "ai_backends", lambda: ["claude-code"])
    runner = _fake_runner({"is_error": False, "structured_output": {"joint": "knuckle", "load_n": 50000}})
    s = parse("knuckle joint 50 kN", runner=runner)
    assert (s.source, s.joint, s.load_n) == ("claude-code", "knuckle", 50000)


def test_claude_code_error_falls_back_to_rules(monkeypatch):
    monkeypatch.setattr(P, "ai_backends", lambda: ["claude-code"])
    s = parse("knuckle joint 50 kN", runner=_fake_runner({}, returncode=1))
    assert s.source == "rules" and s.load_n == 50000
    assert any("AI unavailable" in n for n in s.notes)


def test_ai_mode_raises_when_nothing_works(monkeypatch):
    monkeypatch.setattr(P, "ai_backends", lambda: ["claude-code"])
    with pytest.raises(RuntimeError):
        parse("knuckle joint 50 kN", mode="ai", runner=_fake_runner({}, returncode=1))


def test_disagreement_between_ai_and_rules_is_flagged(monkeypatch):
    monkeypatch.setattr(P, "ai_backends", lambda: ["claude-code"])
    runner = _fake_runner({"is_error": False, "structured_output": {"joint": "knuckle", "load_n": 5000}})
    s = parse("knuckle joint 50 kN or 5 kN", runner=runner)
    assert any("disagree" in n for n in s.notes)


def test_rules_mode_never_calls_ai(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("AI was called")
    monkeypatch.setattr(P, "parse_ai", boom)
    assert parse("knuckle joint 50 kN", mode="rules").source == "rules"


# ---------------------------------------------------------------- AI + rules merge

def test_merge_fills_joint_the_ai_left_empty():
    ai = spec_from_ai_json({"joint": None, "load_n": 35000}, "socket and spigot joint for 35 kN", "claude-code")
    out = P.merge(ai, parse_rules("socket and spigot joint for 35 kN"))
    assert (out.joint, out.load_n, out.source) == ("cotter", 35000, "claude-code+rules")
    assert any("filled from rules" in n for n in out.notes)


def test_merge_keeps_ai_value_when_rules_have_nothing():
    ai = spec_from_ai_json({"joint": "knuckle", "load_n": 19613.3}, "a two tonne knuckle joint", "claude-code")
    out = P.merge(ai, parse_rules("a two tonne knuckle joint"))
    assert out.load_n == pytest.approx(19613.3) and out.source == "claude-code"


def test_ai_is_told_what_each_label_means():
    assert "socket" in P._SYSTEM and "M12" in P._SYSTEM and "fork" in P._SYSTEM


def test_half_a_tonne_is_traceable():
    s = spec_from_ai_json({"joint": "cotter", "load_n": 4903.3}, "cotter joint for half a tonne", "x")
    assert s.load_n == pytest.approx(4903.3)


def test_hindi_number_words_are_no_longer_accepted():
    s = spec_from_ai_json({"joint": "knuckle", "load_n": 19613.3}, "do tonne ka knuckle joint", "x")
    assert s.load_n is None


def test_gib_count_is_read_from_words_not_digits():
    """The count is written in words, so the digit-matching guard must not eat it."""
    from aicad.parse import parse_rules, spec_from_ai_json
    assert parse_rules("double gib and cotter joint for 50 kN").gibs == 2
    assert parse_rules("gib and cotter joint with two gibs for 50 kN").gibs == 2
    assert parse_rules("gib and cotter joint for 50 kN").gibs is None      # default, decided later
    ai = spec_from_ai_json({"joint": "gib_and_cotter", "gibs": 2, "load_n": 50000},
                           "double gib and cotter joint for 50 kN", source="test")
    assert ai.gibs == 2
    bad = spec_from_ai_json({"joint": "gib_and_cotter", "gibs": 7, "load_n": 50000},
                            "gib and cotter joint for 50 kN", source="test")
    assert bad.gibs is None and any("one or two" in n for n in bad.notes)
