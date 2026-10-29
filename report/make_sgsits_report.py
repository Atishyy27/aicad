"""Build the major project report to the SGSITS Mechanical Engineering format.

Follows the two documents the guide circulated:
  Guidelines for Preparation of UG Major Project Report (Mechanical Engineering) 2024-25
  Major Project Format

Implemented from those: A4; Times New Roman; 1.5 line spacing; margins top 1.00 in,
bottom 0.80 in, left 1.00 in plus 0.50 in gutter, right 1.00 in; chapter title on its own page,
right aligned, 14 pt bold upper case; sections 12 pt bold title case with decimal numbering;
table title above and figure caption below, numbered chapter-wise; running header carrying the
chapter title flushed right at 10 pt, suppressed on the first page of each chapter; footer with
the department on the left, the institute on the right and the page number centred; lower case
Roman numerals before the Introduction and Arabic numerals from it onward.

Chrome cannot produce running headers or page numbers in this mode, so each part is rendered
separately and the headers, footers and numbering are stamped on afterwards. That is also what
makes the numbering continuous across parts.

    python report/make_sgsits_report.py
"""
from __future__ import annotations

import base64
import json
import subprocess
from io import BytesIO
from pathlib import Path

import re

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

HERE = Path(__file__).parent
SHOTS = HERE / "shots"
BUILD = HERE / ".build"
BRAVE = __import__("os").environ.get("AICAD_BROWSER", "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser")
F = json.loads((HERE / "facts.json").read_text())

# Sections describing work that has not shipped are written but stay switched off. Flip a flag
# to True only once the corresponding change is live, so the report never claims more than exists.
FEATURES = {"materials": False, "drawing_v2": False, "fast_build": False}
CMP_TAB = ""   # number of the comparison table in Chapter 2, cited from Chapter 3

# ---------------------------------------------------------------- the team and the front page
# Enrolment numbers taken from the team's own presentation, which uses the full form.
# Full enrolment form: 0801ME23 followed by the roll digits, and 0801ME23D0x for the
# diploma entry. Roll digits taken from the team's own presentation.
TEAM = [
    ("0801ME231013", "Ankur Dodke"),
    ("0801ME231014", "Ansh Yadav"),
    ("0801ME231024", "Atishay Jain"),
    ("0801ME231030", "Bhavya Shrivastava"),
    ("0801ME243D02", "Dharmendra Gupta"),
]
GUIDE = "Dr. B. R. Rawal"
GUIDE_DESIG = "Professor and Head"
HOD = "Dr. B. R. Rawal"
SESSION = "2026 - 2027"
DEPT = "Department of Mechanical Engineering"
DEPT_CAPS = "DEPARTMENT OF MECHANICAL ENGINEERING"
INST = "SHRI G.S. INSTITUTE OF TECHNOLOGY AND SCIENCE, INDORE (M.P.)"
INST_SUB = "A Govt. Aided Autonomous Institute, Affiliated to RGPV, Bhopal"
FOOTER_INST = "S.G.S.I.T.S., Indore"
TITLE = "STRATEGIC APPLICATION OF ARTIFICIAL INTELLIGENCE IN CAD"
TITLE_TC = "Strategic Application of Artificial Intelligence in CAD"

FIGS: list[tuple[str, str]] = []   # (number, caption)
TABS: list[tuple[str, str]] = []

# ------------------------------------------------------------------------------------ styling

CSS = """
@page{size:A4 portrait;margin:25.4mm 25.4mm 20.3mm 38.1mm}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:#fff;color:#000;
  font-family:"Times New Roman",Times,serif;font-size:12pt;line-height:1.5;text-align:justify}
p{margin:0 0 2.5mm;text-indent:10mm}
p.noind{text-indent:0}
h2.sec{font-size:12pt;font-weight:700;margin:6mm 0 2mm;text-align:left;page-break-after:avoid}
h3.sub{font-size:12pt;font-weight:700;margin:4.5mm 0 1.5mm;text-align:left;
  page-break-after:avoid}
ul,ol{margin:0 0 2.5mm;padding-left:12mm;text-align:justify}
li{margin-bottom:1.5mm}
b{font-weight:700}

/* chapter opening page: chapter number and title only, right aligned, extra top margin */
.chapter-open{height:247mm;display:flex;flex-direction:column;align-items:flex-end;
  justify-content:flex-start;padding-top:38mm;page-break-after:always;text-align:right}
.chapter-open .no{font-size:14pt;font-weight:700;letter-spacing:.06em}
.chapter-open .ti{font-size:14pt;font-weight:700;text-transform:uppercase;margin-top:6mm;
  line-height:1.45;max-width:100%}

/* front matter */
.fm-h{font-size:20pt;font-weight:700;text-align:center;margin:0 0 8mm;letter-spacing:.02em;text-decoration:underline}
.inst-head{text-align:center;margin-bottom:6mm}
.inst-head .i1{font-size:14pt;font-weight:700;line-height:1.35}
.inst-head .i2{font-size:12pt;line-height:1.4}
.inst-head .i3{font-size:16pt;font-weight:700;margin-top:2mm}
.sess{font-size:18pt;font-weight:700;text-align:center;margin:4mm 0 8mm}
.body16{font-size:16pt;font-weight:700;line-height:1.6;text-align:justify;margin:0 8mm}
.sig14{font-size:14pt;font-weight:700}
.sig-row{display:flex;justify-content:space-between;margin-top:26mm}
.sig-row>div{width:46%;text-align:center}
.sig-line{border-top:0.8pt solid #000;margin-bottom:2mm}
.five{display:flex;justify-content:space-between;margin-top:22mm;gap:2mm}
.five>div{flex:1;text-align:center;font-size:9pt;line-height:1.35}
.five .ln{border-top:0.8pt solid #000;margin-bottom:1.5mm}
.blank{border-bottom:0.8pt dotted #444;display:inline-block;min-width:30mm}

/* cover */
.cover{height:247mm;display:flex;flex-direction:column;align-items:center;text-align:center;
  page-break-after:always}
.cv-title{font-size:18pt;font-weight:700;line-height:1.3;margin-bottom:10mm;
  text-transform:uppercase}
.cv-sub{font-size:16pt;font-style:italic;font-weight:700;line-height:1.15;margin-bottom:9mm}
.cv-sess{font-size:18pt;font-weight:700;margin-bottom:10mm}
.cv-two{display:flex;justify-content:space-between;width:100%;font-size:14pt;font-weight:700;
  text-align:left;margin-bottom:10mm}
.cv-two .r{text-align:right}
.cv-two .nm{font-weight:400;font-size:12pt;line-height:1.5}
.cv-two table td{border:none;font-size:12pt;vertical-align:top}
.cv-inst{font-size:14pt;font-weight:700;margin-top:auto;line-height:1.45}

/* contents, lists */
.toc-row{display:flex;align-items:baseline;margin-bottom:2.2mm;text-align:left}
.toc-row .t{white-space:nowrap}
.toc-row .d{flex:1;border-bottom:1px dotted #777;margin:0 2mm 1.2mm}
.toc-row .p{font-variant-numeric:tabular-nums}
.toc-row.l2{padding-left:9mm;font-size:11.5pt}
.toc-row.l1{font-weight:700}

/* tables and figures */
.tw{margin:4mm 0 5mm;page-break-inside:avoid}
.tcap{font-size:12pt;font-weight:700;text-align:center;margin-bottom:2mm;line-height:1.35}
table{width:100%;border-collapse:collapse;font-size:11pt;line-height:1.15;text-align:left}
th{border:0.8pt solid #000;padding:1.4mm 1.8mm;font-weight:700;background:#efefef;
  text-align:left}
td{border:0.8pt solid #000;padding:1.4mm 1.8mm;vertical-align:top}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
table.sm{font-size:10pt}
table.sm th,table.sm td{padding:1.1mm 1.4mm}
.mono{font-family:"Courier New",monospace;font-size:10pt}
figure{margin:5mm 0;text-align:center;page-break-inside:avoid}
figure img{max-width:100%;border:0.6pt solid #555}
figcaption{font-size:12pt;font-weight:700;margin-top:2.5mm;text-align:center;line-height:1.35}
.eqn{text-align:center;font-family:"Courier New",monospace;font-size:11pt;margin:3mm 0}
.refs{text-align:left}
.refs li{margin-bottom:3.5mm;line-height:1.15}
"""


def logo(width_mm: float = 26) -> str:
    """The institute crest, taken from the Major Project Format template itself."""
    f = HERE / "assets" / "sgsits-logo.png"
    if not f.exists():
        return ""
    b64 = base64.b64encode(f.read_bytes()).decode()
    return (f'<div style="text-align:center;margin:4mm 0">'
            f'<img src="data:image/png;base64,{b64}" style="width:{width_mm}mm" alt="SGSITS"></div>')


def qr_appendix() -> str:
    """Scannable link to the deployed system, shown at the head of the screenshots."""
    f = HERE / "assets" / "demo-qr.png"
    if not f.exists():
        return ""
    b64 = base64.b64encode(f.read_bytes()).decode()
    return (f'<div style="display:flex;align-items:center;gap:8mm;margin:2mm 0 6mm">'
            f'<img src="data:image/png;base64,{b64}" style="width:34mm;height:34mm" '
            f'alt="QR code, deployed system">'
            f'<p class="noind" style="margin:0">The system described in this report is deployed '
            f'and can be used without installation at <b>aicad-vercel.vercel.app</b>. Scan the code '
            f'or enter the address in a browser; the screenshots below were captured from it.</p></div>')


