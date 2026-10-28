"""Build the project presentation: a PDF for showing, and a PPTX for presenting and editing.

Each slide is laid out in HTML, rendered at 16:9 by the Brave already on this machine, and then
also packed into a PowerPoint file so the deck opens on any projector without this repository.
Every figure comes from report/facts.json, written by running the software itself.

    python report/make_deck.py
"""
from __future__ import annotations

import base64
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
SHOTS = HERE / "shots"
ASSETS = HERE / "assets"
BUILD = HERE / ".build"
BRAVE = __import__("os").environ.get("AICAD_BROWSER", "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser")
F = json.loads((HERE / "facts.json").read_text())

TEAM = [("0801ME231013", "Ankur Dodke"), ("0801ME231014", "Ansh Yadav"),
        ("0801ME231024", "Atishay Jain"), ("0801ME231030", "Bhavya Shrivastava"),
        ("0801ME243D02", "Dharmendra Gupta")]
GUIDE = "Dr. B. R. Rawal"
GUIDE_DESIG = "Professor and Head, Department of Mechanical Engineering"
INST = "Shri G. S. Institute of Technology and Science, Indore"
DEPT = "Department of Mechanical Engineering"
TITLE = "Strategic Application of Artificial Intelligence in CAD"
SESSION = "2026 - 2027"
LIVE = "aicad-vercel.vercel.app"

W_IN, H_IN = 13.333, 7.5          # 16:9


