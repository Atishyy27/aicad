"""Learner's guide: one overview page, then one page per presenter. Each page has the core
concepts in plain prose, how they show up in aicad, and the viva questions to expect.
Every project number comes from facts() in make_speaking_pack.py, so the guide cannot drift.

    PYTHONUTF8=1 AICAD_BROWSER=<chrome or brave> python report/make_learners_guide.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from make_speaking_pack import BROWSER, CSS, facts  # noqa: E402

OUT = HERE / "AI-in-CAD-Learners-Guide.pdf"


def qa(pairs) -> str:
    return "<h3>Viva questions</h3><ol>" + "".join(
        f"<li><b>{q}</b><br>{a}</li>" for q, a in pairs) + "</ol>"


def page(who, role, concepts, project, pairs) -> str:
    return (f"<div class='pb'><p class='who'>{who}</p><p class='role'>{role}</p>"
            f"<h3>Core concepts</h3>{concepts}"
            f"<h3>How it shows up in our project</h3><div class='say'>{project}</div>{qa(pairs)}</div>")


def body(F) -> str:
    d, b = F["demo"].dims, F["busiest"]
    use = round(100 * b.stress_mpa / b.allowable_mpa)
    overview = f"""
<h1>AI in CAD: Learner's Guide</h1>
<p class='sub'>Strategic Application of Artificial Intelligence in CAD · SGSITS Mechanical, B.Tech 2026-27 ·
Supervisor Dr. B. R. Rawal · one overview page, then one page per presenter</p>
<div class='box'><b>The project in one line.</b> You type "knuckle joint for 50 kN" and get back a joint that is
sized from design-book formulas, checked against every failure mode, modelled in 3D, drawn on a first-angle A3
sheet and exported as STEP and DXF. AI only reads the sentence. All the engineering is plain, traceable code.</div>
<h2>The pipeline</h2>
<ol>
<li><b>Read.</b> A language model pulls out the joint type and the load, nothing else.</li>
<li><b>Guard.</b> Any number the AI gives that isn't in the sentence is dropped and logged.</li>
<li><b>Size.</b> The governing formula gives one size, rounded up to a standard size.</li>
<li><b>Derive.</b> The other sizes follow from book proportions, each one tagged with its book and equation.</li>
<li><b>Check.</b> Every failure mode (tension, shear, bending, crushing) at the real load. If one fails, the
responsible size grows 1 mm and everything is re-checked.</li>
<li><b>Model and draw.</b> CadQuery builds exact solids. FreeCAD, headless, draws the sheet.</li>
<li><b>Cross-check.</b> gmsh plus CalculiX solve one part by FEA, as an independent check.</li>
</ol>
<h2>Numbers to quote</h2>
<table>
<tr><th>What</th><th>Value</th></tr>
<tr><td>Joints designed end to end</td><td>6</td></tr>
<tr><td>Failure checks, all satisfied</td><td>{F['nchecks']}; busiest per joint {F['lo']} to {F['hi']}%</td></tr>
<tr><td>Knuckle at 50 kN: governing check</td><td>{b.name}, {b.stress_mpa:.1f} of {b.allowable_mpa:g} MPa ({use}%)</td></tr>
<tr><td>Knuckle sizes</td><td>rod D {d['D']:g}, pin d {d['d']:g}, eye d2 {d['d2']:g}, head d3 {d['d3']:g}, t {d['t']:g}, t1 {d['t1']:g} mm</td></tr>
<tr><td>Bhandari Ex 4.5 (knuckle)</td><td>{F['m45']} of {F['n45']} sizes reproduced exactly</td></tr>
<tr><td>Bhandari Ex 4.2 (cotter)</td><td>{F['m42']} of {F['n42']} sizes (book uses FoS 4 for the cotter width)</td></tr>
<tr><td>Design factor</td><td>size at 1.25 times the load, check at the real load</td></tr>
<tr><td>Speed</td><td>about {F['per_ms']:.2f} ms per full knuckle design</td></tr>
<tr><td>Automated tests</td><td>{F['tests']}</td></tr>
<tr><td>Errors found in sources</td><td>3: NPTEL knuckle example fails its own eye-shear check by 23%; cotter spigot
crushing check omitted; bolt preload printed 284d kN, should be 2840d N</td></tr>
</table>
<p class='small'>Who presents what: Atishay = AI · Bhavya = AI in mechanical engineering · Ansh = machine design ·
Dharmendra = drawing and standards · Ankur = FEA and CAD geometry.</p>
"""

    atishay = page("Atishay Jain", "AI: language models, and why sizing is not ML", """
