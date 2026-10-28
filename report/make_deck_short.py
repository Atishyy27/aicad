"""Two presentations for the upload form ("Mid Term Evaluation I & II"), one per rubric:

  1  Phase I rubric  (ME46498, 50 marks):  Problem Formulation, Methodology, Initial Calculations
     and Results, Presentation Skills, Viva-Voce and Final Project Report in Soft copy
  2  Phase II rubric (ME46998, 100 marks): Final Analysis, Final Results Obtained, Conclusion and
     Future Scope, Presentation Skills and Viva-Voce, Project Report in Hard Copy

Slide titles are the rubric headings themselves. Reuses CSS, facts and helpers from make_deck.py.
(The file keeps its old name; the 29-slide master deck is make_deck.py.)

    python report/make_deck_short.py
"""
from __future__ import annotations
import subprocess
import make_deck as D

HERE = D.HERE
BUILD = D.BUILD
BRAVE = D.BRAVE
F = D.F
TEAM = D.TEAM

OUT1 = "AI-in-CAD-Presentation-1-Phase-I.pdf"
OUT2 = "AI-in-CAD-Presentation-2-Phase-II.pdf"

CODE_SNIPPET = '''def _traceable(value, text, factors=(1,)) -> bool:
    for n in _numbers_in(text):
        for f in factors:
            if abs(n * f - value) <= 0.01 * max(abs(value), 1e-9):
                return True
    return False

# used on every field the AI returns:
if not _traceable(v, text, factors):
    spec.notes.append(f"AI gave {key}={v:g}, which is not in the request; dropped")
    continue'''

CODEGEN_SNIPPET = '''# AI-written geometry for a part outside the 6-joint library, verified live:
# request: "a flat washer, 20 mm inner diameter, 40 mm outer diameter, 3 mm thick"
import cadquery as cq
result = cq.Workplane("XY").circle(20).circle(10).extrude(3).translate((0,0,-1.5))

# gate result, this run: 1 solid, valid, bbox (40.0, 40.0, 3.0) == declared (40, 40, 3)'''


def reset() -> None:
    D.S.clear()
    D.N = 0


def render(stem_html: str, out_name: str, title: str) -> None:
    html = (f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title>"
            f"<style>{D.CSS}</style></head><body>{''.join(D.S)}</body></html>")
    BUILD.mkdir(exist_ok=True)
    src = BUILD / stem_html
    src.write_text(html)
    pdf = HERE / out_name
    if pdf.exists():
        pdf.unlink()
    subprocess.run([BRAVE, "--headless", "--disable-gpu", "--no-sandbox",
                    f"--print-to-pdf={pdf}", "--no-pdf-header-footer",
                    "--virtual-time-budget=30000", f"file://{src}"],
                   capture_output=True, timeout=200)
    print(f"{pdf.name}  {pdf.stat().st_size // 1024} KB  {D.N} slides")


def title_slide(label: str) -> None:
    team_rows = "".join(f"<tr><td class='mono'>{e}</td><td>{n}</td></tr>" for e, n in TEAM)
    D.slide(f"""
      <img class="logo" src="{D.LOGO}" alt="SGSITS">
      <div class="kick">{label}</div>
      <h1>{D.TITLE}</h1>
      <div class="band">
        <div><h3>Submitted by</h3><table><tbody>{team_rows}</tbody></table></div>
        <div><h3>Guide</h3>
          <div style="font-size:13px;line-height:1.55;margin-top:4px">
            <b style="color:var(--ink)">{D.GUIDE}</b><br>{D.GUIDE_DESIG}</div></div>
      </div>
      {D.qr_block(22)}""", "title", foot=f"Live at {D.LIVE}")


