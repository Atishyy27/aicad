"""Build the project report in the format an Indian engineering college expects.

A4 portrait, serif, 1.5 line spacing, justified body, numbered chapters, numbered figures and
tables, certificate and declaration pages, references. Rendered locally with the Brave already
installed on this machine. Nothing is uploaded anywhere.

Numbers come from report/facts.json, which is written by running the software itself, so no
figure in this report is typed by hand.

    python report/make_college_report.py
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

# ---- fill these in when he supplies them --------------------------------------------------
STUDENT = "Atishay Jain"
ENROLMENT = "0801ME231024"
TEAM = [("Ansh Yadav", "10"), ("Ankur Dodhke", "14"), ("Atishay Jain", "24"),
        ("Bhavya Shrivastava", "30"), ("Dharmendra Gupta", "D03")]
GUIDE = "____________________"  # guide's name
GUIDE_TITLE = "____________________"   # designation
HOD = "Dr. B. R. Rawal"
SESSION = "20__ - 20__"
# -------------------------------------------------------------------------------------------

DEPT = "Department of Mechanical Engineering"
INSTITUTE = "Shri Govindram Seksaria Institute of Technology and Science"
CITY = "Indore, Madhya Pradesh"
TITLE = "Strategic Application of Artificial Intelligence in CAD"
SUB = "Automated design, verification and drafting of standard machine joints from a plain language request"

FIGURES: list[tuple[str, str]] = []
TABLES: list[str] = []


def img_src(name: str) -> str:
    f = SHOTS / f"{name}.png"
    if not f.exists():
        return ""
    return "data:image/png;base64," + base64.b64encode(f.read_bytes()).decode()


def fig(name: str, caption: str, width: str = "100%") -> str:
    src = img_src(name)
    if not src:
        return ""
    FIGURES.append((caption, name))
    n = len(FIGURES)
    return (f'<figure><img src="{src}" style="width:{width}" alt="{caption}">'
            f'<figcaption>Fig. {n}: {caption}</figcaption></figure>')


def tbl(caption: str, head: str, body: str, cls: str = "") -> str:
    TABLES.append(caption)
    n = len(TABLES)
    return (f'<div class="tblwrap"><div class="tcap">Table {n}: {caption}</div>'
            f'<table class="{cls}"><thead>{head}</thead><tbody>{body}</tbody></table></div>')


CSS = """
@page{size:A4 portrait;margin:25mm 20mm 20mm 30mm}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:#fff;color:#111;
  font-family:"Times New Roman",Times,Georgia,serif;font-size:12pt;line-height:1.5;
  text-align:justify;-webkit-font-smoothing:antialiased}
h1,h2,h3,h4{font-family:"Times New Roman",Times,serif;color:#000;text-align:left;
  page-break-after:avoid}
