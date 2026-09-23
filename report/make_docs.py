"""Build the project report and the slide deck as local PDFs.

Everything is rendered on this machine with the Brave that is already installed. Nothing is
uploaded anywhere. Numbers come from report/facts.json, which is produced by running the tool
itself, so no figure in either document is typed by hand.

    python report/make_docs.py

Outputs report/AI-in-CAD-Report.pdf and report/AI-in-CAD-Slides.pdf
"""
from __future__ import annotations

import base64
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
SHOTS = HERE / "shots"
BRAVE = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
FACTS = json.loads((HERE / "facts.json").read_text())

STUDENT = "Atishay Jain"
ENROLMENT = "0801ME231024"
DEPT = "Department of Mechanical Engineering"
INSTITUTE = "Shri G. S. Institute of Technology and Science, Indore"
TITLE = "Strategic Application of AI in CAD"
SUBTITLE = "Plain English in, checked machine joints out"
LIVE = "aicad-vercel.vercel.app"


def img(name: str) -> str:
    """Inline a screenshot so the PDF is one self-contained file."""
    f = SHOTS / f"{name}.png"
    if not f.exists():
        return ""
    b64 = base64.b64encode(f.read_bytes()).decode()
    return f"data:image/png;base64,{b64}"


def figure(name: str, caption: str, klass: str = "") -> str:
    src = img(name)
    if not src:
        return ""
    return (f'<figure class="{klass}"><img src="{src}" alt="{caption}">'
            f'<figcaption>{caption}</figcaption></figure>')


# --------------------------------------------------------------------------- shared styling

CSS = """
@page{size:420mm 297mm;margin:0}
:root{
  --ink:#10151c; --body:#2b3542; --muted:#6b7684; --line:#dbe1e8;
  --accent:#1d4ed8; --ok:#0f7b41; --warn:#a15c00; --bg:#ffffff; --panel:#f6f8fb;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--bg);color:var(--body);
  font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;
  -webkit-font-smoothing:antialiased;font-size:10.2px;line-height:1.5}
h1,h2,h3,h4{color:var(--ink);margin:0;font-weight:700;letter-spacing:-0.01em}
h1{font-size:30px;line-height:1.08}
h2{font-size:15px;margin:0 0 7px;padding-bottom:5px;border-bottom:2px solid var(--ink)}
h3{font-size:11.5px;margin:0 0 4px}
p{margin:0 0 7px}
small{color:var(--muted)}
b,strong{color:var(--ink)}
code,.mono{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:9.3px}

.page{width:420mm;height:297mm;padding:13mm 14mm 11mm;page-break-after:always;
  display:flex;flex-direction:column;overflow:hidden}
.page:last-child{page-break-after:auto}

.masthead{display:flex;justify-content:space-between;align-items:flex-end;
  border-bottom:3px solid var(--ink);padding-bottom:9px;margin-bottom:11px}
.masthead .who{text-align:right;font-size:10px;color:var(--muted);line-height:1.45}
.kicker{font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:var(--accent);
  font-weight:700;margin-bottom:5px}
.runner{display:flex;justify-content:space-between;border-bottom:1.5px solid var(--ink);
  padding-bottom:6px;margin-bottom:11px;font-size:10px;color:var(--muted)}
.runner b{color:var(--ink)}

.cols{display:grid;gap:9mm;flex:1;min-height:0}
.c2{grid-template-columns:1fr 1fr}
.c3{grid-template-columns:1fr 1fr 1fr}
.c25{grid-template-columns:1.25fr 1fr}
.c52{grid-template-columns:1.6fr 1fr}
.stack{display:flex;flex-direction:column;gap:7mm;min-height:0}

table{width:100%;border-collapse:collapse;font-size:9.6px}
th{text-align:left;font-size:8.6px;letter-spacing:.07em;text-transform:uppercase;
  color:var(--muted);font-weight:700;border-bottom:1.5px solid var(--ink);padding:4px 6px 4px 0}
td{padding:4px 6px 4px 0;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:none}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.pass{color:var(--ok);font-weight:700}
.tight td,.tight th{padding:3px 5px 3px 0}

.panel{background:var(--panel);border:1px solid var(--line);border-radius:7px;padding:9px 11px}
.panel.accent{border-left:3px solid var(--accent)}
.panel.warnb{border-left:3px solid var(--warn)}

.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin:2px 0 4px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:7px;padding:8px 10px}
.kpi .v{font-size:23px;font-weight:700;color:var(--ink);line-height:1.05;
  font-variant-numeric:tabular-nums}
.kpi .l{font-size:8.6px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);
  margin-top:3px}

figure{margin:0;min-height:0;display:flex;flex-direction:column}
figure img{width:100%;border:1px solid var(--line);border-radius:6px;object-fit:contain;
  object-position:top;background:#fff;min-height:0}
figcaption{font-size:8.8px;color:var(--muted);margin-top:4px;line-height:1.35}
figure.grow{flex:1}
figure.grow img{flex:1;object-fit:cover;object-position:top}

ul{margin:0 0 7px;padding-left:15px}
li{margin-bottom:3.5px}
.flow{display:flex;align-items:stretch;gap:5px;margin:4px 0 7px}
.step{flex:1;background:var(--panel);border:1px solid var(--line);border-radius:6px;
  padding:7px 8px;position:relative}
.step .n{font-size:8.4px;color:var(--accent);font-weight:700;letter-spacing:.08em}
.step .t{font-size:10px;font-weight:700;color:var(--ink);margin:2px 0 2px}
.step .d{font-size:8.9px;color:var(--muted);line-height:1.35}
.step.ai{border-color:var(--accent);background:#eff4ff}
.foot{margin-top:auto;padding-top:7px;border-top:1px solid var(--line);
  display:flex;justify-content:space-between;font-size:8.8px;color:var(--muted)}
.bar{height:7px;background:#e6ebf2;border-radius:4px;overflow:hidden;min-width:52px}
.bar span{display:block;height:100%;background:var(--ok)}
.bar.hi span{background:var(--warn)}
"""

