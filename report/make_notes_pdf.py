"""Speaker notes as a printable PDF, because nothing on this Mac opens a .pptx to read them.

One block per slide: the slide number, who presents it, and what to say. Five columns of
presenters means five people need this on their phone, not inside a PowerPoint file.

    python report/make_notes_pdf.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from notes import NOTES                                    # noqa: E402

BRAVE = __import__("os").environ.get("AICAD_BROWSER", "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser")
WHO = {"ANSH": "#1f6feb", "BHAVYA": "#0e7c41", "ATISHAY": "#9a5a00",
       "DHARMENDRA": "#b02418", "ANKUR": "#6d28d9"}

CSS = """
@page{size:A4 portrait;margin:16mm 15mm}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;color:#26313f;font-size:11pt;
 line-height:1.5}
h1{font-size:20pt;color:#0a1020;margin-bottom:2mm}
.sub{color:#6b7684;font-size:10.5pt;margin-bottom:6mm}
.map{width:100%;border-collapse:collapse;font-size:10pt;margin-bottom:8mm}
.map th{text-align:left;border-bottom:1.5pt solid #0a1020;padding:2mm 3mm 2mm 0;
 font-size:8.6pt;letter-spacing:.08em;text-transform:uppercase;color:#6b7684}
.map td{padding:2mm 3mm 2mm 0;border-bottom:.6pt solid #dde4ec}
.n{display:inline-block;min-width:9mm;font-weight:800;color:#0a1020}
.blk{page-break-inside:avoid;margin-bottom:5mm;padding-left:5mm;border-left:3pt solid #dde4ec}
.blk .hd{font-size:9.4pt;letter-spacing:.09em;text-transform:uppercase;font-weight:800;
 margin-bottom:1.5mm}
.blk p{margin-bottom:2mm}
.blk.divider{opacity:.72}
"""


def build() -> None:
    rows = [("Ansh", "1 to 6", "Introduction, the team, the problem, literature review"),
            ("Bhavya", "7 to 10", "What was built, the AI decision, scope"),
            ("Atishay", "11 to 17", "Worked example and output"),
            ("Dharmendra", "18 to 21", "Verification and the three findings"),
            ("Ankur", "22 to 27", "Validation, tests, limits, timeline, conclusion")]
    table = "".join(f"<tr><td><b>{a}</b></td><td>{b}</td><td>{c}</td></tr>" for a, b, c in rows)

    blocks = []
    for n in sorted(NOTES):
        text = NOTES[n].strip()
        first = text.splitlines()[0].strip()
        who = first.split(".")[0].strip()
        colour = WHO.get(who, "#6b7684")
        body = text[len(first):].strip() or first.split(".", 1)[-1].strip()
        paras = "".join(f"<p>{ln.strip()}</p>" for ln in body.split("\n\n") if ln.strip()) \
            or f"<p>{body}</p>"
        cls = "blk divider" if "Section opener" in text else "blk"
        blocks.append(f'<div class="{cls}" style="border-left-color:{colour}">'
                      f'<div class="hd" style="color:{colour}">'
                      f'<span class="n">{n}</span> {who}</div>{paras}</div>')

    html = (f"<!doctype html><html><head><meta charset='utf-8'>"
            f"<title>Speaker notes</title><style>{CSS}</style></head><body>"
            f"<h1>Speaker notes</h1>"
            f"<div class='sub'>Strategic Application of Artificial Intelligence in CAD &middot; "
            f"{len(NOTES)} slides &middot; glance at these, do not read them out</div>"
            f"<table class='map'><tr><th>Presenter</th><th>Slides</th><th>Section</th></tr>"
            f"{table}</table>{''.join(blocks)}</body></html>")

    src = HERE / ".build" / "notes.html"
    src.parent.mkdir(exist_ok=True)
    src.write_text(html)
    out = HERE / "AI-in-CAD-Speaker-Notes.pdf"
    if out.exists():
        out.unlink()
    subprocess.run([BRAVE, "--headless", "--disable-gpu", "--no-sandbox",
                    f"--print-to-pdf={out}", "--no-pdf-header-footer",
                    "--virtual-time-budget=20000", src.resolve().as_uri()],
                   capture_output=True, timeout=200)
    print(f"{out.name}  {out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    build()