<p>A <b>large language model (LLM)</b> is a neural network trained to predict the next <b>token</b>, which is a
word piece (about 3-4 characters of English). It is very good at understanding messy language. It is not reliable
at arithmetic, because it produces the most likely text and doesn't actually compute anything.</p>
<p><b>Hallucination</b> is when the model states something fluent and wrong, e.g. a load nobody gave it. In
engineering that is dangerous: a wrong number becomes a wrong part.</p>
<p><b>Rules vs LLM parsing.</b> Rules (regex) are exact but brittle: "50 kilonewtons" or "5 tonne" can slip
through. An LLM handles any phrasing but might invent things. We use both: regex first, then the LLM, and every
LLM number is verified against the original text.</p>
<p><b>Why sizing is not ML.</b> Machine learning learns patterns from data and gives no reason for its output.
A joint's size must have a reason (formula, book, page) and must be exactly right at every load. Design formulas
already exist, so learning them from data would be less accurate and harder to explain.</p>
<p><b>Text-to-CAD landscape.</b> Commercial tools such as Zoo's Text-to-CAD and research models generate shapes
straight from text. They produce geometry that looks right, but nothing proves it carries the load. Ours goes
the other way: engineering first, then geometry.</p>""",
        """In <span class='k'>aicad/parse.py</span>, the function <span class='k'>_traceable(value, text)</span> checks
that every number the AI returns appears in the user's sentence, allowing unit factors (x1000 for kN, g for
tonne). If not, it is dropped with the note \"AI gave ... which is not in the request; dropped\". So the AI
cannot inject a load. Sizes, checks and geometry never touch the AI.""",
        [("Is this a trained model?", "No. It is a rules engine from design books. AI only reads the request."),
         ("What stops the AI hallucinating a number?", "_traceable: any number not in the sentence is dropped and logged."),
         ("Why not train a model to size joints?", "Formulas already exist and are exact. ML would be approximate and unexplainable."),
         ("What is a token?", "A word piece the model reads and writes, roughly 3-4 characters."),
         ("What if there's no API key or internet?", "The regex parser still works for normal requests. The AI is a fallback for unusual phrasing."),
         ("How is this different from text-to-CAD tools?", "They generate shape. We generate a checked design, then the shape.")])

    bhavya = page("Bhavya Shrivastava", "AI in mechanical engineering", """
<p><b>Physics-informed neural networks (PINN).</b> A normal network minimises the <i>data loss</i> (error against
measurements). A PINN adds a <i>physics residual</i>, which is how far the output is from satisfying the governing
equation (e.g. equilibrium). Loss = data loss + lambda x physics residual. Physics here is a <b>soft
constraint</b>: penalised, but it can still be violated.</p>
<p><b>Surrogate models</b> are fast approximations (neural nets, Gaussian processes) trained on expensive
simulations, so a design can be evaluated in milliseconds instead of hours. They are used in optimisation loops.</p>
<p><b>Generative design and topology optimisation</b> remove material where stress is low, which gives organic,
light shapes (Fusion 360 generative design, SIMP method). The result must still be validated and made
manufacturable.</p>
<p><b>Digital twins</b> are a live virtual copy of a real machine, fed by sensors and used to predict wear and
failure.</p>""",
        """aicad treats physics as a <b>hard constraint</b>: a design is only returned if every failure check passes.
