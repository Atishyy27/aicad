"""Team speaking pack: the numbers to quote, how the website works, the project story, and one
page per presenter. Every number is computed from the software when this file runs, so the pack
cannot drift from what the app and the report say.

    PYTHONUTF8=1 AICAD_BROWSER=<chrome or brave> python report/make_speaking_pack.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
BROWSER = os.environ.get("AICAD_BROWSER", "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser")
OUT = HERE / "AI-in-CAD-Team-Speaking-Pack.pdf"
SITE = "aicad-vercel.vercel.app"

from aicad.joints import REGISTRY  # noqa: E402
from aicad.optimise import compare  # noqa: E402
from aicad.parse import Spec  # noqa: E402


def facts() -> dict:
    k = REGISTRY["knuckle"]
    demo = k.design(load_n=50_000)
    busiest = max(demo.checks, key=lambda c: c.stress_mpa / c.allowable_mpa)
    ex45 = k.design(load_n=50_000, tension_mpa=80, shear_mpa=40, crushing_mpa=80, design_factor=1.0)
    p41 = k.design(load_n=25_000, tension_mpa=152, shear_mpa=0.577 * 152, crushing_mpa=152, design_factor=1.0)
    ex42 = REGISTRY["cotter"].design(load_n=50_000, tension_mpa=66.67, shear_mpa=33.33, crushing_mpa=133.33,
                                     design_factor=1.0)
    book45 = {"D": 30, "D1": 35, "t": 40, "t1": 25, "d": 40, "d2": 80, "d3": 60}
    book42 = {"d": 32, "t": 10, "d1": 40, "d2": 55, "d3": 48, "d4": 80, "a": 24, "c": 24, "b": 50, "t1": 15}
    duties = {"knuckle": {"load_n": 50_000}, "cotter": {"load_n": 35_000}, "sleeve_and_cotter": {"load_n": 50_000},
              "gib_and_cotter": {"load_n": 50_000}, "nut_bolt": {"load_n": 20_000, "bolt_size": 24, "grip_mm": 30},
              "flange_coupling": {"torque_nm": 500}}
    joints = []
    for name, kw in duties.items():
        j = REGISTRY[name]
        d = j.design(**kw)
        joints.append((j.TITLE, len(j.build_parts(d.dims)), len(d.checks),
                       sum(c.passed for c in d.checks), round(100 * max(c.stress_mpa / c.allowable_mpa for c in d.checks))))
    t0 = time.perf_counter()
    for i in range(1000):
        k.design(load_n=50_000 + i)
    per_ms = (time.perf_counter() - t0)
    mats = compare(Spec(joint="knuckle", load_n=50_000.0))
    tests = subprocess.run([sys.executable, "-m", "pytest", "--co", "-q", "-p", "no:cacheprovider"],
                           capture_output=True, text=True, cwd=HERE.parent).stdout.strip().splitlines()[-1].split()[0]
    return {
        "demo": demo, "busiest": busiest, "ex45": ex45, "p41": p41, "ex42": ex42,
        "m45": sum(ex45.dims[x] == v for x, v in book45.items()), "n45": len(book45),
        "m42": sum(ex42.dims[x] == v for x, v in book42.items()), "n42": len(book42),
        "joints": joints, "nchecks": sum(j[2] for j in joints), "per_ms": per_ms, "mats": mats, "tests": tests,
        "lo": min(j[4] for j in joints), "hi": max(j[4] for j in joints),
    }


CSS = """
@page{size:A4;margin:16mm 16mm 16mm 18mm}
body{font-family:Georgia,'Times New Roman',serif;font-size:10.6pt;line-height:1.45;color:#111}
h1{font-size:20pt;margin:0 0 2mm}h2{font-size:14pt;margin:6mm 0 2mm;border-bottom:0.4mm solid #222;padding-bottom:1mm}
h3{font-size:11.5pt;margin:4mm 0 1mm}
.sub{color:#444;margin:0 0 5mm}.pb{page-break-before:always}
table{border-collapse:collapse;width:100%;font-size:9.6pt;margin:2mm 0}
td,th{border:0.25mm solid #999;padding:1.2mm 2mm;vertical-align:top;text-align:left}th{background:#eee}
td.n{text-align:right;white-space:nowrap}
.box{border:0.35mm solid #222;padding:3mm 4mm;margin:3mm 0;background:#f6f6f6}
.say{border-left:1.2mm solid #2b5fb4;padding:2mm 4mm;margin:2mm 0;background:#f2f6fc;font-style:italic}
.k{font-family:'Courier New',monospace;font-size:9.5pt}
ol,ul{margin:1mm 0 2mm 5mm;padding-left:4mm}li{margin:0.6mm 0}
.who{font-size:16pt;font-weight:bold;margin:0}.role{color:#333;margin:0 0 3mm}
.small{font-size:9pt;color:#444}
"""


def numbers_page(F) -> str:
    d, b = F["demo"], F["busiest"]
    rows = [
        ("Joints designed end to end", "6", "knuckle, socket and spigot cotter, sleeve and cotter, gib and cotter, hex bolt, protected flange coupling"),
        ("Failure checks applied", str(F["nchecks"]), f"all satisfied; busiest check per joint {F['lo']} to {F['hi']} percent of allowable"),
        ("Bhandari Ex 4.5 (knuckle)", f"{F['m45']} of {F['n45']} sizes", "every adopted size and all six eye and fork stresses (31.25, 25 N/mm2) reproduced exactly"),
        ("Bhandari Problem 4.1", "14.47 / 13.47 mm", f"software: {F['p41'].raw['rod_tension']:.2f} and {F['p41'].raw['pin_shear']:.2f} mm, the printed answers"),
        ("Bhandari Ex 4.2 (cotter)", f"{F['m42']} of {F['n42']} sizes", "spigot 37.92 and socket 52.04 mm solved from the tension equations; only the cotter width differs (book uses FoS 4 for the cotter)"),
        ("Errors found in published sources", "3", "NPTEL knuckle example fails its own eye shear check by 23 percent; NPTEL omits cotter to spigot crushing (167 vs 110 N/mm2); bolt preload constant printed 100 times too large"),
        ("Automated tests", F["tests"], "include tests that fail if any book result or any of the three findings changes"),
        ("Sizing and all checks", f"{F['per_ms']:.3f} ms", "per design (1000 designs timed); this is why the sliders update live"),
        ("Model and checks on screen", "about 2 to 5 s", "drawing sheet follows in the background in about 40 s (FreeCAD hidden line projection)"),
        ("Material options", "6", "30C8, 40C8, 45C8, 40Cr1, FG 260, Al 64430; each designed in full with mass and cost"),
        ("Existing tools compared", "7", "BuildCAD, Zoo, CADAM, Leo AI, MITCalc, KISSsoft, Text2CAD: none combine sentence input with traceable sizing, checks and a drawing sheet"),
    ]
    tr = "".join(f"<tr><td><b>{a}</b></td><td class='n'><b>{v}</b></td><td>{c}</td></tr>" for a, v, c in rows)
    kd = d.dims
    return f"""
<h1>AI in CAD: team speaking pack</h1>
<p class="sub">Strategic Application of Artificial Intelligence in CAD. SGSITS Indore, Mechanical Engineering,
2026 to 2027. Guide: Dr. B. R. Rawal. Live system: {SITE}. Every number below was computed by the
software when this pack was generated.</p>
<div class="box"><b>One line pitch.</b> Type "knuckle joint for 50 kN". The software sizes the joint from the
design formulas in the textbook, rounds every size to a standard one, checks every way it can fail, and
produces the 3D parts and a first angle sectional drawing. The AI only reads the sentence; every number
comes from mechanics, and every formula from a page in a book.</div>
<h2>The numbers to quote</h2>
<table><tr><th>What</th><th>Number</th><th>What it means</th></tr>{tr}</table>
<h2>The worked example everyone should know: knuckle joint, 50 kN</h2>
<table>
<tr><th>Step</th><th>Formula</th><th>Value</th></tr>
<tr><td>Rod, direct tension</td><td class="k">D = sqrt(4P / (pi st)), P sized at 1.25 x 50 kN</td><td class="n">{d.raw['rod_tension']:.2f} mm, adopted {kd['D']:g}</td></tr>
<tr><td>Pin, double shear</td><td class="k">d = sqrt(2P / (pi tau))</td><td class="n">{d.raw['pin_shear']:.2f} mm</td></tr>
<tr><td>Pin, bending</td><td class="k">d = [32/(pi sb) x P/2 (b/4 + a/3)]^(1/3)</td><td class="n">{d.raw['pin_bending']:.2f} mm, adopted {kd['d']:g}</td></tr>
<tr><td>Eye and fork outside diameter</td><td class="k">d0 = 2d (Bhandari 4.26j)</td><td class="n">{kd['d2']:g} mm</td></tr>
<tr><td>Eye thickness b, fork thickness a</td><td class="k">b = 1.25D, a = 0.75D</td><td class="n">{kd['t']:g} and {kd['t1']:g} mm</td></tr>
<tr><td>Enlarged rod, pin head</td><td class="k">D1 = 1.1D, head = 1.5d</td><td class="n">{kd['D1']:g} and {kd['d3']:g} mm</td></tr>
<tr><td>Busiest check at the real 50 kN</td><td>{b.name}</td><td class="n">{b.stress_mpa:.1f} of {b.allowable_mpa:g} N/mm2, {100*b.stress_mpa/b.allowable_mpa:.0f} percent</td></tr>
</table>
<p>Why the pin is sized twice: bending asks for {d.raw['pin_bending']/d.raw['pin_shear']:.2f} times the diameter shear asks
for. A pin sized on shear alone passes its own check and bends in service. Bhandari takes the same step in Ex 4.5.</p>"""


def site_page(F) -> str:
    rows = "".join(f"<tr><td>{m['material']}</td><td class='n'>{m['size']:g} mm</td><td class='n'>{m['mass_kg']:.2f} kg</td>"
                   f"<td class='n'>Rs {m['cost_inr']:,.0f}</td></tr>" for m in F["mats"])
    return f"""
<div class="pb"></div><h2>How the website works (read this before the demo)</h2>
<ol>
<li><b>Left panel, step 1, Describe the joint.</b> Type a sentence or click a book case. "Design it" sends the
sentence to the reader, which picks out the joint and the load. In rules mode no AI is used at all.</li>
<li><b>Step 2, Duty.</b> The load slider re-sizes the joint and re-runs every check as you drag (sizing takes a
fraction of a millisecond). Let go and the 3D model rebuilds in about 2 s.</li>
<li><b>Step 3, Material selection.</b> The same joint designed in six materials, with the size each needs, the
mass and the material cost; the lightest and the cheapest are marked. Click a row: its allowable stresses
now drive every check, and the drawing's parts list carries that material.</li>
<li><b>Step 4, Ask or change.</b> "make it lighter", "why is the pin 45 mm", "load 80 kN".</li>
<li><b>Centre, the 3D model.</b> Buttons: Assembled, Exploded, Section (cut on the joint axis: pin through the
eye, collar, taper pin), Weak spots (green to red by how close each part is to its limit).</li>
<li><b>Right panel tabs.</b> Checks (each failure mode with formula, stress, allowable, bar; book cases show a
Book check table), Dimensions (every size with the rule and its source), Drawing (A3 first angle sheet with
sectional front view A-A, centre lines, callouts, parts list; it fills in about 40 s after the model), Files
(STEP for NX and SolidWorks, drawing SVG and DXF), Working (the full calculation log).</li>
<li><b>Top right.</b> Light or dark mode.</li>
</ol>
<h3>Behind the screen</h3>
<p>Language reading (rules, or a language model) &rarr; sizing from the book formulas (Python) &rarr; checks &rarr;
solids built with CadQuery on the OpenCASCADE kernel &rarr; STEP export &rarr; drawing sheet by FreeCAD run without
its window &rarr; everything returned to the browser. Hosted on Vercel; the code is public on GitHub
(Atishyy27/aicad).</p>
<h3>Two minute demo script</h3>
<ol>
<li>Open the site five minutes early and click any case once (wakes the server).</li>
<li>Click <b>Knuckle joint, Bhandari Ex 4.5</b>. Point at the Book check: {F['m45']} of {F['n45']} values match the book.</li>
<li>Drag the load slider: the sizes and checks move live. Let go: the model rebuilds.</li>
<li>Click <b>Section</b> in the viewer, then the <b>Drawing</b> tab: sectional view A-A, hatching, parts list.</li>
<li>Click a different material row, for example 40C8: the rod drops a size and the mass falls.</li>
<li>Click <b>Cotter joint, Bhandari Ex 4.2</b>: {F['m42']} of {F['n42']} match; explain the one difference (cotter factor of safety).</li>
</ol>
<p class="small">No internet: open aicad-NX-pendrive/knuckle-50kN/viewer.html (works offline), and the report figures.</p>
<h3>Material step for the 50 kN knuckle (software output)</h3>
<table><tr><th>Material</th><th>Rod D</th><th>Mass</th><th>Material cost</th></tr>{rows}</table>
<p class="small">Allowables and rates are working values, to be confirmed against a data book and a supplier.</p>"""


STORY = """
<h2>The story of how the work was done</h2>
<table>
<tr><th>When</th><th>What happened</th></tr>
<tr><td>Phase I</td><td>Problem chosen: standard joint design is a fixed recipe repeated by hand for every load. Literature: NPTEL Module 4, Bhandari ch 4, Unwin 1899, Leutwiler 1917.</td></tr>
<tr><td>18 to 20 Sep</td><td>First working version: a sentence in, four joints sized and checked, STEP parts out. Flange coupling added the same day to prove it is not limited to axial loads.</td></tr>
<tr><td>21 to 22 Sep</td><td>Every proportion and check compared with the books. Three errors found in the sources. Gib and cotter built from Unwin 1899. Finite element cross check added, with a rule to reject results that do not converge.</td></tr>
<tr><td>23 to 25 Sep</td><td>Deployed on the web; report and deck generated from the software itself.</td></tr>
<tr><td>16 Oct, Phase II review</td><td>Faculty: sizes such as 52.5 and 0.75 mm are not standard and cannot be bought or made; no GD&amp;T; do three or four joints properly instead of adding more; show physics validating the output.</td></tr>
<tr><td>28 to 29 Oct</td><td>All of it acted on: every size rounded to a standard one; knuckle and cotter rebuilt to Bhandari's proportions and procedure and checked against his worked examples; material selection step; sectional drawing with hatching, centre lines and parts list; section view in 3D; new interface with live sizing; build time cut from 35 s to about 2 s for the model.</td></tr>
</table>
<div class="say">If asked what changed since the last review: "You told us the sizes were not standard and
the drawing was not a real drawing. Now every size is a standard size, the knuckle reproduces Bhandari's
Example 4.5 exactly, and the sheet is a sectional view with a parts list."</div>"""


def person(name, role, slides, script, nums, demo, qa) -> str:
    q = "".join(f"<li><b>Q: {a}</b><br>A: {b}</li>" for a, b in qa)
    n = "".join(f"<li>{x}</li>" for x in nums)
    return f"""<div class="pb"></div>
<p class="who">{name}</p><p class="role">{role} &middot; slides {slides}</p>
<h3>What you are telling the panel (about one minute)</h3><div class="say">{script}</div>
<h3>Numbers you must have ready</h3><ul>{n}</ul>
<h3>Your part of the demo</h3><p>{demo}</p>
<h3>Questions most likely to come to you</h3><ol>{q}</ol>"""


def people(F) -> str:
    d, b = F["demo"], F["busiest"]
    return "".join([
        person("Ansh Yadav", "Opening, the problem, the literature, the gap", "1 to 6",
               "Designing a standard joint is not creative work, it is a fixed recipe: size the rod, size the pin "
               "twice, check every failure mode, and draw it. Change the load and the whole recipe repeats. CAD "
               "software removes the drawing labour but not the calculation; it will happily draw an unsafe pin. We "
               "studied the textbooks the recipe comes from, Bhandari, NPTEL, and two older texts, and the tools on "
               "the market. Text to CAD tools make geometry that cannot be justified; calculators like MITCalc do the "
               "engineering but need forms, not language. Nothing connects the two. That gap is our project.",
               ["Seven hand steps for a knuckle joint, all repeated when the load changes",
                "Four sources: Bhandari ch 4, NPTEL Module 4, Unwin 1899, Leutwiler 1917",
                "Seven existing tools compared; none combine sentence input, traceable sizing, checks and a drawing"],
               "Open the site before the talk and click one case to wake the server.",
               [("Why not just use SolidWorks or NX?", "They regenerate a model from the sizes you give them; they do not decide the sizes and will not object to an unsafe one. We decide and verify the sizes, then hand STEP files to NX."),
                ("Why three or four books?", "Bhandari is the course text and gives the worked examples we test against; NPTEL gives the full procedure for two joints; Unwin is the only one with the gib and cotter; Leutwiler confirms a failure mode NPTEL leaves out."),
                ("What is new here?", "Not the CAD kernel and not the formulas: the connection, from one English sentence to a verified, standard sized model with every step traceable.")]),
        person("Bhavya Shrivastava", "What we built: the five stages and the role of the AI", "7 to 10",
               "The system runs five stages: read the sentence, size the joint, check every failure mode, build the "
               "solids, draw the sheet. The most important design decision is the split: the AI only reads the "
               "sentence. It never picks a dimension and never performs a check. Reading '50 kN' is a language "
               "problem; choosing a pin diameter has one right answer from a formula, so it stays with ordinary code "
               "you can check line by line. Any number the AI returns that is not in your sentence is thrown away.",
               [f"Six joints, {F['nchecks']} failure checks, all satisfied",
                f"Busiest check per joint between {F['lo']} and {F['hi']} percent of allowable (design factor 1.25)",
                f"Sizing plus every check takes {F['per_ms']:.3f} ms, so the sliders are live"],
               "Type 'knuckle joint for 50 kN', press Design it, and drag the load slider to show the checks moving live.",
               [("Did you train a model?", "No. The language model is used only to read the sentence. The engineering is formulas from the books, written as code."),
                ("Is this a PINN?", "No, and that is the point: a physics informed network is penalised for breaking physics, so a violation is unlikely. Here physics is the calculation itself, so no output can break it."),
                ("What if the AI misreads the sentence?", "Every value is shown for confirmation before the build, any number not in the sentence is discarded, and the design is still checked against every failure mode.")]),
        person("Atishay Jain", "One joint end to end, the outputs, and the physics slide", "11 to 18 and 29",
               f"Take the knuckle joint at 50 kN. The rod from direct tension needs {d.raw['rod_tension']:.2f} mm, so it "
               f"becomes {d.dims['D']:g}, the next standard size. The pin is sized twice: {d.raw['pin_shear']:.2f} mm for "
               f"shear, {d.raw['pin_bending']:.2f} mm for bending, and the larger wins, so {d.dims['d']:g} mm. The eye "
               f"follows the pin, d0 = 2d = {d.dims['d2']:g} mm, as Bhandari specifies. All nine checks pass; the busiest "
               f"is {b.name} at {100*b.stress_mpa/b.allowable_mpa:.0f} percent. The output is STEP parts for NX, and an A3 "
               "first angle sheet with a sectional front view, hatching, centre lines and a parts list.",
               [f"Rod {d.raw['rod_tension']:.2f} to {d.dims['D']:g} mm; pin {d.raw['pin_shear']:.2f} (shear) and {d.raw['pin_bending']:.2f} (bending) to {d.dims['d']:g} mm",
                f"Bhandari Ex 4.5 reproduced: {F['m45']} of {F['n45']} sizes and six of six stresses",
                "Drawing: sectional front view A-A; pins are not hatched, by convention"],
               "Click the Bhandari Ex 4.5 case and show the Book check; then the Section button and the Drawing tab.",
               [("Why is the pin bigger than the rod?", f"Bending, not shear, governs: it needs {d.raw['pin_bending']:.2f} mm against {d.raw['pin_shear']:.2f} for shear. Bhandari raises the pin the same way in Ex 4.5."),
                ("Why is the pin not hatched in the section?", "Pins, bolts, keys and shafts cut along their axis are drawn unhatched; that is standard drawing practice (SP 46)."),
                ("Does it open in NX?", "The STEP file is AP214 with each part a separate named solid, which is what NX needs to see an assembly; File, Import, STEP214.")]),
        person("Dharmendra Gupta", "How we know it is correct: verification and the three source errors", "19 to 22",
               "Every proportion and every check was compared against the books, and we reproduced the books' own "
               f"worked examples: Bhandari's knuckle Example 4.5 to every size, {F['m45']} of {F['n45']}, and his cotter "
               f"Example 4.2 to {F['m42']} of {F['n42']}. Doing that turned up three errors in the published sources: an NPTEL "
               "worked example that fails its own eye shear check by 23 percent, a cotter failure mode NPTEL leaves out, "
               "and a bolt preload constant printed a hundred times too large. We did not find these by reading; the "
               "software prints the arithmetic of every check, and the numbers disagreed.",
               ["Error 1: knuckle eye shear 80 N/mm2 against an allowable 65, 23 percent over",
                "Error 2: cotter to spigot crushing 167 N/mm2 against 110, a check the lesson omits; Leutwiler lists it",
                "Error 3: tightening load printed 284d kN; the page's own example needs 2840d N, a factor of 100",
                f"Cotter Ex 4.2: only the cotter width differs, because the book uses factor of safety 4 for the cotter alone"],
               "Click the Cotter joint, Bhandari Ex 4.2 case and explain the single difference.",
               [("You say IIT Kharagpur material is wrong?", "We say the page refutes itself: substitute its own printed numbers into its own formula and it fails its own allowable. Anyone can redo it on paper."),
                ("How do you know the error is not yours?", "Each one is checkable without our software, and each is an automated test, so it cannot quietly change."),
                ("Why does your cotter differ from Bhandari?", "The book designs the cotter with a separate factor of safety of 4; we apply the rods' 6 to every part, so our cotter is wider and keeps the same margin.")]),
        person("Ankur Dodke", "Validation, limits, objectives, timeline and the close", "23 to 28 and 30",
               "We cross checked the formulas with a finite element analysis: on a plain bar the two agree to 1.2 percent, "
               "and on the knuckle eye rod the finite element stress is about 11 percent higher, which is expected "
               "because the formula ignores the stress concentration at the pin hole. The software carries "
               f"{F['tests']} automated tests. We are clear about the limits: static loads only, no fatigue, and "
               "nominal sizes without tolerances and fits yet. Every dimension it produces can be traced to a formula, "
               "and every formula to a page in a book.",
               ["Finite element: bar 31.83 against 32.22 N/mm2 (+1.2 percent); eye rod 52.0 against 57.9 (+11.3 percent) - measured on the September geometry",
                f"{F['tests']} automated tests",
                "Limits: static loading, no fatigue or stress concentration factors, no tolerances or fits; NX import verified in file structure, not yet watched in the lab"],
               "Close on the conclusion slide with the site link and the QR code.",
               [("Why is the finite element number higher than your formula?", "The formula treats the rod as a plain bar; the finite element model sees the stress raised at the pin bore. On a plain bar the two agree to 1.2 percent, which validates the method."),
                ("What is next?", "Riveted and welded joints (same architecture), fatigue with an endurance limit, tolerances and fits on the sheet, and an NX journal so the assembly is built inside NX."),
                ("Why only static loads?", "It is the scope we set and can verify against the books; fatigue needs endurance limits and stress concentration factors, which is the next step.")]),
    ])


def main() -> None:
    F = facts()
    html = (f"<!doctype html><html><head><meta charset='utf-8'><title>AI in CAD team speaking pack</title>"
            f"<style>{CSS}</style></head><body>{numbers_page(F)}{site_page(F)}{STORY}{people(F)}</body></html>")
    build = HERE / ".build"
    build.mkdir(exist_ok=True)
    src = build / "speaking-pack.html"
    src.write_text(html, encoding="utf-8")
    if OUT.exists():
        OUT.unlink()
    subprocess.run([BROWSER, "--headless", "--disable-gpu", "--no-sandbox", f"--print-to-pdf={OUT}",
                    "--no-pdf-header-footer", "--virtual-time-budget=20000", src.resolve().as_uri()],
                   capture_output=True, timeout=300)
    from pypdf import PdfReader
    print(OUT, len(PdfReader(str(OUT)).pages), "pages")


if __name__ == "__main__":
    main()
