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


def build(fields: dict, text: str, freecad: bool = True, out_root: Path = OUT_ROOT) -> dict:
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
    with _BUILD_LOCK:
        export_all(joint.build_parts(design.dims), design, joint, out, request=text)
        fc = None
        if freecad:
            from .freecad_pack import run_pack
            fc = run_pack(out, joint, design, text)

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
                                                 "tension_mpa", "shear_mpa", "crushing_mpa")}
    return {"kind": r.kind, "message": r.message, "fields": new, "changes": r.changes,
            "value": r.value, "governing": r.governing}


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
<title>AI in CAD</title>
<style>
:root{--bg:#f6f6f3;--card:#fff;--fg:#1b1b1b;--muted:#666;--line:#ddd;--acc:#1f5fbf;--ok:#1e7a3a;--bad:#b3261e;--warn:#8a5a00}
@media (prefers-color-scheme: dark){:root{--bg:#141414;--card:#1e1e1e;--fg:#eee;--muted:#aaa;--line:#333;--acc:#7aa7ff;--ok:#6fcf8a;--bad:#ff8a80;--warn:#e0b050}}
*{box-sizing:border-box} body{margin:0;font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:var(--bg);color:var(--fg)}
header{padding:18px 20px 6px} h1{margin:0;font-size:22px} header p{margin:4px 0 0;color:var(--muted)}
main{padding:12px 20px 40px;max-width:1300px;margin:0 auto}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;margin-bottom:14px}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
input,select,button{font:inherit;padding:8px 10px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--fg)}
#text{flex:1;min-width:240px} button{background:var(--acc);color:#fff;border:none;cursor:pointer} button:disabled{opacity:.5}
label{display:flex;flex-direction:column;font-size:13px;color:var(--muted);gap:4px}
.missing input,.missing select{border-color:var(--bad);outline:2px solid color-mix(in srgb,var(--bad) 30%,transparent)}
.note{color:var(--warn);font-size:14px;margin:6px 0 0} .err{color:var(--bad)}
#question:not(:empty){background:color-mix(in srgb,var(--warn) 14%,transparent);border:1px solid var(--warn);color:var(--fg);font-size:16px;font-weight:600;padding:10px 12px;border-radius:8px;margin-top:10px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px} @media (max-width:900px){.grid{grid-template-columns:1fr}}
iframe{width:100%;height:520px;border:0;border-radius:8px;background:var(--bg)}
.sheet{width:100%;background:#fff;border-radius:8px;border:1px solid var(--line)}
table{border-collapse:collapse;width:100%;font-size:14px} td,th{padding:5px 6px;border-bottom:1px solid var(--line);text-align:left}
td.num{text-align:right;font-variant-numeric:tabular-nums} .pass{color:var(--ok);font-weight:600} .fail{color:var(--bad);font-weight:600}
.files a{margin-right:12px;display:inline-block;margin-bottom:6px} .muted{color:var(--muted)} .hidden{display:none}
</style></head><body>
<header><h1>AI in CAD</h1><p>Type the joint you need, in English.</p></header>
<main>
<div class="card">
  <div class="row">
    <input id="text" placeholder="e.g. knuckle joint for 50 kN, or: a two tonne cotter joint" autofocus>
    <select id="parser"><option value="auto">AI, else rules</option><option value="rules">rules only (offline)</option><option value="ai">AI only</option></select>
    <button id="go">Understand</button>
  </div>
  <div id="status" class="muted" style="margin-top:8px"></div>
</div>

<div id="specCard" class="card hidden">
  <div class="muted" id="source"></div>
  <div id="question" class="note"></div>
  <div class="row" style="margin-top:10px">
    <label id="f-joint">Joint<select id="joint"></select></label>
    <label id="f-load">Load (kN)<input id="load" type="number" step="any" min="0" placeholder="e.g. 35"></label>
    <label id="f-dia">Rod diameter (mm)<input id="dia" type="number" step="any" min="0" placeholder="or e.g. 25"></label>
    <label id="f-bolt">Bolt size M<input id="bolt" type="number" step="1" min="0" placeholder="e.g. 12"></label>
    <label id="f-grip">Grip (mm)<input id="grip" type="number" step="any" min="0"></label>
    <button id="build" style="align-self:flex-end">Build</button>
  </div>
  <div id="notes"></div>
  <div id="cgBox" class="hidden" style="margin-top:10px">
    <p class="muted">Not a library joint? Let the AI write the CAD code. Experimental: the tool only shows the part
    if it builds one valid solid of the sizes you asked for, and it cannot check holes or other features.</p>
    <button id="cgBtn">Try AI-written CAD</button>
    <div id="cgOut" style="margin-top:8px"></div>
  </div>
</div>

<div id="result" class="hidden">
  <div class="card"><div class="row" style="justify-content:space-between">
    <div><b id="rtitle"></b> <span class="muted" id="rsub"></span></div>
    <div class="files" id="files"></div></div>
    <div id="rnotes"></div>
    <div class="row" style="margin-top:10px">
      <input id="ask" style="flex:1;min-width:240px" placeholder="Ask or change: make it 80 kN / why is the pin 45 mm / how much load can this take / make it lighter">
      <button id="askBtn">Ask</button></div>
    <div id="answer" class="note" style="color:var(--fg)"></div></div>
  <div class="grid">
    <div class="card"><b>3D model</b><iframe id="viewer"></iframe></div>
    <div class="card"><b>Drawing sheet</b> <span class="muted" id="scale"></span><div id="sheetBox" style="margin-top:8px"></div></div>
  </div>
  <div class="grid">
    <div class="card"><b>Dimensions (mm)</b><table id="dims"></table></div>
    <div class="card"><b>Strength checks</b><table id="checks"></table></div>
  </div>
</div>
</main>
<script>
const $=id=>document.getElementById(id);
let joints={}, lastText="", lastFields=null;
async function post(url, body){const r=await fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});return r.json();}
function esc(s){return String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));}
function showFields(){
  const j=$("joint").value, bolt=j==="nut_bolt";
  $("f-dia").classList.toggle("hidden",bolt); $("f-bolt").classList.toggle("hidden",!bolt); $("f-grip").classList.toggle("hidden",!bolt);
}
$("joint").onchange=showFields;
$("text").addEventListener("keydown",e=>{if(e.key==="Enter")$("go").click();});
["load","dia","bolt","grip"].forEach(i=>$(i).addEventListener("keydown",e=>{if(e.key==="Enter")$("build").click();}));
["load","dia","bolt"].forEach(i=>$(i).addEventListener("input",()=>{
  if($(i).value){["f-load","f-dia","f-bolt"].forEach(f=>$(f).classList.remove("missing"));}}));
