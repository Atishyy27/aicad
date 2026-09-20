"""The web app, run in-process on a free port. AI is never called (rules parser)."""
import json
import threading
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
    assert "AI in CAD" in html and "/api/understand" in html


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