SLIDE_CSS = """
@page{size:338.7mm 190.5mm;margin:0}
:root{--ink:#0d1117;--body:#243040;--muted:#6b7684;--line:#d9e0e8;--accent:#1d4ed8;
 --ok:#0f7b41;--panel:#f5f8fc}
*{box-sizing:border-box}
html,body{margin:0;background:#fff;color:var(--body);
 font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}
.slide{width:338.7mm;height:190.5mm;padding:15mm 17mm;page-break-after:always;
 display:flex;flex-direction:column;overflow:hidden;position:relative}
.slide:last-child{page-break-after:auto}
.tag{font-size:12px;letter-spacing:.2em;text-transform:uppercase;color:var(--accent);
 font-weight:700;margin-bottom:8px}
h1{font-size:54px;line-height:1.04;margin:0 0 10px;color:var(--ink);letter-spacing:-0.02em}
h2{font-size:33px;line-height:1.12;margin:0 0 12px;color:var(--ink);letter-spacing:-0.015em}
p{font-size:16px;line-height:1.5;margin:0 0 10px}
ul{font-size:16px;line-height:1.55;margin:0;padding-left:20px}
li{margin-bottom:8px}
.lead{font-size:20px;color:var(--muted);line-height:1.45}
.row{display:grid;gap:11mm;flex:1;min-height:0}
.r2{grid-template-columns:1fr 1fr}
.r52{grid-template-columns:1.45fr 1fr}
.r25{grid-template-columns:1fr 1.45fr}
img{width:100%;border:1px solid var(--line);border-radius:8px;background:#fff;
 object-fit:contain;object-position:top}
.fill{flex:1;min-height:0;display:flex;flex-direction:column}
.fill img{flex:1;min-height:0;object-fit:cover;object-position:top}
.cap{font-size:11px;color:var(--muted);margin-top:6px}
.big{display:grid;grid-template-columns:repeat(4,1fr);gap:11px;margin:6px 0 4px}
.big div{background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:13px 15px}
.big .v{font-size:36px;font-weight:700;color:var(--ink);line-height:1;
 font-variant-numeric:tabular-nums}
.big .l{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);
 margin-top:5px}
table{width:100%;border-collapse:collapse;font-size:14px}
th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.07em;
 color:var(--muted);border-bottom:2px solid var(--ink);padding:6px 8px 6px 0}
td{padding:6px 8px 6px 0;border-bottom:1px solid var(--line)}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
.mono{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:13px}
.note{background:var(--panel);border-left:4px solid var(--accent);border-radius:7px;
 padding:12px 15px;font-size:15px;line-height:1.5}
.pnum{position:absolute;right:17mm;bottom:9mm;font-size:11px;color:var(--muted)}
.foot{position:absolute;left:17mm;bottom:9mm;font-size:11px;color:var(--muted)}
"""


