"""Build the presentation deck as a local PDF, 16:9.

Detailed version: every formula, every number and every screenshot is carried, so the deck can
be presented without needing the report open beside it. Figures come from report/facts.json,
which the software writes when it runs. Rendered with the Brave already on this machine.

    python report/make_slides.py
"""
from __future__ import annotations

import base64
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
SHOTS = HERE / "shots"
BRAVE = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
F = json.loads((HERE / "facts.json").read_text())

TEAM = [("Ansh Yadav", "10"), ("Ankur Dodhke", "14"), ("Atishay Jain", "24"),
        ("Bhavya Shrivastava", "30"), ("Dharmendra Gupta", "D03")]
GUIDE = "____________________"
DEPT = "Department of Mechanical Engineering"
INSTITUTE = "Shri G. S. Institute of Technology and Science, Indore"
TITLE = "Strategic Application of Artificial Intelligence in CAD"
LIVE = "aicad-vercel.vercel.app"

CSS = """
@page{size:338.7mm 190.5mm;margin:0}
:root{--ink:#0b1017;--body:#222c38;--muted:#68727f;--line:#d8e0e8;--accent:#1d4ed8;
 --ok:#0e7a40;--warn:#9a5800;--bad:#b0271f;--panel:#f4f7fb}
*{box-sizing:border-box}
html,body{margin:0;background:#fff;color:var(--body);
 font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}
.s{width:338.7mm;height:190.5mm;padding:13mm 15mm 12mm;page-break-after:always;
 display:flex;flex-direction:column;overflow:hidden;position:relative}
.s:last-child{page-break-after:auto}
.tag{font-size:10.5px;letter-spacing:.2em;text-transform:uppercase;color:var(--accent);
 font-weight:700;margin-bottom:5px}
h1{font-size:46px;line-height:1.05;margin:0 0 9px;color:var(--ink);letter-spacing:-0.02em}
h2{font-size:25px;line-height:1.14;margin:0 0 9px;color:var(--ink);letter-spacing:-0.012em}
h3{font-size:13.5px;margin:0 0 4px;color:var(--ink)}
p{font-size:12.6px;line-height:1.5;margin:0 0 7px}
ul{font-size:12.6px;line-height:1.5;margin:0 0 6px;padding-left:16px}
li{margin-bottom:5px}
.lead{font-size:16px;color:var(--muted);line-height:1.45}
.row{display:grid;gap:9mm;flex:1;min-height:0}
.r2{grid-template-columns:1fr 1fr}
.r3{grid-template-columns:1fr 1fr 1fr}
.r52{grid-template-columns:1.5fr 1fr}
.r25{grid-template-columns:1fr 1.5fr}
.stack{display:flex;flex-direction:column;gap:6mm;min-height:0}
img{width:100%;border:1px solid var(--line);border-radius:7px;background:#fff;
 object-fit:contain;object-position:top}
.fill{flex:1;min-height:0;display:flex;flex-direction:column}
.fill img{flex:1;min-height:0;object-fit:contain;object-position:top}
.cap{font-size:10px;color:var(--muted);margin-top:5px;line-height:1.35}
table{width:100%;border-collapse:collapse;font-size:11.4px}
th{text-align:left;font-size:9.6px;text-transform:uppercase;letter-spacing:.07em;
 color:var(--muted);border-bottom:1.6px solid var(--ink);padding:4px 7px 4px 0;font-weight:700}
td{padding:4px 7px 4px 0;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:none}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
table.sm{font-size:10.4px}
table.sm th,table.sm td{padding:3px 6px 3px 0}
.mono{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:10.6px}
.note{background:var(--panel);border-left:3.5px solid var(--accent);border-radius:6px;
 padding:9px 12px;font-size:12px;line-height:1.48}
.note.bad{border-left-color:var(--bad)}
.note.ok{border-left-color:var(--ok)}
.note b{color:var(--ink)}
.big{display:grid;gap:9px}
.b4{grid-template-columns:repeat(4,1fr)}
.b3{grid-template-columns:repeat(3,1fr)}
.big div{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px 12px}
.big .v{font-size:29px;font-weight:700;color:var(--ink);line-height:1;
 font-variant-numeric:tabular-nums}
.big .l{font-size:9.6px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);
 margin-top:4px}
.pipe{display:flex;gap:6px;margin:4px 0 8px}
.pipe div{flex:1;background:var(--panel);border:1px solid var(--line);border-radius:6px;
 padding:7px 8px}
.pipe .n{font-size:9px;color:var(--accent);font-weight:700;letter-spacing:.08em}
.pipe .t{font-size:11.5px;font-weight:700;color:var(--ink);margin:2px 0}
.pipe .d{font-size:10px;color:var(--muted);line-height:1.35}
.pipe .ai{border-color:var(--accent);background:#eef3ff}
.bar{height:6px;background:#e4eaf1;border-radius:3px;overflow:hidden;min-width:44px}
.bar span{display:block;height:100%;background:var(--ok)}
.bar.hi span{background:var(--warn)}
.pn{position:absolute;right:15mm;bottom:7mm;font-size:10px;color:var(--muted)}
.ft{position:absolute;left:15mm;bottom:7mm;font-size:10px;color:var(--muted)}
.eq{font-family:ui-monospace,"SF Mono",Menlo,monospace;font-size:12.5px;color:var(--ink);
 background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:7px 10px;
 margin:4px 0 7px}
"""


