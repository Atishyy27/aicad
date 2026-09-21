# aicad: sentence in, CAD parts out

Major project, SGSITS Mechanical, sem 7 + 8: Strategic Application of AI in CAD.

Type a request in English. The tool understands it (AI when available, plain rules
otherwise), asks for anything missing, sizes the joint with textbook design formulas,
shows every dimension and strength check, then builds the parts as exact solids plus a
first-angle A3 drawing sheet.

| joint | parts | sized from |
|---|---|---|
| Knuckle joint | single-eye rod, fork, knuckle pin, collar, taper pin | load, or rod diameter |
| Socket and spigot cotter joint | spigot, socket, cotter | load, or rod diameter |
| Sleeve and cotter joint | two rods, sleeve, two cotters | load, or rod diameter |
| Hex bolt, nut and washer | bolt, washer, nut | load, or a size like M12 (+ grip) |
| Protected type rigid flange coupling | 2 shafts, 2 flanged hubs, 2 keys, n bolts and nuts | torque, or power and speed, or shaft diameter |

Gib-and-cotter is recognised but not built: its proportions need the design book page first.

```
out/<name>/
  parts/*.step       one file per part
  assembly.step      every part in position, kept as separate bodies
  assembly.glb       same assembly for web viewers
  exploded.glb       the same parts pulled apart
  viewer.html        double-click: rotate it in any browser, works offline, Assembled/Exploded switch
  report.md          every dimension, the rule it came from, every strength check
  <joint>.FCStd      FreeCAD file: named, coloured parts + an editable drawing page   (needs FreeCAD)
  drawing.svg        A3 first-angle sheet: front, left side, plan, isometric, dimension
                     lines on the views, dimension table, title block                 (needs FreeCAD)
  drawing.dxf        the same views for AutoCAD / LibreCAD                            (needs FreeCAD)
```

## Setup (free, no GPU needed)

1. Install `uv`: https://docs.astral.sh/uv/ (Mac: `brew install uv`).
2. Optional but recommended: install FreeCAD 1.x (Mac: `brew install --cask freecad`,
   Windows: installer from freecad.org). The tool finds it by itself; if it is somewhere
   unusual, set `FREECAD_CMD` to the path of `freecadcmd`.

Mac / Linux:

```
cd ai-cad
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e ".[dev]"
```

Windows (PowerShell):

```
cd ai-cad
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -e ".[dev]"
```

## Use

```
.venv/bin/python -m aicad "knuckle joint for 50 kN"
.venv/bin/python -m aicad "I need a two tonne knuckle joint"
.venv/bin/python -m aicad "socket and spigot joint for an axial pull of 35 kN"
.venv/bin/python -m aicad "M16 nut bolt, plates 30 mm thick, load 20 kN"
.venv/bin/python -m aicad "flange coupling to transmit 20 kW at 1440 rpm"
.venv/bin/python -m aicad
```

(Windows: `.venv\Scripts\python.exe -m aicad ...`.) The last form asks you everything.

| flag | does |
|---|---|
| `--parser auto` | default: AI if available, else rules |
| `--parser rules` | offline pattern matching only, costs nothing |
| `--parser ai` | AI only; stops with an error if no AI path works |
| `--yes` | no questions; fails if something is missing |
| `--out <folder>` | where to write |
| `--no-freecad` | skip the FreeCAD file and drawing sheet |
| `--open` | open the FreeCAD file when done |
| `--model <name>` | AI model: `haiku` (default), `sonnet`, `opus`, or a full model id |

## Beyond a model library

A standard joint can be downloaded ready-made. What a download cannot do, and this tool does:

| ask | what happens |
|---|---|
| "make it 80 kN", "shear 50 MPa", "change it to a cotter joint" | redesigns, and lists every dimension that moved |
| "how much load can this take" | the most load these exact sizes carry, and the check that limits it |
| "why is the pin 45 mm" | the formula, the numbers put into it, the result, and the rule it came from |
| "make it lighter", "cheapest material" | tries each material in `aicad/data/materials.json`, keeps those that pass, picks the lightest or cheapest |
| Weak spots button in the viewer | each part coloured by how close it is to its limit: green lots of margin, red at the limit |

Follow-ups work in the web app (the Ask box under a result) and on the command line (after a build,
unless `--yes`).

## AI-written CAD (experimental)

For parts outside the library:

```
.venv/bin/python -m aicad.codegen "a flat washer, 20 mm inner diameter, 40 mm outer diameter, 3 mm thick"
```

