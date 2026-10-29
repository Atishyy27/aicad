# How It Works — Point by Point

1. **Input.** You type a requirement in plain English: joint type, load (or rod size).
2. **Read (AI).** A language model extracts joint type + load from the sentence only. No dimension, no check, nothing else.
3. **Guard.** Any number the AI returns that isn't actually in your sentence is dropped, not used. Logged as dropped.
4. **Size.** The governing formula for that joint runs (ordinary code, not AI). Raw result rounds up to the nearest standard size.
5. **Derive.** Every other dimension follows from the governing one via a fixed proportion, each tagged with its book + page.
6. **Check.** Every applicable failure mode (shear, bending, crushing, tension) evaluated against allowable stress, at the real load.
7. **Iterate.** Any failed check grows the responsible dimension 1 mm at a time, re-checks everything, repeats until all pass.
8. **Design factor.** Sizing targets 1.25× the stated load; checks report at the real load. Margin is visible, not hidden.
9. **Model.** Each part built as an exact solid (CadQuery/OCCT). Assembly exported as one STEP file, parts separate, not fused.
10. **Draw.** FreeCAD driven headless → first-angle A3 sheet, DXF, dimensions, title block.
11. **Report.** Every run prints: raw value, rounded value, rule + source, every check's substituted arithmetic.
12. **Cross-check.** Optional FEA (CalculiX) validates one component's stress independently; flags NOT CONVERGED if the mesh won't settle instead of reporting a bad number.
13. **Output.** 3D viewer (assembled/exploded/weak-spot colouring), STEP (NX/SolidWorks/Fusion), DXF, FCStd.
14. **Scope today.** 6 joints, 44 checks, all satisfied. 3 errors found in the published sources this was built from, each independently confirmed. 296 automated tests.
15. **What AI never does.** Pick a dimension, run a check, or touch the geometry. One job only: read the sentence.
