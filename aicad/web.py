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
from pathlib import Path

from .joints import REGISTRY
from .parse import Spec, parse

OUT_ROOT = Path("out") / "web"
_BUILD_LOCK = threading.Lock()  # FreeCAD and the geometry kernel are not run in parallel


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
    def say(msg):
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
    from .export import export_all
    from .joints import parts_of
    names = parts_of(joint, design.dims)
    say(f"Sized: {len(design.dims)} dimensions, {len(design.checks)} strength checks")
    with _BUILD_LOCK:
        say(f"Building {len(names)} solid parts")
        parts = joint.build_parts(design.dims)
        say("Writing STEP files, assembly, exploded and weak-spot views")
        export_all(parts, design, joint, out, request=text)
        fc = None
        if freecad:
            from .freecad_pack import run_pack
            say("Drawing the A3 first-angle sheet in FreeCAD")
            fc = run_pack(out, joint, design, text)
    say("Done")

    files = {"viewer": "viewer.html", "assembly_step": "assembly.step", "report": "report.md"}
    files.update({f"part_{p}": f"parts/{p}.step" for p in joint.PARTS})
    if fc and fc.get("ok"):
        files.update({"drawing": "drawing.svg", "fcstd": f"{joint.NAME}.FCStd"})
        if fc.get("dxf"):
            files["dxf"] = "drawing.dxf"
    return {
        "ok": True,
        "id": run_id,
        "title": joint.TITLE,
        "load_n": design.load_n,
        "duty": design.duty,
        "dims": [{"key": k, "label": joint.LABELS.get(k, k), "value": v, "rule": design.rules.get(k, "")}
                 for k, v in design.dims.items()],
        "checks": [{"name": c.name, "stress": round(c.stress_mpa, 1), "allowed": c.allowable_mpa,
                    "formula": c.formula, "passed": c.passed} for c in design.checks],
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
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj):
        self._send(code, json.dumps(obj, default=str).encode(), "application/json")

    def do_GET(self):
        if self.path.startswith("/api/job/"):
            job = JOBS.get(self.path.rsplit("/", 1)[-1])
            return self._json(200 if job else 404, job or {"error": "unknown job"})
        if self.path in ("/", "/index.html"):
            return self._send(200, PAGE.encode(), "text/html; charset=utf-8")
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
            if self.path == "/api/build":
                return self._json(200, build(body.get("fields", {}), body.get("text", ""),
                                             freecad=self.freecad, out_root=self.out_root))
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
    ap.add_argument("--no-freecad", action="store_true")
    args = ap.parse_args(argv)
    srv = make_server(port=args.port, freecad=not args.no_freecad)
    print(f"aicad web app on http://127.0.0.1:{args.port}  (Ctrl+C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>aicad</title>
<style>
:root{
  --bg:#f4f5f7; --panel:#fff; --ink:#15181d; --muted:#5f6672; --line:#e2e5ea;
  --accent:#2c5fd0; --accent-ink:#fff; --ok:#177245; --warn:#8a5a00; --bad:#b3261e;
  --shadow:0 1px 2px rgba(16,20,28,.06),0 8px 24px rgba(16,20,28,.06); --r:12px;
}
@media (prefers-color-scheme:dark){:root{
  --bg:#0f1115; --panel:#171a20; --ink:#e8eaee; --muted:#9aa2b1; --line:#262b34;
  --accent:#7fa6ff; --accent-ink:#0f1115; --ok:#5fcf8a; --warn:#e3b341; --bad:#ff8a80;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35);}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif}
a{color:var(--accent)}
.wrap{max-width:1180px;margin:0 auto;padding:22px 18px 60px}
header h1{margin:0;font-size:24px;letter-spacing:-.01em}
header p{margin:4px 0 18px;color:var(--muted)}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:var(--r);box-shadow:var(--shadow);padding:16px;margin-bottom:16px}
.step{display:flex;align-items:center;gap:8px;font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:10px}
.step b{display:grid;place-items:center;width:20px;height:20px;border-radius:50%;background:var(--accent);color:var(--accent-ink);font-size:12px}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end}
input,select,button,textarea{font:inherit;color:var(--ink);background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:10px 12px}
input:focus,select:focus{outline:2px solid color-mix(in srgb,var(--accent) 45%,transparent);border-color:var(--accent)}
#text,#ask{flex:1;min-width:260px}
button{background:var(--accent);color:var(--accent-ink);border:none;cursor:pointer;font-weight:600}
button.ghost{background:transparent;color:var(--ink);border:1px solid var(--line);font-weight:500}
button:disabled{opacity:.45;cursor:default}
label{display:flex;flex-direction:column;gap:5px;font-size:12.5px;color:var(--muted)}
.chips{display:flex;gap:7px;flex-wrap:wrap;margin-top:10px}
.chip{border:1px solid var(--line);border-radius:999px;padding:5px 11px;font-size:13px;cursor:pointer;background:transparent;color:var(--muted);font-weight:500}
.chip:hover{border-color:var(--accent);color:var(--ink)}
.missing input,.missing select{border-color:var(--bad);box-shadow:0 0 0 3px color-mix(in srgb,var(--bad) 18%,transparent)}
#question:not(:empty){margin-top:12px;padding:11px 13px;border-radius:9px;font-weight:600;
  background:color-mix(in srgb,var(--warn) 13%,transparent);border:1px solid color-mix(in srgb,var(--warn) 45%,transparent)}
