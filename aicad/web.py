"""Local web app for demos: python -m aicad.web  ->  http://127.0.0.1:8765

Type a request, the page shows what was understood and asks for anything
missing, then builds the joint and shows the 3D model, the drawing sheet, the
dimensions and the strength checks, with download links. Only listens on this
computer (127.0.0.1). Standard library only.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import threading
import traceback
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path

from .joints import REGISTRY
from .parse import Spec, parse

# Where built files land. Overridable because a hosted container usually has a read-only
# application directory and only /tmp writable: on Vercel this app got a 500 until
# AICAD_OUT pointed somewhere it could actually write.
OUT_ROOT = Path(os.environ.get("AICAD_OUT") or (Path("out") / "web"))
_BUILD_LOCK = threading.Lock()  # the geometry kernel is not run in parallel
# FreeCAD runs as its own process, so it gets its own lock: a 30 s drawing sheet must not hold
# up the next person's 2 s model.
_SHEET_LOCK = threading.Lock()


def understand(text: str, parser: str = "auto") -> dict:
    spec = parse(text, mode=parser)
    return {
        "spec": {k: getattr(spec, k) for k in ("joint", "load_n", "rod_diameter_mm", "bolt_size", "grip_mm",
                                                "torque_nm", "power_kw", "speed_rpm",
                                                "tension_mpa", "shear_mpa", "crushing_mpa")},
        "source": spec.source,
        "notes": spec.notes,
        "missing": spec.missing(),
        "supported": spec.supported(),
        "joints": {n: {"title": m.TITLE, "parts": len(m.PARTS)} for n, m in REGISTRY.items()},
    }


def _num(v):
    if v in (None, ""):
        return None
    return float(v)


def build(fields: dict, text: str, freecad: bool = True, out_root: Path = OUT_ROOT, progress=None) -> dict:
    # Every step is kept as well as streamed. Hosted, the polling path can lose the job to
    # another container, and then the only way the working reaches the page is in the result.
    steps: list[str] = []

    def say(msg):
        steps.append(msg)
        if progress:
            progress(msg)

    spec = _spec_from_fields(fields)
    if spec.missing():
        return {"ok": False, "missing": spec.missing()}
    if not spec.supported():
        return {"ok": False, "error": f"'{spec.joint}' is not built yet"}
    joint = REGISTRY[spec.joint]
    try:
        design = joint.design(**spec.design_kwargs())
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}

    run_id = f"{joint.NAME}_{datetime.now():%Y%m%d-%H%M%S}_{uuid.uuid4().hex[:6]}"
    out = Path(out_root) / run_id
    from .explain import explain_check, explain_dim, utilisation, utilisation_words
    from .export import export_all
    from .joints import parts_of
    names = parts_of(joint, design.dims)

    say(f"Read as: {joint.TITLE}, {design.duty}")
    for key, value in design.raw.items():
        # the raw solutions of the sizing formulas, before rounding to a standard size
        say(f"  formula {key}: {value:.2f} mm")
    for key, why in (design.rules or {}).items():
        if key in design.dims:
            say(f"  {key} = {design.dims[key]:g} mm  <-  {str(why)[:150]}")
    say(f"Sized: {len(design.dims)} dimensions from {len(design.rules or {})} rules")
    for c in design.checks:
        pct = 100 * c.stress_mpa / c.allowable_mpa if c.allowable_mpa else 0
        say(f"  check {c.name}: {c.formula} = {c.stress_mpa:.1f} MPa vs {c.allowable_mpa:g} allowed"
            f"  ->  {'pass' if c.passed else 'FAIL'} ({pct:.0f}% used)")
    say(f"Checked: {sum(1 for c in design.checks if c.passed)} of {len(design.checks)} pass")
    for n in design.notes:
        say(f"  note: {str(n)[:200]}")
    with _BUILD_LOCK:
        say(f"Building {len(names)} solid parts with the CAD kernel: {', '.join(names)}")
        parts = joint.build_parts(design.dims)
        for name, part in parts.items():
            try:
                solids = part.solids().vals()
                vol = sum(x.Volume() for x in solids) / 1000.0
                say(f"  {name}: {len(solids)} solid, {vol:,.1f} cm3, "
                    f"{vol * 7.85 / 1000:,.2f} kg in steel")
            except Exception:
                say(f"  {name}: built")
        say("Writing STEP files, the assembly, the exploded and weak-spot views")
        export_all(parts, design, joint, out, request=text)
    fc = None
    if freecad:
        from .freecad_pack import run_pack
        say("Drawing the A3 first-angle sheet in FreeCAD")
        with _SHEET_LOCK:
            fc = run_pack(out, joint, design, text, material=fields.get("material"))
    say("Done")

    # Say so when the drawing did not happen. A missing sheet used to look identical to a
    # joint that simply has no sheet, which is how a hosted deploy can quietly lose a feature.
    if freecad and not (fc and fc.get("ok")):
        why = (fc or {}).get("reason") or (fc or {}).get("error") or "FreeCAD did not run"
        log = (fc or {}).get("log") or ""
        # carry the tail of FreeCAD's own output: "exited 1" alone says nothing about why
        design.notes.append(f"No drawing sheet: {str(why)[:200]}"
                            + (f" | FreeCAD said: {str(log)[-400:]}" if log else ""))

    files = {"viewer": "viewer.html", "assembly_step": "assembly.step", "report": "report.md"}
    files.update({f"part_{p}": f"parts/{p}.step" for p in joint.PARTS})
    if fc and fc.get("ok"):
        files.update({"drawing": "drawing.svg", "fcstd": f"{joint.NAME}.FCStd"})
        if fc.get("dxf"):
            files["dxf"] = "drawing.dxf"
    # Carry the viewer and the sheet inside the response, not just as file paths. Hosted, a
    # second request for /out/... can land on a different container with its own empty /tmp,
    # and the 3D model renders as "not found" even though the build succeeded. Anything the
    # page must show immediately travels with the result.
    inline = {}
    for key, rel in (("viewer", "viewer.html"), ("drawing", "drawing.svg")):
        f = out / rel
        if f.exists() and f.stat().st_size <= 8_000_000:
            try:
                inline[key] = f.read_text()
            except Exception:
                pass

    return {
        "ok": True,
        "steps": steps,          # the full working, so the page can show it however it got here
        "inline": inline,
        "id": run_id,
        "title": joint.TITLE,
        "load_n": design.load_n,
        "duty": design.duty,
        "dims": [{"key": k, "label": joint.LABELS.get(k, k), "value": v, "rule": design.rules.get(k, ""),
                  "why": explain_dim(design, joint, k)} for k, v in design.dims.items()],
        "checks": [{"name": c.name, "stress": round(c.stress_mpa, 1), "allowed": c.allowable_mpa,
                    "formula": c.formula, "passed": c.passed, "working": explain_check(design, c)}
                   for c in design.checks],
        "weak_spots": [{"part": p, "used": None if u is None else round(100 * u), "check": c,
                        "words": utilisation_words(u)}
                       for p, (u, c) in utilisation(design, joint).items()],
        "design_factor": design.design_factor,
        "notes": design.notes,
        "verified": design.verified_against_book,
        "sheet_scale": fc.get("sheet_scale") if fc else None,
        "freecad": bool(fc and fc.get("ok")),
        "freecad_reason": None if (fc and fc.get("ok")) else ((fc or {}).get("reason") or "skipped"),
        "files": {k: f"/out/{run_id}/{v}" for k, v in files.items()},
    }


def _spec_from_fields(fields: dict) -> Spec:
    return Spec(
        joint=fields.get("joint") or None,
        load_n=_num(fields.get("load_n")),
        rod_diameter_mm=_num(fields.get("rod_diameter_mm")),
        bolt_size=int(float(fields["bolt_size"])) if fields.get("bolt_size") not in (None, "") else None,
        grip_mm=_num(fields.get("grip_mm")),
        torque_nm=_num(fields.get("torque_nm")),
        power_kw=_num(fields.get("power_kw")),
        speed_rpm=_num(fields.get("speed_rpm")),
        design_factor=_num(fields.get("design_factor")),
        tension_mpa=_num(fields.get("tension_mpa")),
        shear_mpa=_num(fields.get("shear_mpa")),
        crushing_mpa=_num(fields.get("crushing_mpa")),
    )


def followup(fields: dict, text: str, parser: str = "auto") -> dict:
    from .redesign import follow_up
    r = follow_up(_spec_from_fields(fields), text, mode=parser)
    new = None
    if r.spec is not None:
        new = {k: getattr(r.spec, k) for k in ("joint", "load_n", "rod_diameter_mm", "bolt_size", "grip_mm",
                                                 "torque_nm", "power_kw", "speed_rpm",
                                                 "tension_mpa", "shear_mpa", "crushing_mpa")}
    return {"kind": r.kind, "message": r.message, "fields": new, "changes": r.changes,
            "value": r.value, "governing": r.governing}


def _design_json(design, joint) -> dict:
    return {
        "ok": True,
        "title": joint.TITLE,
        "duty": design.duty,
        "raw": {k: round(v, 2) for k, v in design.raw.items()},
        "dims": [{"key": k, "label": joint.LABELS.get(k, k), "value": v, "rule": design.rules.get(k, "")}
                 for k, v in design.dims.items()],
        "checks": [{"name": c.name, "stress": round(c.stress_mpa, 1), "allowed": c.allowable_mpa,
                    "formula": c.formula, "passed": c.passed} for c in design.checks],
        "all_passed": design.all_passed,
        "notes": design.notes,
    }


def size(fields: dict) -> dict:
    """Sizing and every check, no geometry: well under a millisecond, so a slider can call it live."""
    spec = _spec_from_fields(fields)
    if spec.missing() or not spec.supported():
        return {"ok": False, "missing": spec.missing()}
    joint = REGISTRY[spec.joint]
    try:
        return _design_json(joint.design(**spec.design_kwargs()), joint)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}


def _clean_materials(extra) -> list:
    """User-added materials: keep only well-formed rows with positive numbers."""
    out = []
    for m in (extra or [])[:10]:
        try:
            row = {"name": str(m["name"])[:40] or "custom", "is_grade": str(m.get("is_grade", "user added"))[:40],
                   "user": True}
            for k in ("tension", "shear", "crushing", "density", "rate_inr_per_kg"):
                v = float(m[k])
                if not 0 < v < 100_000:
                    raise ValueError(k)
                row[k] = v
            out.append(row)
        except (KeyError, TypeError, ValueError):
            continue
    return out


def materials(fields: dict, extra=None) -> dict:
    """The same joint designed in every material in the table, plus any the user adds, with mass and cost."""
    from .optimise import MATERIALS, compare
    spec = _spec_from_fields(fields)
    if spec.missing() or not spec.supported():
        return {"ok": False, "missing": spec.missing()}
    extra = _clean_materials(extra)
    by_name = {m["name"]: m for m in MATERIALS["materials"] + extra}
    rows = []
    for r in compare(spec, extra):
        m = by_name.get(r["material"], {})
        rows.append({k: v for k, v in r.items() if k != "spec"} | {
            "tension": m.get("tension"), "shear": m.get("shear"), "crushing": m.get("crushing"),
            "density": m.get("density"), "user": bool(m.get("user"))})
    return {"ok": True, "rows": rows, "verified": MATERIALS.get("verified_against_book", False),
            "note": MATERIALS.get("note", "")}


def sheet(fields: dict, text: str, out_root: Path = OUT_ROOT) -> dict:
    """The drawing sheet on its own. Stateless on purpose: hosted, this request may reach a
    different container from the build, so it rebuilds what it needs and returns the sheet inline."""
    r = build(fields, text, freecad=True, out_root=out_root)
    if not r.get("ok"):
        return r
    out = Path(out_root) / r["id"]
    dxf = out / "drawing.dxf"
    return {"ok": bool(r.get("freecad")), "drawing": r["inline"].get("drawing", ""),
            "dxf": dxf.read_text() if dxf.exists() else "", "sheet_scale": r.get("sheet_scale"),
            "reason": r.get("freecad_reason")}


# Results kept per container, keyed on the inputs that decide the design. The first person to
# ask for a joint waits; everyone after gets it at once.
CACHE: dict = {}


_INFLIGHT: dict = {}
_INFLIGHT_LOCK = threading.Lock()


def cached(kind: str, fields: dict, fn):
    """A second request for something already being made waits for that one instead of starting
    its own: two 30 s sheets for the same joint would queue on the FreeCAD lock back to back."""
    key = kind + json.dumps(fields, sort_keys=True, default=str)
    hit = CACHE.get(key)
    if hit is not None:
        return hit | {"cached": True}
    with _INFLIGHT_LOCK:
        ev = _INFLIGHT.get(key)
        owner = ev is None
        if owner:
            ev = _INFLIGHT[key] = threading.Event()
    if not owner:
        ev.wait(600)
        hit = CACHE.get(key)
        return hit | {"cached": True} if hit is not None else fn()
    try:
        r = fn()
        if r.get("ok"):
            if len(CACHE) > 200:
                CACHE.clear()
            CACHE[key] = r
        return r
    finally:
        with _INFLIGHT_LOCK:
            _INFLIGHT.pop(key, None)
        ev.set()


SHEET_FAILED: dict = {}


def sheet_poll(fields: dict, text: str, out_root: Path = OUT_ROOT) -> dict:
    key = "sheet" + json.dumps(fields, sort_keys=True, default=str)
    hit = CACHE.get(key)
    if hit is not None:
        return hit | {"cached": True}
    with _INFLIGHT_LOCK:
        running = key in _INFLIGHT
    failed = SHEET_FAILED.pop(key, None)
    if failed is not None:
        return failed            # say why once, so the page stops asking; the next poll retries
    if not running:
        def run():
            r = cached("sheet", fields, lambda: sheet(fields, text, out_root))
            if not r.get("ok"):
                SHEET_FAILED[key] = r
        threading.Thread(target=run, daemon=True).start()
    return {"ok": False, "pending": True}


EXAMPLES = ["knuckle joint for 50 kN", "socket and spigot joint for 35 kN", "sleeve and cotter joint for 50 kN",
            "gib and cotter joint for 50 kN", "M24 nut bolt, plates 30 mm thick, load 20 kN",
            "flange coupling to transmit 20 kW at 1440 rpm"]


def prebuild(out_root: Path = OUT_ROOT) -> None:
    """Build every example at start-up, model first and sheets after, so a demo never waits."""
    def fields_of(text):
        return {k: v for k, v in understand(text, "rules")["spec"].items() if v is not None}
    for text in EXAMPLES:
        f = fields_of(text)
        cached("build", f, lambda: build(f, text, freecad=False, out_root=out_root))
        cached("materials", f, lambda: materials(f))
    # only the demo joint's sheet: six sheets back to back held the FreeCAD lock for minutes
    f = fields_of(EXAMPLES[0])
    cached("sheet", f, lambda: sheet(f, EXAMPLES[0], out_root))


JOBS: dict = {}


def start_job(fields: dict, text: str, freecad: bool, out_root: Path) -> str:
    job_id = uuid.uuid4().hex[:10]
    JOBS[job_id] = {"progress": [], "done": False, "result": None}

    def run():
        try:
            r = build(fields, text, freecad=freecad, out_root=out_root,
                      progress=lambda m: JOBS[job_id]["progress"].append(m))
        except Exception as exc:
            r = {"ok": False, "error": f"{exc.__class__.__name__}: {exc}"}
        JOBS[job_id]["result"] = r
        JOBS[job_id]["done"] = True

    threading.Thread(target=run, daemon=True).start()
    return job_id


class Handler(BaseHTTPRequestHandler):
    out_root = OUT_ROOT
    freecad = True

    def log_message(self, format, *args):  # noqa: A002  keep the terminal quiet
        pass

    def _send(self, code: int, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        # Never cache the page or the API. Hosted, a browser holding an old copy looks exactly
        # like a deploy that did not work, and that cost real time to tell apart.
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj):
        self._send(code, json.dumps(obj, default=str).encode(), "application/json")

    def do_GET(self):
        if self.path.startswith("/api/job/"):
            job = JOBS.get(self.path.rsplit("/", 1)[-1])
            return self._json(200 if job else 404, job or {"error": "unknown job"})
        if self.path in ("/", "/index.html"):
            page = PAGE.replace("__BUILD_ID__", _BUILD_ID)
            return self._send(200, page.encode(), "text/html; charset=utf-8")
        if self.path.startswith("/out/"):
            root = Path(self.out_root).resolve()
            target = (root / self.path[len("/out/"):].split("?")[0]).resolve()
            if root not in target.parents or not target.is_file():
                return self._send(404, b"not found", "text/plain")
            ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            if target.suffix in (".step", ".FCStd", ".dxf"):
                ctype = "application/octet-stream"
            return self._send(200, target.read_bytes(), ctype)
        self._send(404, b"not found", "text/plain")

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
            if self.path == "/api/understand":
                return self._json(200, understand(body.get("text", ""), body.get("parser", "auto")))
            if self.path == "/api/codegen":
                from .codegen import generate
                r = generate(body.get("text", ""), out_root=self.out_root)
                if r.get("ok"):
                    rid = Path(r["out"]).name
                    r["files"] = {"viewer": f"/out/{rid}/viewer.html", "step": f"/out/{rid}/part.step",
                                  "code": f"/out/{rid}/code.py"}
                return self._json(200, r)
            if self.path == "/api/followup":
                return self._json(200, followup(body.get("fields", {}), body.get("text", ""), body.get("parser", "auto")))
            if self.path == "/api/size":
                return self._json(200, size(body.get("fields", {})))
            if self.path == "/api/materials":
                f, extra = body.get("fields", {}), body.get("extra") or []
                return self._json(200, cached("materials", f | {"_extra": extra}, lambda: materials(f, extra)))
            if self.path == "/api/sheet":
                f, t = body.get("fields", {}), body.get("text", "")
                if body.get("poll"):
                    # Answer at once: done, or still drawing. A browser request held open for the
                    # 30 to 50 s a sheet takes was reset by the host before the body arrived.
                    return self._json(200, sheet_poll(f, t, self.out_root))
                return self._json(200, cached("sheet", f, lambda: sheet(f, t, self.out_root)))
            if self.path == "/api/build":
                f, t = body.get("fields", {}), body.get("text", "")
                if body.get("fast"):
                    # model, checks and files now; the page asks /api/sheet for the drawing
                    return self._json(200, cached("build", f, lambda: build(f, t, freecad=False,
                                                                              out_root=self.out_root)))
                return self._json(200, build(f, t, freecad=self.freecad, out_root=self.out_root))
            if self.path == "/api/build_async":
                job = start_job(body.get("fields", {}), body.get("text", ""), self.freecad, Path(self.out_root))
                return self._json(200, {"job": job})
            self._json(404, {"error": "unknown endpoint"})
        except Exception as exc:
            self._json(500, {"ok": False, "error": f"{exc.__class__.__name__}: {exc}",
                             "trace": traceback.format_exc()[-600:]})


def make_server(host="127.0.0.1", port=8765, out_root: Path = OUT_ROOT, freecad=True) -> ThreadingHTTPServer:
    handler = type("BoundHandler", (Handler,), {"out_root": Path(out_root), "freecad": freecad})
    return ThreadingHTTPServer((host, port), handler)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="aicad.web")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1",
                    help="127.0.0.1 keeps it on this computer; 0.0.0.0 is for a container")
    ap.add_argument("--no-freecad", action="store_true")
    args = ap.parse_args(argv)
    srv = make_server(host=args.host, port=args.port, freecad=not args.no_freecad)
    if os.environ.get("AICAD_PREBUILD"):
        threading.Thread(target=prebuild, daemon=True).start()
    print(f"aicad web app on http://{args.host}:{args.port}  (Ctrl+C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


# Stamped into the page so you can tell at a glance whether the browser is showing a stale copy
_BUILD_ID = datetime.fromtimestamp(Path(__file__).stat().st_mtime).strftime("%Y-%m-%d %H:%M")

PAGE = (Path(__file__).parent / "ui.html").read_text(encoding="utf-8")

if __name__ == "__main__":
    raise SystemExit(main())