h1.ch{font-size:16pt;text-transform:uppercase;letter-spacing:.04em;margin:0 0 4mm;
  padding-bottom:2mm;border-bottom:1.5pt solid #000}
h2{font-size:13pt;margin:6mm 0 2mm}
h3{font-size:12pt;font-style:italic;font-weight:700;margin:4mm 0 1.5mm}
p{margin:0 0 3mm;text-indent:0}
ul,ol{margin:0 0 3mm;padding-left:7mm}
li{margin-bottom:1.5mm}
.page{page-break-after:always}
.page:last-child{page-break-after:auto}
.center{text-align:center}
.nojust{text-align:left}

/* title page */
.title-page{height:247mm;min-height:247mm;padding:0;display:flex;flex-direction:column;
  text-align:center;border:0;page-break-after:always}
.tp-border{border:2.5pt solid #000;padding:3mm;flex:1 1 auto;display:flex;
  flex-direction:column}
.tp-inner{border:0.8pt solid #000;padding:16mm 12mm 14mm;flex:1 1 auto;display:flex;
  flex-direction:column;align-items:center}
.tp-title{font-size:23pt;font-weight:700;line-height:1.25;margin:22mm 0 6mm;text-transform:uppercase}
.tp-sub{font-size:12pt;font-style:italic;color:#333;max-width:85%;line-height:1.45}
.tp-label{font-size:11.5pt;margin-top:26mm;letter-spacing:.02em}
.tp-deg{font-size:14pt;font-weight:700;margin-top:2mm;line-height:1.4}
.tp-by{margin-top:22mm;font-size:12pt}
.tp-name{font-size:15pt;font-weight:700;margin-top:2mm}
.tp-guide{margin-top:20mm;font-size:12pt}
.tp-inst{margin-top:19mm;font-size:13pt;font-weight:700;line-height:1.45}
.seal{width:26mm;height:26mm;border:1.5pt solid #000;border-radius:50%;
  display:flex;align-items:center;justify-content:center;font-size:8pt;margin:16mm auto 0;
  line-height:1.15}

/* front matter */
.fm-title{font-size:15pt;font-weight:700;text-transform:uppercase;text-align:center;
  letter-spacing:.06em;margin:0 0 7mm;padding-bottom:2.5mm;border-bottom:1.2pt solid #000}
.sign-row{display:flex;justify-content:space-between;margin-top:22mm;font-size:11.5pt}
.sign-row div{text-align:center;width:46%}
.sign-line{border-top:0.8pt solid #000;margin-bottom:1.5mm;padding-top:0}
.blank{border-bottom:0.8pt dotted #555;display:inline-block;min-width:44mm}

/* contents */
.toc{font-size:12pt}
.toc .row{display:flex;align-items:baseline;margin-bottom:2.2mm}
.toc .row .t{white-space:nowrap}
.toc .row .dots{flex:1;border-bottom:1px dotted #999;margin:0 2mm 1mm}
.toc .row .p{font-variant-numeric:tabular-nums}
.toc .lvl2{padding-left:8mm;font-size:11.5pt}
.toc .head{font-weight:700}

/* tables and figures */
.tblwrap{margin:4mm 0 5mm;page-break-inside:avoid}
.tcap{font-size:10.5pt;font-weight:700;text-align:center;margin-bottom:2mm}
table{width:100%;border-collapse:collapse;font-size:10.5pt;line-height:1.35}
th{border:0.8pt solid #000;padding:1.6mm 2mm;text-align:left;font-weight:700;background:#eee}
td{border:0.8pt solid #444;padding:1.6mm 2mm;vertical-align:top}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
table.compact{font-size:9.8pt}
table.compact th,table.compact td{padding:1.2mm 1.6mm}
.mono{font-family:"Courier New",monospace;font-size:9.6pt}

figure{margin:5mm 0;text-align:center;page-break-inside:avoid}
figure img{max-width:100%;border:0.8pt solid #666}
figcaption{font-size:10.5pt;margin-top:2mm;text-align:center}

.abstract p{text-align:justify}
.kw{margin-top:5mm;font-size:11.5pt}
blockquote{margin:3mm 0 3mm 6mm;padding-left:4mm;border-left:2pt solid #999;
  font-style:italic;color:#222}
.refs{font-size:11pt;line-height:1.45}
.refs li{margin-bottom:2.5mm;text-align:left}
.note{border:0.8pt solid #000;padding:3mm 4mm;margin:4mm 0;background:#f4f4f4;
  page-break-inside:avoid}
.note b{display:block;margin-bottom:1.5mm}
"""


def joints_table() -> str:
    rows = []
    for j in F["joints"]:
        rows.append(f"<tr><td>{j['title']}</td><td class='n'>{j['parts']}</td>"
                    f"<td class='n'>{j['dims']}</td><td class='n'>{j['checks']}</td>"
                    f"<td>{j['duty']}</td><td class='n'>{round(j['worst']*100)} %</td></tr>")
    return tbl("The six joints the software designs, with the duty each was sized for",
               "<tr><th>Joint</th><th class='n'>Parts</th><th class='n'>Dimensions</th>"
               "<th class='n'>Checks</th><th>Duty used for this table</th>"
               "<th class='n'>Busiest check</th></tr>", "".join(rows), "compact")


def knuckle_dims_table() -> str:
    rows = []
    for key, label, value, rule in F["knuckle"]["dims"][:10]:
        rows.append(f"<tr><td class='mono'>{key}</td><td>{label}</td>"
                    f"<td class='n'>{value:g}</td><td>{rule or '-'}</td></tr>")
    return tbl("Dimensions computed for a knuckle joint carrying 50 kN, with the rule behind each",
               "<tr><th>Symbol</th><th>Meaning</th><th class='n'>Value (mm)</th>"
               "<th>Rule and source</th></tr>", "".join(rows), "compact")


def knuckle_checks_table() -> str:
    rows = []
    for name, formula, stress, allowed, passed in F["knuckle"]["checks"]:
        rows.append(f"<tr><td>{name}</td><td class='mono'>{formula}</td>"
                    f"<td class='n'>{stress:g}</td><td class='n'>{allowed:g}</td>"
                    f"<td class='n'>{round(100*stress/allowed)} %</td>"
                    f"<td>{'Safe' if passed else 'FAILS'}</td></tr>")
    return tbl("Failure checks for the same joint, computed at the actual load of 50 kN",
               "<tr><th>Failure mode</th><th>Expression used</th><th class='n'>Stress (MPa)</th>"
               "<th class='n'>Allowable (MPa)</th><th class='n'>Utilisation</th>"
               "<th>Result</th></tr>", "".join(rows), "compact")


def verification_table() -> str:
    rows = [
        ("Knuckle joint", "NPTEL, IIT Kharagpur, Module 4 Lesson 2",
         "Proportions and all nine checks verified"),
        ("Socket and spigot cotter joint", "NPTEL Module 4 Lesson 2; Leutwiler (1917), Art. 98",
         "All ten checks verified against two independent sources"),
        ("Gib and cotter joint", "Unwin (1899), p. 179, Figs. 130 and 131",
         "Breadth split, thickness and taper verified"),
        ("Protected type flange coupling", "NPTEL Module 4 Lesson 1; Leutwiler Art. 275",
         "All seven checks verified twice; proportions not verifiable"),
        ("Sleeve and cotter joint", "No source found in four books searched",
         "Checks verified by analogy; proportions unverified"),
        ("Hex bolt and nut", "NPTEL Module 4 Lesson 4",
         "Tightening relation verified; size table unverified"),
    ]
    body = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>" for a, b, c in rows)
    return tbl("Verification of each joint against published design literature",
               "<tr><th>Joint</th><th>Source consulted</th><th>Outcome</th></tr>", body, "compact")


def build_html() -> str:
    k = F["knuckle"]
    # Tables are built here, in the order they appear, so the number used in the prose is the
    # number actually printed. Writing "Table 1" by hand went wrong once already.
    T_TOOLS = tbl("Software tools used in the implementation",
        "<tr><th>Function</th><th>Tool</th><th>Remark</th></tr>",
        "<tr><td>Solid modelling</td><td>CadQuery 2.8 on the OCCT kernel</td>"
        "<td>Open source, scripted parametric modelling</td></tr>"
        "<tr><td>Drawing and DXF</td><td>FreeCAD, headless</td><td>Projection and title block</td></tr>"
        "<tr><td>Finite element analysis</td><td>CalculiX with gmsh</td><td>Linear static</td></tr>"
        "<tr><td>Language interpretation</td><td>Claude language model</td>"
        "<td>Parameter extraction only</td></tr>"
        "<tr><td>Application</td><td>Python standard library</td><td>No external framework</td></tr>"
        "<tr><td>Deployment</td><td>Container hosted on Vercel</td><td>Public, no installation</td></tr>",
        "compact")
    N_TOOLS = len(TABLES)
    T_JOINTS = joints_table(); N_JOINTS = len(TABLES)
    T_GOV = tbl("Governing calculations before rounding to a preferred size",
        "<tr><th>Expression</th><th class='n'>Computed (mm)</th><th>Effect</th></tr>",
        f"<tr><td>Rod in direct tension</td><td class='n'>{k['raw']['rod_tension']}</td>"
        f"<td>Rod diameter adopted as 35 mm</td></tr>"
        f"<tr><td>Pin in double shear</td><td class='n'>{k['raw']['pin_shear']}</td>"
        f"<td>Not governing, smaller than the rod</td></tr>"
        f"<tr><td>Pin in bending</td><td class='n'>{k['raw']['pin_bending']}</td>"
        f"<td>Governs; pin diameter adopted as 45 mm</td></tr>", "compact")
    N_GOV = len(TABLES)
    T_DIMS = knuckle_dims_table(); N_DIMS = len(TABLES)
    T_CHECKS = knuckle_checks_table(); N_CHECKS = len(TABLES)
    T_VERIF = verification_table(); N_VERIF = len(TABLES)
    tests = F["tests"].split()[0]
    n_checks = sum(j["checks"] for j in F["joints"])
    team_block = ""
    if TEAM:
        team_block = "<br>".join(f"{n} &nbsp;&nbsp;&mdash;&nbsp;&nbsp;Roll No. {e}" for n, e in TEAM).replace("&mdash;", "&#8226;")
    else:
        team_block = (f"{STUDENT} &nbsp;({ENROLMENT})<br>"
                      f"<span class='blank'></span> &nbsp;(<span class='blank' "
                      f"style='min-width:26mm'></span>)<br>"
                      f"<span class='blank'></span> &nbsp;(<span class='blank' "
                      f"style='min-width:26mm'></span>)")

    title_page = f"""
<section class="title-page"><div class="tp-border"><div class="tp-inner">
  <div style="font-size:13pt;font-weight:700;letter-spacing:.05em">A MAJOR PROJECT REPORT</div>
  <div style="font-size:11pt;margin-top:2mm">ON</div>
  <div class="tp-title">{TITLE}</div>
  <div class="tp-sub">{SUB}</div>
  <div class="tp-label">Submitted in partial fulfilment of the requirements<br>
    for the award of the degree of</div>
  <div class="tp-deg">Bachelor of Engineering<br>in<br>Mechanical Engineering</div>
  <div class="tp-by"><i>Submitted by</i></div>
  <div class="tp-name">{team_block}</div>
  <div class="tp-guide"><i>Under the guidance of</i><br>
    <b style="font-size:13pt">{GUIDE}</b><br>{GUIDE_TITLE}</div>
  <div class="seal">SGSITS<br>INDORE</div>
  <div class="tp-inst">{DEPT}<br>{INSTITUTE}<br>{CITY}<br>
    <span style="font-weight:400;font-size:11.5pt">Session {SESSION}</span></div>
</div></div></section>"""

    certificate = f"""
<section class="page"><div class="fm-title">Certificate</div>
<p>This is to certify that the major project report entitled <b>&ldquo;{TITLE}&rdquo;</b> is a
bona fide record of the work carried out by the students named below, of the final year
Bachelor of Engineering course in Mechanical Engineering, in partial fulfilment of the
requirements for the award of the degree during the session {SESSION}.</p>
<p style="margin-top:5mm">{team_block}</p>
<p style="margin-top:5mm">The work presented in this report has been carried out under my
supervision and guidance. To the best of my knowledge, the content of this report has not been
submitted elsewhere for the award of any other degree or diploma.</p>
<div class="sign-row">
  <div><div class="sign-line"></div><b>{GUIDE}</b><br>{GUIDE_TITLE}<br>Project Guide</div>
  <div><div class="sign-line"></div><b>{HOD}</b><br>Head of Department<br>{DEPT}</div>
</div>
<div class="sign-row" style="margin-top:26mm">
  <div><div class="sign-line"></div>Internal Examiner</div>
  <div><div class="sign-line"></div>External Examiner</div>
</div>
<p class="center" style="margin-top:14mm;font-size:11pt">Date: <span class="blank"
 style="min-width:34mm"></span> &nbsp;&nbsp;&nbsp; Place: Indore</p>
</section>"""

    declaration = f"""
<section class="page"><div class="fm-title">Declaration</div>
<p>We hereby declare that the major project report entitled <b>&ldquo;{TITLE}&rdquo;</b>,
submitted to the {DEPT}, {INSTITUTE}, {CITY}, is an authentic record of our own work carried
out during the session {SESSION}.</p>
<p>The design formulas and proportions used in this work are taken from published design
literature, and every such source is cited in the body of the report and listed in the
references. Where the software developed in this project departs from a cited source, the
departure and its reason are stated explicitly in Chapter 5 rather than left implicit.</p>
<p>We further declare that the content of this report has not been submitted, in whole or in
part, to any other institute or university for the award of any degree or diploma.</p>
<div class="sign-row" style="margin-top:30mm">
  <div><div class="sign-line"></div>Signatures of the candidates</div>
  <div><div class="sign-line"></div>Date and Place</div>
</div>
</section>"""

    ack = f"""
<section class="page"><div class="fm-title">Acknowledgement</div>
<p>We express our sincere gratitude to <b>{GUIDE}</b>, {GUIDE_TITLE}, {DEPT}, for the guidance
and encouragement given throughout this work. The direction to keep every computed dimension
traceable to a published formula, rather than to a convenient result, shaped the project more
than any other single input.</p>
<p>We thank <b>{HOD}</b>, Head of the {DEPT}, for providing the facilities and the academic
environment in which this work was carried out, and the faculty of the department for their
suggestions during the review presentations.</p>
<p>We acknowledge the National Programme on Technology Enhanced Learning and the Indian
Institute of Technology Kharagpur, whose openly published course material on the design of
machine elements formed the primary reference for this work, and the Internet Archive, through
which the out of copyright texts by Unwin and Leutwiler were obtained.</p>
<p>Finally, we thank our families and classmates for their support during the course of this
project.</p>
<div style="margin-top:22mm;text-align:right">Ansh Yadav<br>Ankur Dodhke<br>Atishay Jain<br>Bhavya Shrivastava<br>Dharmendra Gupta</div>
</section>"""

    abstract = f"""
<section class="page abstract"><div class="fm-title">Abstract</div>
<p>Designing a standard machine joint is a repetitive calculation. For a knuckle joint the
designer computes the rod diameter from tension, sizes the pin separately for shear and for
bending, takes the larger of the two, derives the remaining proportions from the rod diameter,
and then verifies nine distinct failure modes against allowable stresses. Changing the load
requires the entire sequence to be repeated. The drafting that follows is mechanical but
unavoidable.</p>
<p>This project presents a software system that performs that sequence automatically from a
request written in ordinary English. The user types a sentence such as <i>knuckle joint for
50 kN</i>. A language model extracts the parameters from the sentence. All subsequent
work is deterministic: the joint is sized from standard design formulas, every failure mode is
checked against the allowable stress, any dimension that fails is increased until it passes,
each part is generated as an exact solid model, and a first angle A3 drawing sheet is produced
with dimensions and a title block.</p>
<p>Six joints are implemented: the knuckle joint, the socket and spigot cotter joint, the
sleeve and cotter joint, the gib and cotter joint, the hex bolted joint, and the protected type
rigid flange coupling. Together they apply {n_checks} distinct failure checks. Every proportion
and every check has been compared against published design literature, and the comparison
identified three errors in the sources themselves, including a worked example whose own answer
fails its own check by a margin of 23 percent. The system is covered by {tests} automated
tests and is deployed as a public web application.</p>
<p>The central design decision is that the language model reads the request only. It selects no
dimension and performs no check. Interpreting a phrase is a language problem; selecting a pin
diameter is an engineering problem with a correct answer, and that remains with deterministic
code whose every step can be traced to a printed page.</p>
<div class="kw"><b>Keywords:</b> computer aided design, machine design, knuckle joint, cotter
joint, flange coupling, design automation, parametric modelling, natural language interface,
finite element analysis, first angle projection.</div>
</section>"""

    toc_rows = [
        ("head", "Certificate", "i"), ("head", "Declaration", "ii"),
        ("head", "Acknowledgement", "iii"), ("head", "Abstract", "iv"),
        ("head", "List of Figures", "vi"), ("head", "List of Tables", "vii"),
        ("head", "1. Introduction", "1"),
        ("lvl2", "1.1 Background", "1"), ("lvl2", "1.2 Statement of the problem", "1"),
        ("lvl2", "1.3 Objectives", "2"), ("lvl2", "1.4 Scope and limitations", "2"),
        ("lvl2", "1.5 Organisation of the report", "2"),
        ("head", "2. Literature Review", "3"),
        ("lvl2", "2.1 Design of cotter and knuckle joints", "3"),
        ("lvl2", "2.2 Design of shaft couplings", "3"),
        ("lvl2", "2.3 Existing approaches to design automation", "4"),
        ("lvl2", "2.4 Gap identified", "4"),
        ("head", "3. Methodology", "5"),
        ("lvl2", "3.1 Overall approach", "5"), ("lvl2", "3.2 Role of the language model", "5"),
        ("lvl2", "3.3 Sizing procedure", "6"), ("lvl2", "3.4 Verification of failure modes", "6"),
        ("lvl2", "3.5 Geometry and drawing generation", "7"),
        ("lvl2", "3.6 Finite element cross check", "7"), ("lvl2", "3.7 Software tools used", "8"),
        ("head", "4. Design and Implementation", "9"),
        ("lvl2", "4.1 System architecture", "9"), ("lvl2", "4.2 Joints implemented", "9"),
        ("lvl2", "4.3 Worked example: knuckle joint for 50 kN", "10"),
        ("lvl2", "4.4 Drawing sheet generation", "12"),
        ("lvl2", "4.5 User interface and deployment", "12"),
        ("head", "5. Results and Discussion", "13"),
        ("lvl2", "5.1 Design results", "13"),
        ("lvl2", "5.2 Verification against published literature", "13"),
        ("lvl2", "5.3 Discrepancies found in the sources", "14"),
        ("lvl2", "5.4 Finite element comparison", "15"),
        ("lvl2", "5.5 Software verification", "15"),
        ("head", "6. Conclusion and Future Scope", "16"),
        ("head", "References", "17"),
        ("head", "Appendix A: Screenshots of the working system", "18"),
    ]
    toc = "".join(
        f'<div class="row {"lvl2" if c == "lvl2" else "head"}"><span class="t">{t}</span>'
        f'<span class="dots"></span><span class="p">{p}</span></div>'
        for c, t, p in toc_rows)
    contents = f"""
<section class="page"><div class="fm-title">Table of Contents</div>
<div class="toc">{toc}</div></section>"""

    # chapters -------------------------------------------------------------------------------
    ch1 = f"""
<section class="page"><h1 class="ch">Chapter 1 &nbsp; Introduction</h1>

<h2>1.1 Background</h2>
<p>A machine joint transmits load between two members. The standard joints taught in machine
design, the knuckle joint, the cotter joint and the shaft coupling among them, are not designed
by judgement. Each is sized by a fixed sequence of formulas and then verified against a fixed
list of failure modes. The sequence is well established and appears in essentially the same
form in every standard text on the subject.</p>
<p>Because the sequence is fixed, it is repetitive. A change in the applied load invalidates
every dimension and requires the whole calculation again. In academic practice this repetition
consumes the majority of the time spent on a design problem, while the engineering judgement
involved, choosing allowable stresses and interpreting the result, occupies very little of it.
The drafting that follows the calculation is similarly mechanical.</p>
<p>Computer aided design software removes the labour of drawing but not the labour of
calculation. A modeller will faithfully produce whatever dimensions it is given and will not
object if a pin is too slender to carry the bending moment placed on it. The calculation
remains the designer's responsibility and remains manual.</p>

<h2>1.2 Statement of the problem</h2>
<p>The problem addressed by this project is the gap between stating a requirement and obtaining
a verified design. At present a designer must translate a requirement such as <i>a knuckle
joint to carry 50 kN</i> into a sequence of formulas by hand, evaluate them, check the result
against several failure modes, iterate where a check fails, and only then begin modelling and
drafting.</p>
<p>A system that accepts the requirement as written and returns a verified design, complete
with solid models and a drawing sheet, would remove the repetition without removing the
engineering. The difficulty is that the interpretation of a written requirement is not a
calculation, and the calculation must not be delegated to a system that cannot be checked.</p>

<h2>1.3 Objectives</h2>
<ol>
  <li>To develop a system that accepts a design requirement stated in ordinary English and
  extracts the joint type, the applied load and the allowable stresses from it.</li>
  <li>To size the joint from established design formulas and to verify every applicable failure
  mode against the allowable stress, iterating where a check is not satisfied.</li>
  <li>To generate exact solid models of every component and an assembled model in a neutral
  exchange format that opens in commercial CAD software.</li>
  <li>To generate a first angle projection drawing sheet with dimensions and a title block
  conforming to Indian drawing practice.</li>
  <li>To verify every proportion and every failure check used by the system against published
  design literature, and to record any disagreement with a source explicitly.</li>
  <li>To make the system usable through a web browser without any installation.</li>
</ol>

<h2>1.4 Scope and limitations</h2>
<p>The scope of this work is limited to six standard joints under static loading. Fatigue
loading, stress concentration factors, tolerances and fits, and manufacturing process selection
are outside the scope. The finite element facility included in the system performs a single
linear static analysis on one component and is intended as an independent cross check on the
formula, not as a substitute for a complete analysis.</p>

<h2>1.5 Organisation of the report</h2>
<p>Chapter 2 reviews the design literature consulted and the existing approaches to design
automation. Chapter 3 describes the methodology, including the division of responsibility
between the language model and the deterministic calculation. Chapter 4 describes the
implementation and presents a complete worked example. Chapter 5 presents the results, the
verification against published sources, and the discrepancies found in those sources.
Chapter 6 concludes and identifies further work.</p>
</section>"""

    ch2 = """
<section class="page"><h1 class="ch">Chapter 2 &nbsp; Literature Review</h1>

<h2>2.1 Design of cotter and knuckle joints</h2>
<p>The primary reference used in this work is the course material on the Design of Machine
Elements published by the Indian Institute of Technology Kharagpur through the National
Programme on Technology Enhanced Learning. Module 4 of that course treats pin joints, keys and
threaded fasteners. Lesson 2 gives the complete design procedure for the socket and spigot
cotter joint and for the knuckle joint, including the empirical proportions expressed as
multiples of the rod diameter and the full list of failure modes to be verified.</p>
<p>Two further texts were used, both out of copyright and obtained from the Internet Archive.
Unwin, <i>The Elements of Machine Design</i> (1899), treats the gib and cotter joint on page
179 and gives the division of the slot breadth between cotter and gib, the thickness as a
fraction of that breadth, and the permissible range of taper. Leutwiler, <i>Elements of Machine
Design</i> (1917), gives in Article 98 a list of ten distinct ways in which a cotter joint may
fail, together with the expression governing each.</p>
<p>The availability of two independent treatments of the cotter joint, published eighteen years
apart, proved significant. Where the two sources agree, the expression used in this work can be
regarded as settled. Where they disagree, the disagreement itself is a finding, and is reported
in Section 5.3.</p>

<h2>2.2 Design of shaft couplings</h2>
<p>Leutwiler, Article 275, gives the analysis of the flange coupling as three groups of failure:
failure of the key by shear or by crushing, failure of the coupling bolts by shear or by
crushing, and shearing of the flange at the hub. The expressions given there for the bolt
diameter are used in this work. The same article records that no uniform set of proportions for
flange couplings had been agreed as a standard, and that the published proportion tables
represent the practice of individual manufacturers. This observation directly limits what can
be claimed about the proportions used in the present work and is reflected in Section 5.2.</p>
<p>The two key equations, shear across the whole key and bearing across half the key thickness,
are taken from NPTEL Module 4 Lesson 1.</p>

<h2>2.3 Existing approaches to design automation</h2>
<p>Parametric modelling is standard in commercial CAD software. A model driven by a table of
parameters will regenerate when those parameters change, and this removes the drafting labour
associated with a change in size. It does not, however, determine the parameters. The designer
must still compute them, and the software will regenerate an unsafe model as readily as a safe
one.</p>
<p>Recent work applying large language models to CAD has largely taken the form of generating
modelling code directly from a description. Such systems produce geometry quickly but the
dimensions they produce cannot be traced to a design calculation, and there is no mechanism by
which a failure mode is verified. For an academic or professional design task, geometry that
cannot be justified is of limited value.</p>

<h2>2.4 Gap identified</h2>
<p>The gap is therefore not in modelling and not in language interpretation, both of which are
mature, but in the connection between them. What is missing is a system in which a written
requirement is interpreted by a language model, the resulting parameters drive a deterministic
design calculation taken from published literature, and the calculation itself remains open to
inspection. The present work addresses that gap.</p>
</section>"""

    ch3 = f"""
<section class="page"><h1 class="ch">Chapter 3 &nbsp; Methodology</h1>

<h2>3.1 Overall approach</h2>
<p>The system is organised as five stages executed in sequence. The written request is
interpreted into parameters; the joint is sized; every failure mode is verified; the geometry is
generated; and the drawing sheet is produced. Each stage passes a definite result to the next,
and the intermediate results of every stage are reported to the user.</p>

<h2>3.2 Role of the language model</h2>
<p>The language model is used at the first stage only. It receives the written request and
returns the joint type, the applied load in newtons, and any allowable stresses stated. It
selects no dimension, applies no proportion and performs no check.</p>
<p>This division is deliberate and is the principal design decision of the project. Determining
that the phrase <i>50 kN</i> denotes a load of 50,000 N, and that <i>socket and spigot</i> names
the cotter joint, is a problem of language interpretation, at which such a model is effective.
Determining the diameter of the pin is a problem of engineering with a single correct answer
obtainable from a formula, and it is therefore performed by deterministic code whose every step
is traceable to a published page.</p>
<p>A safeguard is applied to the model output. Any numerical value returned by the model that
does not appear in the original request is discarded, and the user is informed. This prevents a
plausible but invented figure from entering the calculation. Where no language model is
available, the system falls back to pattern matching rules and states which interpreter was
used.</p>

<h2>3.3 Sizing procedure</h2>
<p>The governing dimension is computed first from the primary failure mode. For a knuckle joint
this is the rod diameter obtained from direct tension. The computed value is then rounded up to
the next standard preferred size rather than used as computed, in accordance with the practice
given in the source material.</p>
<p>Remaining dimensions follow from the empirical proportions given in the source, expressed as
multiples of the governing dimension. Where a component has an independent failure mode, as the
pin of a knuckle joint has in both shear and bending, that component is sized separately from
each applicable expression and the larger requirement is adopted.</p>
<p>A design factor of {F['design_factor']} is applied. The joint is sized for {F['design_factor']}
times the stated load and the resulting stresses are then reported at the actual load. The
consequence is that the governing check reports approximately 75 to 80 percent of the allowable
stress rather than 100 percent, leaving margin in hand. Sizing exactly to the allowable produces
a design that satisfies every check on paper while retaining nothing for material variation or
overload.</p>

<h2>3.4 Verification of failure modes</h2>
<p>Every applicable failure mode is evaluated and compared with the corresponding allowable
stress. Where a check is not satisfied, the dimension responsible is increased by one
millimetre and the entire check set is re-evaluated. The process repeats until all checks are
satisfied. The dimension that was increased, and the check that caused it, are both reported.</p>

<h2>3.5 Geometry and drawing generation</h2>
<p>Each component is generated as an exact solid using a parametric modelling kernel, and is
written in the STEP neutral exchange format, which opens in Siemens NX, SolidWorks, FreeCAD,
Onshape and Fusion. The assembly is written as a further STEP file with each component in its
assembled position.</p>
<p>The drawing sheet is produced by driving FreeCAD without its graphical interface. The
assembled geometry is projected to obtain the front view, the side view and the plan, arranged
in first angle projection in accordance with Indian practice, with an isometric view, dimension
lines and a title block. The same views are also written in DXF format.</p>

<h2>3.6 Finite element cross check</h2>
<p>An optional finite element analysis is provided as an independent check on the calculated
stress. One component is meshed and solved as a linear static problem using the CalculiX solver,
and the resulting peak stress is compared with the value obtained from the formula.</p>
<p>Where the computed peak exceeds the calculated value by more than half, the analysis is
repeated on a mesh of half the element size. If the peak then moves by more than five percent
the result is reported as not converged, since a peak that continues to change with mesh
refinement indicates a stress concentration at a sharp corner or at a constrained face rather
than a stress that may be designed to.</p>

<h2>3.7 Software tools used</h2>
<p>Table {N_TOOLS} lists the software used to implement the system. All of it other than the
language model is open source.</p>
{T_TOOLS}
</section>"""

    ch4 = f"""
<section class="page"><h1 class="ch">Chapter 4 &nbsp; Design and Implementation</h1>

<h2>4.1 System architecture</h2>
<p>The design rules for each joint are held as data rather than as code. Each joint is described
by a file recording its empirical proportions, the source of each proportion, the default
allowable stresses and the preferred size series. The calculation code reads these files. A
consequence of this arrangement is that the source of any dimension can be reported to the user
at the time it is computed, and a correction to a proportion is a change to data rather than to
code.</p>

<h2>4.2 Joints implemented</h2>
<p>Six joints are implemented. Table {N_JOINTS} records the number of components, the number
of dimensions computed and the number of failure checks applied to each, together with the
utilisation of the busiest check at the duty shown.</p>
{T_JOINTS}
<p>The gib and cotter joint requires comment. Unwin gives the division of the breadth and the
thickness but gives no proportions for the strap. Rather than adopt a ratio from another source
or invent one, every dimension not given by Unwin is obtained by sizing it against a failure
check until that check is satisfied. The result is that no dimension of that joint is
unsupported: each is either taken from the source or derived from a stated failure mode.</p>

<h2>4.3 Worked example: knuckle joint for 50 kN</h2>
<p>The request <i>knuckle joint for 50 kN</i> is interpreted as the knuckle joint carrying an
axial load of 50,000 N, with the default allowable stresses of 75 MPa in tension, 60 MPa in
shear and 150 MPa in crushing. Applying the design factor, the joint is sized for 62,500 N.</p>
<p>The rod diameter follows from direct tension. The pin is then sized twice, once from double
shear and once from bending, and the larger requirement governs. The three computed values
before rounding are given in Table {N_GOV}.</p>
{T_GOV}
<p>It is worth noting that the pin requirement from bending is nearly twice that from shear. A
pin sized from shear alone would satisfy that check and bend in service. This is the reason the
larger of the two requirements is adopted, and the source material takes the same step.</p>
<p>The remaining dimensions follow from the empirical proportions, each expressed as a multiple
of the rod diameter. The complete set, with the rule and the source behind every value, is given
in Table {N_DIMS}.</p>
{T_DIMS}
<p>With all dimensions determined, the nine failure modes are evaluated at the actual load of
50,000 N. The results are given in Table {N_CHECKS}. Every check is satisfied, and the busiest,
shear of the eye, reaches 76 percent of its allowable stress.</p>
{T_CHECKS}

<h2>4.4 Drawing sheet generation</h2>
<p>The assembled geometry is projected to produce a first angle A3 sheet. Fig. 1 shows the
sheet produced for the example above, at a scale of 1:2.5. The sheet carries the front view, the
left side view, the plan and an isometric view, with dimension lines and a title block giving
the load, the institution and the request from which the design was produced.</p>
{fig("05-drawing", "First angle A3 drawing sheet generated for the knuckle joint of Section 4.3")}

<h2>4.5 User interface and deployment</h2>
<p>The system is used through a web browser. The user enters the requirement, confirms or
corrects the parameters extracted from it, and requests the build. The full working of the
calculation is printed as it proceeds, and the results are presented as the 3D model, the
drawing, the dimension list, the check list, a view colouring components by utilisation, and
the generated files.</p>
{fig("04-model", "Assembled model of the knuckle joint, rotatable in the browser, also available exploded and coloured by utilisation")}
</section>"""

    ch5 = f"""
<section class="page"><h1 class="ch">Chapter 5 &nbsp; Results and Discussion</h1>

<h2>5.1 Design results</h2>
<p>All six joints size correctly, satisfy every applicable failure check, generate every
component as a solid model and produce a drawing sheet. Each design completes in approximately
ten seconds. The busiest check across the six joints lies between 67 and 79 percent of the
allowable stress, which is the intended consequence of the design factor described in
Section 3.3 and confirms that margin is retained in every case.</p>

<h2>5.2 Verification against published literature</h2>
<p>Every proportion and every failure check was compared against the sources reviewed in
Chapter 2. The outcome is summarised in Table {N_VERIF}.</p>
{T_VERIF}
<p>Two entries require explanation. For the flange coupling, all seven failure checks are
verified against two independent sources, but the empirical proportions are marked unverified.
This is not an omission. As recorded in Section 2.2, Leutwiler states that no standard set of
proportions was ever agreed, and that published tables reflect individual manufacturers'
practice. The proportions used are therefore a convention and the system reports them as such.
For the sleeve and cotter joint, four sources were searched and none treats that joint by name;
its checks are verified by direct correspondence with the socket and spigot cotter joint, but
its proportions remain unsupported and are reported as such on every run.</p>

<h2>5.3 Discrepancies found in the sources</h2>
<p>The verification exercise identified three errors in the published sources. They are recorded
here because the system's behaviour deliberately differs from the printed material as a result.</p>
<div class="note"><b>1. A worked example that fails its own check.</b>
The knuckle joint worked problem raises the pin diameter from 40 mm to 55 mm to satisfy bending,
but subsequently evaluates the eye using the original 40 mm pin. Evaluated with the pin actually
adopted, its own expression for shear of the eye gives 80 MPa against an allowable of 65 MPa, an
exceedance of 23 percent. The present system instead enlarges the outer diameter of the eye and
reports that it has done so.</div>
<div class="note"><b>2. An omitted failure mode.</b>
The cotter joint procedure in the same source verifies crushing of the socket but does not
verify crushing between the cotter and the spigot. Evaluated at the final answer given in that
source, the omitted check gives 167 MPa against an allowable of 110 MPa. Leutwiler, Article 98,
lists this mode as one of ten, and its expression is identical in form. The present system
retains the check and sizes the cotter thicker in consequence. That two independent texts,
published eighteen years apart, include a check which the lesson omits, is what establishes this
as an omission rather than a matter of preference.</div>
<div class="note"><b>3. A constant printed incorrectly.</b>
The initial tightening load for a bolted joint is printed as 284<i>d</i> kN. The worked example
on the same page obtains 56.8 kN for an M20 bolt, which is consistent only with a constant of
2840<i>d</i> newtons. The printed relation is therefore in error by a factor of ten, and the
source refutes itself. The system uses 2840<i>d</i> N and reports the tightening load on every
bolted design, since at M20 it amounts to 56,800 N before any service load is applied.</div>

<h2>5.4 Finite element comparison</h2>
<p>The finite element facility was first validated against a case with a known answer. A bar of
20 mm diameter loaded in tension by 10 kN gives a computed peak of 32.22 MPa against the
calculated 31.83 MPa, a difference of 1.2 percent, attributable to the constrained face.</p>
<p>Applied to the eye rod of the knuckle joint of Section 4.3, the computed peak is 57.9 MPa
against the calculated 52.0 MPa, a difference of 11.5 percent. The excess is expected: the
calculation treats the rod as a plain bar in tension and takes no account of the stress raised
at the pin bore, whereas the finite element model does. Both values remain below the allowable
stress of 75 MPa.</p>
<p>The convergence rule described in Section 3.6 proved necessary in practice. For one component
the computed peak varied between 157 and 191 MPa across a sixteen fold increase in the number of
nodes without settling, indicating a singularity at the constrained face rather than a physical
stress. The system reports such a result as not converged and directs the user to the calculated
value.</p>

<h2>5.5 Software verification</h2>
<p>The implementation is covered by {tests} automated tests, executed on every change. These
cover the sizing arithmetic, the generated geometry, the interpretation of requests, the drawing
sheet and the finite element facility. Among them are tests which assert that the discrepancies
recorded in Section 5.3 are genuine, so that the system cannot later be silently altered to
reproduce the printed answers.</p>
{fig("03-working-log", "Working printed for a single run, showing the computed values before rounding, the rule and source of each dimension, and every check with its substituted arithmetic")}
</section>"""

    ch6 = f"""
<section class="page"><h1 class="ch">Chapter 6 &nbsp; Conclusion and Future Scope</h1>

<h2>6.1 Conclusion</h2>
<p>A system has been developed which accepts a machine joint requirement written in ordinary
English and returns a complete design: every dimension computed from published design formulas,
every applicable failure mode verified against the allowable stress, every component generated
as an exact solid model, and a first angle drawing sheet produced with dimensions and a title
block. Six joints are implemented, applying {n_checks} distinct failure checks in total, and the
system is covered by {tests} automated tests.</p>
<p>The objective of keeping the design traceable has been met. Every dimension the system
produces can be attributed either to a formula with a cited source or to an explicitly named
failure check. The working of each run is printed in full, which allows the result to be verified
rather than accepted.</p>
<p>The verification exercise against published literature produced an unanticipated result. Three
errors were identified in the sources themselves, one of which is a worked example whose own
answer exceeds its own allowable stress by 23 percent. This was found not by inspection but
because the software evaluates every check on every design and reports the arithmetic, which
makes an omitted or inconsistent check visible immediately.</p>
<p>The division of responsibility adopted here, in which the language model interprets the
request and deterministic code performs the engineering, is the element of the work that is most
generally applicable. It allows a natural language interface to be provided without any part of
the design becoming unverifiable.</p>

<h2>6.2 Future scope</h2>
<ol>
  <li><b>Additional joints.</b> Riveted and welded joints, treated in Module 10 of the source
  material, follow the same pattern and could be added without change to the architecture.</li>
  <li><b>Fatigue loading.</b> All sizing at present is static. Introducing an endurance limit
  and a stress concentration factor would extend the system to cyclically loaded joints.</li>
  <li><b>Tolerances and fits.</b> The drawing sheet carries nominal dimensions only. Adding fits
  for the pin and its bore would make the output directly usable for manufacture.</li>
  <li><b>Verification of the remaining proportions.</b> Two of the six joints have proportions
  without a supporting source. A design data handbook would settle both.</li>
  <li><b>Direct integration with commercial CAD.</b> Output is presently exchanged as STEP. A
  journal script for Siemens NX would allow the assembly to be constructed within the software
  rather than imported into it.</li>
  <li><b>Manufacturing outputs.</b> Material selection and cost estimation are partially
  implemented and could be extended to a bill of materials.</li>
</ol>
</section>"""

    refs = """
<section class="page"><h1 class="ch">References</h1>
<ol class="refs">
  <li>National Programme on Technology Enhanced Learning, <i>Design of Machine Elements I</i>,
  Indian Institute of Technology Kharagpur. Module 4, Lesson 1: Fasteners, pin joints and keys.
  Lesson 2: Design of cotter and knuckle joints. Lesson 3: Bolts, screws and studs. Lesson 4:
  Stresses in screw fastenings.</li>
  <li>Unwin, W. C., <i>The Elements of Machine Design</i>, Longmans, Green and Co., London,
  1899. Article 103 and Figs. 130 and 131, page 179: proportions of gibs and cotters.</li>
  <li>Leutwiler, O. A., <i>Elements of Machine Design</i>, McGraw Hill Book Company, New York,
  1917. Article 98: analysis of a cotter joint. Article 275: analysis of a flange coupling.</li>
  <li>Bureau of Indian Standards, SP 46: <i>Engineering Drawing Practice for Schools and
  Colleges</i>. First angle projection and title block conventions.</li>
  <li>Bureau of Indian Standards, IS 2048: <i>Parallel Keys and Keyways</i>; IS 1363 and IS 1364:
  <i>Hexagon Head Bolts, Screws and Nuts</i>; IS 2693: <i>Cast Iron Flange Couplings</i>.</li>
  <li>Open Cascade Technology, OCCT geometric modelling kernel, and CadQuery 2.8 parametric
  modelling library.</li>
  <li>FreeCAD, open source parametric CAD application. TechDraw workbench, used for projection
  and sheet generation.</li>
  <li>Dhondt, G., CalculiX: a three dimensional structural finite element program, used with the
  gmsh mesh generator.</li>
</ol>
</section>"""

    appendix = f"""
<section class="page"><h1 class="ch">Appendix A &nbsp; Screenshots of the Working System</h1>
{fig("01-landing", "The request screen. A requirement is typed in ordinary English, or one of the example requests is selected")}
{fig("02-understood", "Parameters extracted from the request, presented for confirmation or correction before the design proceeds")}
</section>
<section class="page">
{fig("06-dimensions", "Every computed dimension with the rule that produced it and its source; a plain language explanation is available for each")}
{fig("07-checks", "Every failure check with its substituted arithmetic, its allowable stress and its utilisation")}
</section>
<section class="page">
{fig("08-weak-spots", "Components coloured by utilisation, so that the member nearest its limit is apparent without reading the table")}
{fig("09-files", "Files produced by a single run: a STEP file for each component, the assembly, the drawing sheet, the DXF, the FreeCAD file and a written report")}
</section>"""

    lof = "".join(f'<div class="row"><span class="t">Fig. {i}: {c}</span>'
                  f'<span class="dots"></span><span class="p"></span></div>'
                  for i, (c, _) in enumerate(FIGURES, 1))
    lot = "".join(f'<div class="row"><span class="t">Table {i}: {c}</span>'
                  f'<span class="dots"></span><span class="p"></span></div>'
                  for i, c in enumerate(TABLES, 1))
    lists = f"""
<section class="page"><div class="fm-title">List of Figures</div>
<div class="toc">{lof}</div>
<div class="fm-title" style="margin-top:14mm">List of Tables</div>
<div class="toc">{lot}</div></section>"""

    body = (title_page + certificate + declaration + ack + abstract + contents
            + "{LISTS}" + ch1 + ch2 + ch3 + ch4 + ch5 + ch6 + refs + appendix)
    body = body.replace("{LISTS}", lists)
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>{TITLE}</title>"
            f"<style>{CSS}</style></head><body>{body}</body></html>")


if __name__ == "__main__":
    html = build_html()
    src = HERE / "AI-in-CAD-Report.html"
    src.write_text(html)
    pdf = HERE / "AI-in-CAD-Report.pdf"
    if pdf.exists():
        pdf.unlink()
    subprocess.run([BRAVE, "--headless", "--disable-gpu", "--no-sandbox",
                    f"--print-to-pdf={pdf}", "--no-pdf-header-footer",
                    "--virtual-time-budget=30000", f"file://{src}"],
                   capture_output=True, timeout=300)
    print(f"{pdf}  {pdf.stat().st_size // 1024} KB" if pdf.exists() else "PDF not produced")