def demo_slide() -> None:
    D.slide(f"""
      <div class="kick">Live demo</div>
      <h2>Try it yourself: scan, or open {D.LIVE}</h2>
      <div class="row r2" style="align-items:center">
        <div style="text-align:center"><img src="{D.QR}" style="width:62mm;height:62mm" alt="QR code, live demo"></div>
        <div class="col">
          <div class="card l"><b>Set the reader to "rules only"</b> (or "AI, else rules"). The hosted
          copy has no AI key, so "AI only" will report an error.</div>
          <div class="card"><b>Sentences that work:</b> knuckle joint for 50 kN &middot; gib and cotter
          joint for 50 kN &middot; socket and spigot joint for 35 kN &middot; flange coupling to
          transmit 20 kW at 1440 rpm.</div>
          <div class="card"><b>Change the load</b> and every dimension is recomputed, nothing is stored.</div>
        </div>
      </div>""")


def flow_row() -> str:
    return """
      <div class="flow">
        <div class="ai"><div class="n">01 &middot; AI</div><div class="t">Read</div>
          <div class="d">Sentence to joint + load. Nothing invented is kept.</div></div>
        <div><div class="n">02</div><div class="t">Size</div>
          <div class="d">Governing formula, rounded to a preferred size.</div></div>
        <div><div class="n">03</div><div class="t">Check</div>
          <div class="d">Every failure mode vs allowable; iterate on failure.</div></div>
        <div><div class="n">04</div><div class="t">Model</div>
          <div class="d">Exact solids, STEP files, assembly in position.</div></div>
        <div><div class="n">05</div><div class="t">Draw</div>
          <div class="d">First angle A3 sheet, dimensions, title block.</div></div>
      </div>"""


def joint_table() -> str:
    rows = "".join(f"<tr><td>{j['title']}</td><td class='n'>{j['parts']}</td><td class='n'>{j['checks']}</td>"
                   f"<td class='n'>{round(j['worst']*100)}</td></tr>" for j in F["joints"])
    return ("<table class='sm'><tr><th>Joint</th><th class='n'>Parts</th><th class='n'>Checks</th>"
            f"<th class='n'>Busiest, % allowable</th></tr>{rows}</table>")


def team_split() -> str:
    return ("Ansh: the problem and the literature. Bhavya: what was built and the AI/engineering "
            "boundary. Atishay: the worked example, the output and the code. Dharmendra: the "
            "verification and the three findings. Ankur: validation, limits and the close.")


