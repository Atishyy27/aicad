"""The web app, run in-process on a free port. AI is never called (rules parser)."""
import json
import threading
import time
import urllib.error
import urllib.request

import pytest

from aicad.web import make_server


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    out_root = tmp_path_factory.mktemp("web")
    srv = make_server(port=0, out_root=out_root, freecad=False)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def _post(base, path, body):
    req = urllib.request.Request(base + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def test_page_loads(server):
    with urllib.request.urlopen(server + "/") as r:
        html = r.read().decode()
    assert "aicad" in html and "/api/understand" in html
    for marker in ("Describe the joint", "Material selection", "Drawing", "Checks", "Ask or change",
                   "/api/size", "/api/sheet", "/api/materials"):
        assert marker in html, marker


def test_size_is_instant_and_matches_the_design(server):
    import time
    t = time.perf_counter()
    r = _post(server, "/api/size", {"fields": {"joint": "knuckle", "load_n": 50_000}})
    assert time.perf_counter() - t < 1.0
    dims = {d["key"]: d["value"] for d in r["dims"]}
    assert r["ok"] and dims["D"] == 35 and dims["d3"] == 70 and len(r["checks"]) == 9 and r["all_passed"]


def test_materials_lists_every_grade_with_mass_and_cost(server):
    r = _post(server, "/api/materials", {"fields": {"joint": "knuckle", "load_n": 50_000}})
    assert r["ok"] and len(r["rows"]) == 6
    steel = next(x for x in r["rows"] if x["material"].startswith("30C8"))
    assert steel["ok"] and steel["mass_kg"] > 0 and steel["cost_inr"] > 0 and steel["tension"] == 75
    again = _post(server, "/api/materials", {"fields": {"joint": "knuckle", "load_n": 50_000}})
    assert again.get("cached")


def test_fast_build_skips_the_sheet_and_is_cached(server):
    body = {"fields": {"joint": "cotter", "load_n": 35_000}, "text": "socket and spigot joint for 35 kN", "fast": True}
    r = _post(server, "/api/build", body)
    assert r["ok"] and r["inline"].get("viewer") and r["freecad_reason"] == "skipped"
    assert _post(server, "/api/build", body).get("cached")


def test_understand_reports_what_is_missing(server):
    r = _post(server, "/api/understand", {"text": "knuckle joint", "parser": "rules"})
    assert r["spec"]["joint"] == "knuckle"
    assert r["missing"] == ["load or rod diameter"]
    assert set(r["joints"]) >= {"knuckle", "cotter", "sleeve_and_cotter", "nut_bolt"}


def test_build_returns_design_and_serves_files(server):
    r = _post(server, "/api/build", {"fields": {"joint": "cotter", "load_n": 35000}, "text": "cotter 35 kN"})
    assert r["ok"], r
    assert r["title"].startswith("Socket and spigot")
    assert all(c["passed"] for c in r["checks"])
    with urllib.request.urlopen(server + r["files"]["viewer"]) as v:
        assert b"model-viewer" in v.read()
    with urllib.request.urlopen(server + r["files"]["assembly_step"]) as s:
        assert s.read(20).startswith(b"ISO-10303-21")


def test_build_with_missing_input_asks_again(server):
    r = _post(server, "/api/build", {"fields": {"joint": "nut_bolt"}, "text": "bolt"})
    assert r == {"ok": False, "missing": ["load or bolt size"]}


def test_files_outside_the_output_folder_are_not_served(server):
    for path in ("/out/../pyproject.toml", "/out/%2e%2e/%2e%2e/etc/passwd", "/out/nothing/here.step"):
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(server + path)
        assert e.value.code == 404


def test_followup_limit_and_change(server):
    fields = {"joint": "knuckle", "load_n": 50000}
    r = _post(server, "/api/followup", {"fields": fields, "text": "how much load can this take", "parser": "rules"})
    assert r["kind"] == "limit" and r["governing"] == "pin bending"
    r = _post(server, "/api/followup", {"fields": fields, "text": "make it 80 kN", "parser": "rules"})
    assert r["kind"] == "change" and r["fields"]["load_n"] == 80000


def test_build_job_reports_progress_then_the_result(server):
    r = _post(server, "/api/build_async", {"fields": {"joint": "knuckle", "load_n": 20000}, "text": "knuckle 20 kN"})
    job = r["job"]
    for _ in range(300):
        st = json.load(urllib.request.urlopen(f"{server}/api/job/{job}"))
        if st["done"]:
            break
        time.sleep(0.5)
    assert st["done"] and st["result"]["ok"], st
    assert any("Building" in p for p in st["progress"])
    assert st["progress"][-1] == "Done"


def test_unknown_job_is_404(server):
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(server + "/api/job/nope")
    assert e.value.code == 404


def test_coupling_through_the_web_app(server):
    r = _post(server, "/api/understand", {"text": "flange coupling to transmit 20 kW at 1440 rpm", "parser": "rules"})
    assert r["spec"]["power_kw"] == 20 and r["spec"]["speed_rpm"] == 1440 and r["missing"] == []
    b = _post(server, "/api/build", {"fields": {"joint": "flange_coupling", "torque_nm": 500}, "text": "coupling"})
    assert b["ok"] and b["duty"].startswith("Torque") and len(b["checks"]) == 7


def test_sheet_poll_answers_at_once(server):
    import time
    t = time.perf_counter()
    r = _post(server, "/api/sheet", {"fields": {"joint": "nut_bolt", "load_n": 20_000, "bolt_size": 24, "grip_mm": 30},
                                     "text": "M24 bolt", "poll": True})
    assert time.perf_counter() - t < 2.0
    assert r.get("pending") or "ok" in r


def test_user_material_is_designed_alongside_the_table(server):
    extra = [{"name": "EN8 steel", "tension": 110, "shear": 55, "crushing": 220, "density": 7850, "rate_inr_per_kg": 85},
             {"name": "broken", "tension": -5}]
    r = _post(server, "/api/materials", {"fields": {"joint": "knuckle", "load_n": 50_000}, "extra": extra})
    names = [x["material"] for x in r["rows"]]
    assert "EN8 steel" in names and "broken" not in names and len(names) == 7
    mine = next(x for x in r["rows"] if x["material"] == "EN8 steel")
    assert mine["user"] and mine["ok"] and mine["cost_inr"] > 0


def test_followup_scales_and_explains_derived_sizes():
    from aicad.parse import Spec
    from aicad.redesign import follow_up
    s = Spec(joint="knuckle", load_n=50_000.0)
    assert follow_up(s, "double the load", mode="rules").spec.load_n == 100_000
    assert follow_up(s, "double rod diameter", mode="rules").spec.rod_diameter_mm == 70
    r = follow_up(s, "what if we make the pin double length", mode="rules")
    assert r.kind == "explain" and "t + 2 t1" in r.message