.note{color:var(--warn);font-size:13.5px;margin:6px 0 0}
.err{color:var(--bad)}
.muted{color:var(--muted)}
.hidden{display:none}
progress{width:100%;height:6px;appearance:none;border:0;border-radius:99px;overflow:hidden;background:var(--line)}
progress::-webkit-progress-bar{background:var(--line)}progress::-webkit-progress-value{background:var(--accent)}
#log{margin:10px 0 0;padding:0;list-style:none;font-size:13.5px;color:var(--muted)}
#log li{padding:3px 0 3px 22px;position:relative}
#log li::before{content:"●";position:absolute;left:4px;color:var(--accent)}
#log li.done::before{content:"✓";color:var(--ok)}
.tabs{display:flex;gap:4px;border-bottom:1px solid var(--line);margin:-4px -4px 14px;padding:0 4px}
.tab{background:transparent;color:var(--muted);border:0;border-bottom:2px solid transparent;border-radius:0;padding:9px 13px;font-weight:600}
.tab[aria-selected=true]{color:var(--ink);border-bottom-color:var(--accent)}
iframe{width:100%;height:520px;border:0;border-radius:10px;background:var(--bg)}
img.sheet{width:100%;border:1px solid var(--line);border-radius:10px;background:#fff}
table{border-collapse:collapse;width:100%;font-size:14px}
th{text-align:left;font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);font-weight:600}
td,th{padding:7px 8px;border-bottom:1px solid var(--line)}
td.num{text-align:right;font-variant-numeric:tabular-nums}
tr.bad td{background:color-mix(in srgb,var(--bad) 9%,transparent)}
.bar{height:6px;border-radius:99px;background:var(--line);overflow:hidden;min-width:70px}
.bar i{display:block;height:100%}
.pass{color:var(--ok);font-weight:600}.fail{color:var(--bad);font-weight:700}
.files a{display:inline-block;margin:0 10px 8px 0;font-size:13.5px}
.thread{display:flex;flex-direction:column;gap:10px;margin-bottom:12px}
.bub{padding:10px 13px;border-radius:12px;max-width:80%;font-size:14px;white-space:pre-wrap}
.me{align-self:flex-end;background:var(--accent);color:var(--accent-ink)}
.it{align-self:flex-start;background:color-mix(in srgb,var(--ink) 6%,transparent);border:1px solid var(--line)}
.kpi{display:flex;gap:18px;flex-wrap:wrap;margin:2px 0 12px}
.kpi div{font-size:13px;color:var(--muted)}.kpi b{display:block;font-size:19px;color:var(--ink);font-weight:650}
</style></head><body><div class="wrap">
<header><h1>aicad</h1><p>Say what you need. It sizes the joint, checks every way it can fail, and draws it.</p></header>

