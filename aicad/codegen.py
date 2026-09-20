"""EXPERIMENTAL: the AI writes CadQuery code for a part outside the joint library.

    python -m aicad.codegen "a flat washer, 20 mm inner diameter, 40 mm outer diameter, 3 mm thick"

Nothing the AI writes is shown until it passes these gates:
  1. static screen: only `cadquery` and `math` imports; no file, OS, network or eval calls
  2. runs in a separate Python process with a time limit
  3. defines `result` holding exactly one valid solid with positive volume
  4. its bounding box matches the size the AI itself declared (self-consistency)
  5. every overall size you asked for appears as one of the bounding-box extents (within 2 %)
The static screen is a guard against accidents, not a security sandbox.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

ALLOWED_IMPORTS = {"cadquery", "math"}
BANNED_NAMES = {"open", "exec", "eval", "compile", "__import__", "input", "globals", "locals", "vars",
                "getattr", "setattr", "delattr", "breakpoint"}
BANNED_ATTRS = {"system", "popen", "remove", "rmdir", "unlink", "rename", "exportStep", "export", "save"}

SYSTEM = (
    "You write CadQuery (Python) code for one mechanical part. Units are millimetres. "
    "Rules: import only cadquery (as cq) and math. Do not read or write files, do not export, do not print. "
    "Put the final part in a variable named result, as a cq.Workplane containing exactly one solid. "
    "Centre the part sensibly at the origin. Also report expected_bbox_mm: the overall size of the part "
    "along X, Y and Z in millimetres."
)
SCHEMA = {
    "type": "object",
    "properties": {
        "code": {"type": "string"},
        "expected_bbox_mm": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
        "notes": {"type": "string"},
    },
    "required": ["code", "expected_bbox_mm"],
}

_HARNESS = r'''
import json, math, sys
import cadquery as cq
ns = {"cq": cq, "math": math}
src = open(sys.argv[1]).read()
exec(compile(src, "ai_part.py", "exec"), ns)
res = ns.get("result")
out = {"has_result": res is not None}
if res is not None:
    shape = res.val() if hasattr(res, "val") else res
    solids = shape.Solids() if hasattr(shape, "Solids") else []
    out["n_solids"] = len(solids)
    if len(solids) == 1:
        s = solids[0]
        bb = s.BoundingBox()
        out.update(valid=s.isValid(), volume=s.Volume(), bbox=[bb.xlen, bb.ylen, bb.zlen])
        cq.exporters.export(cq.Workplane().add(s), sys.argv[2])
print("AICAD_RESULT " + json.dumps(out))
'''


@dataclass
class Verdict:
    ok: bool
    reasons: list[str] = field(default_factory=list)
    measured: dict = field(default_factory=dict)
    code: str = ""
    declared_bbox: list = field(default_factory=list)


def static_screen(code: str) -> list[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [f"syntax error: {exc.msg} (line {exc.lineno})"]
    problems = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] not in ALLOWED_IMPORTS:
                    problems.append(f"import of {a.name} is not allowed")
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] not in ALLOWED_IMPORTS:
                problems.append(f"import from {node.module} is not allowed")
        elif isinstance(node, ast.Name) and node.id in BANNED_NAMES:
            problems.append(f"use of {node.id} is not allowed")
        elif isinstance(node, ast.Attribute) and (node.attr in BANNED_ATTRS or node.attr.startswith("__")):
            problems.append(f"use of .{node.attr} is not allowed")
    return sorted(set(problems))


def run_code(code: str, timeout: float = 60, python: str | None = None) -> tuple[dict, str | None, str]:
    """Run the code in a separate process. Returns (measurements, step_path or None, error text)."""
    tmp = Path(tempfile.mkdtemp(prefix="aicad_codegen_"))
    (tmp / "ai_part.py").write_text(code)
    (tmp / "harness.py").write_text(_HARNESS)
    step = tmp / "part.step"
    env = {k: v for k, v in os.environ.items() if k in ("PATH", "HOME", "SYSTEMROOT", "TMPDIR", "TEMP", "TMP")}
    try:
        done = subprocess.run([python or sys.executable, str(tmp / "harness.py"), str(tmp / "ai_part.py"), str(step)],
                              capture_output=True, text=True, timeout=timeout, cwd=tmp, env=env)
    except subprocess.TimeoutExpired:
        return {}, None, f"did not finish within {timeout:g} s"
    line = next((l for l in done.stdout.splitlines() if l.startswith("AICAD_RESULT ")), None)
    if done.returncode != 0 or line is None:
        err = (done.stderr.strip().splitlines() or ["unknown error"])[-1]
        return {}, None, f"crashed: {err[:300]}"
    data = json.loads(line[len("AICAD_RESULT "):])
    return data, (str(step) if step.exists() else None), ""


_FEATURE_WORDS = {"inner", "inside", "internal", "hole", "holes", "bore", "keyway", "slot", "groove", "fillet",
                  "chamfer", "radius", "pitch", "spacing", "from", "apart", "deep", "depth", "counterbore", "pcd"}
_EXTENT_WORDS = {"outer", "outside", "overall", "long", "length", "wide", "width", "thick", "thickness",
                 "high", "height", "tall", "diameter", "od", "side", "square", "across", "flats", "af"}


def requested_sizes(text: str) -> list[float]:
    """Overall sizes the request asks for. A number counts when the words next to it describe an
    outside size (outer diameter, long, wide, thick, height). Numbers next to feature words
    (inner, hole, bore, keyway, fillet, from) describe features and are not checked as extents."""
    sizes = []
    low = text.lower()
    # "a shaft 40 mm diameter ... with a keyway 60 mm long": what follows "with" describes features
    low = re.split(r"\bwith\b", low, maxsplit=1)[0]
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)(?:\s*[x×]\s*(\d+(?:\.\d+)?))?\s*mm", low):
        sizes += [float(g) for g in m.groups() if g]
    blocked = [m.span() for m in re.finditer(r"\d+(?:\.\d+)?\s*[x×]\s*\d+(?:\.\d+)?(?:\s*[x×]\s*\d+(?:\.\d+)?)?\s*mm", low)]
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*mm", low):
        if any(a <= m.start() < b for a, b in blocked):
            continue
        # stay inside the same clause: stop at a comma, semicolon, "and" or "with"
        pre = re.split(r"[,;]|\band\b|\bwith\b", low[max(0, m.start() - 40):m.start()])[-1]
        post = re.split(r"[,;]|\band\b|\bwith\b", low[m.end():m.end() + 40])[0]
        before = re.findall(r"[a-z]+", pre)[-3:]
        after = re.findall(r"[a-z]+", post)[:3]
        near = set(before + after)
        if near & _FEATURE_WORDS:
            continue
        if near & _EXTENT_WORDS:
            sizes.append(float(m.group(1)))
    return sizes


def verify(text: str, code: str, declared: list, timeout: float = 60, python: str | None = None) -> tuple[Verdict, str | None]:
    v = Verdict(ok=False, code=code, declared_bbox=list(declared or []))
    problems = static_screen(code)
    if problems:
        v.reasons = ["refused before running: " + "; ".join(problems)]
        return v, None
    m, step, err = run_code(code, timeout=timeout, python=python)
    v.measured = m
    if err:
        v.reasons = [err]
        return v, None
    if not m.get("has_result"):
        v.reasons.append("the code did not define `result`")
    elif m.get("n_solids") != 1:
        v.reasons.append(f"expected exactly one solid, got {m.get('n_solids')}")
    else:
        if not m.get("valid"):
            v.reasons.append("the solid is not valid")
        if not m.get("volume", 0) > 0:
            v.reasons.append("the solid has no volume")
        bbox = sorted(m["bbox"])
        if declared and len(declared) == 3:
            for got, want in zip(bbox, sorted(declared)):
                if abs(got - want) > max(0.02 * want, 0.1):
                    v.reasons.append(f"declared size {sorted(declared)} does not match the built size "
                                     f"{[round(b, 2) for b in bbox]}")
                    break
        # every overall size the request names must show up as an extent (features are skipped)
        for a in sorted(set(requested_sizes(text)), reverse=True):
            if not any(abs(a - b) <= max(0.02 * a, 0.1) for b in bbox):
                v.reasons.append(f"you asked for {a:g} mm but no overall size is {a:g} mm "
                                 f"(built {[round(b, 2) for b in bbox]})")
    v.ok = not v.reasons
    return v, step if v.ok else None


def ask_ai(text: str, timeout: float = 180, runner=subprocess.run) -> dict:
    """Ask Claude Code (logged-in account, tools off) for code plus its declared size."""
    exe = shutil.which("claude") or "claude"
    cmd = [exe, "-p", f"Part to model: {text}", "--output-format", "json", "--json-schema", json.dumps(SCHEMA),
           "--tools", "", "--model", os.environ.get("AICAD_CODEGEN_MODEL", os.environ.get("AICAD_CLAUDE_MODEL", "sonnet")),
           "--no-session-persistence", "--setting-sources", "local", "--system-prompt", SYSTEM]
    with tempfile.TemporaryDirectory() as tmp:
        done = runner(cmd, capture_output=True, text=True, timeout=timeout, cwd=tmp)
    if done.returncode != 0:
        raise RuntimeError(f"claude exited {done.returncode}: {done.stderr.strip()[:200]}")
    payload = json.loads(done.stdout)
    if payload.get("is_error"):
        raise RuntimeError(str(payload.get("result"))[:200])
    out = payload.get("structured_output") or json.loads(payload["result"][payload["result"].find("{"):])
    out["code"] = re.sub(r"^```(?:python)?\s*|\s*```$", "", out["code"].strip())
    return out


def generate(text: str, out_root: Path = Path("out"), runner=subprocess.run, attempts: int = 2) -> dict:
    """Ask, verify, and on failure ask again once with the failure reasons attached."""
    history = []
    prompt = text
    for i in range(attempts):
        ai = ask_ai(prompt, runner=runner)
        verdict, step = verify(text, ai["code"], ai.get("expected_bbox_mm") or [])
        history.append({"attempt": i + 1, "ok": verdict.ok, "reasons": verdict.reasons,
                        "measured": verdict.measured, "declared": verdict.declared_bbox})
        if verdict.ok:
            out = Path(out_root) / f"codegen_{datetime.now():%Y%m%d-%H%M%S}"
            out.mkdir(parents=True, exist_ok=True)
            shutil.copy(str(step), out / "part.step")
            (out / "code.py").write_text(ai["code"])
            (out / "verification.json").write_text(json.dumps(history, indent=1))
            _viewer(out, text)
            return {"ok": True, "out": str(out), "attempts": history, "code": ai["code"]}
        prompt = (f"{text}\n\nYour previous code failed these checks: {'; '.join(verdict.reasons)}. "
                  "Fix it and follow the rules exactly.")
    return {"ok": False, "attempts": history}


def _viewer(out: Path, text: str) -> None:
    import base64

    import cadquery as cq

    from .export import VIEWER_JS
    shape = cq.importers.importStep(str(out / "part.step"))
    a = cq.Assembly(name="ai_part")
    a.add(shape, name="part", color=cq.Color(0.55, 0.6, 0.85, 1.0))
    a.export(str(out / "part.glb"))
    glb = base64.b64encode((out / "part.glb").read_bytes()).decode()
    js = VIEWER_JS.read_text() if VIEWER_JS.exists() else ""
    safe = text.replace("<", "&lt;")
    (out / "viewer.html").write_text(
        f'<!doctype html><html><head><meta charset="utf-8"><title>AI-written part</title>'
        f'<script type="module">{js}</script><style>body{{margin:0;font-family:system-ui}}'
        f'model-viewer{{width:100%;height:80vh}}</style></head><body><p style="padding:12px">'
        f'AI-written part (experimental, verified by size and validity only): {safe}</p>'
        f'<model-viewer src="data:model/gltf-binary;base64,{glb}" camera-controls auto-rotate></model-viewer>'
        f'</body></html>')


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="aicad.codegen")
    ap.add_argument("request", nargs="+")
    args = ap.parse_args(argv)
    text = " ".join(args.request)
    r = generate(text)
    for a in r["attempts"]:
        print(f"attempt {a['attempt']}: {'PASS' if a['ok'] else 'FAIL'} {'; '.join(a['reasons'])}")
    if r["ok"]:
        print(f"Done: {r['out']}  (part.step, code.py, verification.json, viewer.html)")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