The AI (Claude Sonnet via Claude Code by default; `AICAD_CODEGEN_MODEL` changes it) writes CadQuery code.
Nothing is shown until the code passes: an import and call screen, a run in a separate process with a
time limit, exactly one valid solid, a built size matching the size the AI declared, and every overall
size you asked for present. If it fails, the AI gets one retry with the reasons. The screen is a guard
against accidents, not a security sandbox. The checks cannot see holes, keyways or other features, so a
part can pass and still be wrong; `python -m aicad.eval_codegen` measures how often, against 6 parts
whose exact volume was worked out by hand.

Measured 20 Sep 2026 (Claude Sonnet, one attempt each unless noted):

| result | count |
|---|---|
| passed the checks and matched the hand-worked volume and size exactly | 6 of 6 |
| passed the checks but was actually wrong | 0 of 6 |
| rejected by the checks | 1 of 6 on the first run, a fault in the check itself (a keyway length read as an overall size); fixed, then it passed |

10 to 18 s per part. Six parts is a small set, and the checks cannot see features, so keep the
"passed but wrong" count honest by adding harder parts.

## Finite element check (ANSYS-lite)

```
.venv/bin/python -m aicad.fea "knuckle joint for 50 kN"
.venv/bin/python -m aicad "knuckle joint for 50 kN" --fea
```

FreeCAD ships the CalculiX solver and the gmsh mesher, so the tool can run one linear-static
analysis on one part and compare it with the textbook formula it used.

Validated on a case with a known answer: a 20 mm bar pulled by 10 kN gives 32.22 MPa against
the hand answer 31.83 MPa, a 1.2 % difference from the fixed-face effect.

On a real part (50 kN knuckle eye rod, held at the pin bore, pulled at the rod end): 55.1 MPa
against the formula's 49.1 MPa, 12 % higher, because the formula ignores the stress
concentration at the bore. Both are under the 75 MPa allowed.

**This is not ANSYS.** One part, one load case, linear elastic, boundary conditions chosen by
the tool, and stress next to a fixed face is always overstated. Treat it as a second opinion
on the formula.

## Design margin (why nothing is red any more)

By default the tool sizes for **1.25 times** the load you give, then reports the stresses at
your real load. The busiest check lands near 80 % of its allowed stress instead of 99 %.
Change it in a follow-up ("add more margin", "design factor 2") or with `design_factor`.
The colours mean: green below 80 % of the allowed stress, amber to 95 %, red above. The
allowable stress already carries a safety factor of its own.

## Indian context

- SI units throughout, first angle projection, SP 46 title block wording.
- Materials carry IS grade designations (IS 1570, IS 210, IS 733) with rupee rates per kg,
  so "cheapest material" answers in rupees.
- Each joint's data file lists the Indian standards to check it against (IS 1363/1364 bolts,
  IS 2016 washers, IS 2048 keys, IS 2693 couplings, SP 46 drawing practice). All marked to verify.

## Sharing it (Hugging Face Space)

`space/` holds a Dockerfile, a Space README and `space/deploy.md` with the three commands you
run to publish it. Untested: there is no Docker on the development machine.

## Reference books

### What has been checked against a book, and what has not

| Joint | Source | State |
|---|---|---|
| Knuckle | NPTEL IIT Kharagpur, DME I, module 4 lesson 2 | proportions and all nine checks verified |
| Socket and spigot cotter | NPTEL IIT Kharagpur, DME I, module 4 lesson 2 | proportions and all ten checks verified |
| Hex bolt and nut | NPTEL IIT Kharagpur, DME I, module 4 lesson 4 | tightening load verified; size table still unverified |
| Flange coupling | NPTEL IIT Kharagpur, DME I, module 4 lesson 1 | key checks verified; proportions unverified |
| Sleeve and cotter | none held | unverified |

The tool deliberately disagrees with the lesson in two places, both because the lesson's own
answer fails its own check. `tests/test_book_problems.py` asserts each one.

1. **Knuckle eye.** The lesson raises the pin from 40 to 55 mm for bending, then checks the eye
   against the original 40 mm pin. With the real pin in the hole its eye-shear check reads
   80 MPa against 65 allowed. This tool grows the eye outer diameter instead.
2. **Cotter thickness.** The lesson checks crushing of the socket but not crushing between the
   cotter and the spigot, which Khurmi does check. At the lesson's own answer that reads
   167 MPa against 110 allowed, so this tool sizes the cotter thicker.

One typo was also caught: the lesson prints the initial tightening load as `284 d kN`, but its
own M20 example gives 56.8 kN, so the constant is `2840 d` newtons.

### Adding your own

Drop any mechanical-engineering book (PDF) into `reference/` and index it:

```
python tools/reference_library.py add ~/Downloads/some-book.pdf
python tools/reference_library.py list
python tools/reference_library.py find "rivet spacing"
python tools/reference_library.py page <book> 145
python tools/reference_library.py remove <book>
```