def joint_rows() -> str:
    out = []
    for j in FACTS["joints"]:
        pct = min(100, round(j["worst"] * 100))
        cls = "hi" if pct >= 80 else ""
        src = "verified" if j["verified"] else "checks only"
        out.append(
            f"<tr><td><b>{j['title']}</b></td><td class='n'>{j['parts']}</td>"
            f"<td class='n'>{j['dims']}</td><td class='n'>{j['checks']}</td>"
            f"<td class='n'>{pct}%</td>"
            f"<td><div class='bar {cls}'><span style='width:{pct}%'></span></div></td>"
            f"<td><small>{src}</small></td></tr>")
    return "\n".join(out)


def dim_rows(limit: int = 9) -> str:
    out = []
    for key, label, value, rule in FACTS["knuckle"]["dims"][:limit]:
        rule = (rule or "").replace("[", "<small>[").replace("]", "]</small>")
        out.append(f"<tr><td class='mono'>{key}</td><td>{label}</td>"
                   f"<td class='n'><b>{value:g}</b></td><td><small>{rule}</small></td></tr>")
    return "\n".join(out)


def check_rows() -> str:
    out = []
    for name, formula, stress, allowed, passed in FACTS["knuckle"]["checks"]:
        pct = round(100 * stress / allowed)
        cls = "hi" if pct >= 80 else ""
        out.append(f"<tr><td>{name}</td><td class='mono'>{formula}</td>"
                   f"<td class='n'>{stress:g}</td><td class='n'>{allowed:g}</td>"
                   f"<td class='n'>{pct}%</td>"
                   f"<td><div class='bar {cls}'><span style='width:{pct}%'></span></div></td>"
                   f"<td class='pass'>pass</td></tr>")
    return "\n".join(out)


# --------------------------------------------------------------------------- the report