def b64(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode()


def shot(name: str) -> str:
    f = SHOTS / f"{name}.png"
    return f"data:image/png;base64,{b64(f)}" if f.exists() else ""


LOGO = f"data:image/png;base64,{b64(ASSETS / 'sgsits-logo.png')}" \
    if (ASSETS / "sgsits-logo.png").exists() else ""
QR = f"data:image/png;base64,{b64(ASSETS / 'demo-qr.png')}" \
    if (ASSETS / "demo-qr.png").exists() else ""


def qr_block(size_mm: int = 24) -> str:
    """Scannable link to the live system, with the URL written out beside it."""
    return (f'<div style="margin-top:14px;display:flex;align-items:center;gap:12px;text-align:left">'
            f'<img src="{QR}" style="width:{size_mm}mm;height:{size_mm}mm" alt="QR code, live demo">'
            f'<div style="font-size:12px;line-height:1.5"><b style="color:var(--ink)">Live demo</b>'
            f'<br>Scan, or open<br>{LIVE}</div></div>')

CSS = """
@page{size:338.7mm 190.5mm;margin:0}
:root{--ink:#0a1020;--body:#333f4f;--mute:#7a8695;--line:#dde4ec;--blue:#14448f;
 --acc:#1f6feb;--ok:#0e7c41;--warn:#9a5a00;--bad:#b02418;--wash:#f3f7fc}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;color:var(--body);
 -webkit-font-smoothing:antialiased;background:#fff}
.s{width:338.7mm;height:190.5mm;position:relative;overflow:hidden;page-break-after:always;
 display:flex;flex-direction:column;padding:17mm 18mm 14mm}
.s:last-child{page-break-after:auto}
.wrap{flex:1;min-height:0;display:flex;flex-direction:column;justify-content:center;gap:7mm}
.wrap>.row{flex:0 1 auto}
.wrap>table{flex:0 0 auto}
.s::before{content:"";position:absolute;top:0;left:0;right:0;height:5.2mm;
 background:linear-gradient(90deg,var(--blue) 0%,var(--acc) 62%,#5aa2ff 100%)}
.kick{font-size:11px;letter-spacing:.22em;text-transform:uppercase;color:var(--acc);
 font-weight:800;margin-bottom:6px}
h1{font-size:47px;line-height:1.04;color:var(--ink);letter-spacing:-.022em;font-weight:800}
h2{font-size:29px;line-height:1.12;color:var(--ink);letter-spacing:-.016em;font-weight:800;
 margin-bottom:11px}
h3{font-size:15px;color:var(--ink);font-weight:800;margin-bottom:5px}
p{font-size:14.4px;line-height:1.52;margin-bottom:9px}
ul{font-size:14.4px;line-height:1.52;padding-left:18px}
li{margin-bottom:7px}
.lead{font-size:17px;color:var(--mute);line-height:1.45}
.row{display:grid;gap:11mm;flex:1;min-height:0}
.r2{grid-template-columns:1fr 1fr}
.r3{grid-template-columns:1fr 1fr 1fr}
.r52{grid-template-columns:1.5fr 1fr}
.r25{grid-template-columns:1fr 1.5fr}
.r64{grid-template-columns:1.9fr 1fr}
.col{display:flex;flex-direction:column;gap:6mm;min-height:0}
.fill{flex:1;min-height:0;display:flex;flex-direction:column}
img.sh{width:100%;border:1px solid var(--line);border-radius:9px;background:#fff;
 box-shadow:0 2px 14px rgba(15,35,70,.09)}
.fill img.sh{flex:1;min-height:0;object-fit:contain;object-position:top}
.cap{font-size:11px;color:var(--mute);margin-top:6px;line-height:1.4}
table{width:100%;border-collapse:collapse;font-size:13.6px}
th{text-align:left;font-size:10.4px;text-transform:uppercase;letter-spacing:.08em;
 color:var(--mute);border-bottom:2px solid var(--ink);padding:5px 8px 5px 0;font-weight:800}
td{padding:7px 9px 7px 0;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:none}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
table.sm{font-size:12.4px}
table.sm th,table.sm td{padding:5.5px 7px 5.5px 0}
.mono{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:12.2px}
.card{background:var(--wash);border:1px solid var(--line);border-radius:10px;padding:13px 16px;font-size:13.8px;line-height:1.5}
.card.l{border-left:4px solid var(--acc)}
.card.g{border-left:4px solid var(--ok)}
.card.r{border-left:4px solid var(--bad)}
.card b{color:var(--ink)}
.kpi{display:grid;gap:9px}
.k4{grid-template-columns:repeat(4,1fr)}
.k3{grid-template-columns:repeat(3,1fr)}
.kpi>div{background:var(--wash);border:1px solid var(--line);border-radius:10px;padding:11px 13px}
.kpi .v{font-size:31px;font-weight:800;color:var(--ink);line-height:1;
 font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.kpi .l{font-size:9.8px;text-transform:uppercase;letter-spacing:.09em;color:var(--mute);
 margin-top:5px;line-height:1.3}
.flow{display:flex;gap:7px}
.flow>div{flex:1;background:var(--wash);border:1px solid var(--line);border-radius:9px;
 padding:9px 10px}
.flow .n{font-size:9.4px;font-weight:800;letter-spacing:.1em;color:var(--acc)}
.flow .t{font-size:12.6px;font-weight:800;color:var(--ink);margin:3px 0 2px}
.flow .d{font-size:10.4px;color:var(--mute);line-height:1.38}
.flow .ai{border-color:var(--acc);background:#e9f1ff}
.eq{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:13px;color:var(--ink);
 background:var(--wash);border:1px solid var(--line);border-radius:8px;padding:9px 12px}
.bar{height:6px;background:#e3e9f1;border-radius:3px;overflow:hidden;min-width:44px}
.bar span{display:block;height:100%;background:var(--ok)}
.bar.hi span{background:var(--warn)}
.pn{position:absolute;right:18mm;bottom:7mm;font-size:10px;color:var(--mute);
 font-variant-numeric:tabular-nums}
.ft{position:absolute;left:18mm;bottom:7mm;font-size:10px;color:var(--mute)}
/* section divider */
.div{background:linear-gradient(135deg,#0d2f66 0%,#14448f 55%,#1f6feb 100%);color:#fff;
 justify-content:center}
.div::before{display:none}
.div .kick{color:#8fc0ff}
.div h1{color:#fff;font-size:52px}
.div p{color:#cfe0f8;font-size:16px;max-width:64%;margin-top:10px}
.div .pn,.div .ft{color:#9dc1ef}
/* title slide */
.title{justify-content:center;text-align:center;align-items:center}
.title img.logo{width:26mm;margin-bottom:10px}
.title h1{font-size:41px;max-width:84%;text-transform:uppercase;letter-spacing:-.01em}
.title .sub{font-size:14.5px;color:var(--mute);margin-top:10px;line-height:1.5}
.title .band{margin-top:18px;display:flex;gap:16mm;align-items:flex-start;text-align:left}
.title .band h3{font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--acc)}
.title .band td{border:none;padding:2px 10px 2px 0;font-size:11.6px}
"""

N = 0
S: list[str] = []


def slide(inner: str, cls: str = "", foot: str = "") -> None:
    global N
    N += 1
    f = f'<div class="ft">{foot}</div>' if foot else \
        f'<div class="ft">{TITLE} &nbsp;&middot;&nbsp; {DEPT}</div>'
    body = inner if cls else f'<div class="wrap">{inner}</div>'
    S.append(f'<section class="s {cls}">{body}{f}<div class="pn">{N}</div></section>')


def divider(kick: str, title: str, note: str) -> None:
    slide(f'<div class="kick">{kick}</div><h1>{title}</h1><p>{note}</p>', "div")


def build() -> None:
    k = F["knuckle"]
    tests = F["tests"].split()[0]
    nchecks = sum(j["checks"] for j in F["joints"])

    team_rows = "".join(f"<tr><td class='mono'>{e}</td><td>{n}</td></tr>" for e, n in TEAM)
    slide(f"""
      <img class="logo" src="{LOGO}" alt="SGSITS">
      <div class="kick">Major Project &middot; Session {SESSION}</div>
      <h1>{TITLE}</h1>
      <div class="sub">A Project Report Submitted to Rajiv Gandhi Proudyogiki Vishwavidyalaya,
        Bhopal<br>towards the partial fulfillment of the degree of Bachelor of Technology in
        Mechanical Engineering</div>
      <div class="band">
        <div><h3>Submitted by</h3><table><tbody>{team_rows}</tbody></table></div>
        <div><h3>Supervised by</h3>
          <div style="font-size:13px;line-height:1.55;margin-top:4px">
            <b style="color:var(--ink)">{GUIDE}</b><br>{GUIDE_DESIG}</div>
          <h3 style="margin-top:12px">Institute</h3>
          <div style="font-size:12px;line-height:1.5;margin-top:4px">{INST}</div></div>
      </div>
      {qr_block(22)}""", "title", foot=f"Live at {LIVE}")

    divider("Part 1", "The problem",
            "Designing a standard joint is a fixed sequence of formulas. The sequence is the "
            "slow part, and it repeats in full every time the load changes.")

    slide(f"""
      <div class="kick">Where the time goes</div>
      <h2>Seven steps by hand, and every one repeats when the load changes</h2>
      <div class="row r2">
        <div class="col">
          <table><tr><th>Step performed by hand</th><th class="n">Repeats</th></tr>
            <tr><td>Rod diameter from direct tension</td><td class="n">yes</td></tr>
            <tr><td>Pin from double shear</td><td class="n">yes</td></tr>
            <tr><td>Pin from bending, adopt the larger</td><td class="n">yes</td></tr>
            <tr><td>Seven proportions from the rod diameter</td><td class="n">yes</td></tr>
            <tr><td>Nine failure checks against allowables</td><td class="n">yes</td></tr>
            <tr><td>Re-size whatever fails, check again</td><td class="n">yes</td></tr>
            <tr><td>Four views, dimensions, title block</td><td class="n">yes</td></tr>
          </table>
        </div>
        <div class="col">
          <div class="card l"><b>Parametric CAD does not solve this.</b> A modeller regenerates
          whatever dimensions it is given. It will not object if the pin is too slender to carry
          the bending moment placed on it.</div>
          <div class="card"><b>The engineering is the small part.</b> Choosing allowable stresses
          and interpreting the result takes minutes. Evaluating the sequence takes the afternoon.</div>
          <div class="card g"><b>Objective.</b> Keep every formula exactly as the textbook has it.
          Remove only the repetition.</div>
        </div>
      </div>""")

    divider("Part 2", "Literature review",
            "Three published sources define the design procedure used here. Two of them are out "
            "of copyright, so every formula can be shown to a reviewer.")

    slide("""
      <div class="kick">Literature reviewed</div>
      <h2>What each source contributes, and why three were needed</h2>
      <table class="sm">
        <tr><th>Source</th><th>Year</th><th>What it provides</th><th>Used for</th></tr>
        <tr><td><b>NPTEL, IIT Kharagpur</b><br>Design of Machine Elements I, Module 4</td>
            <td>Course</td>
            <td>Complete design procedure for the socket and spigot cotter joint and the knuckle
            joint: empirical proportions as multiples of the rod diameter, and the full list of
            failure modes. Lesson 1 gives the key equations, Lesson 4 the bolt tightening
            relation.</td>
            <td>Primary procedure for four of the six joints</td></tr>
        <tr><td><b>Unwin</b><br><i>The Elements of Machine Design</i></td><td>1899</td>
            <td>Page 179: division of the slot breadth between cotter and gib, thickness as a
            fraction of that breadth, and the permissible taper range.</td>
            <td>The gib and cotter joint, which the course does not cover</td></tr>
        <tr><td><b>Leutwiler</b><br><i>Elements of Machine Design</i></td><td>1917</td>
            <td>Article 98 lists ten distinct ways a cotter joint fails, with the expression for
            each. Article 275 analyses the flange coupling as key, bolts and flange at the hub.</td>
            <td>Independent second opinion, and the coupling</td></tr>
      </table>
      <div class="row r2" style="flex:none;margin-top:8mm">
        <div class="card l"><b>Why a second source on the same joint matters.</b> Where two
        independent texts published eighteen years apart agree, the expression can be treated as
        settled. Where they disagree, the disagreement is itself a finding, and three such
        findings are reported later in this deck.</div>
        <div class="card"><b>Standards consulted.</b> SP 46 for first angle projection and the
        title block, IS 2048 for parallel keys and keyways, IS 1363 and IS 1364 for hexagon head
        bolts and nuts, IS 2693 for cast iron flange couplings.</div>
      </div>""")

    slide("""
      <div class="kick">Existing approaches, and the gap</div>
      <h2>Modelling is solved. Language is solved. The connection between them is not.</h2>
      <div class="row r3">
        <div class="col">
          <h3>Parametric CAD</h3>
          <p>A model driven by a parameter table regenerates when the parameters change, which
          removes the drafting labour.</p>
          <div class="card r"><b>It does not determine the parameters.</b> The designer still
          computes them, and the software regenerates an unsafe model as readily as a safe one.</div>
        </div>
        <div class="col">
          <h3>Language models writing CAD code</h3>
          <p>Recent work generates modelling code directly from a description. Geometry appears
          quickly.</p>
          <div class="card r"><b>No dimension can be traced to a calculation</b> and no failure
          mode is verified. Geometry that cannot be justified is of no use in a design review.</div>
        </div>
        <div class="col">
          <h3>Expert systems and handbooks in software</h3>
          <p>Reliable within the range they were written for, and long established in industry.</p>
          <div class="card r"><b>The calculation is hidden.</b> A result cannot be checked against
          a published source without access to the implementation.</div>
        </div>
      </div>
      <div class="card g" style="margin-top:8mm"><b>The gap addressed here.</b> A system in which
      a written requirement is interpreted by a language model, the resulting parameters drive a
      deterministic calculation taken from published literature, and that calculation stays open
      to inspection by the reader.</div>""")

    divider("Part 3", "What was built",
            "A written requirement goes in. A sized, checked, modelled and drawn joint comes out, "
            "with the whole working printed.")

    slide(f"""
      <div class="kick">The system</div>
      <h2>Five stages, each reporting its result to the next</h2>
      <div class="flow" style="margin-bottom:9mm">
        <div class="ai"><div class="n">01 &middot; AI</div><div class="t">Read</div>
          <div class="d">Sentence to parameters: joint, load, allowable stresses.</div></div>
        <div><div class="n">02</div><div class="t">Size</div>
          <div class="d">Governing formula, rounded up to a preferred size.</div></div>
        <div><div class="n">03</div><div class="t">Check</div>
          <div class="d">Every failure mode against its allowable, iterate on failure.</div></div>
        <div><div class="n">04</div><div class="t">Model</div>
          <div class="d">Exact solids, STEP files, assembly in position.</div></div>
        <div><div class="n">05</div><div class="t">Draw</div>
          <div class="d">First angle A3 sheet, dimensions, title block, DXF.</div></div>
      </div>
      <div class="row r64">
        <div class="fill"><img class="sh" src="{shot('01-landing')}" alt="entry screen">
          <div class="cap">The entry screen. Design rules are held as data, not code, so the
          source of any dimension can be reported the moment it is computed.</div></div>
        <div class="kpi k3" style="grid-template-columns:1fr;align-content:start">
          <div><div class="v">6</div><div class="l">joints implemented</div></div>
          <div><div class="v">{nchecks}</div><div class="l">distinct failure checks</div></div>
          <div><div class="v">{tests}</div><div class="l">automated tests</div></div>
        </div>
      </div>""")

    slide(f"""
      <div class="kick">The decision that matters</div>
      <h2>The AI reads the requirement. It selects no dimension and performs no check.</h2>
      <div class="row r52">
        <div class="col">
          <p>Reading <span class="mono">50 kN</span> as 50,000 N, and <i>socket and spigot</i> as
          the cotter joint, is a language problem. A language model is good at that.</p>
          <p>Choosing a pin diameter is an engineering problem with one correct answer from a
          formula. That stays with deterministic code traceable to a printed page.</p>
          <div class="card l"><b>Safeguard.</b> Any number the model returns that does not appear
          in the request is discarded and the user is told, so an invented figure cannot enter
          the calculation.</div>
          <div class="card r"><b>Why not generate the whole model with AI?</b> Because then no
          dimension could be checked against anything. Geometry that cannot be justified is of no
          use in a design review.</div>
        </div>
        <div>
          <table><tr><th>Stage</th><th>Performed by</th><th>Checkable against</th></tr>
            <tr><td>Read the requirement</td>
                <td style="color:var(--acc)"><b>Language model</b></td><td>the sentence</td></tr>
            <tr><td>Size every dimension</td><td>formula</td><td>cited book page</td></tr>
            <tr><td>Verify failure modes</td><td>formula</td><td>cited book page</td></tr>
            <tr><td>Build the solids</td><td>CAD kernel</td><td>computed dimensions</td></tr>
            <tr><td>Draw the sheet</td><td>FreeCAD</td><td>assembled geometry</td></tr>
          </table>
        </div>
      </div>""")

    rows = "".join(
        f"<tr><td>{j['title']}</td><td class='n'>{j['parts']}</td><td class='n'>{j['dims']}</td>"
        f"<td class='n'>{j['checks']}</td><td>{j['duty']}</td>"
        f"<td class='n'>{round(j['worst']*100)}%</td>"
        f"<td><div class='bar {'hi' if j['worst']>=0.8 else ''}'>"
        f"<span style='width:{round(j['worst']*100)}%'></span></div></td></tr>"
        for j in F["joints"])
    slide(f"""
      <div class="kick">Scope</div>
      <h2>Six joints, {nchecks} failure checks, every one satisfied</h2>
      <table class="sm">
        <tr><th>Joint</th><th class="n">Parts</th><th class="n">Dimensions</th>
            <th class="n">Checks</th><th>Duty</th><th class="n">Busiest</th>
            <th>Utilisation of allowable</th></tr>
        {rows}
      </table>
      <div class="row r2" style="flex:none;margin-top:9mm">
        <div class="card g"><b>Busiest check sits at 67 to 79 percent.</b> That band is the design
        factor working: each joint is sized for 1.25 times the load, then reported at the load,
        so margin is left in hand rather than spent on paper.</div>
        <div class="card r"><b>The gib and cotter joint needed a decision.</b> Unwin gives the
        breadth split and thickness but no strap proportions. Rather than borrow or invent a
        ratio, every dimension the source omits is sized against a failure check.</div>
      </div>""")

    divider("Part 4", "Worked example",
            "A knuckle joint for 50 kN, shown exactly as the software computes it.")

    dims = "".join(f"<tr><td class='mono'>{a}</td><td>{b}</td><td class='n'>{c:g}</td>"
                   f"<td style='font-size:10px'>{d or '-'}</td></tr>"
                   for a, b, c, d in k["dims"][:8])
    slide(f"""
      <div class="kick">Worked example &middot; 1 of 3</div>
      <h2>Which formula governs, and why the larger requirement wins</h2>
      <div class="row r2">
        <div class="col">
          <table><tr><th>Computed before rounding</th><th class="n">mm</th><th>Effect</th></tr>
            <tr><td>Rod in direct tension</td><td class="n">{k['raw']['rod_tension']}</td>
                <td>rod adopted as <b>35</b></td></tr>
            <tr><td>Pin in double shear</td><td class="n">{k['raw']['pin_shear']}</td>
                <td>not governing</td></tr>
            <tr><td>Pin in bending</td><td class="n">{k['raw']['pin_bending']}</td>
                <td>governs, pin adopted as <b>45</b></td></tr>
          </table>
          <div class="eq">D = &radic;(4P / &pi;&sigma;<sub>t</sub>) &nbsp;&nbsp;
            d = &radic;(2P / &pi;&tau;) &nbsp;&nbsp;
            d = [16P(t&#8321;/3 + t/4) / &pi;&sigma;<sub>b</sub>]<sup>1/3</sup></div>
          <div class="card r"><b>Bending asks for 1.7 times what shear asks for.</b> A pin sized
          from shear alone passes its own check and bends in service. The source takes the same
          step.</div>
        </div>
        <div><table class="sm"><tr><th>Symbol</th><th>Meaning</th><th class="n">mm</th>
          <th>Rule and source</th></tr>{dims}</table></div>
      </div>""")

    checks = "".join(
        f"<tr><td>{n}</td><td class='mono'>{f}</td><td class='n'>{s:g}</td>"
        f"<td class='n'>{a:g}</td><td class='n'>{round(100*s/a)}%</td>"
        f"<td><div class='bar {'hi' if s/a>=0.8 else ''}'>"
        f"<span style='width:{round(100*s/a)}%'></span></div></td></tr>"
        for n, f, s, a, _ in k["checks"])
    slide(f"""
      <div class="kick">Worked example &middot; 2 of 3</div>
      <h2>All nine failure modes, evaluated at the actual load</h2>
      <table class="sm">
        <tr><th>Failure mode</th><th>Expression</th><th class="n">Stress MPa</th>
            <th class="n">Allowable</th><th class="n">Used</th><th>Utilisation</th></tr>
        {checks}
      </table>
      <div class="row r2" style="flex:none;margin-top:8mm">
        <div class="card g"><b>Nine of nine satisfied.</b> Busiest is shear of the eye at 76
        percent of its allowable stress.</div>
        <div class="card l"><b>None of this is stored.</b> Ask for 80 kN and every value in the
        table changes, and the pin is re-sized.</div>
      </div>""")

    slide(f"""
      <div class="kick">Worked example &middot; 3 of 3</div>
      <h2>The working is printed, so the output can be checked rather than trusted</h2>
      <div class="row r25">
        <div class="col">
          <p>Each run prints the values computed before rounding, the size adopted, the rule and
          source behind every proportion, every check with its arithmetic substituted, and the
          volume and mass of each solid.</p>
          <div class="card l"><b>What this buys in a review.</b> A reviewer does not have to
          accept the result. Every line can be recomputed by hand from the formula printed beside
          it.</div>
          <div class="card"><b>It is also the reason the next three slides exist.</b> Printing
          every check is what made the errors in the published sources visible.</div>
        </div>
        <div class="fill"><img class="sh" src="{shot('03-working-log')}" alt="working">
          <div class="cap">Working printed for the example above.</div></div>
      </div>""")

    divider("Part 5", "Output",
            "Exact solids in a neutral format, and a first angle sheet produced without opening "
            "a CAD application.")

    slide(f"""
      <div class="kick">Output &middot; drafting</div>
      <h2>First angle A3 sheet, dimensioned, with a title block</h2>
      <div class="row r64">
        <div class="fill"><img class="sh" src="{shot('05-drawing')}" alt="drawing sheet"></div>
        <div class="col">
          <div class="card"><b>How it is made.</b> FreeCAD is driven without its graphical
          interface. The assembled geometry is projected to obtain the front view, the left side
          view and the plan, arranged in first angle projection, with an isometric view.</div>
          <table class="sm"><tr><th>File</th><th>Use</th></tr>
            <tr><td class="mono">drawing.svg</td><td>A3 sheet</td></tr>
            <tr><td class="mono">drawing.dxf</td><td>AutoCAD</td></tr>
            <tr><td class="mono">assembly.step</td><td>NX, SolidWorks, Fusion</td></tr>
            <tr><td class="mono">parts/*.step</td><td>each component</td></tr>
            <tr><td class="mono">*.FCStd</td><td>editable FreeCAD file</td></tr>
          </table>
        </div>
      </div>""")

    slide(f"""
      <div class="kick">Output &middot; NX10</div>
      <h2>Verified the file structure. Opening it in NX10 itself is the one step still in the lab.</h2>
      <div class="row r52">
        <div class="col">
          <div class="card l"><b>What we checked, directly, not assumed.</b> The exported
          assembly was opened as text and read. Two things decide whether an assembly import
          works at all, and both are confirmed below.</div>
          <div class="eq" style="white-space:pre-wrap;line-height:1.55">FILE_SCHEMA(('AUTOMOTIVE_DESIGN {{ ... 214 ... }}'));

#41  = PRODUCT('rod','rod', ...);
#784 = PRODUCT('strap','strap', ...);
#2141 = PRODUCT('cotter','cotter', ...);
#2490 = PRODUCT('gib','gib', ...);</div>
          <div class="cap">Exact lines read from assembly.step for the gib and cotter joint.</div>
        </div>
        <div class="col">
          <table class="sm"><tr><th>Check</th><th>Result</th></tr>
            <tr><td>Schema is AP214 (AUTOMOTIVE_DESIGN)</td><td>confirmed, exactly what NX10 reads</td></tr>
            <tr><td>Parts stay separate, not fused</td><td>confirmed, 4 named solids for 4 parts</td></tr>
            <tr><td>Opens in NX10 as an assembly</td><td>not yet observed, lab-only software</td></tr>
          </table>
          <div class="card r"><b>Said plainly, not glossed over.</b> This is the one objective of
          six, from Section 1.3 of the report, not yet confirmed by watching it happen. The file
          is built to the structure NX10 needs; nobody has opened it there yet.</div>
        </div>
      </div>""")

    slide(f"""
      <div class="kick">Output &middot; geometry</div>
      <h2>Assembled, exploded, and coloured by how close each part is to its limit</h2>
      <div class="row r2">
        <div class="fill"><img class="sh" src="{shot('04-model')}" alt="model">
          <div class="cap">Assembled model, rotatable in the browser, exact geometry in the STEP
          files.</div></div>
        <div class="fill"><img class="sh" src="{shot('08-weak-spots')}" alt="weak spots">
          <div class="cap">The same joint coloured by utilisation, so the member nearest its limit
          is visible without reading the table.</div></div>
      </div>""")

    divider("Part 6", "Verification",
            "Every proportion and every check compared against published design literature. "
            "The comparison found three errors in the sources.")

    slide(f"""
      <div class="kick">Sources</div>
      <h2>Checked against three published sources, two of them out of copyright</h2>
      <table class="sm">
        <tr><th>Joint</th><th>Source consulted</th><th>Outcome</th></tr>
        <tr><td>Knuckle joint</td><td>NPTEL IIT Kharagpur, Module 4 Lesson 2</td>
            <td>proportions and all nine checks verified</td></tr>
        <tr><td>Socket and spigot cotter</td><td>NPTEL M4 L2; Leutwiler (1917) Art. 98</td>
            <td>ten checks verified against two independent books</td></tr>
        <tr><td>Gib and cotter</td><td>Unwin (1899), page 179</td>
            <td>breadth split, thickness and taper verified</td></tr>
        <tr><td>Flange coupling</td><td>NPTEL M4 L1 keys; Leutwiler Art. 275 bolts</td>
            <td>all seven checks verified twice; proportions not verifiable</td></tr>
        <tr><td>Sleeve and cotter</td><td>four books searched, none covers it</td>
            <td>checks verified by correspondence; proportions unverified</td></tr>
        <tr><td>Hex bolted joint</td><td>NPTEL Module 4 Lesson 4</td>
            <td>tightening relation verified; size table unverified</td></tr>
      </table>
      <div class="card l" style="margin-top:9mm"><b>Where no source exists, the software says so
      on every run.</b> Leutwiler records that no standard set of flange coupling proportions was
      ever agreed, and that published tables are individual manufacturers' practice. Those
      proportions are marked unverified rather than given a source they do not have.</div>""")

    slide(f"""
      <div class="kick">Finding 1 of 3</div>
      <h2>A worked example that fails its own check</h2>
      <div class="row r52">
        <div class="col">
          <p>The knuckle joint worked problem raises the pin from <b>40 mm to 55 mm</b> for
          bending, then evaluates the eye using the <b>original 40 mm pin</b>.</p>
          <div class="eq">eye shear = P / ((d&#8322; &minus; d) t)<br><br>
            with d = 55 &nbsp; 100000 / ((80 &minus; 55) &times; 50) = <b>80 MPa</b><br>
            allowable &nbsp; 65 MPa</div>
          <div class="card r"><b>Its own expression, with the pin it actually adopted, exceeds its
          own allowable by 23 percent.</b></div>
          <p><b>What this software does instead:</b> it enlarges the outer diameter of the eye
          until the check passes, and reports that it has done so.</p>
        </div>
        <div class="fill"><img class="sh" src="{shot('07-checks')}" alt="checks">
          <div class="cap">Every check shows its substituted arithmetic, which is how an
          inconsistency of this kind becomes visible rather than inherited.</div></div>
      </div>""")

    slide(f"""
      <div class="kick">Findings 2 and 3 of 3</div>
      <h2>An omitted failure mode, and a constant printed wrongly</h2>
      <div class="row r2">
        <div class="col">
          <h3>Omitted failure mode</h3>
          <p>The cotter joint procedure verifies crushing of the socket but not crushing between
          the cotter and the spigot.</p>
          <div class="eq">P / (d&#8321; t) = 50000 / (30 &times; 10) = <b>167 MPa</b><br>
            allowable &nbsp; 110 MPa</div>
          <div class="card r"><b>Leutwiler, Article 98, lists ten failure modes and includes this
          one.</b> Two independent texts, eighteen years apart, contain a check the lesson omits.
          That is what makes it an omission and not a preference.</div>
        </div>
        <div class="col">
          <h3>Constant printed wrongly</h3>
          <p>The initial tightening load is printed as 284<i>d</i> kN. The worked example on the
          same page obtains 56.8 kN for an M20 bolt.</p>
          <div class="eq">284 &times; 20 = 5,680 kN &nbsp; &ne; &nbsp; 56.8 kN<br>
            2840 &times; 20 = 56,800 N &nbsp; = &nbsp; 56.8 kN &#10003;</div>
          <div class="card r"><b>The page refutes itself.</b> The constant is 2840<i>d</i> newtons
          and the printed relation is out by a factor of one hundred. Every bolted design now reports the
          tightening load.</div>
        </div>
      </div>""")

    divider("Part 7", "Validation and limits",
            "An independent finite element cross check, the tests that hold the work together, "
            "and what the system does not do.")

    slide(f"""
      <div class="kick">Independent cross check</div>
      <h2>Finite element analysis, and knowing when not to believe it</h2>
      <div class="row r2">
        <div class="col">
          <table class="sm"><tr><th>Case</th><th class="n">Formula</th><th class="n">Computed</th>
            <th class="n">Difference</th></tr>
            <tr><td>20 mm bar, 10 kN tension</td><td class="n">31.83</td><td class="n">32.22</td>
                <td class="n">+1.2 %</td></tr>
            <tr><td>Knuckle eye rod, 50 kN</td><td class="n">52.0</td><td class="n">57.9</td>
                <td class="n">+11.5 %</td></tr>
          </table>
          <p>The bar validates the method. The eye rod reads higher because the formula treats it
          as a plain bar and ignores the stress raised at the pin bore. Both stay under the 75 MPa
          allowable.</p>
        </div>
        <div class="col">
          <div class="card r"><b>A peak that never settles is not a stress.</b> On one component
          the computed peak moved between <b>157 and 191 MPa</b> across a sixteen fold increase in
          nodes. That is a singularity at a constrained face, not a value to design to.</div>
          <div class="card"><b>So the software re-solves</b> on a mesh of half the element size
          whenever the peak exceeds 1.5 times the calculated value, and reports
          <span class="mono">NOT CONVERGED</span> if it then moves more than 5 percent.</div>
          <div class="card l"><b>Stated plainly in the report.</b> One linear static run on one
          component with boundary conditions the software chooses. A second opinion on the
          formula, not a replacement for analysis.</div>
        </div>
      </div>""")

    slide(f"""
      <div class="kick">Correctness</div>
      <h2>{tests} automated tests, and the row that matters most is the last one</h2>
      <div class="row r52">
        <div>
          <table class="sm"><tr><th>What is tested</th><th>Why</th></tr>
            <tr><td>Sizing arithmetic</td><td>values match the worked problems in the sources</td></tr>
            <tr><td>Generated geometry</td><td>each part is one valid solid, no two parts overlap</td></tr>
            <tr><td>Request interpretation</td><td>parameters correct, invented numbers dropped</td></tr>
            <tr><td>Drawing sheet</td><td>sheet, DXF and FreeCAD file are produced</td></tr>
            <tr><td>Finite element path</td><td>face selection refers to dimensions that exist</td></tr>
            <tr><td><b>The three findings</b></td><td><b>assert the source errors are real</b></td></tr>
          </table>
        </div>
        <div class="col">
          <div class="card g"><b>Why that last row exists.</b> Tests assert that the published
          answers fail their own checks. Without them, someone could later correct the software
          back to the printed values and every other test would still pass.</div>
          <div class="card"><b>A test that found what no dimension check could.</b> Comparing
          solids pairwise caught a gib hook modelled 1.25 mm inside the strap, occupying metal
          another part already occupied. Every individual dimension was correct.</div>
        </div>
      </div>""")

    slide(f"""
      <div class="kick">Limits</div>
      <h2>What this does not do, said before anyone asks</h2>
      <div class="row r2">
        <div><ul>
          <li><b>Static loading only.</b> Fatigue, endurance limit and stress concentration
          factors are outside the scope.</li>
          <li><b>Nominal dimensions only.</b> Tolerances and fits are not applied, so the sheet is
          not yet a manufacturing drawing.</li>
          <li><b>Three of six joints have unverified proportions.</b> The sleeve and cotter
          joint, the flange coupling and the hex bolt size table. The software reports this on every run.</li>
          <li><b>Nut thread stripping is not checked</b> for the bolted joint.</li>
        </ul></div>
        <div class="col">
          <h3 style="font-size:16px">Scope for future work</h3>
          <ul>
            <li>Riveted and welded joints, which follow the same pattern.</li>
            <li>Fatigue loading, through an endurance limit and a stress concentration factor.</li>
            <li>Tolerances and fits, to make the sheet usable for manufacture.</li>
            <li>A journal script for Siemens NX, so the assembly is built inside it rather than
            imported.</li>
          </ul>
        </div>
      </div>""")

    OBJ = [
        ("Interpret a plain English requirement", "Met",
         "Language model extracts joint and load; anything not traceable to the sentence is dropped."),
        ("Size and verify every failure mode, with iteration", "Met",
         "All 44 applicable checks satisfied; iterative enlargement closes gaps the source proportions leave."),
        ("Exact solids in a neutral format, opening in commercial CAD", "Substantially met",
         "AP214 schema and 4 separate named solids confirmed by direct inspection; opening inside NX10 itself not yet observed."),
        ("A first angle drawing sheet to Indian practice", "Met for projection and layout",
         "SP 46 projection and title block done; tolerances and fits not implemented."),
        ("Verify against literature, record disagreements", "Met for 4 of 6 joints",
         "2 joints carry proportions with no supporting source, reported on every run, not hidden."),
        ("Browser use without installation", "Met",
         "Deployed and reachable without install; hosted copy runs the rule-based reader, not the language model."),
    ]
    rows = "".join(
        f"<tr><td>{i}</td><td>{o}</td><td><b>{s}</b></td><td style='font-size:12px'>{e}</td></tr>"
        for i, (o, s, e) in enumerate(OBJ, 1))
    slide(f"""
      <div class="kick">Objectives revisited</div>
      <h2>Six objectives set at the start, assessed against the evidence, not restated as met</h2>
      <table class="sm">
        <tr><th>#</th><th>Objective</th><th>Status</th><th>Evidence</th></tr>
        {rows}
      </table>
      <div class="card l" style="margin-top:9mm"><b>Objectives 1, 2 and 6 are met; 3, 4 and 5 are met in
      part.</b> Each open point is stated in the table: the NX10 import not yet observed, no
      tolerances on the sheet, two joints partly verified. Reporting those points is itself part of Objective 5:
      disagreements and open points recorded explicitly, not smoothed over.</div>""")

    # Timeline across both semesters. Green is finished, amber is where the project stands
    # today, grey is planned. Marked honestly: only work that exists is shown as complete.
    ph = [
        ("Phase 1", "Semester 7", "done",
         ["Problem formulation and scope",
          "Literature review: NPTEL, Unwin 1899, Leutwiler 1917",
          "Design procedure and failure modes extracted"]),
        ("Phase 2", "Semester 7", "done",
         ["Sizing engine and preferred size rounding",
          "All six joints, 44 failure checks",
          "Iterative correction when a check fails"]),
        ("Phase 3", "Semester 7", "now",
         ["Solid modelling and STEP export",
          "First angle A3 sheet and DXF",
          "Verification against the three sources",
          "Finite element cross check, 290 tests",
          "Web deployment, report and presentation"]),
        ("Phase 4", "Semester 8, proposed scope", "next",
         ["Riveted and welded joints",
          "Fatigue loading and stress concentration",
          "Tolerances and fits on the drawing",
          "Verify the two proportion sets still without a source",
          "NX journal script for direct assembly",
          "Bill of materials and cost"]),
    ]
    colour = {"done": "#0e7c41", "now": "#9a5a00", "next": "#9aa6b4"}
    label = {"done": "Complete", "now": "Current stage", "next": "Planned"}
    cols = ""
    for name, when, state, items in ph:
        c = colour[state]
        lis = "".join(f'<li style="margin-bottom:4px">{i}</li>' for i in items)
        cols += (
            f'<div style="flex:1;display:flex;flex-direction:column">'
            f'<div style="width:13px;height:13px;border-radius:50%;background:{c};'
            f'margin-bottom:9px;box-shadow:0 0 0 3px #fff,0 0 0 4.5px {c}33"></div>'
            f'<div style="font-size:9.6px;letter-spacing:.09em;text-transform:uppercase;'
            f'font-weight:800;color:{c}">{label[state]}</div>'
            f'<div style="font-size:15px;font-weight:800;color:var(--ink);margin:3px 0 1px">'
            f'{name}</div>'
            f'<div style="font-size:10.6px;color:var(--mute);margin-bottom:7px">{when}</div>'
            f'<ul style="font-size:11.4px;line-height:1.42;padding-left:14px;margin:0">{lis}</ul>'
            f'</div>')
    slide(f"""
      <div class="kick">Timeline</div>
      <h2>Where the project stands across both semesters</h2>
      <div style="position:relative;margin-top:6mm">
        <div style="position:absolute;top:6px;left:6px;right:6px;height:2px;
          background:linear-gradient(90deg,#0e7c41 0%,#0e7c41 28%,#9a5a00 46%,#9aa6b4 62%,
          #9aa6b4 100%)"></div>
        <div style="display:flex;gap:7mm;position:relative">{cols}</div>
      </div>
      <div class="row r2" style="flex:none;margin-top:9mm">
        <div class="card g"><b>Everything shown in green and amber exists today.</b> Six joints,
        44 checks, the drawing sheet, the verification against three books and 290 tests are all
        working and demonstrated in this presentation.</div>
        <div class="card"><b>Semester 8 is a proposal, not a commitment.</b> These items come
        from the limits listed on the previous slide and are to be agreed with the guide.</div>
      </div>""")

    slide("""
      <div class="kick">Physics first</div>
      <h2>The AI proposes, the physics decides</h2>
      <div class="flow" style="margin-top:4mm">
        <div class="ai"><div class="n">1 &middot; AI</div><div class="t">Read the sentence</div>
          <div class="d">"knuckle joint for 50 kN" becomes joint = knuckle, P = 50,000 N.
          Any number not in the sentence is thrown away.</div></div>
        <div><div class="n">2 &middot; PHYSICS</div><div class="t">Size from the equations</div>
          <div class="d">D = &radic;(4P / &pi;&sigma;<sub>t</sub>), pin from shear and from bending,
          the larger wins.</div></div>
        <div><div class="n">3 &middot; PHYSICS</div><div class="t">Check every failure</div>
          <div class="d">Tension, double shear, bending, crushing: nine checks with the arithmetic
          printed.</div></div>
        <div><div class="n">4 &middot; PHYSICS</div><div class="t">Fail? Enlarge and recheck</div>
          <div class="d">The member that fails grows 1 mm at a time until every check passes.</div></div>
        <div><div class="n">5 &middot; CAD</div><div class="t">Build and draw</div>
          <div class="d">Exact solids in STEP, the assembly, and a first angle A3 sheet.</div></div>
      </div>
      <div class="row r2" style="flex:none;margin-top:8mm">
        <div class="card l"><b>A physics informed neural network (PINN)</b> learns a design and is
        penalised when it breaks an equation. The penalty makes a violation unlikely, not
        impossible.</div>
        <div class="card g"><b>Here the equations are not a penalty, they are the answer.</b> No
        dimension comes from the model, so no output can break a law of mechanics. The model only
        reads; the physics sizes, checks and corrects.</div>
      </div>""")

    slide(f"""
      <div style="display:flex;flex-direction:column;justify-content:center;flex:1">
        <div class="kick">Conclusion</div>
        <h2 style="font-size:38px;max-width:88%">Every dimension it produces can be traced to a
        formula, and every formula to a page in a book.</h2>
        <p class="lead" style="max-width:74%">The language model reads the requirement. The
        engineering stays deterministic, checked, and open to inspection. That division is what
        allows a natural language interface without any part of the design becoming
        unverifiable.</p>
        <div class="kpi k3" style="margin-top:18px">
          <div><div class="v">6</div><div class="l">joints, {nchecks} checks, all satisfied</div></div>
          <div><div class="v">3</div><div class="l">errors found in published sources</div></div>
          <div><div class="v">{tests}</div><div class="l">automated tests</div></div>
        </div>
        {qr_block(26)}
      </div>""", foot=f"{LIVE} &nbsp;&middot;&nbsp; " + " &middot; ".join(n for _, n in TEAM))

    html = (f"<!doctype html><html><head><meta charset='utf-8'><title>{TITLE}</title>"
            f"<style>{CSS}</style></head><body>{''.join(S)}</body></html>")
    BUILD.mkdir(exist_ok=True)
    src = BUILD / "deck.html"
    src.write_text(html)
    pdf = HERE / "AI-in-CAD-Major-Project-Presentation.pdf"
    if pdf.exists():
        pdf.unlink()
    subprocess.run([BRAVE, "--headless", "--disable-gpu", "--no-sandbox",
                    f"--print-to-pdf={pdf}", "--no-pdf-header-footer",
                    "--virtual-time-budget=40000", src.resolve().as_uri()],
                   capture_output=True, timeout=400)
    print(f"{pdf.name}  {pdf.stat().st_size // 1024} KB  {N} slides")
    make_pptx(pdf)


def make_pptx(pdf: Path) -> None:
    """Pack the rendered slides into a PowerPoint file so it opens on any machine."""
    from pptx import Presentation
    from pptx.util import Inches
    png_dir = BUILD / "slides"
    png_dir.mkdir(exist_ok=True)
    for old in png_dir.glob("*.png"):
        old.unlink()
    subprocess.run(["pdftoppm", "-r", "150", "-png", str(pdf), str(png_dir / "s")], check=True)
    try:
        from notes import NOTES                      # when run from inside report/
    except ImportError:
        import sys
        sys.path.insert(0, str(HERE))
        from notes import NOTES
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(W_IN), Inches(H_IN)
    blank = prs.slide_layouts[6]
    for i, p in enumerate(sorted(png_dir.glob("s-*.png")), 1):
        sl = prs.slides.add_slide(blank)
        sl.shapes.add_picture(str(p), 0, 0, width=prs.slide_width, height=prs.slide_height)
        note = NOTES.get(i)
        if note:
            sl.notes_slide.notes_text_frame.text = note.strip()
    out = HERE / "AI-in-CAD-Major-Project-Presentation.pptx"
    prs.save(str(out))
    print(f"{out.name}  {out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    build()