def img_src(name: str) -> str:
    f = SHOTS / f"{name}.png"
    return ("data:image/png;base64," + base64.b64encode(f.read_bytes()).decode()) if f.exists() else ""


def fig(ch, name: str, caption: str) -> str:
    src = img_src(name)
    if not src:
        return ""
    num = f"{ch}.{sum(1 for n, _ in FIGS if n.startswith(f'{ch}.')) + 1}"
    FIGS.append((num, caption))
    return (f'<figure><img src="{src}" alt="{caption}">'
            f'<figcaption>Figure {num}: {caption}</figcaption></figure>')


def tab(ch, caption: str, head: str, body: str, cls: str = "") -> tuple[str, str]:
    num = f"{ch}.{sum(1 for n, _ in TABS if n.startswith(f'{ch}.')) + 1}"
    TABS.append((num, caption))
    html = (f'<div class="tw"><div class="tcap">Table {num}: {caption}</div>'
            f'<table class="{cls}"><thead>{head}</thead><tbody>{body}</tbody></table></div>')
    return html, num


def page(html: str) -> str:
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head>" \
           f"<body>{html}</body></html>"


def render(html: str, stem: str) -> Path:
    BUILD.mkdir(exist_ok=True)
    src = BUILD / f"{stem}.html"
    src.write_text(page(html))
    out = BUILD / f"{stem}.pdf"
    if out.exists():
        out.unlink()
    subprocess.run([BRAVE, "--headless", "--disable-gpu", "--no-sandbox",
                    f"--print-to-pdf={out}", "--no-pdf-header-footer",
                    "--virtual-time-budget=30000", src.resolve().as_uri()],
                   capture_output=True, timeout=300)
    return out


