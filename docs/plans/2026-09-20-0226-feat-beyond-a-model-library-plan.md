---
title: Beyond a Model Library - Plan
date: 2026-09-20
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
product_contract_source: ce-plan-bootstrap
execution: code
---

# Beyond a Model Library - Plan

## Goal Capsule

- **Objective:** make the tool do things a downloaded CAD model cannot: redesign on follow-up
  requests, show where it will fail, explain every number, optimise, and build parts outside
  its library with verified AI-written code.
- **Product authority:** Atishay, 2026-09-20 (picked B, C, D, E, F and the NX journal).
- **Open blockers:** the real V. B. Bhandari book (the downloaded PDF is a different book), so
  book-problem tests wait.

## Problem Frame

A standard joint can be downloaded ready-made, so "sentence in, model out" alone looks like a
model library. The value has to be in design reasoning a static file cannot carry.

## Requirements

- **R1. English only.** Hinglish support removed from the reader, tests and evaluation set.
- **R2. Explain (D).** For any dimension or check, give the formula, the numbers substituted,
  and the rule it came from.
- **R3. Weak-spot view (C).** Colour each part by utilisation (worst stress / allowable), and
  name the governing check.
- **R4. Conversational redesign (B).** A follow-up sentence changes the current design (new
  load, stresses, sizes, joint) or asks an inverse question (max load for a given rod
  diameter). Show what changed.
- **R5. Optimise (F).** Pick the lightest or cheapest material that passes every check, from a
  material table, and show the trade-off table.
- **R6. AI-written CAD for new parts (E).** For a part outside the library, the AI writes
  CadQuery code; the tool runs it in a separate process with a time limit, checks it produces
  one valid solid whose size matches the request, and only then shows it. Failures are
  reported, not hidden.
- **R7. NX journal.** A script to run inside NX that imports the part files as an assembly.
  Unverifiable here (no NX); marked so.
- **R8. Tests for every new behaviour.**

## Key Technical Decisions

- **KTD1.** The AI still never sizes a standard joint; R6 is a separate, clearly labelled mode
  with automatic verification. (session-settled: user-directed, E added alongside, not instead)
- **KTD2.** AI-written code runs in a subprocess with a timeout and no network use by the code
  itself; it only gets CadQuery.
- **KTD3.** Material table values are textbook-style and UNVERIFIED, like every other table.

## Implementation Units

### U1. English only
Files: `aicad/parse.py`, `tests/test_parse.py`, `eval/golden_requests.json`.
Tests: English sentences still parse; Hinglish number words no longer counted as traceable.

### U2. Explain
Files: `aicad/explain.py`, `aicad/joints/*.py`, `tests/test_explain.py`.
Tests: every dimension of every joint has an explanation; a check explanation contains the
substituted numbers and the result.

### U3. Weak-spot view
Files: `aicad/export.py`, `aicad/joints/*.py`, `tests/test_geometry.py`.
Tests: every part maps to at least one check; colours follow utilisation; the governing check
is reported.

### U4. Conversational redesign
Files: `aicad/redesign.py`, `aicad/web.py`, `aicad/__main__.py`, `tests/test_redesign.py`.
Tests: "make it 80 kN" changes the load only; "shear 50 MPa" changes one stress; "max load
for a 30 mm rod" returns a load where every check passes and 1 % more fails.

### U5. Optimise
Files: `aicad/data/materials.json`, `aicad/optimise.py`, `tests/test_optimise.py`.
Tests: the chosen material passes all checks; no lighter passing option exists in the table.

### U6. AI-written CAD
Files: `aicad/codegen.py`, `tests/test_codegen.py`, `eval/codegen_requests.json`.
Tests (fake AI): good code accepted; code that crashes, loops, makes no solid or the wrong
size is rejected with the reason. Live run on a small request set, results recorded.

### U7. NX journal
Files: `nx/import_assembly.py`, README section. Test expectation: none -- needs NX.

## Verification Contract

All tests green; each unit demonstrated once through the CLI or web app; live numbers for U6
recorded with their denominators.

## Definition of Done

U1 to U7 built, docs updated, demo folders refreshed, open items listed honestly.