def im(name: str) -> str:
    f = SHOTS / f"{name}.png"
    return ("data:image/png;base64," + base64.b64encode(f.read_bytes()).decode()) if f.exists() else ""


N = 0


def slide(body: str, foot: str = "") -> str:
    global N
    N += 1
    ft = f'<div class="ft">{foot}</div>' if foot else ""
    return f'<section class="s">{body}{ft}<div class="pn">{N}</div></section>'


def build() -> str:
    k = F["knuckle"]
    tests = F["tests"].split()[0]
    nchecks = sum(j["checks"] for j in F["joints"])
    S = []

    team_rows = "".join(f"<tr><td>{n}</td><td class='n'>{r}</td></tr>" for n, r in TEAM)

    S.append(slide(f"""
      <div style="display:flex;flex-direction:column;justify-content:center;flex:1">
        <div class="tag">Major Project &middot; Semester 7</div>
        <h1 style="max-width:80%">{TITLE}</h1>
        <p class="lead" style="max-width:72%">A written requirement goes in. A sized, checked,
        modelled and drawn machine joint comes out, with every number traceable to a published
        formula.</p>
        <div class="row r2" style="flex:none;margin-top:18px">
          <table class="sm"><tr><th>Submitted by</th><th class="n">Roll No.</th></tr>{team_rows}</table>
          <div style="font-size:12.6px;padding-top:18px">
            <b>Guide:</b> {GUIDE}<br>
            <span style="color:var(--muted)">{DEPT}<br>{INSTITUTE}</span></div>
        </div>
      </div>""", f"Live at {LIVE}"))

    S.append(slide(f"""
      <div class="tag">The problem</div>
      <h2>The calculation is repetitive, and repeating it is where the time goes</h2>
      <div class="row r2">
        <div class="stack">
          <p>For a single knuckle joint the designer computes the rod from tension, sizes the pin
          twice, derives seven proportions, then verifies nine separate failure modes. Change the
          load and every one of those steps is done again.</p>
          <p>Parametric CAD removes the drafting labour but not this. A modeller will regenerate
          whatever dimensions it is given, and will not object if the pin is too slender to carry
          its bending moment.</p>
          <div class="note"><b>The aim.</b> Keep every formula exactly as the textbook has it and
          remove only the repetition, so that the engineering stays checkable.</div>
        </div>
        <div>
          <table><tr><th>Step done by hand, per joint</th><th class="n">Repeats on load change</th></tr>
            <tr><td>Rod diameter from direct tension</td><td class="n">yes</td></tr>
            <tr><td>Pin from double shear</td><td class="n">yes</td></tr>
            <tr><td>Pin from bending, take the larger</td><td class="n">yes</td></tr>
            <tr><td>Seven proportions from the rod</td><td class="n">yes</td></tr>
            <tr><td>Nine failure checks</td><td class="n">yes</td></tr>
            <tr><td>Re-size anything that fails, re-check</td><td class="n">yes</td></tr>
            <tr><td>Four views, dimensions, title block</td><td class="n">yes</td></tr>
          </table>
        </div>
      </div>"""))

    S.append(slide(f"""
      <div class="tag">Objectives</div>
      <h2>What the project set out to do</h2>
      <div class="row r2">
        <div><ul>
          <li><b>Interpret a written requirement.</b> Extract joint type, load and allowable
          stresses from a sentence in ordinary English.</li>
          <li><b>Size from published formulas.</b> Use the procedure given in the design
          literature, rounding to preferred sizes as the source directs.</li>
          <li><b>Verify every failure mode</b> against the allowable stress, and iterate where a
          check is not satisfied.</li>
          <li><b>Generate exact solid models</b> of each component and the assembly, in a format
          that opens in commercial CAD.</li>
        </ul></div>
        <div><ul>
          <li><b>Produce a first angle drawing sheet</b> with dimensions and a title block, to
          Indian drawing practice.</li>
          <li><b>Verify the system itself</b> against published design literature, and record any
          disagreement with a source explicitly rather than silently.</li>
          <li><b>Make it usable in a browser</b> with nothing installed.</li>
        </ul>
        <div class="note ok" style="margin-top:6px"><b>Measure of success.</b> Every dimension the
        system produces can be attributed either to a formula with a cited source, or to a named
        failure check. Nothing is unexplained.</div>
        </div>
      </div>"""))

    S.append(slide(f"""
      <div class="tag">System overview</div>
      <h2>Five stages, each reporting its result to the next</h2>
      <div class="pipe">
        <div class="ai"><div class="n">STAGE 1 &middot; AI</div><div class="t">Read the request</div>
          <div class="d">Sentence to parameters: joint, load, allowable stresses. Pattern rules
          as fallback.</div></div>
        <div><div class="n">STAGE 2</div><div class="t">Size</div>
          <div class="d">Governing formula gives the primary diameter, rounded up to a preferred
          size. Proportions follow.</div></div>
        <div><div class="n">STAGE 3</div><div class="t">Check</div>
          <div class="d">Every failure mode evaluated against its allowable. Failing dimension
          raised 1 mm and re-checked.</div></div>
        <div><div class="n">STAGE 4</div><div class="t">Model</div>
          <div class="d">Each part built as an exact solid, written as STEP, plus the assembly in
          position.</div></div>
        <div><div class="n">STAGE 5</div><div class="t">Draw</div>
          <div class="d">First angle A3 sheet, four views, dimensions, title block, and a DXF.</div></div>
      </div>
      <div class="row r52" style="margin-top:2mm">
        <div class="fill"><img src="{im('01-landing')}" alt="request screen">
          <div class="cap">The request screen. The design rules for each joint are held as data,
          not code, so the source of any dimension can be reported as it is computed.</div></div>
        <div class="stack">
          <div class="big b3" style="grid-template-columns:1fr">
            <div><div class="v">6</div><div class="l">joints implemented</div></div>
            <div><div class="v">{nchecks}</div><div class="l">distinct failure checks</div></div>
            <div><div class="v">{tests}</div><div class="l">automated tests</div></div>
          </div>
        </div>
      </div>"""))

    S.append(slide(f"""
      <div class="tag">The central design decision</div>
      <h2>The AI reads the request. It selects no dimension and performs no check.</h2>
      <div class="row r52">
        <div class="stack">
          <p>Determining that <span class="mono">50 kN</span> denotes 50,000 N, and that
          <i>socket and spigot</i> names the cotter joint, is a language problem. A language model
          is effective at that.</p>
          <p>Determining the pin diameter is an engineering problem with one correct answer
          obtainable from a formula. It stays with deterministic code whose every step is
          traceable to a printed page.</p>
          <div class="note"><b>Safeguard.</b> Any number the model returns that does not appear in
          the original request is discarded and the user is told. A plausible but invented figure
          cannot enter the calculation.</div>
          <div class="note bad"><b>Why not let it generate the whole model?</b> Because then no
          dimension could be checked against anything. Geometry that cannot be justified is of no
          use in a design review.</div>
        </div>
        <div>
          <table><tr><th>Stage</th><th>Performed by</th><th>Checkable against</th></tr>
            <tr><td>Read the sentence</td><td style="color:var(--accent)"><b>Language model</b></td>
                <td>the sentence itself</td></tr>
            <tr><td>Size every dimension</td><td>formula</td><td>cited book page</td></tr>
            <tr><td>Verify failure modes</td><td>formula</td><td>cited book page</td></tr>
            <tr><td>Build solids</td><td>CAD kernel</td><td>the computed dimensions</td></tr>
            <tr><td>Draw the sheet</td><td>FreeCAD</td><td>the assembled geometry</td></tr>
          </table>
        </div>
      </div>"""))

    S.append(slide(f"""
      <div class="tag">Sizing procedure</div>
      <h2>How a dimension is arrived at</h2>
      <div class="row r2">
        <div class="stack">
          <h3>1. Governing dimension from the primary failure mode</h3>
          <div class="eq">D = sqrt( 4P / (&pi; &sigma;<sub>t</sub>) )</div>
          <p style="margin-top:-2px">The computed value is rounded <b>up to the next preferred
          size</b>, as the source directs, not used as computed.</p>
          <h3>2. A component with two independent modes is sized from both</h3>
          <div class="eq">pin shear: d = sqrt( 2P / (&pi; &tau;) )<br>
          pin bending: d = [ 16P (t&#8321;/3 + t/4) / (&pi; &sigma;<sub>b</sub>) ]<sup>1/3</sup></div>
          <p style="margin-top:-2px">The <b>larger requirement governs</b>. A pin sized from shear
          alone satisfies that check and bends in service.</p>
        </div>
        <div class="stack">
          <h3>3. Remaining dimensions from book proportions</h3>
          <p style="margin-bottom:4px">Each expressed as a multiple of the governing dimension,
          with its source recorded beside it, for example</p>
          <div class="eq">d&#8322; = 2.0 D &nbsp;&nbsp; t = 1.25 D &nbsp;&nbsp; t&#8321; = 0.75 D
          <br><span style="font-size:10px;color:var(--muted)">NPTEL IIT KGP, Module 4 Lesson 2,
          Fig. 4.2.3.1</span></div>
          <h3>4. Iterate until every check passes</h3>
          <p style="margin-bottom:4px">Where a check fails, the responsible dimension is raised by
          1 mm and the whole set is re-evaluated. Both the dimension raised and the check that
          caused it are reported.</p>
          <div class="note ok"><b>Design factor {F['design_factor']}.</b> The joint is sized for
          {F['design_factor']} times the stated load, then every stress is reported at the actual
          load. The governing check lands near 75 to 80 percent of allowable instead of 100, so
          margin is retained for material variation and overload.</div>
        </div>
      </div>"""))

    rows = "".join(
        f"<tr><td>{j['title']}</td><td class='n'>{j['parts']}</td><td class='n'>{j['dims']}</td>"
        f"<td class='n'>{j['checks']}</td><td>{j['duty']}</td>"
        f"<td class='n'>{round(j['worst']*100)}%</td>"
        f"<td><div class='bar {'hi' if j['worst']>=0.8 else ''}'>"
        f"<span style='width:{round(j['worst']*100)}%'></span></div></td></tr>"
        for j in F["joints"])
    S.append(slide(f"""
      <div class="tag">Scope</div>
      <h2>Six joints, {nchecks} failure checks in total</h2>
      <table class="sm">
        <tr><th>Joint</th><th class="n">Parts</th><th class="n">Dimensions</th>
            <th class="n">Checks</th><th>Duty used here</th><th class="n">Busiest</th>
            <th>Utilisation of allowable</th></tr>
        {rows}
      </table>
      <div class="note" style="margin-top:10px"><b>Reading the last column.</b> Every joint passes
      every check, and the busiest check sits between 67 and 79 percent of allowable. That spread
      is the design factor working: sizing exactly to the allowable would leave a design that
      passes on paper with nothing in reserve.</div>
      <div class="note bad" style="margin-top:8px"><b>The gib and cotter joint needed a decision.</b>
      Unwin gives the breadth split and the thickness but no strap proportions. Rather than borrow
      a ratio or invent one, every dimension the source does not give is sized against a failure
      check until it passes. No dimension of that joint is unsupported.</div>"""))

    dims = "".join(f"<tr><td class='mono'>{a}</td><td>{b}</td><td class='n'>{c:g}</td>"
                   f"<td style='font-size:9.6px'>{(d or '-')[:74]}</td></tr>"
                   for a, b, c, d in k["dims"][:8])
    S.append(slide(f"""
      <div class="tag">Worked example &middot; 1 of 3</div>
      <h2>Knuckle joint for 50 kN: which formula governs</h2>
      <div class="row r2">
        <div class="stack">
          <table><tr><th>Computed before rounding</th><th class="n">mm</th><th>Effect</th></tr>
            <tr><td>Rod in direct tension</td><td class="n">{k['raw']['rod_tension']}</td>
                <td>rod adopted as <b>35</b></td></tr>
            <tr><td>Pin in double shear</td><td class="n">{k['raw']['pin_shear']}</td>
                <td>not governing</td></tr>
            <tr><td>Pin in bending</td><td class="n">{k['raw']['pin_bending']}</td>
                <td>governs, pin adopted as <b>45</b></td></tr>
          </table>
          <div class="note"><b>The point of this slide.</b> The bending requirement is nearly
          <b>1.7 times</b> the shear requirement. A pin sized from shear alone would satisfy its
          own check and bend in service. The source material takes the same step.</div>
          <p style="font-size:11.6px;color:var(--muted)">Allowable stresses used: 75 MPa tension,
          60 MPa shear, 150 MPa crushing. Sized for 62,500 N, reported at 50,000 N.</p>
        </div>
        <div>
          <table class="sm"><tr><th>Symbol</th><th>Meaning</th><th class="n">mm</th>
            <th>Rule and source</th></tr>{dims}</table>
        </div>
      </div>"""))

    checks = "".join(
        f"<tr><td>{n}</td><td class='mono'>{f}</td><td class='n'>{s:g}</td>"
        f"<td class='n'>{a:g}</td><td class='n'>{round(100*s/a)}%</td>"
        f"<td><div class='bar {'hi' if s/a>=0.8 else ''}'>"
        f"<span style='width:{round(100*s/a)}%'></span></div></td></tr>"
        for n, f, s, a, _ in k["checks"])
    S.append(slide(f"""
      <div class="tag">Worked example &middot; 2 of 3</div>
      <h2>All nine failure modes, evaluated at the actual load</h2>
      <table class="sm">
        <tr><th>Failure mode</th><th>Expression</th><th class="n">Stress MPa</th>
            <th class="n">Allowable</th><th class="n">Used</th><th>Utilisation</th></tr>
        {checks}
      </table>
      <div class="row r2" style="flex:none;margin-top:9px">
        <div class="note ok"><b>Every check satisfied.</b> The busiest is shear of the eye at
        76 percent of its allowable stress.</div>
        <div class="note"><b>Nothing here is stored.</b> These are computed for this request. At
        80 kN every value in the table changes, and the pin would be re-sized.</div>
      </div>"""))

    S.append(slide(f"""
      <div class="tag">Worked example &middot; 3 of 3</div>
      <h2>The working is printed, so the output can be checked rather than trusted</h2>
      <div class="row r25">
        <div class="stack">
          <p>Each run prints the values computed before rounding, the size adopted, the rule and
          source behind every proportion, every check with its arithmetic substituted, and the
          volume and mass of each solid produced.</p>
          <div class="note"><b>Why this matters for a review.</b> A reviewer does not have to
          accept the result. Each line can be recomputed by hand from the formula shown beside
          it.</div>
          <p style="font-size:11.6px;color:var(--muted)">This is also what made the errors in the
          published sources visible, on the following slides.</p>
        </div>
        <div class="fill"><img src="{im('03-working-log')}" alt="working">
          <div class="cap">Working printed for a single run of the example above.</div></div>
      </div>"""))

    S.append(slide(f"""
      <div class="tag">Output &middot; geometry</div>
      <h2>Exact solids, assembled, exploded, and coloured by utilisation</h2>
      <div class="row r52">
        <div class="fill"><img src="{im('04-model')}" alt="3D model">
          <div class="cap">Assembled model, rotatable in the browser.</div></div>
        <div class="stack">
          <table class="sm"><tr><th>File</th><th>Use</th></tr>
            <tr><td class="mono">parts/*.step</td><td>each component separately</td></tr>
            <tr><td class="mono">assembly.step</td><td>all parts in position</td></tr>
            <tr><td class="mono">drawing.svg</td><td>A3 first angle sheet</td></tr>
            <tr><td class="mono">drawing.dxf</td><td>same views for AutoCAD</td></tr>
            <tr><td class="mono">*.FCStd</td><td>editable FreeCAD file</td></tr>
            <tr><td class="mono">report.md</td><td>dimensions, rules and checks</td></tr>
          </table>
          <div class="note"><b>STEP is a neutral format.</b> The same file opens in Siemens NX,
          SolidWorks, FreeCAD, Onshape and Fusion, so the output is not tied to this software.</div>
        </div>
      </div>"""))

    S.append(slide(f"""
      <div class="tag">Output &middot; drafting</div>
      <h2>First angle A3 sheet, generated without opening a CAD application</h2>
      <div class="fill"><img src="{im('05-drawing')}" alt="drawing sheet">
        <div class="cap">Front view, left side view, plan and isometric, with dimension lines and
        a title block carrying the load and the request. Produced by driving FreeCAD without its
        graphical interface, projecting the assembled geometry and composing the sheet.</div></div>"""))

    S.append(slide(f"""
      <div class="tag">Verification</div>
      <h2>Checked against published design literature</h2>
      <table class="sm">
        <tr><th>Joint</th><th>Source consulted</th><th>Outcome</th></tr>
        <tr><td>Knuckle joint</td><td>NPTEL IIT Kharagpur, Module 4 Lesson 2</td>
            <td>proportions and all nine checks verified</td></tr>
        <tr><td>Socket and spigot cotter</td><td>NPTEL M4 L2; Leutwiler (1917) Art. 98</td>
            <td>all ten checks verified against two independent books</td></tr>
        <tr><td>Gib and cotter</td><td>Unwin (1899), p. 179, Figs. 130 and 131</td>
            <td>breadth split, thickness and taper verified</td></tr>
        <tr><td>Flange coupling</td><td>NPTEL M4 L1 keys; Leutwiler Art. 275 bolts</td>
            <td>all seven checks verified twice; proportions cannot be</td></tr>
        <tr><td>Sleeve and cotter</td><td>four books searched, none covers it</td>
            <td>checks verified by correspondence; proportions not</td></tr>
        <tr><td>Hex bolt and nut</td><td>NPTEL Module 4 Lesson 4</td>
            <td>tightening relation verified; size table not</td></tr>
      </table>
      <div class="note" style="margin-top:9px"><b>Where a source does not exist, the software says
      so on every run.</b> Leutwiler records that no standard set of flange coupling proportions
      was ever agreed and that published tables are individual manufacturers' practice. Those
      proportions are therefore marked unverified rather than given a source they do not have.</div>"""))

    S.append(slide(f"""
      <div class="tag">Finding 1 of 3</div>
      <h2>A worked example that fails its own check</h2>
      <div class="row r2">
        <div class="stack">
          <p>The knuckle joint worked problem raises the pin from <b>40 mm to 55 mm</b> to satisfy
          bending. It then evaluates the eye using the <b>original 40 mm pin</b>.</p>
          <div class="eq">eye shear = P / ((d&#8322; &minus; d) t)<br>
          with d = 55: 100000 / ((80 &minus; 55) &times; 50) = <b>80 MPa</b><br>
          allowable = 65 MPa</div>
          <div class="note bad"><b>Its own expression, evaluated with the pin it actually adopted,
          exceeds its own allowable by 23 percent.</b></div>
          <p><b>What this software does instead:</b> it enlarges the outer diameter of the eye
          until the check passes, and reports that it has done so.</p>
        </div>
        <div class="fill"><img src="{im('07-checks')}" alt="checks">
          <div class="cap">Because every check is evaluated and its arithmetic printed, an
          inconsistency of this kind becomes visible immediately rather than being inherited.</div></div>
      </div>"""))

    S.append(slide(f"""
      <div class="tag">Findings 2 and 3 of 3</div>
      <h2>An omitted failure mode, and a constant printed wrongly</h2>
      <div class="row r2">
        <div class="stack">
          <h3>Omitted failure mode</h3>
          <p style="margin-bottom:4px">The cotter joint procedure verifies crushing of the socket
          but not crushing between the cotter and the spigot.</p>
          <div class="eq">P / (d&#8321; t) = 50000 / (30 &times; 10) = <b>167 MPa</b><br>
          allowable = 110 MPa</div>
          <div class="note bad" style="margin-top:-2px"><b>Leutwiler, Article 98, lists ten failure
          modes and includes this one.</b> Two independent texts, published eighteen years apart,
          contain a check the lesson omits. That is what makes it an omission rather than a
          preference. The software keeps the check and sizes the cotter thicker.</div>
        </div>
        <div class="stack">
          <h3>Constant printed wrongly</h3>
          <p style="margin-bottom:4px">The initial tightening load for a bolt is printed as
          284<i>d</i> kN. The worked example on the same page obtains 56.8 kN for an M20 bolt.</p>
          <div class="eq">284 &times; 20 = 5.68 kN &nbsp; &ne; &nbsp; 56.8 kN<br>
          2840 &times; 20 = 56,800 N &nbsp; = &nbsp; 56.8 kN &#10003;</div>
          <div class="note bad" style="margin-top:-2px"><b>The page refutes itself.</b> The constant
          is 2840<i>d</i> newtons, and the printed relation is out by a factor of ten. Every bolted
          design now reports the tightening load, because at M20 it is 56,800 N before any service
          load is applied.</div>
        </div>
      </div>"""))

    S.append(slide(f"""
      <div class="tag">Independent cross check</div>
      <h2>Finite element analysis, and knowing when not to believe it</h2>
      <div class="row r2">
        <div class="stack">
          <table class="sm"><tr><th>Case</th><th class="n">Formula</th><th class="n">Computed</th>
            <th class="n">Difference</th></tr>
            <tr><td>20 mm bar, 10 kN tension</td><td class="n">31.83</td><td class="n">32.22</td>
                <td class="n">+1.2 %</td></tr>
            <tr><td>Knuckle eye rod, 50 kN</td><td class="n">52.0</td><td class="n">57.9</td>
                <td class="n">+11.5 %</td></tr>
          </table>
          <p style="font-size:11.6px">The bar validates the method. The eye rod reads higher
          because the formula treats it as a plain bar and takes no account of the stress raised
          at the pin bore. Both remain below the 75 MPa allowable.</p>
        </div>
        <div class="stack">
          <div class="note bad"><b>A result that never settles is not a stress.</b> On one
          component the computed peak moved between <b>157 and 191 MPa</b> across a sixteen fold
          increase in nodes. That is a singularity at a sharp corner or a constrained face, not a
          value to design to.</div>
          <p style="font-size:11.6px;margin-bottom:4px">The software therefore re-solves on a mesh
          of half the element size whenever the peak exceeds 1.5 times the calculated value, and
          reports <span class="mono">NOT CONVERGED</span> if the peak then moves more than 5
          percent.</p>
          <div class="note"><b>Stated plainly in the report:</b> this is one linear static run on
          one component with boundary conditions the software chooses. It is a second opinion on
          the formula, not a substitute for a full analysis.</div>
        </div>
      </div>"""))

    S.append(slide(f"""
      <div class="tag">Correctness</div>
      <h2>{tests} automated tests, including tests that protect the findings</h2>
      <div class="row r52">
        <div class="stack">
          <table class="sm"><tr><th>What is tested</th><th>Why</th></tr>
            <tr><td>Sizing arithmetic</td><td>values match the worked problems in the sources</td></tr>
            <tr><td>Generated geometry</td><td>each part is one valid solid, no two parts overlap</td></tr>
            <tr><td>Request interpretation</td><td>parameters extracted correctly, invented numbers dropped</td></tr>
            <tr><td>Drawing sheet</td><td>sheet, DXF and FreeCAD file are produced</td></tr>
            <tr><td>Finite element path</td><td>face selection refers to dimensions that exist</td></tr>
            <tr><td>The three findings</td><td>assert the source errors are real</td></tr>
          </table>
        </div>
        <div class="stack">
          <div class="note ok"><b>The last row is the unusual one.</b> Tests assert that the
          published answers fail their own checks. Without them, someone could later "correct" the
          software back to the printed values and every other test would still pass.</div>
          <div class="note"><b>Overlap testing found a real error.</b> A gib hook was modelled
          1.25 mm inside the strap, occupying metal that another part already occupied. No
          dimension check would have caught it; only comparing the solids did.</div>
        </div>
      </div>"""))

    S.append(slide(f"""
      <div class="tag">Deployment</div>
      <h2>Runs in a browser, with nothing installed</h2>
      <div class="row r25">
        <div class="stack">
          <table class="sm"><tr><th>Component</th><th>Tool</th></tr>
            <tr><td>Solid modelling</td><td>CadQuery 2.8, OCCT kernel</td></tr>
            <tr><td>Drawing and DXF</td><td>FreeCAD, headless</td></tr>
            <tr><td>Finite element</td><td>CalculiX with gmsh</td></tr>
            <tr><td>Request reading</td><td>Claude, rules as fallback</td></tr>
            <tr><td>Application</td><td>Python standard library</td></tr>
            <tr><td>Hosting</td><td>container, free tier</td></tr>
          </table>
          <div class="note"><b>Measured requirement:</b> the CAD kernel alone needs 449 MB of
          memory and a full run peaks near 800 MB, which is what determined the hosting choice.</div>
        </div>
        <div class="fill"><img src="{im('09-files')}" alt="files produced">
          <div class="cap">Files produced by one run, downloadable directly from the browser.</div></div>
      </div>"""))

    S.append(slide(f"""
      <div class="tag">Limits</div>
      <h2>What this does not do, stated before anyone asks</h2>
      <div class="row r2">
        <div><ul>
          <li><b>Static loading only.</b> Fatigue, endurance limit and stress concentration factors
          are outside the scope.</li>
          <li><b>Nominal dimensions only.</b> Tolerances and fits are not applied, so the sheet is
          not yet a manufacturing drawing.</li>
          <li><b>Two joints have unverified proportions.</b> The sleeve and cotter joint and the
          flange coupling. The software reports this on every run.</li>
          <li><b>Nut thread stripping is not checked</b> for the bolted joint.</li>
          <li><b>The published site reads with pattern rules</b>, not the language model, because
          the server holds no API key.</li>
        </ul></div>
        <div class="fill"><img src="{im('08-weak-spots')}" alt="weak spots">
          <div class="cap">Components coloured by utilisation, so the member nearest its limit is
          visible without reading the table.</div></div>
      </div>"""))

    S.append(slide(f"""
      <div class="tag">Future scope</div>
      <h2>Where this goes next</h2>
      <div class="row r2">
        <div><ul>
          <li><b>Riveted and welded joints.</b> Treated in Module 10 of the same source and
          following the same pattern, so they need no change to the architecture.</li>
          <li><b>Fatigue loading.</b> An endurance limit and a stress concentration factor would
          extend the system to cyclically loaded joints.</li>
          <li><b>Tolerances and fits</b> for the pin and its bore, which would make the sheet
          directly usable for manufacture.</li>
        </ul></div>
        <div><ul>
          <li><b>Verification of the two remaining proportion sets</b> from a design data
          handbook.</li>
          <li><b>A journal script for Siemens NX</b>, so the assembly is constructed inside the
          software rather than imported into it.</li>
          <li><b>Bill of materials and cost</b>, extending the material selection that is already
          partly implemented.</li>
        </ul></div>
      </div>"""))

    S.append(slide(f"""
      <div style="display:flex;flex-direction:column;justify-content:center;flex:1">
        <div class="tag">Conclusion</div>
        <h2 style="font-size:34px;max-width:86%">Every dimension it produces can be traced to a
        formula, and every formula to a page in a book.</h2>
        <p class="lead" style="max-width:76%">The language model reads the request. The engineering
        stays deterministic, checked and open to inspection. That division is what allows a natural
        language interface without any part of the design becoming unverifiable.</p>
        <div class="row r3" style="flex:none;margin-top:16px">
          <div class="note ok"><b>6 joints, {nchecks} checks</b><br>every one verified against the
          allowable stress on every run</div>
          <div class="note"><b>3 errors found</b><br>in the published sources, protected by tests
          so they cannot be silently reverted</div>
          <div class="note"><b>{tests} tests</b><br>covering arithmetic, geometry, parsing,
          drafting and analysis</div>
        </div>
        <div style="margin-top:16px;font-size:14px"><b>{LIVE}</b></div>
      </div>""", " &middot; ".join(n for n, _ in TEAM)))

    return (f"<!doctype html><html><head><meta charset='utf-8'><title>{TITLE}</title>"
            f"<style>{CSS}</style></head><body>{''.join(S)}</body></html>")


if __name__ == "__main__":
    html = build()
    src = HERE / "AI-in-CAD-Slides.html"
    src.write_text(html)
    pdf = HERE / "AI-in-CAD-Slides.pdf"
    if pdf.exists():
        pdf.unlink()
    subprocess.run([BRAVE, "--headless", "--disable-gpu", "--no-sandbox",
                    f"--print-to-pdf={pdf}", "--no-pdf-header-footer",
                    "--virtual-time-budget=30000", f"file://{src}"],
                   capture_output=True, timeout=300)
    print(f"{pdf}  {pdf.stat().st_size // 1024} KB" if pdf.exists() else "not produced")