def roman(n: int) -> str:
    vals = [(1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"),
            (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    out = ""
    for v, s in vals:
        while n >= v:
            out += s
            n -= v
    return out


def stamp(pdf_in: Path, marks: list[dict]) -> PdfWriter:
    """Draw the running header and the footer onto each page.

    marks[i] describes page i: {"num": printed number or None, "header": chapter title or None}.
    """
    reader = PdfReader(str(pdf_in))
    writer = PdfWriter()
    w, h = A4
    for i, pg in enumerate(reader.pages):
        m = marks[i] if i < len(marks) else {}
        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        if m.get("header"):
            c.setFont("Times-Roman", 10)
            c.drawRightString(w - 25.4 * 2.8346, h - 17 * 2.8346, m["header"])
        if m.get("num"):
            c.setFont("Times-Roman", 10)
            y = 11 * 2.8346
            c.drawString(38.1 * 2.8346, y, DEPT)
            c.drawCentredString(w / 2, y, str(m["num"]))
            c.drawRightString(w - 25.4 * 2.8346, y, FOOTER_INST)
        c.showPage()          # without this an overlay with nothing drawn has no page at all
        c.save()
        buf.seek(0)
        overlay = PdfReader(buf).pages[0]
        pg.merge_page(overlay)
        writer.add_page(pg)
    return writer


def header_for(title: str) -> str:
    """Chapter title for the running header, shortened per the guidelines."""
    words = title.split()
    if len(words) <= 5:
        return title
    return " ".join(words[:2]) + " ... " + " ".join(words[-2:])


# ------------------------------------------------------------------------------ front matter

def cover_html() -> str:
    names = "".join(
        f'<tr><td style="padding:0.6mm 0;white-space:nowrap">{e}</td>'
        f'<td style="padding:0.6mm 0 0.6mm 4mm;white-space:nowrap">{n}</td></tr>'
        for e, n in TEAM)
    names = (f'<table style="border-collapse:collapse;margin-left:auto">'
             f'<tbody>{names}</tbody></table>')
    return f"""
<div class="cover">
  <div class="cv-title">{TITLE}</div>
  {logo(30)}
  <div class="cv-sub">A Project Report Submitted to<br>
    Rajiv Gandhi Proudyogiki Vishwavidyalaya, Bhopal<br>
    towards the partial fulfillment of the degree of Bachelor of Technology<br>
    in Mechanical Engineering</div>
  <div class="cv-sess">{SESSION}</div>
  <div class="cv-two">
    <div>Supervised by:<br><span class="nm">{GUIDE}<br>{GUIDE_DESIG}<br>{DEPT}</span></div>
    <div class="r">Submitted by:<br><span class="nm">{names}</span></div>
  </div>
  <div class="cv-inst">{INST}</div>
</div>"""


def inst_head() -> str:
    return f"""<div class="inst-head"><div class="i1">{INST}</div>
      <div class="i2">{INST_SUB}</div><div class="i3">{DEPT_CAPS}</div></div>
      {logo(26)}
      <div class="sess">{SESSION}</div>"""


def recommendation_html() -> str:
    names = ", ".join(n for _, n in TEAM)
    return f"""{inst_head()}
<div class="fm-h">RECOMMENDATION</div>
<div class="body16">We are pleased to recommend that the project work entitled
<i>{TITLE_TC}</i> submitted by {names} may be accepted in partial fulfillment of the degree of
Bachelor of Technology in Mechanical Engineering of Rajiv Gandhi Proudyogiki Vishwavidyalaya,
Bhopal (M.P.) during the session {SESSION}.</div>
<div class="sig-row sig14">
  <div style="text-align:left">{GUIDE}<br>{GUIDE_DESIG}<br>{DEPT}</div>
  <div style="text-align:left">Head of Department<br>{GUIDE_DESIG}<br>{DEPT}</div>
</div>"""


def certificate_html() -> str:
    names = ", ".join(n for _, n in TEAM)
    return f"""{inst_head()}
<div class="fm-h">CERTIFICATE</div>
<div class="body16">This is to certify that the Project entitled <i>{TITLE_TC}</i> submitted by
{names} is accepted in partial fulfillment of the degree of Bachelor of Technology in Mechanical
Engineering of Rajiv Gandhi Proudyogiki Vishwavidyalaya, Bhopal during the session
{SESSION}.</div>
<div class="sig-row sig14">
  <div><div class="sig-line"></div>Internal Examiner<br>Date: <span class="blank"></span></div>
  <div><div class="sig-line"></div>External Examiner<br>Date: <span class="blank"></span></div>
</div>"""


def declaration_html() -> str:
    cols = "".join(
        f'<div><div class="ln"></div>Signature of the candidate<br>Date<br><br>'
        f'<b>{n}</b><br>{e}</div>' for e, n in TEAM)
    return f"""
<div class="fm-h">DECLARATION</div>
<p class="noind">We, the undersigned students of the final year Bachelor of Technology course in
Mechanical Engineering, {DEPT}, {INST}, declare that the project entitled
<i>{TITLE_TC}</i> is our own work conducted under the supervision of {GUIDE},
{GUIDE_DESIG}, {DEPT}, Shri G. S. Institute of Technology and Science, Indore.</p>
<p>We affirm that this work is entirely original and has not been copied from any source. All
sources consulted during the work have been duly acknowledged and cited in the references. Every
design formula and empirical proportion used in the software developed for this project is
attributed in the text to the published source from which it is taken, and every instance in
which the software departs from a cited source is stated explicitly in Chapter 7 together with
the reason for the departure.</p>
<p>We further declare that, to the best of our knowledge, this project work does not contain any
part of any work which has been submitted for the award of any degree either in this University
or in any other University or from any website without proper citation.</p>
<div class="five">{cols}</div>"""


def acknowledgement_html() -> str:
    sig = "".join(f'<div>{n}<br><span style="font-size:11pt">{e}</span></div>' for e, n in TEAM)
    return f"""
<div class="fm-h">ACKNOWLEDGEMENT</div>
<p class="noind">We express our sincere gratitude to {GUIDE}, {GUIDE_DESIG}, {DEPT}, for the
guidance and encouragement extended throughout this work. The direction to keep every computed
dimension traceable to a published formula, rather than to a convenient result, shaped this
project more than any other single input, and it is the reason the verification exercise
reported in Chapter 7 was carried out at all.</p>
<p>We thank the faculty of the {DEPT} for their observations during the review presentations,
which repeatedly sharpened the scope of the work, and the Institute for providing the facilities
and the academic environment in which the work was carried out.</p>
<p>We acknowledge the National Programme on Technology Enhanced Learning and the Indian
Institute of Technology Kharagpur, whose openly published course material on the design of
machine elements is the primary reference for this work, and the Internet Archive, through which
the out of copyright texts by Unwin and by Leutwiler were obtained.</p>
<p>Finally, we thank our families and our classmates for their support during the course of this
project.</p>
<div style="margin-top:20mm;text-align:right;line-height:1.7">{sig}
  <div style="margin-top:6mm">Date: <span class="blank"></span></div></div>"""


def abstract_html() -> str:
    n_checks = sum(j["checks"] for j in F["joints"])
    tests = F["tests"].split()[0]
    return f"""
<div class="fm-h">ABSTRACT</div>
<p class="noind">Designing a standard machine joint is a repetitive calculation. For a knuckle
joint the designer computes the rod diameter from direct tension, sizes the pin separately for
double shear and for bending, adopts the larger of the two requirements, derives the remaining
proportions from the rod diameter, and then verifies nine distinct failure modes against
allowable stresses. A change in the applied load invalidates every one of those results and
requires the entire sequence again. The drafting that follows is mechanical but unavoidable.
Computer aided design software removes the labour of drawing but not the labour of calculation:
a modeller regenerates whatever dimensions it is given and will not object if a pin is too
slender to carry the bending moment placed upon it.</p>
<p>This project presents a software system that performs the complete sequence automatically
from a requirement written in ordinary English. The user enters a sentence such as
<i>knuckle joint for 50 kN</i>. A language model extracts the parameters from that sentence. All
subsequent work is deterministic: the joint is sized from standard design formulas, each computed
diameter is rounded up to the next preferred size and each derived thickness to the next whole
millimetre, every applicable failure mode is verified
against the allowable stress, any dimension that fails is increased until it passes, every
component is generated as an exact solid model, and a first angle A3 drawing sheet is produced
with dimension lines and a title block.</p>
<p>Six joints are implemented: the knuckle joint, the socket and spigot cotter joint, the sleeve
and cotter joint, the gib and cotter joint, the hex bolted joint and the protected type rigid
flange coupling. Together they apply {n_checks} distinct failure checks. Every proportion and
every check was compared against published design literature, and the comparison identified three
errors in the sources themselves, including a worked example whose own answer exceeds its own
allowable stress by 23 percent. The implementation is covered by {tests} automated tests and is
deployed as a web application requiring no installation.</p>
<p>The central design decision is that the language model reads the requirement only. It selects
no dimension and performs no check. Interpreting a phrase is a problem of language; selecting a
pin diameter is a problem of engineering with a single correct answer, and it remains with
deterministic code whose every step can be traced to a printed page.</p>"""


# ---------------------------------------------------------------------------------- chapters

CH = [
    "Introduction",
    "Literature Review",
    "Gap Identification and Problem Formulation",
    "About the Case Study and Data Collection",
    "Analysis and Design Methodology",
    "Implementation",
    "Results and Discussion",
    "Conclusions and Scope of Future Work",
]


def chapter_open(n: int) -> str:
    return (f'<div class="chapter-open"><div class="no">CHAPTER {n}</div>'
            f'<div class="ti">{CH[n-1]}</div></div>')


def ch1() -> str:
    return """
<h2 class="sec">1.1 Background</h2>
<p class="noind">A machine joint transmits load between two members. The standard joints taught
in machine design, among them the knuckle joint, the cotter joint and the shaft coupling, are not
designed by judgement. Each is sized by a fixed sequence of formulas and then verified against a
fixed list of failure modes. The sequence is well established and appears in substantially the
same form in every standard text on the subject.</p>
<p>Because the sequence is fixed, it is repetitive. A change in the applied load invalidates
every dimension and requires the whole calculation to be performed again. In academic practice
this repetition consumes the majority of the time spent on a design problem, while the
engineering judgement involved, namely the choice of allowable stresses and the interpretation of
the result, occupies very little of it. The drafting that follows the calculation is similarly
mechanical.</p>
<p>Computer aided design software removes the labour of drawing but not the labour of
calculation. A parametric modeller will faithfully regenerate a model when its driving parameters
change, and will not object if the pin of a knuckle joint is too slender to carry the bending
moment placed upon it. Determining the parameters remains the responsibility of the designer and
remains manual.</p>

<h2 class="sec">1.2 Motivation</h2>
<p class="noind">The motivation for this work is the gap between stating a requirement and
obtaining a verified design. At present a designer must translate a requirement such as
<i>a knuckle joint to carry 50 kN</i> into a sequence of formulas by hand, evaluate them, check
the result against several failure modes, iterate wherever a check fails, and only then begin
modelling and drafting.</p>
<p>A system that accepts the requirement as written and returns a verified design, complete with
solid models and a drawing sheet, would remove the repetition without removing the engineering.
The difficulty is that interpreting a written requirement is not a calculation, while the
calculation itself must not be delegated to a mechanism that cannot be checked.</p>

<h2 class="sec">1.3 Objectives</h2>
<p class="noind">The objectives of the present work are as follows.</p>
<ol>
  <li>To develop a system that accepts a design requirement stated in ordinary English and
  extracts from it the joint type, the applied load and the allowable stresses.</li>
  <li>To size the joint using established design formulas and to verify every applicable failure
  mode against the allowable stress, iterating wherever a check is not satisfied.</li>
  <li>To generate exact solid models of every component and of the assembly in a neutral
  exchange format that opens in commercial CAD software.</li>
  <li>To generate a first angle projection drawing sheet carrying dimensions and a title block
  in conformity with Indian drawing practice.</li>
  <li>To verify every proportion and every failure check used by the system against published
  design literature, and to record any disagreement with a source explicitly.</li>
  <li>To make the system usable through a web browser without any installation.</li>
</ol>

<h2 class="sec">1.4 Scope of the Work</h2>
<p class="noind">The scope of the present work is limited to six standard joints under static
loading. Fatigue loading, stress concentration factors, tolerances and fits, and the selection of
manufacturing processes are outside the scope. The finite element facility included in the
system performs a single linear static analysis on one component and is intended as an
independent cross check on the formula rather than as a substitute for a complete analysis.</p>

<h2 class="sec">1.5 Organisation of the Report</h2>
<p class="noind">Chapter 2 reviews the design literature consulted and the existing approaches to
design automation. Chapter 3 identifies the gap and formulates the problem. Chapter 4 describes
the joints selected as case studies and the data collected for them. Chapter 5 sets out the
analysis and design methodology, including the division of responsibility between the language
model and the deterministic calculation. Chapter 6 describes the implementation. Chapter 7
presents the results, the verification against published sources and the discrepancies found in
those sources. Chapter 8 concludes and identifies the scope for further work.</p>"""


def ch2() -> str:
    global CMP_TAB
    Y, N, NS = "Yes", "No", "Not stated"
    cmp_rows = [
        ("BuildCAD AI", Y, NS, NS, NS, NS, Y),
        ("Zoo Text-to-CAD", Y, NS, NS, NS, NS, Y),
        ("CADAM (Adam)", Y, NS, NS, NS, "DXF only", N),
        ("Leo AI", Y, "Cited calculations", NS, NS, NS, NS),
        ("MITCalc", N, Y, NS, NS, "DXF insert", NS),
        ("KISSsoft", N, Y, NS, NS, NS, NS),
        ("Text2CAD (NeurIPS 2024)", Y, N, NS, NS, NS, NS),
        ("<b>Present work</b>", Y, Y, Y, Y, Y, Y),
    ]
    cmp_body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in cmp_rows)
    t_cmp, n_cmp = tab(2, "Comparison of the present work with existing tools, as stated on the "
                          "vendors' websites on 29 October 2026",
                       "<tr><th>Tool</th><th>Natural language input</th>"
                       "<th>Sizing traceable to formulas</th><th>Failure mode checks</th>"
                       "<th>Standard size rounding</th><th>2D drawing sheet</th>"
                       "<th>STEP export</th></tr>", cmp_body, "sm")
    CMP_TAB = n_cmp
    return f"""
<h2 class="sec">2.1 Design of Cotter and Knuckle Joints</h2>
<p class="noind">The primary reference used in this work is the course material on the Design of
Machine Elements published by the Indian Institute of Technology Kharagpur through the National
Programme on Technology Enhanced Learning. Module 4 of that course treats pin joints, keys and
threaded fasteners. Lesson 2 gives the complete design procedure for the socket and spigot cotter
joint and for the knuckle joint, including the empirical proportions expressed as multiples of
the rod diameter and the full list of failure modes to be verified.</p>
<p>Two further texts were used, both out of copyright and obtained from the Internet Archive.
Unwin, in <i>The Elements of Machine Design</i> of 1899, treats the gib and cotter joint on page
179 and gives the division of the slot breadth between the cotter and the gib, the thickness of
both as a fraction of that breadth, and the permissible range of taper. Leutwiler, in
<i>Elements of Machine Design</i> of 1917, gives in Article 98 a list of ten distinct ways in
which a cotter joint may fail, together with the expression governing each of them.</p>
<p>The availability of two independent treatments of the cotter joint, published eighteen years
apart, proved significant to this work. Where the two sources agree, the expression adopted here
may be regarded as settled. Where they disagree, the disagreement is itself a finding, and is
reported in Section 7.4.</p>

<h2 class="sec">2.2 Design of Shaft Couplings</h2>
<p class="noind">Leutwiler, in Article 275, presents the analysis of the flange coupling as three
groups of failure: failure of the key by shear or by crushing, failure of the coupling bolts by
shear or by crushing, and shearing of the flange at the hub. The expressions given there for the
bolt diameter are adopted in the present work.</p>
<p>The same article records that no uniform set of proportions for flange couplings had been
proposed for adoption as a standard, and that the published proportion tables represent the
practice of individual manufacturers. That observation directly limits what may be claimed about
the proportions used in the present work, and the limitation is stated in Section 7.3 rather than
passed over. The two key equations, shear across the whole key and bearing across half the key
thickness, are taken from Module 4 Lesson 1 of the same NPTEL course.</p>

<h2 class="sec">2.3 Standards Consulted</h2>
<p class="noind">Indian Standards were consulted for drawing practice and for the fasteners and
keys used in the joints implemented. SP 46 governs first angle projection and the title block.
IS 2048 covers parallel keys and keyways, IS 1363 and IS 1364 cover hexagon head bolts, screws
and nuts, and IS 2693 covers cast iron flange couplings.</p>

<h2 class="sec">2.4 Existing Approaches to Design Automation</h2>
<p class="noind">Parametric modelling is standard in commercial CAD software. A model driven by a
table of parameters regenerates when those parameters change, which removes the drafting labour
associated with a change of size. It does not, however, determine the parameters. The designer
must still compute them, and the software will regenerate an unsafe model as readily as a safe
one.</p>
<p>Recent work applying large language models to computer aided design has largely taken the form
of generating modelling code directly from a description. Such systems produce geometry quickly,
but the dimensions they produce cannot be traced to a design calculation, and there is no
mechanism by which a failure mode is verified. For an academic or a professional design task,
geometry that cannot be justified is of limited value.</p>
<p>A third group of approaches embeds engineering knowledge in expert systems and design
handbooks implemented as software. These are reliable within the range for which they were
written, but the calculation is typically hidden from the user, so a result cannot be checked
against a source without access to the implementation.</p>

<h2 class="sec">2.5 Comparison with Existing Tools</h2>
<p class="noind">Table {n_cmp} compares the present work with seven existing tools and research
systems. The entries are taken from each vendor's website, or from the published paper in the case
of Text2CAD, as stated on 29 October 2026. They record what each source claims, not what was found
by testing the tool, and an entry marked as not stated means only that the source does not state
the feature.</p>
{t_cmp}
<p>Two groups are visible. The tools that accept natural language, namely BuildCAD AI, Zoo
Text-to-CAD, CADAM and Text2CAD, generate geometry, and none of them states that a dimension is
sized from a design formula or verified against a failure mode. The tools that do carry out machine
element calculation, namely MITCalc and KISSsoft, work from form input rather than from a written
requirement. Leo AI is the nearest to the present work in that it cites its calculations, but its
output formats are not stated. No source examined states the combination of natural language
input, traceable sizing, failure checks, rounding to standard sizes and a drawing sheet.</p>"""


def ch3() -> str:
    return f"""
<h2 class="sec">3.1 Gap Identified</h2>
<p class="noind">From the review presented in Chapter 2, the gap lies neither in modelling nor in
language interpretation, both of which are mature, but in the connection between them. What is
absent is a system in which a written requirement is interpreted by a language model, the
resulting parameters drive a deterministic design calculation taken from published literature,
and the calculation itself remains open to inspection by the user. Table {CMP_TAB} shows that none
of the tools compared in Section 2.5 states all of these capabilities together.</p>
<p>Three specific deficiencies follow from this. First, parametric CAD regenerates geometry but
verifies no failure mode. Second, systems that generate modelling code from a description produce
dimensions that cannot be attributed to any formula. Third, where design calculation is
automated, the working is generally hidden, so the result must be trusted rather than checked.</p>

<h2 class="sec">3.2 Problem Formulation</h2>
<p class="noind">The problem addressed in this work is stated as follows. Given a design
requirement expressed in ordinary English, produce a complete design of the specified machine
joint such that every dimension is obtained from a published design formula or from a named
failure check, every applicable failure mode is verified against its allowable stress, the
geometry is generated in a neutral exchange format, a first angle drawing sheet is produced, and
the entire working is reported to the user in a form that permits independent verification.</p>

<h2 class="sec">3.3 Conditions the Solution Must Satisfy</h2>
<ol>
  <li>No dimension may be produced without an attributable basis, which is either a design
  formula with a cited source or an explicitly named failure check.</li>
  <li>The language model may interpret the requirement but may not select any dimension and may
  not perform any check.</li>
  <li>Any numerical value returned by the language model that does not appear in the original
  requirement must be discarded, so that an invented figure cannot enter the calculation.</li>
  <li>Every applicable failure mode must be evaluated on every run and its arithmetic reported,
  not merely its outcome.</li>
  <li>Where the empirical proportions used have no supporting source, the system must state that
  fact rather than imply a source it does not have.</li>
</ol>"""


def ch4() -> str:
    rows = "".join(
        f"<tr><td>{j['title']}</td><td class='n'>{j['parts']}</td><td class='n'>{j['dims']}</td>"
        f"<td class='n'>{j['checks']}</td><td>{j['duty']}</td></tr>" for j in F["joints"])
    t1, n1 = tab(4, "Joints selected as case studies, with the duty adopted for each",
                 "<tr><th>Joint</th><th class='n'>Components</th><th class='n'>Dimensions</th>"
                 "<th class='n'>Failure checks</th><th>Duty adopted</th></tr>", rows, "sm")
    t2, n2 = tab(4, "Allowable stresses adopted, and the sizes to which computed diameters are "
                    "rounded up",
                 "<tr><th>Quantity</th><th>Value adopted</th><th>Source</th></tr>",
                 "<tr><td>Allowable tensile stress</td><td>75 MPa</td>"
                 "<td>working value used in the source material</td></tr>"
                 "<tr><td>Allowable shear stress</td><td>60 MPa</td>"
                 "<td>working value used in the source material</td></tr>"
                 "<tr><td>Allowable crushing stress</td><td>150 MPa</td>"
                 "<td>working value used in the source material</td></tr>"
                 "<tr><td>Design factor</td><td>1.25</td>"
                 "<td>sized for 1.25 times the load, reported at the load</td></tr>"
                 "<tr><td>Preferred diameters</td>"
                 "<td>6 to 22 in steps of 2 mm, 25 to 60 in steps of 5 mm, thereafter 10 mm</td>"
                 "<td>standard shaft sizes, NPTEL Module 4 Lesson 2</td></tr>", "sm")
    return f"""
<h2 class="sec">4.1 Selection of Case Studies</h2>
<p class="noind">Six joints were selected. They were chosen because each is a standard joint with
a published design procedure, because between them they exercise every common failure mode
(tension, double shear, crushing, bending and torsion), and because they differ sufficiently in
geometry to test whether the system generalises. Table {n1} lists them.</p>
{t1}
<p>The flange coupling differs from the remaining five in that it is sized from a transmitted
torque rather than from an axial load, and in that the number of bolts varies with the shaft
diameter. It was included specifically to confirm that the system is not limited to axially
loaded joints.</p>

<h2 class="sec">4.2 Data Collected</h2>
<p class="noind">For each joint, three categories of data were collected from the sources listed
in Chapter 2: the empirical proportions expressed as multiples of the governing dimension, the
complete list of failure modes with the expression governing each, and the worked numerical
example given in the source, which was later used to verify the implementation.</p>
<p>The allowable stresses and the preferred size series adopted are given in Table {n2}. The
preferred size series is significant: the source material directs that a computed diameter be
rounded up to the next standard size rather than used as computed, and the system follows that
direction.</p>
{t2}

<h2 class="sec">4.3 Basis for Verification</h2>
<p class="noind">The worked examples given in the sources form the basis on which the
implementation was verified. For the knuckle joint and the cotter joint, the source provides a
complete numerical example with the load, the allowable stresses and every resulting dimension.
Those examples were reproduced by the system and compared value by value. The outcome of that
comparison, including the instances in which the system and the source disagree, is reported in
Chapter 7.</p>"""


def ch5() -> str:
    t1, n1 = tab(5, "Division of responsibility between the language model and the "
                    "deterministic calculation",
                 "<tr><th>Stage</th><th>Performed by</th><th>Verifiable against</th></tr>",
                 "<tr><td>Interpretation of the requirement</td><td>Language model</td>"
                 "<td>the requirement as written</td></tr>"
                 "<tr><td>Sizing of every dimension</td><td>Deterministic calculation</td>"
                 "<td>cited design formula</td></tr>"
                 "<tr><td>Verification of failure modes</td><td>Deterministic calculation</td>"
                 "<td>cited design formula</td></tr>"
                 "<tr><td>Generation of solid geometry</td><td>Modelling kernel</td>"
                 "<td>the computed dimensions</td></tr>"
                 "<tr><td>Generation of the drawing sheet</td><td>FreeCAD</td>"
                 "<td>the assembled geometry</td></tr>", "sm")
    return f"""
<h2 class="sec">5.1 Overall Approach</h2>
<p class="noind">The system is organised as five stages executed in sequence. The written
requirement is interpreted into parameters; the joint is sized; every failure mode is verified;
the geometry is generated; and the drawing sheet is produced. Each stage passes a definite result
to the next, and the intermediate result of every stage is reported to the user.</p>

<h2 class="sec">5.2 Role of the Language Model</h2>
<p class="noind">The language model is used at the first stage only. It receives the written
requirement and returns the joint type, the applied load in newtons, and any allowable stresses
stated. It selects no dimension, applies no proportion and performs no check. Table {n1} sets out
the division of responsibility.</p>
{t1}
<p>This division is deliberate and is the principal design decision of the project. Determining
that the phrase <i>50 kN</i> denotes a load of 50,000 N, and that <i>socket and spigot</i> names
the cotter joint, is a problem of language interpretation, at which such a model is effective.
Determining the diameter of the pin is a problem of engineering with a single correct answer
obtainable from a formula, and it is therefore performed by deterministic code whose every step
is traceable to a published page.</p>
<p>A safeguard is applied to the output of the model. Any numerical value it returns that does
not appear in the original requirement is discarded and the user is informed. This prevents a
plausible but invented figure from entering the calculation. Where no language model is
available, the system falls back to pattern matching rules and reports which interpreter was
used.</p>

<h2 class="sec">5.3 Sizing Procedure</h2>
<p class="noind">The governing dimension is computed first from the primary failure mode. For a
knuckle joint this is the rod diameter obtained from direct tension, given by Equation (5.1).</p>
<div class="eqn">D = &radic;( 4P / ( &pi; &sigma;<sub>t</sub> ) ) &nbsp;&nbsp;&nbsp; (5.1)</div>
<p class="noind">The computed value is then rounded up to the next standard preferred size rather
than used as computed, in accordance with the practice given in the source material.</p>
<p>Where a component has more than one independent failure mode, as the pin of a knuckle joint
has in both double shear and bending, that component is sized separately from each applicable
expression, given by Equations (5.2) and (5.3), and the larger requirement is adopted.</p>
<div class="eqn">d = &radic;( 2P / ( &pi; &tau; ) ) &nbsp;&nbsp;&nbsp; (5.2)</div>
<div class="eqn">d = [ 16P ( t<sub>1</sub>/3 + t/4 ) / ( &pi; &sigma;<sub>b</sub> ) ]<sup>1/3</sup>
  &nbsp;&nbsp;&nbsp; (5.3)</div>
<p class="noind">The remaining dimensions follow from the empirical proportions given in the
source, expressed as multiples of the governing dimension.</p>

<h2 class="sec">5.4 Design Factor</h2>
<p class="noind">A design factor of 1.25 is applied. The joint is sized for 1.25 times the stated
load, and the resulting stresses are then reported at the actual load. The consequence is that
the governing check reports approximately 75 to 80 percent of the allowable stress rather than
100 percent, so that margin remains in hand. Sizing exactly to the allowable produces a design
that satisfies every check on paper while retaining nothing for material variation or for
overload.</p>

<h2 class="sec">5.5 Verification of Failure Modes</h2>
<p class="noind">Every applicable failure mode is evaluated and compared with the corresponding
allowable stress. Where a check is not satisfied, the dimension responsible is increased by one
millimetre and the entire check set is evaluated again. The process repeats until all checks are
satisfied. The dimension that was increased, and the check that caused the increase, are both
reported to the user.</p>

<h2 class="sec">5.6 Generation of Geometry and Drawings</h2>
<p class="noind">Each component is generated as an exact solid using a parametric modelling
kernel and is written in the STEP neutral exchange format, which opens in Siemens NX, SolidWorks,
FreeCAD, Onshape and Fusion. The assembly is written as a further STEP file with each component
in its assembled position.</p>
<p>The drawing sheet is produced by driving FreeCAD without its graphical interface. The
assembled geometry is projected to obtain the front view, the left side view and the plan,
arranged in first angle projection in accordance with Indian practice, together with an isometric
view, dimension lines and a title block. The same views are also written in DXF format.</p>{drawing_v2_para()}

<h2 class="sec">5.7 Finite Element Cross Check</h2>
<p class="noind">An optional finite element analysis is provided as an independent check on the
calculated stress. One component is meshed and solved as a linear static problem using the
CalculiX solver, and the resulting peak stress is compared with the value obtained from the
formula. Where the computed peak exceeds the calculated value by more than half, the analysis is
repeated on a mesh of half the element size. If the peak then moves by more than five percent the
result is reported as not converged, since a peak that continues to change with mesh refinement
indicates a stress concentration at a sharp corner or at a constrained face rather than a stress
to which a component may be designed.</p>{materials_section()}"""


def materials_section() -> str:
    """Section 5.8, rendered only when FEATURES['materials'] is on."""
    if not FEATURES["materials"]:
        return ""
    M = F.get("materials", {})
    fos = M.get("factor_of_safety")
    rows = ""
    for g in M.get("grades", []):
        cast = g["class"].endswith("iron")
        base = g.get("ultimate_mpa") if cast else g.get("yield_mpa")
        if base is None:
            continue                       # no verified property value yet: no row
        cells = (f"<td>{g['grade']}</td><td>{g['standard']}</td><td class='n'>"
                 f"{g.get('yield_mpa') if g.get('yield_mpa') is not None else '-'}</td>"
                 f"<td class='n'>{g.get('ultimate_mpa') if g.get('ultimate_mpa') is not None else '-'}</td>")
        if fos:
            t = base / fos
            cells += (f"<td class='n'>{t:.0f}</td><td class='n'>{0.5*t:.0f}</td>"
                      f"<td class='n'>{2*t:.0f}</td>")
        else:
            cells += "<td class='n'>-</td><td class='n'>-</td><td class='n'>-</td>"
        rows += f"<tr>{cells}</tr>"
    table = ref = ""
    if rows:
        table, nm = tab(5, "Material grades offered, with the allowable stresses derived from them",
                        "<tr><th>Grade</th><th>Standard</th><th class='n'>Yield, MPa</th>"
                        "<th class='n'>Ultimate, MPa</th><th class='n'>Tension, MPa</th>"
                        "<th class='n'>Shear, MPa</th><th class='n'>Crushing, MPa</th></tr>",
                        rows, "sm")
        ref = f" The property values and the resulting allowable stresses are given in Table {nm}."
    return f"""

<h2 class="sec">5.8 Material Selection</h2>
<p class="noind">The user selects the material of the joint from a list of Indian standard
grades. Three are plain carbon steels to IS 1570, namely 30C8, 40C8 and 45C8, and one is grey cast
iron to IS 210, namely FG 200.{ref}</p>
<p>For the steels the allowable tensile stress is the yield strength divided by the factor of
safety. For the cast iron it is the ultimate strength divided by the factor of safety, since grey
cast iron shows no distinct yield point. In both cases the allowable shear stress is taken as 0.5
times the allowable tensile stress and the allowable crushing stress as 2 times it. The material
chosen is passed to every failure check, so that the allowable stress in each check follows the
selected grade and not a fixed working value.</p>{table}"""


def drawing_v2_para() -> str:
    """Addition to Section 5.6, rendered only when FEATURES['drawing_v2'] is on."""
    if not FEATURES["drawing_v2"]:
        return ""
    return """
<p>The drawing sheet is further developed in the following respects. The front view is drawn as a
half sectional view, with the cut faces hatched in accordance with SP 46. Centre lines are drawn
on all axes and through all bores. Dimensions are placed on the views themselves. The taper pin of
the knuckle joint is drawn with its taper of 1 in 50. A parts list accompanies the title block and
gives, for each component, the part number, the name, the material and the quantity.</p>"""


def ch6() -> str:
    t1, n1 = tab(6, "Software tools used in the implementation",
                 "<tr><th>Function</th><th>Tool</th><th>Remark</th></tr>",
                 "<tr><td>Solid modelling</td><td>CadQuery 2.8 on the OCCT kernel</td>"
                 "<td>open source, scripted parametric modelling</td></tr>"
                 "<tr><td>Drawing sheet and DXF</td><td>FreeCAD, without its interface</td>"
                 "<td>projection, dimensioning and title block</td></tr>"
                 "<tr><td>Finite element analysis</td><td>CalculiX with gmsh</td>"
                 "<td>linear static, single component</td></tr>"
                 "<tr><td>Interpretation of the requirement</td><td>Claude language model</td>"
                 "<td>parameter extraction only</td></tr>"
                 "<tr><td>Application</td><td>Python standard library</td>"
                 "<td>no external web framework</td></tr>"
                 "<tr><td>Deployment</td><td>container on a public host</td>"
                 "<td>no installation required of the user</td></tr>", "sm")
    return f"""
<h2 class="sec">6.1 System Architecture</h2>
<p class="noind">The design rules for each joint are held as data rather than as code. Each joint
is described by a file recording its empirical proportions, the source of each proportion, the
default allowable stresses and the preferred size series. The calculation code reads these files.
Two consequences follow. The source of any dimension can be reported to the user at the moment
it is computed, and a correction to a proportion is a change to data rather than to code.</p>

<h2 class="sec">6.2 Software Tools</h2>
<p class="noind">Table {n1} lists the tools used. All of them other than the language model are
open source.</p>
{t1}

<h2 class="sec">6.3 Implementation of the Joints</h2>
<p class="noind">Each joint is implemented as a module exposing the same interface: a sizing
function, a list of failure checks, a geometry builder and a set of dimension specifications for
the drawing sheet. Adding a joint therefore requires no change to the surrounding system, which
is what allowed the gib and cotter joint to be added after the other five were complete.</p>
<p>The gib and cotter joint requires particular comment. Unwin gives the division of the breadth
and the thickness of the gib and cotter but gives no proportions for the strap. Rather than adopt
a ratio from an unrelated source or invent one, every dimension the source does not supply is
sized against a failure check until that check is satisfied. The result is that no dimension of
that joint is unsupported: each is either taken from the source or derived from a stated failure
mode.</p>

<h2 class="sec">6.4 User Interface</h2>
<p class="noind">The system is used through a web browser. The user enters the requirement,
confirms or corrects the parameters extracted from it, and requests the build. The complete
working of the calculation is printed as it proceeds. The results are presented as the three
dimensional model, the drawing sheet, the list of dimensions, the list of checks, a view
colouring components by utilisation, and the generated files.</p>
{fig(6, "01-landing", "Entry screen of the system, showing the requirement field and the "
                      "example requirements provided")}
{fig(6, "03-working-log", "Working printed during a single run, showing the values computed "
                          "before rounding, the rule and source of each proportion, and every "
                          "check with its arithmetic substituted")}

<h2 class="sec">6.5 Verification of the Implementation</h2>
<p class="noind">The implementation is covered by {F['tests'].split()[0]} automated tests which
are executed on every change. These cover the sizing arithmetic, the generated geometry, the
interpretation of requirements, the drawing sheet and the finite element facility. Among them are
tests which assert that the discrepancies recorded in Section 7.4 are genuine, so that the system
cannot subsequently be altered to reproduce the printed answers without a test failing.</p>
<p>One class of test deserves mention because it detected an error that no dimensional check
could have detected. The geometry tests compare the solids of every pair of components and
require that no two occupy the same space. That test found a hooked gib modelled 1.25 mm inside
the strap, an error invisible in the dimension list because every individual dimension was
correct.</p>{build_time_section()}"""


def build_time_section() -> str:
    """Section 6.6, rendered only when FEATURES['fast_build'] is on."""
    if not FEATURES["fast_build"]:
        return ""
    t, nt = tab(6, "Measured time of each stage of a build",
                "<tr><th>Stage</th><th>Time</th></tr>",
                "<tr><td>Sizing and the nine failure checks</td><td>under 1 ms</td></tr>"
                "<tr><td>Five solid models</td><td>0.9 s</td></tr>"
                "<tr><td>STEP and viewer files</td><td>negligible</td></tr>"
                "<tr><td>FreeCAD drawing sheet</td><td>about 33 s of the 35 s build</td></tr>",
                "sm")
    return f"""

<h2 class="sec">6.6 Build Time</h2>
<p class="noind">The time taken by each stage of a build was measured. Table {nt} gives the
result. The calculation and the solid models take about a second between them, and the drawing
sheet produced by FreeCAD accounts for about 33 s of a 35 s build.</p>
{t}
<p>Three changes follow from this measurement. The system now returns the model and the failure
checks first and produces the drawing sheet in the background, so that the user can read the
result while the sheet is still being drawn. Identical requests are cached, so that a repeated
request does not repeat the work. The example joints offered on the entry screen are built in
advance.</p>"""


def ch7() -> str:
    k = F["knuckle"]
    n_checks = sum(j["checks"] for j in F["joints"])
    rows = "".join(
        f"<tr><td>{j['title']}</td><td class='n'>{j['parts']}</td><td class='n'>{j['checks']}</td>"
        f"<td class='n'>{round(j['worst']*100)}</td><td>all satisfied</td></tr>"
        for j in F["joints"])
    t1, n1 = tab(7, "Design results for the six joints at the duties given in Table 4.1",
                 "<tr><th>Joint</th><th class='n'>Components</th><th class='n'>Checks</th>"
                 "<th class='n'>Busiest check, percent of allowable</th><th>Outcome</th></tr>",
                 rows, "sm")
    t2, n2 = tab(7, "Governing calculations for a knuckle joint carrying 50 kN, before rounding",
                 "<tr><th>Expression</th><th class='n'>Computed, mm</th><th>Effect</th></tr>",
                 f"<tr><td>Rod in direct tension</td><td class='n'>{k['raw']['rod_tension']}</td>"
                 f"<td>rod diameter adopted as 35 mm</td></tr>"
                 f"<tr><td>Pin in double shear</td><td class='n'>{k['raw']['pin_shear']}</td>"
                 f"<td>not governing</td></tr>"
                 f"<tr><td>Pin in bending</td><td class='n'>{k['raw']['pin_bending']}</td>"
                 f"<td>governs; pin diameter adopted as 45 mm</td></tr>", "sm")
    dims = "".join(f"<tr><td class='mono'>{a}</td><td>{b}</td><td class='n'>{c:g}</td>"
                   f"<td>{(d or '-')[:150]}</td></tr>" for a, b, c, d in k["dims"][:10])
    t3, n3 = tab(7, "Dimensions computed for the knuckle joint, with the rule behind each",
                 "<tr><th>Symbol</th><th>Meaning</th><th class='n'>Value, mm</th>"
                 "<th>Rule and source</th></tr>", dims, "sm")
    checks = "".join(f"<tr><td>{n}</td><td class='mono'>{f}</td><td class='n'>{s:g}</td>"
                     f"<td class='n'>{a:g}</td><td class='n'>{round(100*s/a)}</td>"
                     f"<td>safe</td></tr>" for n, f, s, a, _ in k["checks"])
    t4, n4 = tab(7, "Failure checks for the knuckle joint, evaluated at the actual load of 50 kN",
                 "<tr><th>Failure mode</th><th>Expression</th><th class='n'>Stress, MPa</th>"
                 "<th class='n'>Allowable, MPa</th><th class='n'>Utilisation, percent</th>"
                 "<th>Result</th></tr>", checks, "sm")
    ver = ("<tr><td>Knuckle joint</td><td>NPTEL Module 4 Lesson 2</td>"
           "<td>proportions and all nine checks verified</td></tr>"
           "<tr><td>Socket and spigot cotter joint</td>"
           "<td>NPTEL Module 4 Lesson 2; Leutwiler Article 98</td>"
           "<td>all ten checks verified against two independent sources</td></tr>"
           "<tr><td>Gib and cotter joint</td><td>Unwin, page 179</td>"
           "<td>breadth division, thickness and taper verified</td></tr>"
           "<tr><td>Protected type flange coupling</td>"
           "<td>NPTEL Module 4 Lesson 1; Leutwiler Article 275</td>"
           "<td>all seven checks verified twice; proportions not verifiable</td></tr>"
           "<tr><td>Sleeve and cotter joint</td><td>four sources searched, none covers it</td>"
           "<td>checks verified by correspondence; proportions unverified</td></tr>"
           "<tr><td>Hex bolted joint</td><td>NPTEL Module 4 Lesson 4</td>"
           "<td>tightening relation verified; size table unverified</td></tr>")
    t5, n5 = tab(7, "Verification of each joint against published design literature",
                 "<tr><th>Joint</th><th>Source consulted</th><th>Outcome</th></tr>", ver, "sm")
    t6, n6 = tab(7, "Comparison of the finite element result with the calculated stress",
                 "<tr><th>Case</th><th class='n'>Calculated, MPa</th>"
                 "<th class='n'>Computed, MPa</th><th class='n'>Difference, percent</th></tr>",
                 "<tr><td>Bar of 20 mm diameter, 10 kN in tension</td><td class='n'>31.83</td>"
                 "<td class='n'>32.22</td><td class='n'>+1.2</td></tr>"
                 "<tr><td>Knuckle joint eye rod, 50 kN</td><td class='n'>52.0</td>"
                 "<td class='n'>57.9</td><td class='n'>+11.3</td></tr>", "sm")
    return f"""
<h2 class="sec">7.1 Design Results</h2>
<p class="noind">All six joints size correctly, satisfy every applicable failure check, generate
every component as a solid model and produce a drawing sheet. Each design completes in
approximately ten seconds. Table {n1} summarises the results.</p>
{t1}
<p>The busiest check across the six joints lies between 67 and 79 percent of the allowable
stress. That range is the intended consequence of the design factor described in Section 5.4 and
confirms that margin is retained in every case.</p>

<h2 class="sec">7.2 Worked Example</h2>
<p class="noind">The requirement <i>knuckle joint for 50 kN</i> is interpreted as the knuckle
joint carrying an axial load of 50,000 N with the default allowable stresses. Applying the design
factor, the joint is sized for 62,500 N. Table {n2} gives the three governing calculations.</p>
{t2}
<p>The requirement arising from bending is nearly 1.7 times that arising from shear. A pin sized
from shear alone would satisfy its own check and bend in service. This is the reason the larger
of the two requirements is adopted, and the source material takes the same step. Table {n3} gives
the complete set of dimensions with the rule and the source behind each.</p>
{t3}
<p>With all dimensions determined, the nine failure modes are evaluated at the actual load of
50,000 N. The results are given in Table {n4}. Every check is satisfied, and the busiest, shear
of the eye, reaches 76 percent of its allowable stress.</p>
{t4}
{fig(7, "05-drawing", "First angle A3 drawing sheet generated for the knuckle joint of "
                      "Section 7.2, at a scale of 1:2.5")}
{fig(7, "04-model", "Assembled model of the same joint, also available exploded and coloured "
                    "by utilisation")}

<h2 class="sec">7.3 Verification Against Published Literature</h2>
<p class="noind">Every proportion and every failure check was compared against the sources
reviewed in Chapter 2. The outcome is given in Table {n5}.</p>
{t5}
<p>Two entries require explanation. For the flange coupling, all seven failure checks are
verified against two independent sources, but the empirical proportions are marked unverified.
This is not an omission. As recorded in Section 2.2, Leutwiler states that no standard set of
proportions was ever agreed and that published tables reflect the practice of individual
manufacturers. The proportions used are therefore a convention, and the system reports them as
such on every run. For the sleeve and cotter joint, four sources were searched and none treats
that joint by name; its checks are verified by direct correspondence with the socket and spigot
cotter joint, but its proportions remain unsupported and are reported as such.</p>

<h2 class="sec">7.4 Discrepancies Found in the Sources</h2>
<p class="noind">The verification exercise identified three errors in the published sources. They
are recorded here because the behaviour of the system deliberately differs from the printed
material in consequence.</p>
<h3 class="sub">7.4.1 A Worked Example That Fails Its Own Check</h3>
<p class="noind">The knuckle joint worked problem raises the pin diameter from 40 mm to 55 mm to
satisfy bending, but subsequently evaluates the eye using the original 40 mm pin. Evaluated with
the pin actually adopted, its own expression for shear of the eye gives 80 MPa against an
allowable of 65 MPa, an exceedance of 23 percent. The present system instead enlarges the outer
diameter of the eye and reports that it has done so.</p>
<h3 class="sub">7.4.2 An Omitted Failure Mode</h3>
<p class="noind">The cotter joint procedure in the same source verifies crushing of the socket
but does not verify crushing between the cotter and the spigot. Evaluated at the final answer
given in that source, the omitted check gives 167 MPa against an allowable of 110 MPa. Leutwiler,
in Article 98, lists this mode as one of ten, and its expression is identical in form. The
present system retains the check and sizes the cotter thicker in consequence. That an independent
text, published eighteen years earlier, lists a check which the lesson omits is what establishes
this as an omission rather than a matter of preference.</p>
<h3 class="sub">7.4.3 A Constant Printed Incorrectly</h3>
<p class="noind">The initial tightening load for a bolted joint is printed as 284<i>d</i> kN. The
worked example on the same page obtains 56.8 kN for an M20 bolt, which is consistent only with a
constant of 2840<i>d</i> newtons. The printed relation is therefore in error by a factor of one hundred,
and the source refutes itself. The system uses 2840<i>d</i> N and reports the tightening load on
every bolted design, since at M20 it amounts to 56,800 N before any service load is applied.</p>

<h2 class="sec">7.5 Finite Element Comparison</h2>
<p class="noind">The finite element facility was first validated against a case with a known
answer. Table {n6} gives the comparison.</p>
{t6}
<p>The bar validates the method. The eye rod reads higher because the calculation treats the rod
as a plain bar in tension and takes no account of the stress raised at the pin bore, whereas the
finite element model does. Both values remain below the allowable stress of 75 MPa.</p>
<p>The convergence rule described in Section 5.7 proved necessary in practice. For one component
the computed peak varied between 157 and 191 MPa across a sixteen fold increase in the number of
nodes without settling, which indicates a singularity at the constrained face rather than a
physical stress. The system reports such a result as not converged and directs the user to the
calculated value.</p>
{fig(7, "08-weak-spots", "Components coloured by utilisation, so that the member nearest its "
                         "limit is apparent without reading the table")}

<h2 class="sec">7.6 Discussion</h2>
<p class="noind">The results support the approach adopted. The division of responsibility set out
in Section 5.2 allowed a natural language interface to be provided without any part of the design
becoming unverifiable, and the requirement that every check be evaluated and its arithmetic
printed is what made the three discrepancies of Section 7.4 visible. None of them was found by
inspection of the sources; all three surfaced because a number computed by the system disagreed
with a number printed in a book, and the disagreement could be traced.</p>

<h2 class="sec">7.7 Objectives Revisited</h2>
<p class="noind">Section 1.3 set out six objectives. Each is assessed against the evidence
presented above, rather than restated as met without qualification.</p>
<ol>
<li><b>Interpreting a plain English requirement.</b> Met. The language model extracts the joint
type and load, as shown in Section 5.2, and any value it returns that cannot be traced back to
the original sentence is discarded rather than used, which is the safeguard against a fabricated
input rather than a verified calculation.</li>
<li><b>Sizing and verifying against every failure mode, with iteration.</b> Met. All six joints
satisfy all {n_checks} applicable checks at the stated load, as given in Table {n1}, and the
iterative enlargement described in Section 5.5 is what makes the knuckle eye and the gib and
cotter strap pass where the source proportions alone would not.</li>
<li><b>Exact solid models in a neutral format that opens in commercial CAD software.</b>
Substantially met. Every exported assembly was inspected directly and confirmed to carry the
AUTOMOTIVE_DESIGN (AP214) schema with each component as a separate named solid rather than a
single fused body, which is the structure Siemens NX requires to recognise an assembly on
import. Opening the file inside NX itself, available only in the departmental laboratory, is the
one objective not yet confirmed by direct observation and is recorded as such rather than assumed.</li>
<li><b>A first angle drawing sheet conforming to Indian practice.</b> Met for projection and
sheet layout, as shown in Figure 7.1. Dimensioning to SP 46 tolerance and surface finish
conventions is not implemented and is listed in Section 8.2 rather than claimed here.</li>
<li><b>Verification against published literature, with disagreements recorded.</b> Met for four
of six joints, and partially met for the remaining two, exactly as tabulated in Table {n5}. The
three discrepancies of Section 7.4 are the direct product of this objective rather than a
side finding.</li>
<li><b>Browser use without installation.</b> Met. The system is deployed and reachable without a
local install, though the hosted copy runs the rule based interpreter rather than the language
model, a distinction recorded in Section 5.2 rather than left implicit.</li>
</ol>
<p>Taken together, Objectives 1, 2 and 6 are met without qualification. Objectives 3, 4 and 5 are
met in part, and the open point in each is stated above: the import into NX is not yet observed,
dimensioning to SP 46 tolerances is not implemented, and two joints remain partly unverified. Reporting that
distinction is itself a requirement of Objective 5, which calls for disagreements and open points
to be recorded explicitly rather than smoothed over.</p>"""


def ch8() -> str:
    n_checks = sum(j["checks"] for j in F["joints"])
    tests = F["tests"].split()[0]
    return f"""
<h2 class="sec">8.1 Conclusions</h2>
<p class="noind">A system has been developed which accepts a machine joint requirement written in
ordinary English and returns a complete design: every dimension computed from published design
formulas, every applicable failure mode verified against the allowable stress, every component
generated as an exact solid model, and a first angle drawing sheet produced with dimensions and a
title block. Six joints are implemented, applying {n_checks} distinct failure checks in total,
and the implementation is covered by {tests} automated tests.</p>
<p>The objective of keeping the design traceable has been met. Every dimension the system
produces can be attributed either to a formula with a cited source or to an explicitly named
failure check. The working of each run is printed in full, which allows the result to be verified
rather than accepted.</p>
<p>The verification exercise against published literature produced an unanticipated result. Three
errors were identified in the sources themselves, one of which is a worked example whose own
answer exceeds its own allowable stress by 23 percent. This was found not by inspection but
because the system evaluates every check on every design and reports the arithmetic, which makes
an omitted or inconsistent check visible immediately.</p>
<p>The division of responsibility adopted here, in which the language model interprets the
requirement and deterministic code performs the engineering, is the element of the work that is
most generally applicable beyond the six joints implemented.</p>

<h2 class="sec">8.2 Scope for Future Work</h2>
<ol>
  <li><b>Additional joints.</b> Riveted and welded joints, treated in Module 10 of the source
  material, follow the same pattern and could be added without change to the architecture.</li>
  <li><b>Fatigue loading.</b> All sizing at present is static. Introducing an endurance limit and
  a stress concentration factor would extend the system to cyclically loaded joints.</li>
  <li><b>Tolerances and fits.</b> The drawing sheet carries nominal dimensions only. Adding fits
  for the pin and its bore would make the output directly usable for manufacture.</li>
  <li><b>Verification of the remaining proportions.</b> Three of the six joints have proportions
  without a supporting source: the sleeve and cotter joint, the flange coupling and the size table
  of the hex bolted joint. A design data handbook would settle all three.</li>
  <li><b>Direct integration with commercial CAD.</b> Output is presently exchanged as STEP. A
  journal script for Siemens NX would allow the assembly to be constructed within that software
  rather than imported into it.</li>
  <li><b>Manufacturing outputs.</b> Material selection and cost estimation are partially
  implemented and could be extended to produce a bill of materials.</li>
</ol>"""


def references_html() -> str:
    return """
<div class="fm-h">REFERENCES</div>
<ol class="refs">
  <li>Indian Institute of Technology Kharagpur. Design of Machine Elements I, Module 4: Fasteners
  and Joints. National Programme on Technology Enhanced Learning; Lessons 1 to 4.</li>
  <li>Unwin WC. The Elements of Machine Design, Part I. London: Longmans, Green and Co.; 1899.
  Article 103 and Figures 130 and 131, page 179.</li>
  <li>Leutwiler OA. Elements of Machine Design. New York: McGraw Hill Book Company; 1917.
  Article 98, pages 122 to 124; Article 275, pages 383 to 386.</li>
  <li>IS 2048: Parallel Keys and Keyways. New Delhi: Bureau of Indian Standards.</li>
  <li>IS 1363 and IS 1364: Hexagon Head Bolts, Screws and Nuts. New Delhi: Bureau of Indian
  Standards.</li>
  <li>IS 2693: Cast Iron Flange Couplings. New Delhi: Bureau of Indian Standards.</li>
  <li>SP 46: Engineering Drawing Practice for Schools and Colleges. New Delhi: Bureau of Indian
  Standards.</li>
  <li>Open Cascade SAS. Open CASCADE Technology geometric modelling kernel.
  &lt;https://dev.opencascade.org/&gt; (Accessed on September 20, 2026).</li>
  <li>CadQuery Developers. CadQuery 2.8, parametric modelling library for Python.
  &lt;https://cadquery.readthedocs.io/&gt; (Accessed on September 20, 2026).</li>
  <li>FreeCAD Developers. FreeCAD, an open source parametric CAD application; TechDraw
  workbench. &lt;https://www.freecad.org/&gt; (Accessed on September 21, 2026).</li>
  <li>Dhondt G. CalculiX: A Three Dimensional Structural Finite Element Program.
  &lt;http://www.calculix.de/&gt; (Accessed on September 21, 2026).</li>
  <li>Geuzaine C, Remacle JF. Gmsh: a three dimensional finite element mesh generator with built
  in pre and post processing facilities. International Journal for Numerical Methods in
  Engineering. 2009; 79(11):1309-1331.</li>
  <li>BuildCAD AI. Text and photo to 3D model generator. &lt;https://buildcad.ai/&gt;
  (Accessed on October 29, 2026).</li>
  <li>Zoo. Text-to-CAD. &lt;https://zoo.dev/&gt; (Accessed on October 29, 2026).</li>
  <li>CADAM (Adam). Open source text to parametric OpenSCAD. &lt;https://adam.new/&gt;
  (Accessed on October 29, 2026).</li>
  <li>Leo AI. Engineering copilot. &lt;https://getleo.ai/&gt; (Accessed on October 29, 2026).</li>
  <li>MITCalc. Mechanical, industrial and technical calculations. &lt;https://mitcalc.com/&gt;
  (Accessed on October 29, 2026).</li>
  <li>KISSsoft. Software for the sizing and analysis of machine elements.
  &lt;https://www.kisssoft.com/&gt; (Accessed on October 29, 2026).</li>
  <li>Khan MS, Sinha S, Uddin T, Stricker D, Ali SA, Afzal MZ. Text2CAD: Generating Sequential
  CAD Models from Beginner-to-Expert Level Text Prompts. Advances in Neural Information
  Processing Systems 37 (NeurIPS 2024).</li>
</ol>"""


def page_texts(pdf: Path) -> list[str]:
    """Text of each page, used to find which page a section or a caption landed on."""
    out = []
    n = len(PdfReader(str(pdf)).pages)
    for i in range(1, n + 1):
        r = subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), str(pdf), "-"],
                           capture_output=True, text=True)
        out.append(r.stdout)
    return out