# ---------------------------------------------------------------- Presentation 1 (Phase I)
def build_phase1() -> None:
    reset()
    nj = len(F["joints"])
    nchecks = sum(j["checks"] for j in F["joints"])
    k = F["knuckle"]

    title_slide("Major Project Phase I &middot; Mid Term Evaluation")

    D.slide("""
      <div class="kick">Problem Formulation</div>
      <h2>Given a requirement in plain English, produce a verified design of a standard joint</h2>
      <div class="row r2">
        <div class="col">
          <p><b>The problem.</b> A knuckle, cotter or coupling joint is sized by a fixed sequence of
          textbook formulas, then checked against a fixed list of failure modes. A change of load
          means repeating the whole sequence by hand.</p>
          <p><b>Why a modeller does not solve it.</b> Parametric CAD regenerates whatever dimensions
          it is given. It does not object if a pin is too slender to survive.</p>
          <p><b>Application and importance.</b> First-pass sizing, checking and drawing of standard
          joints for a design office or a machine design laboratory, with every number traceable to a
          page, so the result can be checked rather than trusted.</p>
        </div>
        <div class="col">
          <table class="sm"><tr><th>Literature integrated</th><th>Used for</th></tr>
            <tr><td>NPTEL IIT Kharagpur, Design of Machine Elements I, Module 4</td><td>procedure, proportions, failure modes</td></tr>
            <tr><td>Unwin, Elements of Machine Design (1899), p. 179</td><td>gib and cotter joint</td></tr>
            <tr><td>Leutwiler, Elements of Machine Design (1917), Art. 98, 275</td><td>second source; coupling</td></tr>
            <tr><td>SP 46, IS 2048, IS 1363/1364, IS 2693</td><td>drawing practice, keys, bolts, couplings</td></tr>
            <tr><td>OCCT, CadQuery, FreeCAD, CalculiX, gmsh</td><td>modelling, drawing, finite element</td></tr>
          </table>
          <div class="cap">12 references in the report, 3 of them the design sources every formula traces to.</div>
        </div>
      </div>""")

    D.slide(f"""
      <div class="kick">Methodology</div>
      <h2>Five stages; the AI reads the requirement and the engineering stays deterministic</h2>
      {flow_row()}
      <div class="row r2" style="flex:none;margin-top:7mm">
        <div class="card l"><b>Assumptions stated.</b> Static loading only. Allowable tensile 75, shear
        60, crushing 150 MPa (working values of the source). Design factor 1.25: sized for 1.25 times
        the load, checked at the real load. Computed diameters rounded up to a preferred size.</div>
        <div class="card"><b>Tools.</b> CadQuery on the OCCT kernel for solids, FreeCAD for the A3 sheet,
        CalculiX with gmsh for the finite element cross-check, a language model for reading the
        sentence only.</div>
      </div>""")

    D.slide(f"""
      <div class="kick">Methodology &middot; why the split, and the code that enforces it</div>
      <h2>The AI never picks a dimension: any number not in the request is dropped</h2>
      <div class="eq" style="white-space:pre-wrap;line-height:1.5;font-size:12px">{CODE_SNIPPET}</div>
      <p style="margin-top:5mm">Reading "50 kN" as 50,000 N is a language problem. Choosing a pin
      diameter has one correct answer from a formula, so that stays deterministic and traceable to a
      book page. Nothing anywhere is trained.</p>""")

    bars = "".join(
        f"<tr><td>{n}</td><td class='n'>{s:g}</td><td class='n'>{a:g}</td>"
        f"<td style='width:34%'><div class='bar{' hi' if s/a > .75 else ''}'><span style='width:{round(100*s/a)}%'></span></div></td>"
        f"<td class='n'>{round(100*s/a)}%</td></tr>" for n, _, s, a, _ in k["checks"])
    D.slide(f"""
      <div class="kick">Initial Calculations and Results</div>
      <h2>Worked example: a knuckle joint for 50 kN, all nine checks at the real load</h2>
      <div class="row r2">
        <div class="col">
          <table class="sm"><tr><th>Sizing, before rounding</th><th class="n">mm</th><th>Adopted</th></tr>
            <tr><td>Rod, direct tension</td><td class="n">{k['raw']['rod_tension']}</td><td>35 mm</td></tr>
            <tr><td>Pin, double shear</td><td class="n">{k['raw']['pin_shear']}</td><td>not governing</td></tr>
            <tr><td>Pin, bending</td><td class="n">{k['raw']['pin_bending']}</td><td>governs, 45 mm</td></tr>
          </table>
          <div class="card l"><b>Bending asks for 1.7 times what shear asks for.</b> A pin sized from
          shear alone would pass its own check and bend in service. The source takes the same step, and
          the source's worked example was reproduced value by value (report, Section 4.3).</div>
        </div>
        <table class="sm"><tr><th>Check</th><th class="n">MPa</th><th class="n">Allow.</th><th>Used</th><th class="n">%</th></tr>{bars}</table>
      </div>""")

    D.slide(f"""
      <div class="kick">Initial Calculations and Results &middot; all joints</div>
      <h2>{nj} fundamental joints, {nchecks} failure checks, every one satisfied</h2>
      {joint_table()}
      <div class="card" style="margin-top:7mm"><b>Why these {nj}.</b> Between them they exercise tension,
      double shear, crushing, bending and torsion. The flange coupling is sized from torque rather
      than axial load, to show the method is not limited to one kind of joint. Riveted and welded
      joints follow as the extension, on the same architecture.</div>""")

    D.slide(f"""
      <div class="kick">Presentation Skills</div>
      <h2>Five sections, five presenters, each owning what they can defend</h2>
      <p>{team_split()}</p>
      <div class="card" style="margin-top:6mm"><b>On questions.</b> Every claim traces to a file or a
      source and is said out loud if asked. Nothing is presented as more certain than it was checked
      to be.</div>""")

    D.slide(f"""
      <div class="kick">Viva-Voce and Final Project Report in Soft copy</div>
      <h2>The report is the evidence file for every answer</h2>
      <div class="kpi k4">
        <div><div class="v">50</div><div class="l">pages, department format</div></div>
        <div><div class="v">8</div><div class="l">chapters plus appendix</div></div>
        <div><div class="v">12</div><div class="l">references</div></div>
        <div><div class="v">{nchecks}</div><div class="l">checks, each with its arithmetic</div></div>
      </div>
      <div class="card l" style="margin-top:8mm"><b>Structured for questions.</b> Chapter 7 records the
      results, the verification against the sources and the three discrepancies found in them; the
      soft copy carries the figures and the live-demo QR code.</div>""")

    demo_slide()
    render("deck-phase1.html", OUT1, f"{D.TITLE}: Phase I")