<section class="panel">
  <div class="step"><b>1</b> what do you need</div>
  <div class="row">
    <input id="text" placeholder="knuckle joint for 50 kN" autofocus>
    <label>reader<select id="parser">
      <option value="auto">AI, else rules</option><option value="rules">rules only (offline)</option><option value="ai">AI only</option>
    </select></label>
    <button id="go">Understand</button>
  </div>
  <div class="chips" id="chips"></div>
  <div id="status" class="muted" style="margin-top:10px"></div>
</section>

<section id="specCard" class="panel hidden">
  <div class="step"><b>2</b> check the numbers</div>
  <div class="muted" id="source"></div>
  <div id="question"></div>
  <div class="row" style="margin-top:12px">
    <label id="f-joint">joint<select id="joint"></select></label>
    <label id="f-load">load (kN)<input id="load" type="number" step="any" min="0" placeholder="e.g. 50"></label>
    <label id="f-dia">rod diameter (mm)<input id="dia" type="number" step="any" min="0" placeholder="or e.g. 30"></label>
    <label id="f-bolt">bolt size M<input id="bolt" type="number" step="1" min="0" placeholder="e.g. 12"></label>
    <label id="f-grip">grip (mm)<input id="grip" type="number" step="any" min="0"></label>
    <label id="f-torque">torque (N m)<input id="torque" type="number" step="any" min="0" placeholder="e.g. 500"></label>
    <label id="f-power">power (kW)<input id="power" type="number" step="any" min="0"></label>
    <label id="f-speed">speed (rpm)<input id="speed" type="number" step="any" min="0"></label>
    <button id="build">Build</button>
  </div>
  <div id="notes"></div>
  <div id="cgBox" class="hidden" style="margin-top:12px">
    <p class="muted">Not a library joint? The AI can write the CAD code. Experimental: shown only if it builds
    one valid solid of the sizes you asked for, and features like holes are not checked.</p>
    <button id="cgBtn" class="ghost">Try AI-written CAD</button>
    <div id="cgOut" style="margin-top:10px"></div>
  </div>
</section>

<section id="progCard" class="panel hidden">
  <div class="step"><b>3</b> building</div>
  <progress id="prog" max="5" value="0"></progress>
  <ul id="log"></ul>
</section>

<section id="result" class="panel hidden">
  <div class="tabs" role="tablist">
    <button class="tab" data-tab="v3d" aria-selected="true">3D model</button>
    <button class="tab" data-tab="vsheet">Drawing</button>
    <button class="tab" data-tab="vdims">Dimensions</button>
    <button class="tab" data-tab="vchecks">Checks</button>
    <button class="tab" data-tab="vfiles">Files</button>
  </div>
  <h2 id="rtitle" style="margin:0 0 2px;font-size:19px"></h2>
  <div class="muted" id="rsub" style="margin-bottom:12px"></div>
  <div class="kpi" id="kpi"></div>
  <div id="v3d"><iframe id="viewer"></iframe></div>
  <div id="vsheet" class="hidden"><div id="sheetBox"></div></div>
  <div id="vdims" class="hidden"><table id="dims"></table></div>
  <div id="vchecks" class="hidden"><table id="checks"></table></div>
  <div id="vfiles" class="hidden"><div class="files" id="files"></div></div>
  <div id="rnotes"></div>
</section>