def toc_row(text: str, num: str, lvl: int = 1) -> str:
    return (f'<div class="toc-row l{lvl}"><span class="t">{text}</span>'
            f'<span class="d"></span><span class="p">{num}</span></div>')


def main() -> None:
    BUILD.mkdir(exist_ok=True)

    # 1. chapters first: their Arabic numbering does not depend on the front matter length
    chapter_bodies = [ch1(), ch2(), ch3(), ch4(), ch5(), ch6(), ch7(), ch8()]
    chapter_pdfs, chapter_pages, chapter_start = [], [], []
    page_no = 1
    for i, body in enumerate(chapter_bodies, 1):
        pdf = render(chapter_open(i) + body, f"ch{i}")
        n = len(PdfReader(str(pdf)).pages)
        chapter_pdfs.append(pdf)
        chapter_pages.append(n)
        chapter_start.append(page_no)
        page_no += n

    appendix_pdf = render(appendix_html(), "appendix")
    appendix_start, appendix_n = page_no, len(PdfReader(str(appendix_pdf)).pages)
    page_no += appendix_n
    refs_pdf = render(references_html(), "refs")
    refs_start, refs_n = page_no, len(PdfReader(str(refs_pdf)).pages)
    page_no += refs_n

    # 2. locate every numbered section, figure and table in the rendered chapters
    sec_page: dict[str, int] = {}
    item_page: dict[str, int] = {}
    for i, (pdf, body) in enumerate(zip(chapter_pdfs, chapter_bodies), 1):
        for num, title in re.findall(r'<h[23] class="(?:sec|sub)">([\d.]+)\s+([^<]+)</h[23]>', body):
            SEC_TITLES[num] = title.strip()
        pages = page_texts(pdf)
        for num, title in sorted(SEC_TITLES.items()):
            if not num.startswith(f"{i}."):
                continue
            needle = f"{num} {title}".replace("  ", " ")
            for off, txt in enumerate(pages):
                flat = " ".join(txt.split())
                if needle.lower() in flat.lower():
                    sec_page[num] = chapter_start[i - 1] + off
                    break
        for off, txt in enumerate(pages):
            g = chapter_start[i - 1] + off
            for line in txt.splitlines():
                t = line.strip()
                if t.startswith("Figure ") or t.startswith("Table "):
                    parts_ = t.split()
                    if len(parts_) > 1 and parts_[1].endswith(":"):   # captions only, not in-text mentions
                        item_page.setdefault(("F" if t[0] == "F" else "T")
                                             + parts_[1].rstrip(":"), g)

    # 3. front matter
    fm = [("cover", cover_html(), False), ("inner", cover_html(), False),
          ("recommendation", recommendation_html(), True),
          ("certificate", certificate_html(), True),
          ("declaration", declaration_html(), True),
          ("acknowledgement", acknowledgement_html(), True),
          ("abstract", abstract_html(), True)]
    fm_pdfs, fm_numbered = [], []
    for stem, html, numbered in fm:
        fm_pdfs.append(render(html, stem))
        fm_numbered.append(numbered)

    roman_no = 1
    fm_marks: list[dict] = []
    for pdf, numbered in zip(fm_pdfs, fm_numbered):
        for _ in range(len(PdfReader(str(pdf)).pages)):
            if numbered:
                fm_marks.append({"num": roman(roman_no)})
                roman_no += 1
            else:
                fm_marks.append({})

    # 4. contents and the lists, using the page numbers just measured
    rows = [toc_row("Recommendation", "i"), toc_row("Certificate", "ii"),
            toc_row("Declaration", "iii"), toc_row("Acknowledgement", "iv"),
            toc_row("Abstract", "v")]
    for i, name in enumerate(CH, 1):
        rows.append(toc_row(f"Chapter {i} &nbsp; {name}", str(chapter_start[i - 1])))
        for key in sorted((k for k in sec_page if k.startswith(f"{i}.")),
                          key=lambda s: [int(x) for x in s.split(".")]):
            rows.append(toc_row(key + " " + SEC_TITLES.get(key, ""), str(sec_page[key]), 2))
    rows.append(toc_row("Appendix A &nbsp; Screenshots of the Working System", str(appendix_start)))
    rows.append(toc_row("References", str(refs_start)))
    contents = '<div class="fm-h">TABLE OF CONTENTS</div>' + "".join(rows)

    lof = '<div class="fm-h">LIST OF FIGURES</div>' + "".join(
        toc_row(f"Figure {n}: {c}", str(item_page.get("F" + n, ""))) for n, c in FIGS)
    lot = '<div class="fm-h">LIST OF TABLES</div>' + "".join(
        toc_row(f"Table {n}: {c}", str(item_page.get("T" + n, ""))) for n, c in TABS)

    lists_pdf = render(contents + '<div style="page-break-before:always"></div>' + lof
                       + '<div style="page-break-before:always"></div>' + lot
                       + '<div style="page-break-before:always"></div>' + symbols_html(),
                       "lists")
    for _ in range(len(PdfReader(str(lists_pdf)).pages)):
        fm_marks.append({"num": roman(roman_no)})
        roman_no += 1

    # 5. stitch everything, then stamp
    merged = BUILD / "merged.pdf"
    parts = [str(p) for p in fm_pdfs] + [str(lists_pdf)] + [str(p) for p in chapter_pdfs] \
        + [str(appendix_pdf), str(refs_pdf)]
    subprocess.run(["pdfunite", *parts, str(merged)], check=True, capture_output=True)

    marks = list(fm_marks)
    for i, pdf in enumerate(chapter_pdfs, 1):
        n = len(PdfReader(str(pdf)).pages)
        head = header_for(CH[i - 1])
        for off in range(n):
            if off == 0:                      # chapter opening page: no header, no number
                marks.append({})
            else:
                marks.append({"num": chapter_start[i - 1] + off, "header": head})
    for off in range(appendix_n):
        marks.append({} if off == 0 else {"num": appendix_start + off, "header": "Appendix A"})
    for off in range(refs_n):
        marks.append({"num": refs_start + off, "header": "References"})

    writer = stamp(merged, marks)
    out = HERE / "AI-in-CAD-Major-Project-Report.pdf"
    with open(out, "wb") as f:
        writer.write(f)
    print(f"{out}  {out.stat().st_size // 1024} KB  "
          f"{len(PdfReader(str(out)).pages)} pages")