# ---------------------------------------------------------------- Presentation 2 (Phase II)
def build_phase2() -> None:
    reset()
    nj = len(F["joints"])
    nchecks = sum(j["checks"] for j in F["joints"])
    tests = F["tests"].split()[0]

    title_slide("Major Project Phase II &middot; Mid Term Evaluation")

    D.slide(f"""
      <div class="kick">Where Phase I ended</div>
      <h2>A plain English requirement in, a sized, checked, modelled and drawn joint out</h2>
      {flow_row()}
      <div class="kpi k4" style="margin-top:8mm">
        <div><div class="v">{nj}</div><div class="l">joints</div></div>
        <div><div class="v">{nchecks}</div><div class="l">failure checks</div></div>
        <div><div class="v">3</div><div class="l">design sources</div></div>
        <div><div class="v">{tests}</div><div class="l">automated tests</div></div>
      </div>""")

    D.slide("""
      <div class="kick">Final Analysis</div>
      <h2>Three errors found in published design literature, each traced, not assumed</h2>
      <table class="sm">
        <tr><th>Finding</th><th>Evidence</th></tr>
        <tr><td>Knuckle eye shear: pin raised to 55&nbsp;mm for bending, eye still checked with
        the original 40&nbsp;mm pin</td><td>With the real pin: 80&nbsp;MPa vs 65 allowed, 23% over
        its own limit</td></tr>
        <tr><td>Cotter-spigot crushing never checked in the source</td>
        <td>167&nbsp;MPa vs 110 allowed at the source's own numbers; Leutwiler (1917) lists this
        mode independently, identical formula</td></tr>
        <tr><td>Bolt tightening constant printed as 284<i>d</i>&nbsp;kN</td>
        <td>Source's own M20 example only works out at 2840<i>d</i>&nbsp;N, a factor of one hundred
        out</td></tr>
      </table>
      <div class="card l" style="margin-top:7mm"><b>None found by reading.</b> All three surfaced
      because the system checks every failure mode on every run and prints the arithmetic, so a
      computed number disagreeing with a printed one was impossible to miss.</div>""")

    D.slide(f"""
      <div class="kick">Final Results Obtained</div>
      <h2>Cross-checked by an independent method, and against our own stated objectives</h2>
      {joint_table()}
      <div class="row r2" style="flex:none;margin-top:6mm">
        <div class="card"><b>Finite element validation.</b> 1.2% off a known case before trusting
        the method; 11.5% higher than the hand formula on the real eye rod, expected, because the
        formula ignores the stress concentration at the pin bore that the FEA sees directly.</div>
        <div class="card"><b>5 of 6 stated objectives met without qualification.</b> The sixth,
        opening the exported file inside NX10 itself, is verified in file structure (AP214 schema,
        4 separate solids on the gib and cotter example), not yet watched opening on a lab machine.</div>
      </div>""")

    D.slide(f"""
      <div class="kick">Final Analysis &middot; the code behind the claim</div>
      <h2>The guard that stops the AI from inventing a number</h2>
      <div class="eq" style="white-space:pre-wrap;line-height:1.5;font-size:12.5px">{CODE_SNIPPET}</div>
      <p style="margin-top:6mm">Any value the model returns that cannot be matched back to a number
      actually present in the request, after unit conversion, is dropped and reported dropped. This is
      the literal mechanism behind "the AI only reads the sentence."</p>""")

    D.slide(f"""
      <div class="kick">Final Results Obtained &middot; going deeper with AI</div>
      <h2>Where a part has no library entry, the AI writes the geometry itself, gated</h2>
      <div class="eq" style="white-space:pre-wrap;line-height:1.5;font-size:12px">{CODEGEN_SNIPPET}</div>
      <div class="row r2" style="flex:none;margin-top:6mm">
        <div class="card l"><b>Five gates before anything generated is trusted.</b> Static screen
        (only cadquery/math, no file or network calls), separate process with a time limit, exactly
        one valid solid, bounding box matching what the AI declared, every size asked for present
        within 2 percent.</div>
        <div class="card"><b>Re-run live on 16 Oct:</b> attempt 1, PASS, one valid solid, bounding box
        (40.0, 40.0, 3.0) mm against a declared (40, 40, 3), volume 2827 mm&sup3;.</div>
      </div>""")

    D.slide(f"""
      <div class="kick">Conclusion and Future Scope</div>
      <h2>What exists today, what is proposed, kept clearly apart</h2>
      <div class="row r2">
        <div class="card g"><b>Today.</b> {nj} joints, {nchecks} checks, verified against three
        published sources, an independent finite element cross-check, {tests} automated tests, a live
        web deployment.</div>
        <div class="card"><b>Semester 8, proposed, not committed.</b> Riveted and welded joints
        (same architecture), fatigue and stress concentration, tolerances and fits, the two
        unverified proportion sets, an NX journal script, a bill of materials.</div>
      </div>
      <div class="card l" style="margin-top:7mm"><b>Beyond the academic scope, as a direction, not
      a claim.</b> The same translation layer, English requirement to verified design, applies to
      any catalogue of standard mechanical parts, which is what would make an industrial tie-up or
      a product around this pipeline realistic to propose once the joint library is broad enough.</div>""")

    D.slide(f"""
      <div class="kick">Presentation Skills and Viva-Voce</div>
      <h2>Five sections, five presenters, each owning what they can defend</h2>
      <p>{team_split()}</p>
      <div class="card" style="margin-top:6mm"><b>On questions.</b> Every claim traces to a file or a
      source and is said out loud if asked. Nothing is presented as more certain than it was checked
      to be.</div>""")

    D.slide(f"""
      <div class="kick">Project Report in Hard Copy</div>
      <h2>Fifty pages in the department format, every claim traced to its source</h2>
      <div class="kpi k4">
        <div><div class="v">50</div><div class="l">pages</div></div>
        <div><div class="v">8</div><div class="l">chapters plus appendix</div></div>
        <div><div class="v">12</div><div class="l">references</div></div>
        <div><div class="v">6</div><div class="l">objectives, each assessed in Section 7.7</div></div>
      </div>
      <div class="card l" style="margin-top:8mm"><b>Built on the guide's own templates.</b> Cover,
      certificate, declaration, acknowledgement, abstract, eight chapters, references and an appendix
      of screenshots; Section 7.7 scores each stated objective against evidence.</div>""")

    demo_slide()
    render("deck-phase2.html", OUT2, f"{D.TITLE}: Phase II")


if __name__ == "__main__":
    build_phase1()
    build_phase2()