Nothing is penalised and traded off. That's the right choice for a few standard joints with known formulas. A PINN
or a surrogate earns its place when there is no closed-form formula, e.g. a complex casting. So the honest pitch:
we used AI where it is strong (language) and exact physics where a mistake breaks a part.""",
        [("What is a PINN?", "A network trained on data loss plus a physics-equation residual, so physics is a soft constraint."),
         ("Soft vs hard constraint?", "Soft = penalised and can be violated. Hard = must hold. aicad uses hard checks."),
         ("Why didn't you use a PINN?", "The joint formulas are closed-form and exact. A PINN would only approximate them."),
         ("What is a surrogate model?", "A fast learned stand-in for an expensive simulation, used inside optimisation."),
         ("Topology optimisation in one line?", "Remove material where stress is low until the stiffness target is met."),
         ("Where would AI help next?", "Surrogates for FEA on unlisted shapes, and generative design for custom brackets.")])

    ansh = page("Ansh Yadav", "Machine design of joints", f"""
<p><b>Failure modes.</b> Each part can fail by tension (pulled apart), shear (sliced across), bending (pin bowed
between fork plates) or crushing (bearing pressure on contact faces). Design means sizing so that each stress
stays under its allowable value.</p>
<p><b>Allowable stress</b> = yield strength / factor of safety: sigma_t = Syt / FoS. For shear, tau = 0.5 Syt / FoS
(maximum shear stress theory).</p>
<p><b>Knuckle, Bhandari eq 4.26.</b> Rod D from tension. Pin d from shear <i>and</i> bending, whichever is larger.
Then: eye outer d0 = 2d, fork thickness a = 0.75D, eye thickness b = 1.25D, pin head 1.5d, enlarged rod
D1 = 1.1D, clearance x = 10 mm.</p>
<p><b>Socket and spigot cotter.</b> Rod d, cotter thickness t = 0.31d, collar d3 = 1.5d, socket collar d4 = 2.4d,
a = c = 0.75d, cotter width b = 1.6d, collar thickness t1 = 0.45d, cotter taper 1 in 32 (self-locking). Spigot and
socket diameters are solved from their own tension equations.</p>""",
        f"""At 50 kN the rod needs {F['demo'].raw['rod_tension']:.2f} mm, so D = {d['D']:g}. The pin needs
{F['demo'].raw['pin_shear']:.2f} mm for shear but {F['demo'].raw['pin_bending']:.2f} mm for bending, so bending
governs and d = {d['d']:g}. Then d2 = {d['d2']:g}, d3 = {d['d3']:g}, t = {d['t']:g}, t1 = {d['t1']:g}. The busiest
check is {b.name} at {use}%. Bhandari Ex 4.5 is reproduced {F['m45']}/{F['n45']} sizes.""",
        [("Why size the pin for bending too?", "Shear alone under-sizes it. Here bending needs 44.85 mm vs 25.75 for shear."),
         ("Why is the cotter tapered 1 in 32?", "A small taper is self-locking under friction but still drives out with a hammer."),
         ("What is allowable shear stress?", "0.5 Syt / FoS, from the maximum shear stress theory."),
         ("Why do checks sit at 71-79%, not 100%?", "Sized at 1.25 x load, checked at the real load, plus rounding up."),
         ("Knuckle vs cotter joint?", "Knuckle allows angular movement (pin). Cotter is rigid, for axial load only."),
         ("What happens if a check fails?", "The responsible size grows 1 mm and every check re-runs until all pass.")])

    dharmendra = page("Dharmendra Gupta", "Engineering drawing and standards", """
<p><b>First-angle projection</b> (Indian standard, SP 46 / IS 10711): the object sits between observer and plane,
so the top view goes <i>below</i> the front view and the left view goes on the <i>right</i>. The symbol is a
truncated cone shown with its circle views.</p>
<p><b>Sectioning.</b> A cutting plane (marked A-A, a chain line thick at the ends, arrows show viewing direction)
reveals the inside. Cut faces are hatched with thin lines at 45 degrees, and adjacent parts get opposite or
different-spaced hatching.</p>
<p><b>Not hatched lengthwise:</b> solid pins, bolts, nuts, keys, shafts, cotters, rivets and ribs. Cutting them
along their length gives no information, so they're drawn whole.</p>
<p><b>Centre lines</b> (thin chain) on every axis and hole. A <b>parts list</b> gives each part's number, name,
material and quantity, linked by balloons.</p>
<p><b>Tolerances, fits and GD&T.</b> Fits (e.g. H7/g6 for a pin in a hole) set the clearance. GD&T controls form
and position (flatness, perpendicularity, concentricity) against datums.</p>""",
        """FreeCAD runs headless and produces an A3 first-angle sheet: the front view as sectioned A-A with hatching, the