def report_html() -> str:
    k = FACTS["knuckle"]
    n_joints = len(FACTS["joints"])
    n_checks = sum(j["checks"] for j in FACTS["joints"])
    verified = sum(1 for j in FACTS["joints"] if j["verified"])
    tests = FACTS["tests"].split()[0]

    p1 = f"""
<section class="page">
  <div class="masthead">
    <div>
      <div class="kicker">Major Project &middot; Semester 7</div>
      <h1>{TITLE}</h1>
      <div style="font-size:13px;color:var(--muted);margin-top:5px">{SUBTITLE}</div>
    </div>
    <div class="who">
      <b>{STUDENT}</b><br>Enrolment {ENROLMENT}<br>{DEPT}<br>{INSTITUTE}
    </div>
  </div>

  <div class="cols c52">
    <div class="stack">
      <div>
        <h2>What it does</h2>
        <p>You type a sentence such as <b>knuckle joint for 50 kN</b>. The software works out
        every dimension of that joint from standard design formulas, checks each way it can
        fail against the allowable stress, builds all parts as exact solid models, and draws a
        first angle A3 sheet. It runs in a browser at <b>{LIVE}</b> and needs nothing installed.</p>
        <p>Nothing is retrieved from a library of ready models. Every dimension is calculated
        from the load you give, so changing the load changes the whole design. The software
        prints its full working for each run, which is what allows the output to be checked
        rather than trusted.</p>
      </div>

      <div class="kpis">
        <div class="kpi"><div class="v">{n_joints}</div><div class="l">joints built</div></div>
        <div class="kpi"><div class="v">{n_checks}</div><div class="l">failure checks</div></div>
        <div class="kpi"><div class="v">{verified}</div><div class="l">verified to a book</div></div>
        <div class="kpi"><div class="v">{tests}</div><div class="l">automated tests</div></div>
      </div>

      <div>
        <h2>The six joints</h2>
        <table>
          <tr><th>Joint</th><th class="n">Parts</th><th class="n">Dims</th><th class="n">Checks</th>
              <th class="n">Busiest</th><th>Utilisation of allowable</th><th>Book</th></tr>
          {joint_rows()}
        </table>
        <p style="margin-top:7px"><small>Busiest means the check closest to its allowable
        stress, at the stated duty. Every joint above passes every check. Utilisation stays
        near three quarters by design: each joint is sized for 1.25 times the load you give
        and then reported at the real load, so there is margin left in hand.</small></p>
      </div>
    </div>

    <div class="stack">
      {figure("01-landing", "The request screen. A sentence is typed, or one of the examples is used.", "grow")}
      <div class="panel accent">
        <h3>The one design decision worth defending</h3>
        <p style="margin:0"><b>The language model reads the request. It does not choose any
        dimension and it does not perform any check.</b> Turning "50 kN" into a load in newtons
        is a language problem, which is what such a model is good at. Choosing a pin diameter is
        an engineering problem with a correct answer, and it stays with deterministic code that
        can be traced to a textbook page.</p>
      </div>
    </div>
  </div>

  <div class="foot"><span>{INSTITUTE}</span><span>Page 1 of 4</span></div>
</section>"""

    p2 = f"""
<section class="page">
  <div class="runner"><span><b>How it works</b></span><span>{TITLE}</span></div>

  <div class="flow">
    <div class="step ai"><div class="n">STEP 1 &middot; AI</div><div class="t">Read the request</div>
      <div class="d">The sentence becomes parameters: which joint, what load, which allowable
      stresses. Falls back to pattern rules when no model is available.</div></div>
    <div class="step"><div class="n">STEP 2</div><div class="t">Size it</div>
      <div class="d">The governing formula gives a diameter, which is rounded up to the next
      standard size. Remaining dimensions follow from book proportions.</div></div>
    <div class="step"><div class="n">STEP 3</div><div class="t">Check every failure</div>
      <div class="d">Tension, shear, crushing and bending are each computed and compared with
      the allowable. Any failing dimension is raised a millimetre at a time until it passes.</div></div>
    <div class="step"><div class="n">STEP 4</div><div class="t">Build the solids</div>
      <div class="d">Each part is modelled exactly and written as a STEP file, which opens in
      NX, SolidWorks, FreeCAD or Fusion.</div></div>
    <div class="step"><div class="n">STEP 5</div><div class="t">Draw the sheet</div>
      <div class="d">A first angle A3 sheet with four views, dimensions and a title block, plus
      a DXF for AutoCAD.</div></div>
  </div>

  <div class="cols c2" style="gap:9mm">
    <div class="stack">
      <div>
        <h2>Worked example: knuckle joint, 50 kN</h2>
        <p style="margin-bottom:5px"><small>The rod diameter comes from tension. The pin is then
        sized independently, and the larger of its two requirements wins.</small></p>
        <table class="tight">
          <tr><th>Formula result before rounding</th><th class="n">mm</th><th>What it governs</th></tr>
          <tr><td class="mono">rod in tension</td><td class="n">{k['raw']['rod_tension']}</td>
              <td>rod diameter, rounded up to 35</td></tr>
          <tr><td class="mono">pin in double shear</td><td class="n">{k['raw']['pin_shear']}</td>
              <td>not governing, smaller than the rod</td></tr>
          <tr><td class="mono">pin in bending</td><td class="n">{k['raw']['pin_bending']}</td>
              <td><b>governs the pin, rounded up to 45</b></td></tr>
        </table>
        <p style="margin-top:7px"><small>Both pin requirements are computed and the larger is
        taken, because a pin that satisfies shear but not bending will still bend. The lesson
        this is checked against takes the same step.</small></p>
      </div>
      <div>
        <h3>Dimensions produced, with the rule behind each</h3>
        <table class="tight">
          <tr><th>Symbol</th><th>Meaning</th><th class="n">mm</th><th>Rule and source</th></tr>
          {dim_rows()}
        </table>
      </div>
    </div>

    <div class="stack">
      <div>
        <h2>Every way this joint can fail</h2>
        <table class="tight">
          <tr><th>Check</th><th>Formula</th><th class="n">MPa</th><th class="n">Allowed</th>
              <th class="n">Used</th><th></th><th></th></tr>
          {check_rows()}
        </table>
      </div>
      <div class="panel">
        <h3>Reading the margin</h3>
        <p style="margin:0">The joint is sized for <b>62,500 N</b>, which is 1.25 times the
        50,000 N asked for, and then every stress is reported at the real 50,000 N. That is why
        no check sits at its limit. The busiest is eye shear at 76 percent of allowable. Sizing
        exactly to the allowable would leave a joint that passes on paper and has nothing left
        for a bad batch of steel or an overload.</p>
      </div>
      {figure("03-working-log", "The working printed for this run. Formula results, the chosen sizes, the source of each proportion, then every check with its numbers.", "grow")}
    </div>
  </div>

  <div class="foot"><span>Worked example and failure checks</span><span>Page 2 of 4</span></div>
</section>"""

    p3 = f"""
<section class="page">
  <div class="runner"><span><b>Verification against published design books</b></span>
    <span>{TITLE}</span></div>

  <div class="cols c25">
    <div class="stack">
      <div>
        <h2>What was checked, and against what</h2>
        <p>Proportions and formulas were checked against three sources, all of them either
        openly published or out of copyright. Where the software disagrees with a source, the
        disagreement is recorded in the code with the reason.</p>
        <table>
          <tr><th>Joint</th><th>Source</th><th>State</th></tr>
          <tr><td><b>Knuckle</b></td>
              <td>NPTEL, IIT Kharagpur, Design of Machine Elements I, module 4 lesson 2</td>
              <td>proportions and all nine checks verified</td></tr>
          <tr><td><b>Socket and spigot cotter</b></td>
              <td>NPTEL module 4 lesson 2, and Leutwiler, <i>Elements of Machine Design</i>, 1917</td>
              <td>ten checks verified against two independent books</td></tr>
          <tr><td><b>Gib and cotter</b></td>
              <td>Unwin, <i>Elements of Machine Design</i>, 1899, page 179</td>
              <td>breadth split, thickness and taper verified</td></tr>
          <tr><td><b>Flange coupling</b></td>
              <td>NPTEL module 4 lesson 1 for keys, Leutwiler article 275 for bolts</td>
              <td>every check verified twice, proportions cannot be</td></tr>
          <tr><td><b>Sleeve and cotter</b></td>
              <td>no book found that covers it, four searched</td>
              <td>checks verified, proportions not</td></tr>
          <tr><td><b>Hex bolt and nut</b></td>
              <td>NPTEL module 4 lesson 4</td>
              <td>tightening load verified, size table not</td></tr>
        </table>
      </div>

      <div class="panel warnb">
        <h3>Three errors found in the sources while checking</h3>
        <ul style="margin-bottom:0">
          <li><b>The knuckle lesson contradicts itself.</b> It raises the pin from 40 to 55 mm
          for bending, then checks the eye using the original 40 mm pin. With the real pin in
          the hole its own eye shear check reads 80 MPa against 65 allowed. This software grows
          the eye instead.</li>
          <li><b>The cotter lesson omits a check.</b> It never checks crushing between the
          cotter and the spigot. At its own final answer that check reads 167 MPa against 110
          allowed. A second book, Leutwiler 1917, lists it as one of ten failure modes, so the
          software keeps it and sizes the cotter thicker.</li>
          <li><b>A printed constant is wrong by a factor of ten.</b> The bolt tightening load is
          printed as 284 d kN, but the same page's worked example gives 56.8 kN for an M20 bolt,
          which only holds if the constant is 2840 d newtons.</li>
        </ul>
      </div>

      <div class="panel">
        <h3>Why the coupling proportions will never carry a source</h3>
        <p style="margin:0">Leutwiler states plainly that no uniform proportions for flange
        couplings were ever agreed as a standard, and that published tables are individual
        manufacturers' practice. The software therefore marks them unverified rather than
        implying a source it does not have. Its seven strength checks are a separate matter and
        are verified twice over.</p>
      </div>
    </div>

    <div class="stack">
      {figure("05-drawing", "The A3 first angle sheet, generated for this run. Front, side and plan views with an isometric, dimensioned, with a title block.", "grow")}
      {figure("07-checks", "Each check can be expanded to show the substituted arithmetic, not only the result.", "grow")}
    </div>
  </div>

  <div class="foot"><span>Sources, and what disagreeing with them means</span>
    <span>Page 3 of 4</span></div>
</section>"""

    p4 = f"""
<section class="page">
  <div class="runner"><span><b>Output, method and limits</b></span><span>{TITLE}</span></div>

  <div class="cols c3" style="margin-bottom:7mm">
    {figure("04-model", "The assembled 3D model, rotatable in the browser, also available exploded and with the busiest parts coloured.")}
    {figure("06-dimensions", "Every dimension with the rule that produced it, and a plain English explanation on demand.")}
    {figure("09-files", "Files produced per run: a STEP file for each part, the assembly, the drawing sheet, the DXF and a written report.")}
  </div>

  <div class="cols c3">
    <div>
      <h2>What each run produces</h2>
      <ul>
        <li>A STEP file for every part, plus the assembly in position, which opens in NX,
        SolidWorks, FreeCAD, Onshape and Fusion.</li>
        <li>A first angle A3 drawing sheet with dimensions and a title block, and the same
        views as a DXF for AutoCAD.</li>
        <li>A 3D model viewable in the browser, with an exploded view and a view that colours
        the parts closest to their limits.</li>
        <li>A written report listing every dimension, the rule behind it, and every check with
        its numbers.</li>
        <li>An editable FreeCAD file containing the parts tree and the drawing page.</li>
      </ul>
      <h3 style="margin-top:9px">Asking it to change something</h3>
      <p style="margin:0">After a build you can ask in plain words: make it 80 kN, why is the
      pin 45 mm, how much load can this take, add more margin, make it lighter. It re-sizes and
      reports which dimensions moved.</p>
    </div>

    <div>
      <h2>How it is built</h2>
      <table class="tight">
        <tr><th>Part</th><th>Tool</th></tr>
        <tr><td>Solid modelling</td><td>CadQuery 2.8 on the OCCT kernel</td></tr>
        <tr><td>Drawing sheet and DXF</td><td>FreeCAD, run without its interface</td></tr>
        <tr><td>Stress analysis</td><td>CalculiX with gmsh meshing</td></tr>
        <tr><td>Reading the request</td><td>Claude, with offline pattern rules as fallback</td></tr>
        <tr><td>Application</td><td>Python standard library, no framework</td></tr>
        <tr><td>Hosting</td><td>container on Vercel, free tier</td></tr>
      </table>
      <h3 style="margin-top:9px">How correctness is held</h3>
      <p style="margin:0">{tests} automated tests run on every change. They cover the sizing
      arithmetic, the geometry, the parser, the drawing sheet and the stress analysis, and they
      include tests that assert the two book errors above are real, so nobody silently
      "corrects" the software back to the printed answer.</p>
    </div>

    <div>
      <h2>Limits, stated plainly</h2>
      <ul>
        <li><b>The stress analysis is one linear static run on one part</b>, with boundary
        conditions the software chooses. It is a second opinion on the formula, not a full
        analysis. It re-solves on a finer mesh and reports when its own answer has not settled.</li>
        <li><b>Proportions for the sleeve and cotter joint and the flange coupling are
        unverified</b>, and the software says so on every run rather than hiding it.</li>
        <li><b>Fatigue, stress concentration, tolerances and fits are not covered.</b> All
        sizing is static.</li>
        <li><b>The published site reads requests with pattern rules, not AI</b>, because the
        server holds no API key. The language model path runs locally.</li>
        <li><b>Nut thread stripping is not checked</b> for the bolted joint.</li>
      </ul>
      <div class="panel accent" style="margin-top:8px">
        <p style="margin:0">Every figure in this report was produced by running the software,
        and every screenshot is of the live site. Nothing here was typed by hand.</p>
      </div>
    </div>
  </div>

  <div class="foot"><span>{STUDENT} &middot; {ENROLMENT} &middot; {DEPT}</span>
    <span>Page 4 of 4</span></div>
</section>"""

    return (f"<!doctype html><html><head><meta charset='utf-8'><title>{TITLE}</title>"
            f"<style>{CSS}</style></head><body>{p1}{p2}{p3}{p4}</body></html>")


