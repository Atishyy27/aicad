"""AI-written CAD gates, tested with hand-written code and a fake AI (no plan usage)."""
import json
import math
import subprocess

import pytest

from aicad import codegen as C

WASHER = """
import cadquery as cq
result = cq.Workplane("XY").circle(20).circle(10).extrude(3)
"""
REQ = "a flat washer, 20 mm inner diameter, 40 mm outer diameter, 3 mm thick"


def test_good_code_passes_and_is_measured():
    v, step = C.verify(REQ, WASHER, [40, 40, 3])
    assert v.ok, v.reasons
    assert v.measured["volume"] == pytest.approx(math.pi / 4 * (40**2 - 20**2) * 3, rel=1e-4)
    assert step and step.endswith("part.step")


@pytest.mark.parametrize("code,why", [
    ("import os\nresult = None", "import of os"),
    ("import cadquery as cq\nopen('x','w')\nresult = cq.Workplane().box(1,1,1)", "use of open"),
    ("import cadquery as cq\nresult = cq.Workplane().box(1,1,1)\nresult.val().exportStep('x')", "exportStep"),
    ("import cadquery as cq\nx = cq.__dict__", "__dict__"),
    ("import subprocess", "subprocess"),
    ("def f(:\n pass", "syntax error"),
])
def test_dangerous_or_broken_code_is_refused_before_running(code, why):
    v, _ = C.verify(REQ, code, [40, 40, 3])
    assert not v.ok and why in v.reasons[0]
    assert v.measured == {}  # never ran


def test_code_that_crashes_is_rejected():
    v, _ = C.verify(REQ, "import cadquery as cq\nresult = cq.Workplane().circle(-1).extrude(3)", [40, 40, 3])
    assert not v.ok and ("crashed" in v.reasons[0] or "valid" in " ".join(v.reasons))


def test_code_that_hangs_is_stopped():
    v, _ = C.verify(REQ, "import math\nwhile True:\n    math.sqrt(2)", [40, 40, 3], timeout=5)
    assert not v.ok and "did not finish" in v.reasons[0]


def test_missing_result_is_rejected():
    v, _ = C.verify(REQ, "import cadquery as cq\nx = cq.Workplane().box(1, 1, 1)", [1, 1, 1])
    assert not v.ok and "result" in v.reasons[0]


def test_two_solids_are_rejected():
    code = "import cadquery as cq\nresult = cq.Workplane().box(5,5,5).union(cq.Workplane().box(5,5,5).translate((20,0,0)))"
    v, _ = C.verify("two cubes", code, [25, 5, 5])
    assert not v.ok and "one solid" in v.reasons[0]


def test_wrong_size_against_the_request_is_rejected():
    wrong = "import cadquery as cq\nresult = cq.Workplane('XY').circle(25).circle(10).extrude(3)"  # 50 OD, asked 40
    v, _ = C.verify(REQ, wrong, [50, 50, 3])
    assert not v.ok and any("you asked for 40 mm" in r for r in v.reasons)


def test_declared_size_must_match_built_size():
    v, _ = C.verify("a washer", WASHER, [60, 60, 3])
    assert not v.ok and any("declared size" in r for r in v.reasons)


def _fake(responses):
    calls = iter(responses)

    def run(cmd, **kw):
        assert "--tools" in cmd and cmd[cmd.index("--tools") + 1] == ""
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(next(calls)), stderr="")
    return run


def test_generate_retries_once_with_the_failure_reasons(tmp_path):
    bad = {"is_error": False, "structured_output": {"code": "import os", "expected_bbox_mm": [40, 40, 3]}}
    good = {"is_error": False, "structured_output": {"code": WASHER, "expected_bbox_mm": [40, 40, 3]}}
    r = C.generate(REQ, out_root=tmp_path, runner=_fake([bad, good]))
    assert r["ok"] and len(r["attempts"]) == 2 and not r["attempts"][0]["ok"]
    assert (tmp_path / r["out"].split("/")[-1] / "part.step").exists()


def test_generate_gives_up_after_two_failures(tmp_path):
    bad = {"is_error": False, "structured_output": {"code": "import os", "expected_bbox_mm": [1, 1, 1]}}
    r = C.generate(REQ, out_root=tmp_path, runner=_fake([bad, bad]))
    assert not r["ok"] and len(r["attempts"]) == 2


@pytest.mark.parametrize("text,want", [
    ("a flat washer, 20 mm inner diameter, 40 mm outer diameter, 3 mm thick", [40, 3]),
    ("a rectangular plate 100 x 60 x 10 mm with four 8 mm holes 10 mm from each corner", [100, 60, 10]),
    ("a solid shaft 40 mm diameter and 200 mm long", [40, 200]),
    ("a solid shaft 40 mm diameter and 200 mm long with a flat-bottomed keyway 12 mm wide, 5 mm deep "
     "and 60 mm long, square-ended, starting at one end", [40, 200]),
])
def test_requested_overall_sizes_skip_features(text, want):
    assert sorted(C.requested_sizes(text)) == sorted(want)