`add` copies the PDF into `reference/`, so it shows you the list first and asks. Files that do
not look like engineering books (short, nothing bookish in the name) are flagged and skipped
unless you say "all". Point it at the books themselves, not at a whole folder: a glob like
`~/Downloads/*.pdf` will sweep up everything you have.

It uses the PDF's text layer when there is one and OCRs scanned books (needs
`brew install poppler tesseract`). `reference/` is gitignored, so books stay on your machine.

## NX

`nx/import_assembly.py` is a journal to run inside NX (Tools > Journal > Play) that imports
`assembly.step` as an assembly. It was written without NX and is untested. The reliable route by hand:
File > Import > STEP214 > choose assembly.step > Import to: New Part.

## Web app (for the demo)

```
.venv/bin/python -m aicad.web
```

Then open http://127.0.0.1:8765. Four steps on one page:

1. **Say what you need**, or click an example.
2. **Check the numbers** it read. Anything missing is highlighted and asked for.
3. **Building**, with each stage shown as it happens (sizing, solids, files, drawing sheet).
4. **Ask or change**, as a conversation that keeps its history.

Results come as tabs: the 3D model (Assembled / Exploded / Weak spots), the drawing sheet, the
dimensions, the checks with a bar showing how much of the allowed stress each one uses, and the
downloads. It only listens on this computer. Stop it with Ctrl+C.

## The AI part

Order tried in auto mode:

1. `ANTHROPIC_API_KEY`, then `GEMINI_API_KEY`, if set (not yet run against the live APIs).
2. Claude Code on this machine (`claude -p`), using whoever is logged in, with Claude Haiku 4.5
   by default (`--model` changes it). Tools are switched off and only local settings load, so
   personal hooks and instructions stay out of it.
   Tested live 18 Sep 2026: about 8 s and roughly $0.006 of plan usage per sentence.
3. Plain rules, always available.

Whatever the AI returns is checked. Every number must match a number, or a number word
(two, fifty, half...), in the sentence after unit conversion; otherwise it is dropped
and the tool asks. When AI and rules disagree the output says so.

The AI only turns the sentence into numbers. Sizing and geometry are plain engineering code,
so every dimension can be traced to a formula or a table row.

## Evaluating the parser (for the paper)

```
.venv/bin/python -m aicad.eval_parse
.venv/bin/python -m aicad.eval_parse --ai
.venv/bin/python -m aicad.eval_codegen
```

Scores 22 hand-written sentences in `eval/golden_requests.json`, field by field, for rules
alone, AI alone, and AI with rules filling its gaps (both AI scores use the same answers, so
`--ai` costs about 20 calls).

Measured 18 Sep 2026 (Claude Code, Haiku):

| parser | fully correct | notes |
|---|---|---|
| rules, 22 English sentences (20 Sep) | 18 of 22 | misses are numbers as words ("two tonne", "fifty", "half") and a joint described instead of named |
| rules, older 20-sentence set with Hinglish (18 Sep) | 17 of 20 | not comparable with the row above |
| AI alone, older set | 18 of 20 | both misses were timeouts, right on retry |
| AI + rules, older set | 20 of 20 | recomputed from the same answers |

A typical AI call takes 8 to 22 s; the timeout is now 45 s, after which the tool uses rules.
The golden set was written by the tool's author, so add real sentences from classmates
before quoting any of these numbers.

## Files to check against the book

`aicad/data/*.json` (one per joint, plus `materials.json`) hold every proportion, table value
and default stress. **None are verified against the design book yet.** Check each line, fill
in `page`, set `verified_against_book` to true. Two engineering choices to confirm:

- Knuckle pin bending: by default the pin is enlarged until bending passes (50 kN gives a
  30 mm rod but a 45 mm pin). If your book only checks bending, set `pin_bending.mode` to
  `check_only` in knuckle.json.
- Cotter joint: proportions are rounded up to whole mm, then any dimension whose check still
  fails is raised 1 mm at a time; the report lists every raise.

## Tests

```
.venv/bin/python -m pytest -q
```

244 tests: explanations, follow-up redesign, maximum-load limits, optimisation, AI-code gates, the web app (in-process, with a path-traversal check), exploded views that really separate, sizing numbers, a 10-load sweep where every check must pass for every joint, dimension
lists for every drawing,
parser cases (units, number words, bolts, missing info), the AI guard and fallback
(with a fake Claude, so tests never spend usage), each part being one valid solid, no two
parts overlapping (with a test proving that check can fail), the assembly re-importing as
separate solids, and the FreeCAD pack (skipped where FreeCAD is not installed).