$("go").onclick=async()=>{
  lastText=$("text").value.trim(); if(!lastText)return;
  $("go").disabled=true; $("status").textContent="Understanding... (the AI can take 10 to 20 s)"; $("result").classList.add("hidden");
  try{
    const r=await post("/api/understand",{text:lastText,parser:$("parser").value});
    if(r.error){$("status").innerHTML='<span class="err">'+esc(r.error)+'</span>';return;}
    joints=r.joints; const s=r.spec;
    $("joint").innerHTML='<option value="">choose...</option>'+Object.entries(joints).map(([k,v])=>`<option value="${k}">${esc(v.title)} (${v.parts} parts)</option>`).join("");
    $("joint").value=s.joint&&joints[s.joint]?s.joint:"";
    $("load").value=s.load_n!=null?+(s.load_n/1000).toFixed(4):""; $("dia").value=s.rod_diameter_mm??"";
    $("bolt").value=s.bolt_size??""; $("grip").value=s.grip_mm??"";
    showFields();
    ["f-joint","f-load","f-dia","f-bolt"].forEach(i=>$(i).classList.remove("missing"));
    let q=[];
    if(s.joint&&!joints[s.joint]) q.push(`"${s.joint}" is recognised but not built yet. Pick another joint.`);
    for(const m of r.missing){
      if(m==="joint type"){$("f-joint").classList.add("missing");q.push("Which joint?");}
      if(m==="load or rod diameter"){$("f-load").classList.add("missing");$("f-dia").classList.add("missing");q.push("What load must it carry? Or give the rod diameter.");}
      if(m==="load or bolt size"){$("f-load").classList.add("missing");$("f-bolt").classList.add("missing");q.push("What load must it carry? Or give the bolt size.");}
    }
    if(q.length) q.push("Fill the red box, then press Build (or Enter).");
    $("question").textContent=q.join(" ");
    $("source").textContent="Understood by: "+r.source;
    $("notes").innerHTML=r.notes.map(n=>'<p class="note">'+esc(n)+'</p>').join("");
    $("specCard").classList.remove("hidden"); $("status").textContent="";
    $("cgBox").classList.toggle("hidden", !!(s.joint && joints[s.joint])); $("cgOut").innerHTML="";
    const firstMissing=document.querySelector("#specCard .missing:not(.hidden) input, #specCard .missing:not(.hidden) select");
    if(firstMissing){firstMissing.focus();firstMissing.scrollIntoView({block:"center"});}
    else if(r.supported) $("build").focus();
  }catch(e){$("status").innerHTML='<span class="err">'+esc(e)+'</span>';}
  finally{$("go").disabled=false;}
};
$("build").onclick=async()=>{
  const j=$("joint").value, bolt=j==="nut_bolt";
  const fields={joint:j,load_n:$("load").value?+$("load").value*1000:null,
    rod_diameter_mm:bolt?null:($("dia").value||null),bolt_size:bolt?($("bolt").value||null):null,grip_mm:bolt?($("grip").value||null):null};
  $("build").disabled=true; $("status").textContent="Building solids, FreeCAD file and drawing sheet... (about 10 to 40 s)";
  try{
    const r=await post("/api/build",{fields,text:lastText});
    if(r.ok) lastFields=Object.assign({},fields,{tension_mpa:fields.tension_mpa??null,shear_mpa:fields.shear_mpa??null,crushing_mpa:fields.crushing_mpa??null});
    if(!r.ok){$("status").innerHTML='<span class="err">'+esc(r.error||("Still missing: "+(r.missing||[]).join(", ")))+'</span>';return;}
    await renderBuild(r); $("status").textContent="";
  }catch(e){$("status").innerHTML='<span class="err">'+esc(e)+'</span>';}
  finally{$("build").disabled=false;}
};
async function renderBuild(r){
    $("rtitle").textContent=r.title;
    $("rsub").textContent=(r.load_n?` for ${(r.load_n/1000).toLocaleString()} kN`:" from the rod size")+(r.verified?"":" (rules not yet checked against the design book)");
    const names={viewer:"3D viewer",assembly_step:"assembly.step",drawing:"drawing.svg",fcstd:"FreeCAD file",dxf:"drawing.dxf",report:"report.md"};
    $("files").innerHTML=Object.entries(r.files).map(([k,u])=>`<a href="${u}" ${k==="viewer"||k==="drawing"?'target="_blank"':"download"}>${esc(names[k]||k.replace("part_","")+".step")}</a>`).join("");
    $("viewer").src=r.files.viewer;
    $("sheetBox").innerHTML=r.files.drawing?`<a href="${r.files.drawing}" target="_blank"><img class="sheet" src="${r.files.drawing}" alt="drawing sheet"></a>`:`<p class="muted">No sheet: ${esc(r.freecad_reason)}. Install FreeCAD to get one.</p>`;
    $("scale").textContent=r.sheet_scale?"scale "+r.sheet_scale+", first angle":"";
    $("dims").innerHTML=r.dims.map(d=>`<tr><td>${esc(d.key)}</td><td>${esc(d.label)}</td><td class="num">${d.value}</td></tr>`).join("");
    $("checks").innerHTML=r.checks.length?r.checks.map(c=>`<tr><td>${esc(c.name)}</td><td class="num">${c.stress}</td><td class="num">${c.allowed}</td><td class="${c.passed?"pass":"fail"}">${c.passed?"pass":"FAIL"}</td></tr>`).join(""):'<tr><td class="muted">No load given, so no checks.</td></tr>';
    $("rnotes").innerHTML=r.notes.map(n=>'<p class="note">'+esc(n)+'</p>').join("");
    $("result").classList.remove("hidden");
}
$("cgBtn").onclick=async()=>{
  $("cgBtn").disabled=true; $("cgOut").textContent="The AI is writing and the tool is checking the code (about 1 to 3 minutes)...";
  try{
    const r=await post("/api/codegen",{text:lastText});
    const att=(r.attempts||[]).map(a=>`attempt ${a.attempt}: ${a.ok?"passed":"failed: "+esc((a.reasons||[]).join("; "))}`).join("<br>");
    $("cgOut").innerHTML=r.ok?`${att}<br><a href="${r.files.step}" download>part.step</a> <a href="${r.files.code}" target="_blank">code.py</a><iframe src="${r.files.viewer}" style="height:420px"></iframe>`
      :`<span class="err">No part shown: it did not pass the checks.</span><br>${att}`;
  }catch(e){$("cgOut").textContent=String(e);}
  finally{$("cgBtn").disabled=false;}
};
$("ask").addEventListener("keydown",e=>{if(e.key==="Enter")$("askBtn").click();});
$("askBtn").onclick=async()=>{
  const q=$("ask").value.trim(); if(!q||!lastFields)return;
  $("askBtn").disabled=true; $("answer").textContent="Thinking...";
  try{
    const r=await post("/api/followup",{fields:lastFields,text:q,parser:$("parser").value});
    $("answer").textContent=r.message||r.error||"";
    if(r.kind==="change"&&r.fields){
      const f=r.fields; $("joint").value=f.joint||""; showFields();
      $("load").value=f.load_n!=null?+(f.load_n/1000).toFixed(4):""; $("dia").value=f.rod_diameter_mm??"";
      $("bolt").value=f.bolt_size??""; $("grip").value=f.grip_mm??"";
      lastText=lastText+" | "+q;
      const keep=$("answer").textContent;
      const fields=Object.assign({},f); 
      $("status").textContent="Rebuilding with the change... (about 10 to 40 s)";
      const b=await post("/api/build",{fields,text:lastText});
      if(b.ok){lastFields=fields; await renderBuild(b);} $("answer").textContent=keep; $("status").textContent="";
    }
  }catch(e){$("answer").textContent=String(e);}
  finally{$("askBtn").disabled=false;}
};
</script></body></html>
"""

if __name__ == "__main__":
    raise SystemExit(main())
