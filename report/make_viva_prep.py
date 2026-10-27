"""Viva prep sheet: the hardest question each presenter is likely to get, with the answer
they should give cold, no reading off a slide. Written adversarially on purpose, because the
panel went hard on this group at the Phase I evaluation and the brief this time is: it should
not happen again.

Three cross-cutting questions anyone on the panel could point at any one of the five, plus one
targeted hard question per presenter tied to their own section of the deck.

    python report/make_viva_prep.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

BRAVE = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
WHO = {"Ansh": "#1f6feb", "Bhavya": "#0e7c41", "Atishay": "#9a5a00",
       "Dharmendra": "#b02418", "Ankur": "#6d28d9"}

CROSS = [
    ("\"Did you train a model?\"",
     "No. Say it exactly like that, flat, no hedge. The language model is an off the shelf one; "
     "the only thing done to it is tell it what fields to extract and discard anything it "
     "returns that is not in the sentence. The joint is sized and checked by ordinary code "
     "written against the formulas in the three books, not by anything learned."),
    ("\"You keep saying AI, but isn't this just a rules engine with a chatbot on top?\"",
     "Push back on the word 'just'. The AI's one job, reading free text English into a load and "
     "a joint type, is genuinely a language problem a rules engine cannot do reliably across "
     "phrasing. The engineering, pin diameter, failure checks, is correctly NOT done by the "
     "model, because that has one right answer from a formula and a model would make it "
     "unverifiable. The division is the design decision, not an accident."),
    ("\"Where is the novelty? NX and SolidWorks already do parametric modelling.\"",
     "Parametric CAD regenerates whatever parameters it is given; it does not choose them and "
     "will not object to an unsafe design. The novelty here is specifically the translation "
     "layer from a one line English requirement to a verified, correctly sized model, not the "
     "solid modelling itself, which uses an existing kernel (CadQuery/OCCT) on purpose rather "
     "than reinventing one."),
]

HARD = {
    "Ansh": ("\"You cite three books for six joints. Isn't that padding, or did you actually "
             "need all three?\"",
             "No padding: NPTEL gives the full procedure for only two of the six joints. Unwin "
             "1899 is the only source that covers the gib and cotter joint at all, found after "
             "searching four books. Leutwiler is cited twice, once because it is the only book "
             "that lists crushing between cotter and spigot as a failure mode, which is exactly "
             "how we caught NPTEL omitting it. Each book earns its place by covering something "
             "the others do not."),
    "Bhavya": ("\"If the AI can misread a sentence, how is this safer than a human doing it by "
               "hand?\"",
               "It is not claimed to be infallible, it is claimed to be checkable. Any number "
               "the model returns that is not traceable to the original sentence is thrown away "
               "and the user is told, which a human making a transcription slip has no "
               "equivalent safeguard for. And a misread load produces an obviously wrong design "
               "that still gets checked against every failure mode, it does not produce a "
               "silently unsafe one."),
    "Atishay": ("\"Your knuckle pin is sized by both shear and bending, then you take the "
                "larger. How do you know bending is even the right second check, and not "
                "something you added to make the demo look more thorough?\"",
                "It is the step the source material itself takes, not an addition: the NPTEL "
                "lesson sizes the same pin on both checks and adopts the larger. The reason it "
                "matters is numeric, not stylistic: at 50 kN, bending demands 43.7 mm against "
                "shear's 25.75 mm, a pin sized on shear alone would pass its own check and still "
                "bend in service."),
    "Dharmendra": ("\"You are a final year mechanical student saying a published lesson from "
                   "IIT Kharagpur is wrong. What makes you confident enough to say that instead "
                   "of assuming you misunderstood it?\"",
                   "Confidence comes from a second, independent book agreeing, not from our own "
                   "judgement. Leutwiler 1917, written eighteen years before NPTEL even exists "
                   "as a course, lists the exact same crushing check NPTEL's worked example "
                   "omits, with an algebraically identical formula. And for the eye shear error, "
                   "the lesson's own final numbers fail its own stated allowable by 23 percent, "
                   "arithmetic anyone can redo by hand from the lesson's printed values."),
    "Ankur": ("\"Your FEA gives 11.5 percent higher stress than the hand formula on the eye rod. "
              "Doesn't that mean one of your two methods is wrong?\"",
              "No, it means they are measuring slightly different things and that is expected, "
              "stated plainly rather than hidden: the hand formula treats the rod as a plain bar "
              "in tension, the finite element model sees the actual stress concentration at the "
              "pin bore that the formula cannot represent. The control for this is the 20 mm "
              "bar validation case with no bore, which matches the formula to 1.2 percent, "
              "proving the method itself is sound before it is applied to the harder geometry."),
}

CSS = """
@page{size:A4 portrait;margin:16mm 15mm}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;color:#26313f;font-size:11pt;
 line-height:1.5}
h1{font-size:20pt;color:#0a1020;margin-bottom:2mm}
.sub{color:#6b7684;font-size:10.5pt;margin-bottom:7mm}
h2{font-size:12.5pt;color:#0a1020;margin:7mm 0 3mm}
.q{font-weight:800;color:#0a1020;margin-bottom:1.5mm}
.a{margin-bottom:4mm}
.blk{page-break-inside:avoid;margin-bottom:5mm;padding-left:5mm;border-left:3pt solid #dde4ec}
.note{background:#f3f7fc;border:1px solid #dde4ec;border-radius:8px;padding:8px 11px;
 font-size:10pt;color:#4a5564;margin-bottom:7mm}
"""


def build() -> None:
    cross_html = "".join(
        f'<div class="blk" style="border-left-color:#7a8695">'
        f'<div class="q">{q}</div><div class="a">{a}</div></div>'
        for q, a in CROSS)
    hard_html = "".join(
        f'<h2 style="color:{WHO[name]}">{name}</h2>'
        f'<div class="blk" style="border-left-color:{WHO[name]}">'
        f'<div class="q">{q}</div><div class="a">{a}</div></div>'
        for name, (q, a) in HARD.items())
    html = (f"<!doctype html><html><head><meta charset='utf-8'>"
            f"<title>Viva prep</title><style>{CSS}</style></head><body>"
            f"<h1>Viva prep: the hardest question you are likely to get</h1>"
            f"<div class='sub'>Strategic Application of Artificial Intelligence in CAD &middot; "
            f"answer these cold, do not read off a slide</div>"
            f"<div class='note'>Three questions anyone on the panel could point at any one of "
            f"you, then one question targeted at each person's own section of the deck. If the "
            f"actual question is close but not identical, give the same answer: it is built to "
            f"survive a reworded version, not a memorised one.</div>"
            f"<h2 style='color:#26313f'>Cross-cutting</h2>{cross_html}"
            f"{hard_html}</body></html>")
    src = HERE / ".build" / "viva-prep.html"
    src.parent.mkdir(exist_ok=True)
    src.write_text(html)
    out = HERE / "AI-in-CAD-Viva-Prep.pdf"
    if out.exists():
        out.unlink()
    subprocess.run([BRAVE, "--headless", "--disable-gpu", "--no-sandbox",
                    f"--print-to-pdf={out}", "--no-pdf-header-footer",
                    "--virtual-time-budget=20000", f"file://{src}"],
                   capture_output=True, timeout=200)
    print(f"{out.name}  {out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    build()