SEC_TITLES: dict[str, str] = {}


def symbols_html() -> str:
    rows = [("P", "Applied axial load", "N"), ("T", "Transmitted torque", "N mm"),
            ("D", "Rod diameter", "mm"), ("d", "Pin or spigot diameter", "mm"),
            ("d₂", "Outer diameter of the eye or socket", "mm"),
            ("t", "Thickness of the eye, or of the cotter", "mm"),
            ("t₁", "Thickness of each fork plate", "mm"),
            ("b", "Breadth of the cotter and gib", "mm"),
            ("σₜ", "Allowable tensile stress", "MPa"),
            ("σ_b", "Allowable bending stress", "MPa"),
            ("σ_c", "Allowable crushing stress", "MPa"),
            ("τ", "Allowable shear stress", "MPa")]
    body = "".join(f"<tr><td class='mono'>{a}</td><td>{b}</td><td>{c}</td></tr>"
                   for a, b, c in rows)
    abb = [("CAD", "Computer Aided Design"), ("STEP", "Standard for the Exchange of Product data"),
           ("DXF", "Drawing Exchange Format"), ("FEA", "Finite Element Analysis"),
           ("NPTEL", "National Programme on Technology Enhanced Learning"),
           ("OCCT", "Open CASCADE Technology"), ("BIS", "Bureau of Indian Standards"),
           ("MPa", "Megapascal, newton per square millimetre")]
    abody = "".join(f"<tr><td class='mono'>{a}</td><td>{b}</td></tr>" for a, b in abb)
    return (f'<div class="fm-h">LIST OF SYMBOLS</div>'
            f'<table class="sm"><thead><tr><th>Symbol</th><th>Meaning</th><th>Unit</th></tr>'
            f'</thead><tbody>{body}</tbody></table>'
            f'<div class="fm-h" style="margin-top:12mm">LIST OF ABBREVIATIONS</div>'
            f'<table class="sm"><thead><tr><th>Abbreviation</th><th>Expansion</th></tr></thead>'
            f'<tbody>{abody}</tbody></table>')


def appendix_html() -> str:
    return f"""
<div class="chapter-open"><div class="no">APPENDIX A</div>
  <div class="ti">Screenshots of the Working System</div></div>
{qr_appendix()}
{fig("A", "02-understood", "Parameters extracted from the requirement, presented for confirmation "
                         "or correction before the design proceeds")}
{fig("A", "06-dimensions", "Every computed dimension with the rule that produced it and its "
                         "source")}
{fig("A", "07-checks", "Every failure check with its substituted arithmetic, its allowable stress "
                     "and its utilisation")}
{fig("A", "09-files", "Files produced by a single run, available for download")}"""


if __name__ == "__main__":
    main()