pin and cotter left unhatched, centre lines, dimensions, a title block and a parts list, plus a DXF. <b>Not
implemented yet:</b> tolerances, fits and GD&T. Faculty raised this on 16 October, so say it before they do.""",
        [("Why first-angle?", "It is the Indian standard SP 46 that we're taught. Top view below, left view on the right."),
         ("Why is the pin not hatched?", "Solid pins, bolts, keys, shafts and cotters aren't sectioned lengthwise."),
         ("How do you show the cutting plane?", "A chain line, thick at the ends, labelled A-A, with arrows for the viewing direction."),
         ("What fit would the knuckle pin use?", "A clearance fit like H9/d9 so it can rotate. Not yet on our drawing."),
         ("What is GD&T?", "Symbols controlling form and position, e.g. perpendicularity to a datum."),
         ("What does the parts list carry?", "Part number, name, material and quantity, linked to balloons.")])

    ankur = page("Ankur Dodke", "FEA and CAD geometry", """
<p><b>FEM basics.</b> Split the part into small elements (a mesh), assume a simple displacement field in each, and
assemble a stiffness equation K u = F. Solve for displacement u, then compute strain and stress.</p>
<p><b>Meshing (gmsh).</b> Tetrahedral elements, finer where stress changes fast (holes, fillets). Second-order
(10-node) tets are much more accurate than linear ones.</p>
<p><b>Convergence and singularities.</b> Refine the mesh until the result stops changing: that's convergence.
At a sharp re-entrant corner or a point load the stress keeps rising with every refinement. That is a
<i>singularity</i>, a modelling artefact, not real stress, so don't report it.</p>
<p><b>CalculiX</b> is an open-source solver that reads Abaqus-style input. <b>B-rep</b> (boundary representation)
stores a solid as exact faces, edges and vertices. <b>OpenCASCADE</b> is the kernel and <b>CadQuery</b> is the Python
API on top of it. <b>STEP AP214</b> is the neutral format that carries the exact geometry into NX or SolidWorks.</p>""",
        """Validation on a plain bar: hand formula 31.83 MPa vs FE 32.22 MPa, so +1.2%, and the solver is trusted. Knuckle
eye rod: hand formula 52.0 vs FE 57.9 MPa, +11.3%. The gap is stress concentration that the formula ignores. Both
were measured on the September geometry, and CalculiX runs only on the server. If the mesh won't settle, the
software says NOT CONVERGED rather than giving a number.""",
        [("Why validate on a plain bar first?", "Its exact answer is known, so +1.2% proves the solver setup."),
         ("Why is FE 11% higher on the eye?", "Stress concentration at the hole, which the textbook formula doesn't model."),
         ("What is a singularity?", "A sharp corner or point load where stress rises forever with refinement. It's an artefact."),
         ("How do you know it converged?", "The result changes negligibly between mesh refinements. Otherwise it's flagged NOT CONVERGED."),
         ("B-rep vs mesh?", "B-rep is exact surfaces for CAD and STEP. A mesh is an approximation for FEA."),
         ("Why STEP AP214?", "A neutral exact-geometry format that NX, SolidWorks and Fusion all open as an assembly.")])

    return overview + atishay + bhavya + ansh + dharmendra + ankur


def build() -> None:
    src = HERE / "_learners_guide.html"
    src.write_text(f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head>"
                   f"<body>{body(facts())}</body></html>", encoding="utf-8")
    subprocess.run([BROWSER, "--headless", "--disable-gpu", "--no-sandbox",
                    f"--print-to-pdf={OUT}", "--no-pdf-header-footer",
                    "--virtual-time-budget=20000", src.resolve().as_uri()],
                   capture_output=True, timeout=200)
    src.unlink()
    print(f"{OUT.name}  {OUT.stat().st_size // 1024} KB")


if __name__ == "__main__":
    build()