<section id="askCard" class="panel hidden">
  <div class="step"><b>4</b> ask or change</div>
  <div class="thread" id="thread"></div>
  <div class="row">
    <input id="ask" placeholder="make it 80 kN  /  why is the pin 45 mm  /  how much load can this take  /  make it lighter">
    <button id="askBtn">Send</button>
  </div>
</section>
</div>
<script>
const $=id=>document.getElementById(id);
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
let joints={}, lastText="", lastFields=null;
const EXAMPLES=["knuckle joint for 50 kN","socket and spigot joint for 35 kN","sleeve and cotter joint for 50 kN",
  "M16 nut bolt, plates 30 mm thick, load 20 kN","flange coupling to transmit 20 kW at 1440 rpm"];
$("chips").innerHTML=EXAMPLES.map(e=>`<button class="chip">${esc(e)}</button>`).join("");
$("chips").onclick=e=>{if(e.target.classList.contains("chip")){$("text").value=e.target.textContent;$("go").click();}};
document.querySelectorAll(".tab").forEach(t=>t.onclick=()=>{
  document.querySelectorAll(".tab").forEach(x=>x.setAttribute("aria-selected",x===t));
  ["v3d","vsheet","vdims","vchecks","vfiles"].forEach(id=>$(id).classList.toggle("hidden",id!==t.dataset.tab));
});
async function post(u,b){const r=await fetch(u,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(b)});return r.json();}
function showFields(){
  const j=$("joint").value;
  const vis={"f-load":j!=="flange_coupling","f-dia":j!=="nut_bolt","f-bolt":j==="nut_bolt","f-grip":j==="nut_bolt",
             "f-torque":j==="flange_coupling","f-power":j==="flange_coupling","f-speed":j==="flange_coupling"};
  for(const k in vis) $(k).classList.toggle("hidden",!vis[k]);
}
$("joint").onchange=showFields;
$("text").addEventListener("keydown",e=>{if(e.key==="Enter")$("go").click();});
["load","dia","bolt","grip","torque","power","speed"].forEach(i=>{
  $(i).addEventListener("keydown",e=>{if(e.key==="Enter")$("build").click();});
  $(i).addEventListener("input",()=>document.querySelectorAll(".missing").forEach(n=>n.classList.remove("missing")));
});
$("go").onclick=async()=>{
  lastText=$("text").value.trim(); if(!lastText)return;
  $("go").disabled=true; $("status").textContent="Reading your request (the AI takes 10 to 20 s)...";
  ["result","askCard","progCard"].forEach(i=>$(i).classList.add("hidden"));
  try{
    const r=await post("/api/understand",{text:lastText,parser:$("parser").value});
    joints=r.joints; const s=r.spec;
    $("joint").innerHTML='<option value="">choose...</option>'+Object.entries(joints)
      .map(([k,v])=>`<option value="${k}">${esc(v.title)} (${v.parts} parts)</option>`).join("");
    $("joint").value=s.joint&&joints[s.joint]?s.joint:"";
    $("load").value=s.load_n!=null?+(s.load_n/1000).toFixed(4):""; $("dia").value=s.rod_diameter_mm??"";
    $("bolt").value=s.bolt_size??""; $("grip").value=s.grip_mm??"";
    $("torque").value=s.torque_nm??""; $("power").value=s.power_kw??""; $("speed").value=s.speed_rpm??"";
    showFields();
    document.querySelectorAll(".missing").forEach(n=>n.classList.remove("missing"));
    const q=[];
    if(s.joint&&!joints[s.joint]) q.push(`"${s.joint}" is recognised but not built yet. Pick another joint below.`);
    for(const m of r.missing){
      if(m==="joint type"){$("f-joint").classList.add("missing");q.push("Which joint?");}
      if(m==="load or rod diameter"){$("f-load").classList.add("missing");$("f-dia").classList.add("missing");q.push("What load must it carry? Or give the rod diameter.");}
      if(m==="load or bolt size"){$("f-load").classList.add("missing");$("f-bolt").classList.add("missing");q.push("What load must it carry? Or give the bolt size.");}
      if(m.startsWith("torque")){$("f-torque").classList.add("missing");q.push("What torque must it transmit? Or give power and speed.");}
    }
    if(q.length) q.push("Fill the red box, then press Build (or Enter).");
    $("question").textContent=q.join(" ");
    $("source").textContent="Read by: "+r.source;
    $("notes").innerHTML=r.notes.map(n=>`<p class="note">${esc(n)}</p>`).join("");
    $("specCard").classList.remove("hidden"); $("status").textContent="";
    $("cgBox").classList.toggle("hidden", !!(s.joint&&joints[s.joint])); $("cgOut").innerHTML="";
    const miss=document.querySelector("#specCard .missing:not(.hidden) input, #specCard .missing:not(.hidden) select");
    if(miss){miss.focus();miss.scrollIntoView({block:"center"});} else $("build").focus();
  }catch(e){$("status").innerHTML=`<span class="err">${esc(e)}</span>`;}
  finally{$("go").disabled=false;}
};
function fields(){
  const j=$("joint").value, num=id=>$(id).value?+$(id).value:null;
  return {joint:j, load_n:$("load").value?+$("load").value*1000:null, rod_diameter_mm:num("dia"),
          bolt_size:num("bolt"), grip_mm:num("grip"), torque_nm:num("torque"), power_kw:num("power"), speed_rpm:num("speed")};
}
async function runBuild(f){
  $("progCard").classList.remove("hidden"); $("log").innerHTML=""; $("prog").value=0;
  const {job}=await post("/api/build_async",{fields:f,text:lastText});
  let seen=0;
  for(;;){
    await new Promise(r=>setTimeout(r,600));
    const st=await (await fetch("/api/job/"+job)).json();
    while(seen<st.progress.length){
      const li=document.createElement("li"); li.textContent=st.progress[seen++]; $("log").appendChild(li);
      $("log").querySelectorAll("li").forEach((n,i,a)=>n.classList.toggle("done",i<a.length-1));
      $("prog").value=seen;
    }
    if(st.done){$("log").querySelectorAll("li").forEach(n=>n.classList.add("done")); $("prog").value=5; return st.result;}
  }
}
$("build").onclick=async()=>{
  const f=fields(); $("build").disabled=true; $("status").textContent="";
  try{
    const r=await runBuild(f);
    if(!r.ok){$("status").innerHTML=`<span class="err">${esc(r.error||("Still missing: "+(r.missing||[]).join(", ")))}</span>`;return;}
    lastFields=f; render(r); $("thread").innerHTML=""; $("askCard").classList.remove("hidden");
  }catch(e){$("status").innerHTML=`<span class="err">${esc(e)}</span>`;}
  finally{$("build").disabled=false;}
};
function render(r){
  $("rtitle").textContent=r.title;
  $("rsub").textContent=(r.duty||"")+(r.verified?"":" · rules not yet checked against the design book");
  const worst=(r.checks||[]).reduce((a,c)=>Math.max(a,c.stress/c.allowed),0);
  $("kpi").innerHTML=[
    ["parts",Object.keys(r.files).filter(k=>k.startsWith("part_")).length],
    ["checks",(r.checks||[]).length+" run, "+(r.checks||[]).filter(c=>c.passed).length+" pass"],
    ["closest to its limit",worst?Math.round(worst*100)+"%":"-"],
    ["sheet",r.sheet_scale?("scale "+r.sheet_scale+", first angle"):"not made"],
  ].map(([k,v])=>`<div>${k}<b>${esc(v)}</b></div>`).join("");
  $("viewer").src=r.files.viewer;
  $("sheetBox").innerHTML=r.files.drawing
    ?`<a href="${r.files.drawing}" target="_blank"><img class="sheet" src="${r.files.drawing}" alt="drawing sheet"></a>`
    :`<p class="muted">No sheet: ${esc(r.freecad_reason)}. Install FreeCAD to get one.</p>`;
  $("dims").innerHTML="<tr><th>symbol</th><th>meaning</th><th>mm</th></tr>"+
    r.dims.map(d=>`<tr><td>${esc(d.key)}</td><td class="muted">${esc(d.label)}</td><td class="num">${d.value}</td></tr>`).join("");
  $("checks").innerHTML=(r.checks||[]).length
    ?"<tr><th>check</th><th>stress</th><th>allowed</th><th>used</th><th></th></tr>"+r.checks.map(c=>{
      const u=Math.min(1,c.stress/c.allowed), col=u>.9?"var(--bad)":u>.75?"var(--warn)":"var(--ok)";
      return `<tr class="${c.passed?"":"bad"}"><td>${esc(c.name)}</td><td class="num">${c.stress}</td><td class="num">${c.allowed}</td>
      <td><div class="bar"><i style="width:${Math.round(u*100)}%;background:${col}"></i></div></td>
      <td class="${c.passed?"pass":"fail"}">${c.passed?"pass":"FAIL"}</td></tr>`;}).join("")
    :'<tr><td class="muted">No load given, so no checks.</td></tr>';
  const names={viewer:"3D viewer",assembly_step:"assembly.step",drawing:"drawing.svg",fcstd:"FreeCAD file",dxf:"drawing.dxf",report:"report.md"};
  $("files").innerHTML=Object.entries(r.files).map(([k,u])=>
    `<a href="${u}" ${k==="viewer"||k==="drawing"?'target="_blank"':"download"}>${esc(names[k]||k.replace("part_","")+".step")}</a>`).join("");
  $("rnotes").innerHTML=(r.notes||[]).map(n=>`<p class="note">${esc(n)}</p>`).join("");
  $("result").classList.remove("hidden");
}
function bubble(cls,text){const d=document.createElement("div");d.className="bub "+cls;d.textContent=text;$("thread").appendChild(d);d.scrollIntoView({block:"nearest"});}
$("ask").addEventListener("keydown",e=>{if(e.key==="Enter")$("askBtn").click();});
$("askBtn").onclick=async()=>{
  const q=$("ask").value.trim(); if(!q||!lastFields)return;
  bubble("me",q); $("ask").value=""; $("askBtn").disabled=true;
  try{
    const r=await post("/api/followup",{fields:lastFields,text:q,parser:$("parser").value});
    bubble("it",r.message||r.error||"");
    if(r.kind==="change"&&r.fields){
      const f=Object.assign({},r.fields); lastText+=" | "+q;
      const out=await runBuild(f);
      if(out.ok){lastFields=f; render(out); bubble("it","Rebuilt with the change.");}
      else bubble("it","Could not rebuild: "+(out.error||""));
    }
  }catch(e){bubble("it",String(e));}
  finally{$("askBtn").disabled=false;}
};
$("cgBtn").onclick=async()=>{
  $("cgBtn").disabled=true; $("cgOut").textContent="The AI is writing the code and the tool is checking it (1 to 3 minutes)...";
  try{
    const r=await post("/api/codegen",{text:lastText});
    const att=(r.attempts||[]).map(a=>`attempt ${a.attempt}: ${a.ok?"passed every check":"failed: "+esc((a.reasons||[]).join("; "))}`).join("<br>");
    $("cgOut").innerHTML=r.ok
      ?`${att}<div class="files" style="margin-top:8px"><a href="${r.files.step}" download>part.step</a><a href="${r.files.code}" target="_blank">code.py</a></div><iframe src="${r.files.viewer}" style="height:430px"></iframe>`
      :`<span class="err">No part shown: it did not pass the checks.</span><br>${att}`;
  }catch(e){$("cgOut").textContent=String(e);}
  finally{$("cgBtn").disabled=false;}
};
</script></body></html>
"""

if __name__ == "__main__":
    raise SystemExit(main())
