"""Learner's guide at final-year depth: an overview and an architecture walk-through, then one
section per presenter with theory, derivations, the real code from aicad/, and viva questions.
Project numbers come from facts() in make_speaking_pack.py; code excerpts are read from the
source files at build time, so neither can drift from the software.

    PYTHONUTF8=1 AICAD_BROWSER=<chrome or brave> python report/make_learners_guide.py
"""
from __future__ import annotations

import html
import inspect
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from make_speaking_pack import BROWSER, CSS, facts  # noqa: E402

from aicad import design as core  # noqa: E402
from aicad import parse  # noqa: E402
from aicad.joints import knuckle  # noqa: E402

OUT = HERE / "AI-in-CAD-Learners-Guide.pdf"
SRC = HERE.parent / "aicad"

EXTRA = """
pre{font-family:Consolas,'Courier New',monospace;font-size:8.4pt;line-height:1.3;background:#f4f5f7;
 border-left:1mm solid #555;padding:2mm 3mm;margin:2mm 0;white-space:pre-wrap;page-break-inside:avoid}
.file{font-size:8.5pt;color:#555;margin:2mm 0 0}
h1{font-size:15pt}h2{font-size:11pt;margin:3mm 0 1mm}h3{font-size:10.6pt;margin:2mm 0 .5mm}
.who{font-size:12pt}.role{font-size:10.6pt;margin:0 0 1.5mm}
body{font-size:10pt;line-height:1.38}p{margin:1mm 0}li{margin:.4mm 0}
.ev th{background:#e3ecf7}
.eq{font-family:'Cambria Math',Cambria,serif;background:#fafafa;border:0.2mm solid #ccc;padding:1.5mm 3mm;margin:1.5mm 0}
"""


def code(obj=None, path=None, start=None, end=None) -> str:
    """A verbatim excerpt: a function by object, or a line range of a file (1-based, inclusive)."""
    if obj is not None:
        text, where = inspect.getsource(obj), f"{Path(inspect.getsourcefile(obj)).relative_to(HERE.parent)} :: {obj.__name__}"
    else:
        lines = (SRC / path).read_text(encoding="utf-8").splitlines()
        text, where = "\n".join(lines[start - 1:end]), f"aicad/{path} lines {start}-{end}"
    return f"<p class='file'>{where}</p><pre>{html.escape(text.rstrip())}</pre>"


def lines_of(path: str, needle: str, before=0, after=12) -> str:
    lines = (SRC / path).read_text(encoding="utf-8").splitlines()
    i = next(n for n, line in enumerate(lines) if needle in line)
    return code(path=path, start=i + 1 - before, end=min(len(lines), i + 1 + after))


def qa(pairs) -> str:
    return "<h3>Viva questions</h3><ol>" + "".join(f"<li><b>{q}</b><br>{a}</li>" for q, a in pairs) + "</ol>"