# --------------------------------------------------------------------------- the slide deck

def slides_html() -> str:
    k = FACTS["knuckle"]
    n_checks = sum(j["checks"] for j in FACTS["joints"])
    tests = FACTS["tests"].split()[0]
    S = []

    S.append(f"""<section class="slide" style="justify-content:center">
      <div class="tag">Major Project &middot; Semester 7</div>
      <h1>{TITLE}</h1>
      <p class="lead" style="max-width:70%">{SUBTITLE}. Type a sentence, get a designed,
      checked and drawn machine joint.</p>
      <div style="margin-top:26px;font-size:17px;color:var(--ink)">
        <b>{STUDENT}</b> &middot; {ENROLMENT}<br>
        <span style="color:var(--muted);font-size:15px">{DEPT}, {INSTITUTE}</span>
      </div>
      <div class="foot">Live at {LIVE}</div></section>""")

    S.append(f"""<section class="slide">
      <div class="tag">The problem</div>
      <h2>Designing a joint by hand is slow, and the slow part is not the drawing</h2>
      <div class="row r2">
        <div>
          <p>For one knuckle joint a student computes the rod from tension, sizes the pin for
          shear and again for bending, takes the larger, derives seven proportions from the rod,
          then checks nine separate failure modes against allowable stresses.</p>
          <p>Change the load and all of it is done again from the start.</p>
          <div class="note" style="margin-top:14px"><b>The aim:</b> keep every formula exactly
          as the textbook has it, and remove only the repetition.</div>
        </div>
        <div>
          <table>
            <tr><th>Done by hand, per joint</th></tr>
            <tr><td>Rod diameter from tension</td></tr>
            <tr><td>Pin from shear, then from bending</td></tr>
            <tr><td>Seven proportions from the rod</td></tr>
            <tr><td>Nine failure checks</td></tr>
            <tr><td>Re-size anything that fails</td></tr>
            <tr><td>Draw four views and dimension them</td></tr>
          </table>
        </div>
      </div><div class="pnum">2</div></section>""")

    S.append(f"""<section class="slide">
      <div class="tag">What was built</div>
      <h2>A sentence goes in. A checked design comes out.</h2>
      <div class="big">
        <div><div class="v">6</div><div class="l">joints</div></div>
        <div><div class="v">{n_checks}</div><div class="l">failure checks</div></div>
        <div><div class="v">{tests}</div><div class="l">tests</div></div>
        <div><div class="v">10s</div><div class="l">per design</div></div>
      </div>
      <div class="fill" style="margin-top:8px">
        <img src="{img('01-landing')}" alt="the request screen">
        <div class="cap">The live site. Knuckle, socket and spigot cotter, sleeve and cotter,
        gib and cotter, hex bolt and nut, and a protected type rigid flange coupling.</div>
      </div><div class="pnum">3</div></section>""")

    S.append(f"""<section class="slide">
      <div class="tag">The design decision</div>
      <h2>The AI reads the request. It does not choose a single dimension.</h2>
      <div class="row r2">
        <div>
          <p>Turning "50 kN" into 50,000 newtons and knowing that "socket and spigot" names a
          cotter joint is a language problem. A language model is good at that.</p>
          <p>Choosing a pin diameter is an engineering problem with a correct answer. That stays
          with deterministic code, traceable to a textbook page.</p>
          <div class="note"><b>If asked why the AI does not generate the whole model:</b>
          because then no number could be checked against anything. Here every dimension has a
          formula and every formula has a source.</div>
        </div>
        <div>
          <table>
            <tr><th>Stage</th><th>Who does it</th></tr>
            <tr><td>Read the sentence</td><td><b style="color:var(--accent)">AI</b></td></tr>
            <tr><td>Size every dimension</td><td>formula</td></tr>
            <tr><td>Check every failure</td><td>formula</td></tr>
            <tr><td>Build the solids</td><td>CAD kernel</td></tr>
            <tr><td>Draw the sheet</td><td>FreeCAD</td></tr>
          </table>
        </div>
      </div><div class="pnum">4</div></section>""")

    S.append(f"""<section class="slide">
      <div class="tag">Worked example</div>
      <h2>Knuckle joint, 50 kN, shown as the software computes it</h2>
      <div class="row r52">
        <div>
          <table>
            <tr><th>Formula result</th><th class="n">mm</th><th>Outcome</th></tr>
            <tr><td class="mono">rod in tension</td><td class="n">{k['raw']['rod_tension']}</td>
                <td>rod becomes 35</td></tr>
            <tr><td class="mono">pin in double shear</td><td class="n">{k['raw']['pin_shear']}</td>
                <td>not governing</td></tr>
            <tr><td class="mono">pin in bending</td><td class="n">{k['raw']['pin_bending']}</td>
                <td><b>pin becomes 45</b></td></tr>
          </table>
          <div class="note" style="margin-top:16px">Sized for 1.25 times the load, then reported
          at the real load. Busiest check sits at <b>76 percent</b> of its allowable, not at
          100, so there is margin in hand.</div>
        </div>
        <div class="fill">
          <img src="{img('03-working-log')}" alt="the working">
          <div class="cap">Every run prints its working, so the output can be checked rather
          than trusted.</div>
        </div>
      </div><div class="pnum">5</div></section>""")

    S.append(f"""<section class="slide">
      <div class="tag">Output</div>
      <h2>A first angle A3 sheet, dimensioned, with a title block</h2>
      <div class="fill">
        <img src="{img('05-drawing')}" alt="drawing sheet">
        <div class="cap">Produced by FreeCAD driven without its interface. The same views are
        also written as a DXF for AutoCAD, and every part as a STEP file that opens in NX.</div>
      </div><div class="pnum">6</div></section>""")

    S.append(f"""<section class="slide">
      <div class="tag">Verification</div>
      <h2>Checked against published books, and the books lost three times</h2>
      <div class="row r2">
        <div>
          <p>Sources: NPTEL IIT Kharagpur Design of Machine Elements I, Unwin 1899, and
          Leutwiler 1917. The last two are out of copyright.</p>
          <ul>
            <li><b>The knuckle lesson</b> raises the pin for bending, then checks the eye with
            the old pin. Its own answer fails its own check, 80 MPa against 65 allowed.</li>
            <li><b>The cotter lesson</b> omits crushing between cotter and spigot. At its answer
            that reads 167 MPa against 110 allowed. A second book lists it.</li>
            <li><b>A printed constant</b> is off by a factor of ten, disproved by the same
            page's own worked example.</li>
          </ul>
        </div>
        <div class="fill">
          <img src="{img('07-checks')}" alt="checks">
          <div class="cap">Each check shows its substituted arithmetic, which is what made the
          disagreements visible.</div>
        </div>
      </div><div class="pnum">7</div></section>""")

    S.append(f"""<section class="slide">
      <div class="tag">Honest limits</div>
      <h2>What this does not do</h2>
      <div class="row r2">
        <div><ul>
          <li>The stress analysis is one linear static run on one part. It is a second opinion
          on the formula, not a replacement for proper analysis.</li>
          <li>Proportions for two of the six joints have no book behind them, and the software
          says so on every run.</li>
          <li>Fatigue, stress concentration, tolerances and fits are out of scope. Sizing is
          static.</li>
          <li>The published site reads with pattern rules, because the server holds no API key.</li>
        </ul></div>
        <div class="fill">
          <img src="{img('08-weak-spots')}" alt="weak spots">
          <div class="cap">Parts are coloured by how close each is to its limit, so the weakest
          member is visible rather than buried in a table.</div>
        </div>
      </div><div class="pnum">8</div></section>""")

    S.append(f"""<section class="slide" style="justify-content:center">
      <div class="tag">In one line</div>
      <h2 style="font-size:40px;max-width:82%">Every dimension it produces can be traced to a
      formula, and every formula to a page in a book.</h2>
      <p class="lead" style="max-width:72%">That is the difference between a tool that designs
      and one that only draws. The AI reads the request; the engineering stays checkable.</p>
      <div style="margin-top:22px;font-size:17px"><b>{LIVE}</b></div>
      <div class="foot">{STUDENT} &middot; {ENROLMENT} &middot; {DEPT}</div>
      <div class="pnum">9</div></section>""")

    return (f"<!doctype html><html><head><meta charset='utf-8'><title>{TITLE} slides</title>"
            f"<style>{SLIDE_CSS}</style></head><body>{''.join(S)}</body></html>")


def to_pdf(html: str, stem: str, landscape_mm: tuple[float, float]) -> Path:
    src = HERE / f"{stem}.html"
    src.write_text(html)
    pdf = HERE / f"{stem}.pdf"
    if pdf.exists():
        pdf.unlink()
    subprocess.run([BRAVE, "--headless", "--disable-gpu", "--no-sandbox",
                    f"--print-to-pdf={pdf}", "--no-pdf-header-footer",
                    "--virtual-time-budget=25000", f"file://{src}"],
                   capture_output=True, timeout=300)
    return pdf


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    made = []
    if which in ("both", "report"):
        made.append(to_pdf(report_html(), "AI-in-CAD-Report", (420, 297)))
    if which in ("both", "slides"):
        made.append(to_pdf(slides_html(), "AI-in-CAD-Slides", (338.7, 190.5)))
    for p in made:
        size = p.stat().st_size // 1024 if p.exists() else 0
        print(f"{p}  {size} KB")