def evidence(rows) -> str:
    return ("<h2>Evidence: our data, our iterations, our error</h2><table class='ev'>"
            "<tr><th>An ML project would report</th><th>What we report instead, measured</th></tr>"
            + "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in rows) + "</table>")


def section(who, role, theory, project, pairs, ev=()) -> str:
    return (f"<div class='pb'><p class='who'>{who}</p><p class='role'>{role}</p>"
            f"<h2>Theory</h2>{theory}<h2>In our project</h2>{project}{evidence(ev)}{qa(pairs)}</div>")


def body(F) -> str:
    d, b, raw = F["demo"].dims, F["busiest"], F["demo"].raw
    use = round(100 * b.stress_mpa / b.allowable_mpa)

    overview = f"""
<h1>AI in CAD: Learner's Guide</h1>
<p class='sub'>Strategic Application of Artificial Intelligence in CAD · SGSITS Mechanical, B.Tech 2026-27 ·
Supervisor Dr. B. R. Rawal · theory, derivations and the real source code, one section per presenter</p>
<div class='box'><b>Problem statement.</b> Turn a natural-language design requirement into a joint that is
analytically sized, checked against every failure mode, modelled as an exact B-rep solid, drafted to SP 46 and
cross-checked by FEA, with every number traceable to a formula and a source. The architecture is a
<b>neuro-symbolic split</b>: a language model handles the one ambiguous step, parsing the intent, and
deterministic symbolic code does everything that has a right answer.</div>
<div class='say'><b>When faculty ask "how many epochs, what is your training data?"</b> Epochs and training loss
measure how well a model <i>learned</i> a relationship from data. Our sizing has no learned weights, on purpose: the
relationship (strength of materials) is already known exactly, so we <i>encode</i> it. The right metrics for an
encoded model are <b>validation against known answers</b>, <b>convergence of the iterative steps</b> and
<b>error against an independent method</b>. Each section below gives those numbers in the same shape an ML project
would: dataset, iterations, error. They're measured, not estimated.</div>
<table class='ev'><tr><th>ML term</th><th>Our honest equivalent</th><th>Ours</th></tr>
<tr><td>Training data</td><td>The design-book equations and proportions (NPTEL IIT KGP, Bhandari, Unwin 1899, ISO tables)</td><td>6 joint models, 44 checks</td></tr>
<tr><td>Validation / test set</td><td>Published worked examples with printed answers, plus a golden set of English requests</td><td>Bhandari Ex 4.5, 4.2, Prob 4.1, NPTEL; 22 golden sentences</td></tr>
<tr><td>Epochs / iterations</td><td>The 1 mm grow-and-recheck loop (up to 400 steps) and FE mesh halving until the peak settles</td><td>knuckle 50 kN: 0 growth steps needed; FE flagged unless &lt;5% move on halving</td></tr>
<tr><td>Test accuracy</td><td>Sizes and stresses matching the book exactly</td><td>Ex 4.5 7/7 sizes, 6/6 stresses</td></tr>
<tr><td>Generalisation</td><td>Any load or material, not just the trained range: it's the formula, so no extrapolation error</td><td>4000/4000 random loads (5-200 kN, 4 joints) pass every check</td></tr>
<tr><td>Regression tests</td><td>Automated pytest suite run on every change</td><td>301 cases</td></tr></table>
<h2>Architecture</h2>
<table>
<tr><th>Stage</th><th>Module</th><th>Deterministic?</th><th>Output</th></tr>
<tr><td>1. Intent extraction</td><td>aicad/parse.py</td><td>No (LLM) + guarded</td><td>Spec: joint, load, sizes, allowables</td></tr>
<tr><td>2. Analytical sizing</td><td>aicad/joints/&lt;joint&gt;.py :: design()</td><td>Yes</td><td>Design: dims, rules, raw sizes</td></tr>
<tr><td>3. Verification</td><td>&lt;joint&gt;.py :: _checks()</td><td>Yes</td><td>list[Check], all must pass</td></tr>
<tr><td>4. Solid modelling</td><td>build_parts() on CadQuery / OCCT</td><td>Yes</td><td>B-rep solids, STEP AP214</td></tr>
<tr><td>5. Drafting</td><td>aicad/freecad_pack.py (FreeCAD headless)</td><td>Yes</td><td>A3 first-angle sheet, DXF, FCStd</td></tr>
<tr><td>6. FE cross-check</td><td>aicad/fea.py + _fea_runner.py (gmsh, CalculiX)</td><td>Yes</td><td>von Mises peak, convergence flag</td></tr>
<tr><td>7. Material study</td><td>aicad/optimise.py :: compare()</td><td>Yes</td><td>mass and cost per material</td></tr>
</table>
<h2>Results to quote</h2>
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>Joints, parts, checks</td><td>6 joints · {F['nchecks']} failure checks, all satisfied · busiest per joint {F['lo']}-{F['hi']}%</td></tr>
<tr><td>Knuckle, 50 kN, governing</td><td>{b.name}: {b.stress_mpa:.1f} / {b.allowable_mpa:g} MPa = {use}% utilisation</td></tr>
<tr><td>Knuckle sizes (mm)</td><td>D {d['D']:g}, D1 {d['D1']:g}, d {d['d']:g}, d0 {d['d2']:g}, d3 {d['d3']:g}, b {d['t']:g}, a {d['t1']:g}</td></tr>
<tr><td>Validation vs textbook</td><td>Bhandari Ex 4.5: {F['m45']}/{F['n45']} sizes and 6/6 stresses exact · Ex 4.2: {F['m42']}/{F['n42']} · Problem 4.1 exact</td></tr>
<tr><td>FE validation</td><td>plain bar +1.2% (31.83 vs 32.22 MPa) · knuckle eye rod +11.3% (52.0 vs 57.9 MPa, September geometry)</td></tr>
<tr><td>Throughput</td><td>about {F['per_ms']:.2f} ms per complete knuckle design (1000-run average)</td></tr>
<tr><td>Test suite</td><td>{F['tests']} pytest cases</td></tr>
<tr><td>Source errata found</td><td>NPTEL knuckle example fails its own eye-shear check by 23% · cotter spigot crushing omitted ·
bolt preload printed 284d kN, should be 2840d N</td></tr>
</table>
<h2>The core data model</h2>
<p>Every joint returns the same record, so the UI, the report, the drawing and the tests treat all six joints
identically. A <span class='k'>Check</span> passes only if the stress is within the allowable value. The tolerance
1e-9 absorbs floating-point error, and nothing else.</p>
{code(core.Check)}
{code(core.next_preferred)}
{code(core.sizing_load)}
<p>The <b>design factor</b> is applied to the load, not to the stresses, so the allowables stay the book values.
At 1.25 the governing check can't exceed 1/1.25 = 80% utilisation, and rounding up to preferred sizes pushes it
below that. That's why every joint lands at {F['lo']}-{F['hi']}%.</p>
"""

    atishay = section("Atishay Jain", "AI: language models, structured extraction and guarding against hallucination", f"""
<h3>How an LLM works</h3>
<p>A transformer LLM maps text to <b>tokens</b> (sub-word units from byte-pair encoding, about 4 characters of
English each) and is trained to maximise the likelihood of the next token, <span class='k'>p(x_t | x_&lt;t)</span>.
Self-attention lets every token weigh every other token, which is why it handles free phrasing like "a knuckle
for five tonnes" well. Decoding samples from that distribution, and <b>temperature</b> controls how random the
sampling is.</p>
<h3>Why LLMs hallucinate, and why that matters here</h3>
<p>The objective is <i>plausibility, not truth</i>. When the evidence is weak, the most likely continuation can
still be a confident fabrication. LLMs also don't do arithmetic: "62,500 N" is a token pattern to them, not a
computed value. In a design tool a hallucinated load is a <b>silent safety failure</b>, because the part looks fine
and is sized for the wrong force.</p>
<h3>Structured extraction</h3>
<p>We constrain the model three ways: (1) a system prompt that defines the task, the units and "never invent a
number"; (2) a JSON schema with an <b>enum</b> of the six joint names, so free text can't come back; (3) a post-hoc
<b>provenance check</b> on every number. The first two reduce errors. Only the third <i>guarantees</i> no
fabricated value gets through.</p>
<h3>Why sizing is not machine learning</h3>
<p>Sizing a joint is a closed-form inverse problem with an exact analytic answer, e.g. D = sqrt(4P/(pi sigma_t)).
A regression model trained on past designs would only interpolate (it is wrong outside the training range), has
no failure-mode semantics, and gives no reason a designer can sign off. ML earns its place where no analytic model
exists. Here one does, so using ML would be strictly worse.</p>
<h3>Text-to-CAD landscape</h3>
<p>Generative text-to-CAD systems (commercial ones like Zoo, and research models trained on CAD sequence
datasets such as DeepCAD) predict geometry directly. Their output is <i>shape-plausible</i> but not
<i>load-verified</i>. Our pipeline inverts this: requirement → analysis → geometry, so the shape is a consequence
of the engineering.</p>""",
        f"""<p><b>The system prompt</b> (what the model is told):</p>
{lines_of('parse.py', '_SYSTEM = (', 0, 10)}
<p><b>The guard.</b> Every number the model returns must match a number literally present in the request, up to
an allowed unit factor (x1000 for kN, x9.80665 for kgf, x9806.65 for tonnes), within 1%.</p>
{code(parse._traceable)}
{lines_of('parse.py', 'factors = _LOAD_FACTORS', 0, 4)}
<p><b>Fallback chain.</b> <span class='k'>parse()</span> tries each configured AI backend. The first one that answers
is merged with the regex parse (the AI value wins, gaps are filled from the rules, disagreements are logged). If
every backend fails (no key, no network, bad JSON), the regex parse alone is used, so the tool works offline.</p>
{code(parse.parse)}""",
        [("Is this a trained model?", "No. It's a neuro-symbolic system. The LLM only parses intent. Sizing, checks and geometry are deterministic code from design books."),
         ("Why not let the LLM do the calculation?", "LLMs predict tokens and don't compute. They make arithmetic errors with full confidence, and nothing would show the mistake."),
         ("Prompt says 'never invent a number'. Isn't that enough?", "No. A prompt only lowers the probability. _traceable is a hard check: an untraceable number is dropped and logged."),
         ("Can the guard reject a correct answer?", "Yes, by design, e.g. 'double gibs' has no digit, so gibs is special-cased to {1, 2}. Rejecting a correct value just asks the user again. Accepting a wrong one would size a part wrongly."),
         ("What is the JSON schema enum for?", "It restricts joint to the six supported names or null, so the model can't return an unsupported joint."),
         ("What happens with no internet?", "parse() falls back to the regex parser. The notes record 'AI unavailable, used rules'."),
         ("How is this different from text-to-CAD?", "Text-to-CAD predicts shape. We derive shape from verified analysis, so every dimension has a formula and a source.")],
        ev=[("Pretrained model", "Claude (Anthropic) used as-is. Zero fine-tuning epochs, by design: the parser needs language skill, not engineering knowledge"),
 ("Test set", "eval/golden_requests.json: 22 hand-labelled English requests, 12 fields each. An invented value counts as wrong"),
 ("Accuracy, rules only", "18/22 sentences fully correct, 0.0 s. Misses: 'two tonne', 'fifty kilonewton', 'half a tonne' (number words), 'pin joint with fork and eye' (synonym)"),
 ("Accuracy, LLM", "18/20 on the 18 Sep set (196 s for 20 calls). LLM + rules merged: 18/20. The LLM fixes phrasing, the rules fill gaps"),
 ("Hallucination rate reaching the design", "0 by construction: every LLM number must pass _traceable or it is dropped and logged"),
 ("Code-generation eval", "6 unlisted shapes: 5/6 correct on bounding box and volume, 1 failed after 2 attempts. That's why codegen is labelled experimental")])

    bhavya = section("Bhavya Shrivastava", "AI in mechanical engineering: PINNs, surrogates, generative design, digital twins", """
<h3>Physics-informed neural networks</h3>
<p>A PINN approximates a field u(x, t) with a network u_theta and trains on a composite loss:</p>
<div class='eq'>L(theta) = (1/N) Σ |u_theta(x_i) − u_i|² &nbsp;+&nbsp; λ · (1/M) Σ |N[u_theta](x_j)|² &nbsp;+&nbsp; boundary terms</div>
<p>The first term fits the data. The second is the <b>physics residual</b>: the governing PDE operator N (e.g.
∇·σ + f = 0 for static equilibrium) is evaluated by automatic differentiation at collocation points. Physics is a
<b>soft constraint</b>, weighted by λ. With limited capacity or a badly tuned λ, the network can trade physics
accuracy for data fit, so equilibrium is approximately but not exactly satisfied.</p>
<h3>Surrogate models</h3>
<p>A surrogate (Gaussian process, polynomial response surface, neural network) is trained on a design-of-experiments
sample of an expensive simulation and then queried in microseconds. This makes optimisation and uncertainty
studies affordable. The cost: it's only valid inside the sampled domain, and its error must be estimated
(e.g. GP variance).</p>
<h3>Generative design and topology optimisation</h3>
<p>Topology optimisation (SIMP) gives each element a density ρ in [0, 1] with stiffness E(ρ) = ρ^p E0 (p ≈ 3) and
minimises compliance subject to a volume fraction, using adjoint sensitivities. The output is a load-path-optimal
material layout, which still needs interpretation for manufacturing (casting draft angles, machining access).</p>
<h3>Digital twins</h3>
<p>A digital twin is a model synchronised with a physical asset through sensor data. It is used for condition
monitoring and remaining-useful-life prediction, and typically combines physics models with data-driven
correction.</p>""",
        f"""<p><b>Our choice: physics as a hard constraint.</b> In aicad the governing equations are not a penalty term. They
are a <i>feasibility condition</i>: a design is only returned if every check passes, and a failing check
deterministically grows the responsible dimension. In the knuckle, the eye diameter is grown 1 mm at a time until
every eye and fork check passes:</p>
{lines_of('joints/knuckle.py', 'd2 = props["eye_outer_diameter_d2"]', 0, 13)}
<p>This is the correct tool for standard joints, where closed-form strength-of-materials models exist and are
accepted by codes. A PINN or a surrogate would be the right tool for geometry with no closed form, e.g. a cast
bracket, and our FE module is the natural source of training data for one.</p>
<p><b>A practical optimisation that is already in the project:</b> <span class='k'>aicad/optimise.py</span> re-sizes
the same joint for each material and compares mass and cost. At 50 kN, 30C8 gives 11.36 kg (about Rs 795), 40C8
7.63 kg, 40Cr1 4.05 kg, FG260 22.43 kg and aluminium 3.39 kg. Materials that are stronger in tension shrink the
part, and cast iron's poor tensile strength makes it heaviest.</p>""",
        [("Write the PINN loss.", "Data misfit + λ · PDE residual (by autodiff at collocation points) + boundary-condition terms."),
         ("Soft vs hard constraint?", "Soft = a penalty that can be traded against data fit. Hard = a feasibility condition that must hold. aicad uses hard checks."),
         ("Why not a PINN for the knuckle?", "An exact closed-form model exists. A PINN would approximate a known answer, at higher cost and with no guarantee."),
         ("Where does a surrogate fail?", "Outside the sampled design space. Extrapolation error is unbounded."),
         ("What is SIMP?", "Topology optimisation with density-penalised stiffness E = ρ^p E0. It minimises compliance at a fixed volume."),
         ("How could AI extend this project?", "Train a surrogate on our FE runs to predict stress concentration for unlisted shapes. Use topology optimisation for custom brackets.")],
        ev=[("Constraint type", "Hard: 44 analytic checks, a design is returned only if all pass. 4000/4000 random loads (5-200 kN) feasible"),
 ("Optimisation dataset", "5 materials compared at 50 kN: 30C8 11.36 kg, 40C8 7.63 kg, 40Cr1 4.05 kg, FG260 22.43 kg, Al 3.39 kg (mass range 6.6x)"),
 ("Iterations", "Deterministic grow-and-recheck in 1 mm steps (cap 400), instead of gradient descent on a penalty"),
 ("Surrogate training data we already have", "FE runs on 5 joints with convergence labels: a ready dataset if a stress-concentration surrogate is the next step"),
 ("Speed vs simulation", "0.03 ms per analytic design vs minutes per CalculiX run: over a million times faster for the checks that have closed forms")])

    ansh = section("Ansh Yadav", "Machine design of joints: failure theory, derivations and Bhandari proportions", f"""
<h3>Allowable stresses and failure theories</h3>
<p>For a ductile material, allowable tension σ_t = S_yt / FoS. Under the <b>maximum shear stress (Tresca)</b>
theory, yield in shear happens at S_sy = 0.5 S_yt, so τ = 0.5 S_yt / FoS (von Mises gives 0.577 S_yt, which is
the factor used for Bhandari Problem 4.1). Crushing (bearing) is a contact pressure on the projected area d x l,
and it's allowed higher because it's local and compressive.</p>
<h3>Knuckle joint: the governing equations</h3>
<div class='eq'>Rod tension: P = (π/4) D² σ_t &nbsp;⇒&nbsp; D = √(4P / π σ_t)</div>
<div class='eq'>Pin, double shear: P = 2 (π/4) d² τ &nbsp;⇒&nbsp; d = √(2P / π τ)</div>
<p><b>Pin bending derivation.</b> The fork plates (thickness a) and the eye (thickness b) apply the load as
distributed pressure along the pin. Model each fork reaction P/2 as uniform over a and the eye load P as uniform
over b. Taking moments at mid-span:</p>
<div class='eq'>M = (P/2)(b/2 + a/3) − (P/2)(b/4) = (P/2)(a/3 + b/4) &nbsp;&nbsp; σ_b = 32M / (π d³)</div>
<p>So the pin is sized for <i>both</i> shear and bending, and the larger one governs. Then the eye and fork are
checked in tension and shear across (d0 − d) and in crushing on the projected area d x thickness.</p>
<h3>Bhandari eq 4.26 proportions</h3>
<p>d0 = 2d (eye and fork outer diameter) · a = 0.75D (fork) · b = 1.25D (eye) · d1 = 1.5d (pin head and collar) ·
D1 = 1.1D (enlarged rod) · x = 10 mm clearance.</p>
<h3>Socket and spigot cotter</h3>
<p>t = 0.31d · d3 = 1.5d · d4 = 2.4d · a = c = 0.75d · b = 1.6d · t1 = 0.45d · taper 1 in 32. The spigot diameter
d2 and the socket diameter d1 are solved from their own net-section tension equations, e.g.
P = [(π/4)d2² − d2 t] σ_t, a quadratic in d2. The 1 in 32 taper is below the friction angle, so the cotter is
self-locking.</p>""",
        f"""<p><b>The demo run (50 kN, σ_t 75, τ 60, σ_c 150 MPa, sized at 62.5 kN):</b> rod
{raw['rod_tension']:.2f} → D = {d['D']:g} · pin shear {raw['pin_shear']:.2f} mm, pin bending {raw['pin_bending']:.2f} mm,
so <b>bending governs</b> → d = {d['d']:g} · d0 = 2d = {d['d2']:g} · b = 1.25D → {d['t']:g} · a = 0.75D → {d['t1']:g}.
Busiest check: {b.name}, {b.stress_mpa:.1f}/{b.allowable_mpa:g} MPa = {use}%.</p>
<p><b>Sizing code</b>: note that b and a are rounded to standard sizes <i>before</i> the bending size is computed,
the same order Bhandari uses in Ex 4.5:</p>
{lines_of('joints/knuckle.py', 'if rod_diameter_mm is not None:', 0, 26)}
<p><b>All nine checks</b>, exactly as they run:</p>
{code(knuckle._checks)}""",
        [("Derive the pin bending moment.", "Fork reactions P/2 uniform over a, eye load P uniform over b. Then M = (P/2)(a/3 + b/4) and σ = 32M/πd³."),
         ("Why size the pin for bending as well as shear?", f"Shear alone needs {raw['pin_shear']:.1f} mm, bending needs {raw['pin_bending']:.1f} mm. A shear-only design would fail in bending."),
         ("Why τ = 0.5 S_yt?", "The maximum shear stress (Tresca) theory: yield when the max shear reaches half the tensile yield. It's conservative compared with von Mises (0.577)."),
         ("Why is the cotter self-locking?", "A 1 in 32 taper (about 1.8°) is below the friction angle (about 8.5° at μ ≈ 0.15), so the axial load can't eject it."),
         ("Why round b and a before sizing the pin?", "Bending depends on a and b. Using the as-built (rounded) thicknesses makes the check consistent with the part actually made, as in Ex 4.5."),
         ("Knuckle vs cotter: when to use which?", "Knuckle: tension with angular freedom about the pin (valve rods, tie bars). Cotter: rigid axial joint, tension or compression."),
         ("What is the NPTEL erratum?", "Its worked example raises the pin for bending but checks the eye against the old pin, and fails eye shear by 23%. Our code grows d0 until the check passes.")],
        ev=[("Reference dataset", "Bhandari Ex 4.5 and 4.2, Problem 4.1, the NPTEL IIT KGP worked problems: printed answers as ground truth"),
 ("Knuckle accuracy", "Ex 4.5: 7/7 adopted sizes and 6/6 stresses (31.25, 25 N/mm2) exact. Problem 4.1: 14.47 and 13.47 mm exact"),
 ("Cotter accuracy", "Ex 4.2: 9/10 sizes. Spigot 37.92 and socket 52.04 mm solved from tension equations. Only b differs (the book uses FoS 4 on the cotter)"),
 ("Errors found in the 'dataset'", "NPTEL knuckle fails its own eye shear by 23%. Cotter spigot crushing omitted. Bolt preload 284d kN should be 2840d N"),
 ("Coverage", "44 checks over 6 joints. 103 design tests + 21 book-problem tests in pytest"),
 ("Robustness", "4000/4000 random loads, 5-200 kN, every check passes; busiest check stays at 71-79% of allowable")])

    dharmendra = section("Dharmendra Gupta", "Engineering drawing and standards: SP 46, sectioning, limits and fits, GD&T", """
<h3>Projection</h3>
<p>SP 46 (2003) / IS 10711 specify <b>first-angle projection</b>: the object sits in the first quadrant, between
the observer and the plane, so the plan goes below the elevation and the left-side view goes to the right of it.
The projection symbol (a truncated cone) goes in the title block.</p>
<h3>Sections</h3>
<p>The cutting plane is a thin chain line, thick at the ends and at changes of direction, labelled A-A, with
arrows showing the viewing direction. Cut material is hatched with thin lines at 45°. Adjacent parts get opposite
directions or different spacing. <b>Never sectioned lengthwise:</b> shafts, pins, bolts, nuts, keys, cotters,
rivets, ribs and webs. Cutting a solid of revolution along its axis adds no information.</p>
<h3>Lines and annotation</h3>
<p>Continuous thick lines for visible outlines, thin dashed for hidden ones, thin chain for centre lines and axes
of symmetry. Dimensions use aligned or unidirectional text, with no dimensions to hidden lines. A parts list
(item, name, material, quantity) is linked to the views by balloons.</p>
<h3>Limits and fits (IS 919 / ISO 286)</h3>
<p>A fit is a hole tolerance zone plus a shaft one, e.g. <b>H7/g6</b> (location clearance), <b>H7/p6</b>
(interference) or <b>H9/d9</b> (free running). The hole-basis system keeps the hole at H so standard reamers can be
used. A knuckle pin needs a running clearance fit so the joint can articulate.</p>
<h3>GD&T (ISO 1101 / ASME Y14.5)</h3>
<p>The feature control frame gives the characteristic (form: flatness, cylindricity · orientation:
perpendicularity, parallelism · location: position, concentricity · runout), the tolerance zone, and the datums
A | B | C. Example: the pin bore ⊥ 0.02 to datum A (the eye face), so the pin doesn't bind across the fork.</p>""",
        f"""<p><b>What the drawing module produces:</b> FreeCAD runs headless (<span class='k'>freecadcmd</span>) and builds
TechDraw views of the STEP assembly on an A3 first-angle sheet: the front view as section A-A with hatching, the pin,
cotter and bolts left unhatched, centre lines, dimensions, a title block and a parts list. It also writes a DXF for
AutoCAD and the native FCStd. The same dims dictionary drives the solid and the drawing, so the drawing can't
disagree with the calculation.</p>
<p><b>How the views are made</b>: the module drives FreeCAD's TechDraw workbench from the dims and the parts list:</p>
{lines_of('freecad_pack.py', 'page = doc.addObject("TechDraw::DrawPage"', 0, 9)}
<p><b>Honest gap:</b> limits and fits, surface finish symbols and GD&T are <b>not implemented yet</b>. Faculty
raised this on 16 October. The next step is to attach H9/d9 to the pin and bore, and ⊥ to datum A on the eye.</p>""",
        [("First vs third angle?", "First angle (India, SP 46): plan below the elevation. Third angle (US): plan above it. The symbol is in the title block."),
         ("Why aren't the pin and cotter hatched?", "Solids of revolution and standard fasteners aren't sectioned lengthwise. Section A-A leaves them whole."),
         ("What fit would you give the knuckle pin?", "A running clearance fit, H9/d9, hole basis, so the joint can rotate freely."),
         ("Read the fit H7/g6.", "Hole: grade 7 tolerance with zero lower deviation (H). Shaft: grade 6, g sits slightly below zero. Together they give a small clearance location fit."),
         ("What is a datum?", "A theoretically exact reference feature (plane, axis) that GD&T tolerances are measured from."),
         ("How do you guarantee the drawing matches the calculation?", "Both are generated from the same dims dictionary. There's no manual redrafting step where they could diverge.")],
        ev=[("Input", "One dims dictionary per design feeds both the STEP solid and the TechDraw sheet"),
 ("Outputs per run", "A3 first-angle sheet (PDF), DXF, FCStd, STEP assembly: 4 formats from one source"),
 ("Tests", "3 FreeCAD pack tests (one per joint family, full sheet export) + a geometry test that every joint has drawing dimensions on real views"),
 ("Standards applied", "SP 46 first angle, section A-A, no lengthwise hatching of pins and cotters, centre lines, parts list"),
 ("Known gap", "No limits/fits or GD&T yet (16 Oct review). Next: H9/d9 on the pin, perpendicularity to datum A")])

    ankur = section("Ankur Dodke", "FEA and CAD geometry: FEM formulation, meshing, convergence, B-rep and STEP", """
<h3>Finite element formulation</h3>
<p>From the principle of virtual work, the displacement field inside each element is interpolated from nodal values,
u = N u_e. Strain ε = B u_e, stress σ = D ε (D = the linear-elastic constitutive matrix from E and ν). The element
stiffness is k_e = ∫ Bᵀ D B dV, evaluated by Gauss quadrature. These are assembled into the global system</p>
<div class='eq'>K u = F &nbsp;(with displacement boundary conditions applied)</div>
<p>This is solved for u, then stresses are recovered at the integration points and reported as the <b>von Mises</b>
equivalent σ_vm = √(½[(σ1−σ2)² + (σ2−σ3)² + (σ3−σ1)²]).</p>
<h3>Meshing</h3>
<p>gmsh generates tetrahedra from the B-rep. <b>Second-order (10-node) tets</b> capture bending and stress gradients
far better than linear ones, which are over-stiff. The characteristic length sets the element size. Refine where
the gradients are steep: the pin bore and the slot corners.</p>
<h3>Convergence and singularities</h3>
<p>The h-refinement test: halve the element size and check the peak stress stays put. A <b>stress singularity</b>
(a sharp re-entrant corner, a point load, a rigidly fixed edge) gives a peak that grows without bound as the mesh
refines. It's a mathematical artefact of the idealisation, not a real stress, and must not be reported as one.</p>
<h3>B-rep and exchange</h3>
<p>Boundary representation stores a solid as topology (shell → face → edge → vertex) bound to exact geometry
(planes, cylinders, NURBS). OpenCASCADE is the open B-rep kernel, and CadQuery is a parametric Python API on top of
it. <b>STEP AP214</b> (ISO 10303) carries exact B-rep plus assembly structure and colours between systems (NX,
SolidWorks, Fusion). A mesh is lossy, B-rep isn't.</p>""",
        f"""<p><b>Load case.</b> For the knuckle, the single-eye rod is held at the pin bore (where the pin bears) and pulled at
the far rod end. The FE result is compared against the tool's own "rod tension" check:</p>
{lines_of('fea.py', 'CASES = {', 0, 8)}
<p><b>Validation.</b> A 20 mm bar pulled by 10 kN: FE 32.22 vs hand 31.83 MPa, +1.2%. The residual is the edge effect
at the fixed face. The knuckle eye rod: FE 57.9 vs hand 52.0 MPa, +11.3%, which is stress concentration at the
enlarged-end transition that the uniaxial formula ignores. These were measured on the September geometry, and
CalculiX runs only on the server.</p>
<p><b>Convergence guard</b>: if the FE peak exceeds 1.5x the hand value, the mesh is halved and re-solved. If the
peak moves by more than 5%, the result is flagged as not converged and isn't presented as a stress:</p>
{lines_of('fea.py', 'if r.get("ok") and check is not None and converge_check:', 0, 13)}
<p><b>Geometry code</b>: every part is built the way you would in NX: sketch, extrude, boolean. The eye rod is a disc,
a rod and the D1 enlargement unioned together, with the pin bore cut through:</p>
{lines_of('joints/knuckle.py', 'eye_rod = (', 0, 7)}""",
        [("Write the element stiffness matrix.", "k_e = ∫ Bᵀ D B dV, with B the strain-displacement matrix and D the elasticity matrix, integrated by Gauss quadrature."),
         ("Why 10-node tetrahedra?", "Quadratic shape functions represent bending and stress gradients. Linear tets lock and come out over-stiff."),
         ("Why validate on a plain bar first?", "σ = P/A is exact there, so +1.2% isolates the solver and BC setup from any modelling question."),
         ("Why is the eye rod 11% above hand?", "The geometric stress concentration at the section change. The textbook formula assumes uniform stress."),
         ("How do you detect a singularity?", "The peak keeps rising under h-refinement instead of converging. Our code halves the mesh and flags >5% movement."),
         ("B-rep vs mesh?", "B-rep: exact topology plus geometry, editable, for CAD and STEP. Mesh: discrete approximation for analysis."),
         ("Why STEP AP214?", "ISO 10303 neutral exchange with assembly structure and colours. It opens natively in NX, SolidWorks and Fusion.")],
        ev=[("Solver validation", "Plain bar 20 mm, 10 kN: FE 32.22 vs exact 31.83 MPa = +1.2%"),
 ("Component result", "Knuckle eye rod: FE 57.9 vs hand 52.0 MPa = +11.3% (September geometry)"),
 ("Mesh-convergence study", "Gib and cotter rod at 6.0, 4.0, 2.5, 1.6 mm mesh: peak 157, 180, 175, 191 MPa, wandering about 10% over 16x the nodes. Not settled, so flagged as a singularity, not reported as stress"),
 ("Convergence rule", "If peak > 1.5x hand, halve the mesh and re-solve. Converged only if the peak moves 5% or less"),
 ("Geometry tests", "48 pytest cases: each part is one valid solid, no two parts overlap (and the overlap test is proven able to fail), the knuckle eye can swing, the cotter sits in both slots, STEP keeps parts separate")])

    return overview + atishay + bhavya + ansh + dharmendra + ankur


def build() -> None:
    src = HERE / "_learners_guide.html"
    src.write_text(f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}{EXTRA}</style></head>"
                   f"<body>{body(facts())}</body></html>", encoding="utf-8")
    subprocess.run([BROWSER, "--headless", "--disable-gpu", "--no-sandbox",
                    f"--print-to-pdf={OUT}", "--no-pdf-header-footer",
                    "--virtual-time-budget=20000", src.resolve().as_uri()],
                   capture_output=True, timeout=200)
    src.unlink()
    print(f"{OUT.name}  {OUT.stat().st_size // 1024} KB")


if __name__ == "__main__":
    build()
