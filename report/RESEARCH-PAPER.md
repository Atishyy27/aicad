# Strategic Application of Artificial Intelligence in CAD

*A. Dodke, A. Yadav, A. Jain, B. Shrivastava, D. Gupta — Department of Mechanical Engineering,
Shri G. S. Institute of Technology and Science, Indore. Guide: Dr. B. R. Rawal, Professor and
Head.*

**Draft 1, generated from the verified project record (code, facts.json, and the SGSITS report
chapters already written and rebuilt this session). Ready to paste into a Doc; not yet formatted
to a specific journal/conference template.**

---

## Abstract

Designing a standard machine joint, a knuckle joint, a cotter joint, a shaft coupling, is not a
creative act. It is a fixed sequence of published design formulas followed by a fixed list of
failure checks, repeated in full whenever the applied load changes. Parametric CAD software
removed the drafting labour from this process decades ago but not the calculation: a parametric
model regenerates whatever dimensions it is given and will size an unsafe pin as readily as a
safe one. This work presents a system that accepts a design requirement stated in ordinary
English and returns a complete, verified design: every dimension computed from a published
formula, every applicable failure mode checked against its allowable stress and corrected by
iteration where necessary, an exact solid model of every component and of the assembly in a
neutral exchange format, and a first-angle engineering drawing sheet. A language model is used
for exactly one task, interpreting the written requirement; every dimension and every check is
produced by deterministic code traceable to a cited page in one of three design references. Six
standard joints are implemented, exercising 44 distinct failure checks, all satisfied at their
stated duty. Verification of the system's proportions and checks against the source literature
surfaced three genuine errors in that literature itself, each confirmed either by an independent
second source or by the source's own worked example contradicting its own stated result. An
independent finite element cross-check validates the governing hand calculations to within 1.2
percent on a known case. The implementation is covered by 290 automated tests and is deployed as
a public web application.

---

## 1. Introduction

### 1.1 Background

A machine joint transmits load between two members. The standard joints taught in machine design
are not designed by judgement; each is sized by a fixed sequence of formulas and verified against
a fixed list of failure modes, in substantially the same form across every standard text on the
subject. Because the sequence is fixed, it is repetitive: a change in the applied load invalidates
every dimension and requires the entire calculation to be repeated, while the engineering
judgement involved, the choice of allowable stresses and the interpretation of the result, occupies
a small fraction of that time.

### 1.2 Motivation

The motivation for this work is the gap between stating a requirement and obtaining a verified
design. At present, a designer translates a requirement such as *a knuckle joint to carry 50 kN*
into formulas by hand, evaluates them, checks the result against several failure modes, iterates
wherever a check fails, and only then begins modelling and drafting. A system that accepts the
requirement as written and returns a verified design, complete with solid models and a drawing
sheet, removes the repetition without removing the engineering, provided the translation step
(interpreting the written requirement) and the engineering step (every subsequent decision) are
kept strictly separate.

### 1.3 Objectives

1. Accept a design requirement in ordinary English and extract the joint type, applied load and
   allowable stresses.
2. Size the joint using established design formulas and verify every applicable failure mode,
   iterating wherever a check is not satisfied.
3. Generate exact solid models of every component and the assembly in a neutral exchange format
   that opens in commercial CAD software.
4. Generate a first-angle projection drawing sheet carrying dimensions and a title block,
   conforming to Indian drawing practice (SP 46).
5. Verify every proportion and failure check against published design literature, recording any
   disagreement with a source explicitly rather than silently.
6. Make the system usable through a web browser without local installation.

### 1.4 Scope

The present scope covers six standard joints under static loading. Fatigue, stress concentration
factors, tolerances and fits, and manufacturing process selection are outside scope. A single
linear-static finite element run on one component is used as an independent cross-check on the
governing hand formula, not as a complete structural analysis.

---

## 2. Related Work

Three existing approaches address parts of this problem, and each stops short in a different way.

**Parametric CAD** regenerates a model when its driving parameters change, which removes drafting
labour. It does not determine the parameters: the designer still computes them, and the software
regenerates an unsafe model as readily as a safe one.

**Language models generating CAD code directly** from a text description produce geometry
quickly, but no dimension they produce can be traced to a calculation, and no failure mode is
verified. Geometry that cannot be justified is of limited use in a design review.

**Expert systems and design handbooks implemented as software** are reliable within the range for
which they were written, but the calculation is typically hidden, so a result cannot be checked
against a published source without access to the implementation itself.

The gap, therefore, is not in modelling and not in language interpretation; both are individually
mature. It is in the connection between them: a system where a written requirement is interpreted
by a language model, the resulting parameters drive a deterministic calculation taken from
published literature, and that calculation remains open to inspection.

---

## 3. Problem Formulation

Given a design requirement expressed in ordinary English, produce a complete design of the
specified joint such that: every dimension is obtained from a published formula or a named
failure check; every applicable failure mode is verified against its allowable stress; the
geometry is generated in a neutral exchange format; a first-angle drawing sheet is produced; and
the complete working is reported in a form that permits independent verification.

This yields five conditions the solution must satisfy:

1. No dimension may be produced without an attributable basis (a cited formula, or a named
   failure check).
2. The language model may interpret the requirement but may select no dimension and perform no
   check.
3. Any numerical value returned by the language model that does not appear in the original
   requirement must be discarded, so an invented figure cannot enter the calculation.
4. Every applicable failure mode must be evaluated on every run and its arithmetic reported, not
   merely its outcome.
5. Where the empirical proportions used have no supporting source, the system must state that
   fact rather than imply a source it does not have.

---

## 4. Case Studies and Data

Six joints were selected: the knuckle joint, the socket and spigot cotter joint, the sleeve and
cotter joint, the gib and cotter joint, the hex bolted joint, and the protected-type rigid flange
coupling. They were chosen because each has a published design procedure, because between them
they exercise every common failure mode (tension, double shear, crushing, bending and torsion),
and because they differ enough in geometry to test generalisation. The flange coupling alone is
sized from a transmitted torque rather than an axial load, and its bolt count varies with shaft
diameter, specifically to confirm the system is not limited to axially loaded joints.

For each joint, three categories of data were collected: the empirical proportions as multiples
of the governing dimension, the complete list of failure modes with the expression governing
each, and the worked numerical example given in the source, later used to verify the
implementation value by value.

An allowable tensile stress of 75 MPa, shear of 60 MPa and crushing of 150 MPa are adopted
(working values from the source material), with a design factor of 1.25 and a preferred-diameter
rounding series matching NPTEL Module 4 Lesson 2.

---

## 5. Methodology

### 5.1 Pipeline

The system runs five stages in sequence: the written requirement is interpreted into parameters;
the joint is sized; every failure mode is verified; the geometry is generated; the drawing sheet
is produced. Each stage passes a definite result to the next, and every intermediate result is
reported to the user.

### 5.2 Division of Responsibility

The language model is used at the first stage only. It receives the requirement and returns the
joint type, the applied load, and any stated allowable stresses; it selects no dimension, applies
no proportion, performs no check. Determining that "50 kN" denotes 50,000 N is a language problem,
at which such a model is effective. Determining a pin diameter is an engineering problem with a
single correct answer from a formula, performed instead by deterministic code traceable to a
printed page.

A safeguard sits underneath this: any numerical value the model returns that does not appear in
the original requirement is discarded and the user is informed, which prevents a plausible but
invented figure from entering the calculation.

### 5.3 Sizing and Iteration

The governing dimension is computed first from the primary failure mode, e.g. for a knuckle joint
the rod diameter from direct tension,

> D = √(4P / (π σₜ))

rounded up to the next standard preferred size. Where a component has more than one independent
failure mode, such as the knuckle pin under both double shear and bending,

> d = √(2P / (π τ))  and  d = [16P(t₁/3 + t/4) / (π σ_b)]^(1/3)

it is sized separately from each expression and the larger requirement is adopted. Every remaining
dimension follows from the source's empirical proportions, as a multiple of the governing
dimension.

A design factor of 1.25 is applied: the joint is sized for 1.25× the stated load and the
resulting stresses are reported at the actual load, so the governing check reports roughly 67–79
percent of the allowable stress rather than 100 percent, retaining margin rather than spending it
on paper. Where a check is not satisfied, the responsible dimension is increased by 1 mm and the
full check set is re-evaluated, repeating until every check passes; both the dimension grown and
the check that triggered it are reported.

### 5.4 Geometry, Drawing, and the Finite Element Cross-Check

Each component is generated as an exact solid (CadQuery 2.8 on the OCCT kernel) and written in the
STEP neutral exchange format, opening in Siemens NX, SolidWorks, FreeCAD, Onshape and Fusion. The
assembly STEP file keeps components as separate, named solids rather than a single fused body — a
structural requirement confirmed by direct inspection of the exported file (schema
`AUTOMOTIVE_DESIGN`/AP214; one `PRODUCT` entry per component, one `MANIFOLD_SOLID_BREP` per part).

The drawing sheet is produced by driving FreeCAD headlessly: the assembled geometry is projected
to the front, left-side and plan views in first-angle projection per SP 46, with an isometric
view, dimension lines and a title block; the same views are exported as DXF.

An optional finite element analysis (CalculiX, meshed with gmsh) provides an independent check on
one component's calculated stress. If the computed peak exceeds the hand value by more than 50
percent, the mesh is refined and re-solved; if the peak then still moves by more than 5 percent,
the result is reported NOT CONVERGED rather than returned as a value, since a peak that keeps
moving under refinement indicates a mesh singularity at a sharp corner or constrained face, not a
physical stress.

---

## 6. Implementation

Design rules are stored as data, not code: each joint's module holds its proportions, the source
of each proportion, default allowables and the preferred size series, read by a shared calculation
engine. This means the source of any dimension can be reported the instant it is computed, and
correcting a proportion is a data change, not a code change. Each joint exposes the same interface
(a sizing function, a list of failure checks, a geometry builder, drawing specifications), which
is why the gib and cotter joint could be added after the other five with no change to the
surrounding system — and why, for that joint specifically, every dimension Unwin's source does not
supply (the strap proportions) is sized against a failure check rather than borrowed or invented.

The system is used through a browser: the user enters the requirement, confirms or corrects the
extracted parameters, and requests the build; the full working is printed as it proceeds, followed
by the 3D model (assembled, exploded, and coloured by utilisation), the drawing sheet, the
dimension and check tables, and the generated files.

The implementation is covered by 290 automated tests covering sizing arithmetic, generated
geometry, requirement interpretation, the drawing sheet and the finite element path — including
tests that assert the three literature discrepancies reported in Section 7.2 are real, so the
system cannot later be "corrected" back to the printed textbook answers without a test failing.
One geometry test, comparing every pair of solids for overlap, caught a gib hook modelled 1.25 mm
inside the strap: an error invisible to any individual dimension check, since every dimension in
isolation was correct.

---

## 7. Results

### 7.1 Design Results

All six joints size correctly and satisfy every applicable failure check; the busiest check across
all six lies between 67 and 79 percent of allowable, the intended consequence of the 1.25 design
factor. For the worked example *knuckle joint for 50 kN*: the rod from direct tension computes to
32.57 mm, adopted at the standard 35 mm; the pin computes to 25.75 mm from double shear and 43.72
mm from bending — bending governs, nearly 1.7× the shear requirement, and the pin is adopted at
45 mm, the same step the source material itself takes (a pin sized on shear alone would pass its
own check and bend in service). All nine applicable failure checks on this joint are satisfied at
the real 50,000 N load, the busiest (eye shear) at 76 percent of allowable.

### 7.2 Discrepancies Found in the Source Literature

Verification against the source literature surfaced three errors in that literature, reported
here because the system's behaviour deliberately departs from the printed material in
consequence.

1. **A worked example that fails its own check.** The knuckle joint worked problem raises the pin
   from 40 mm to 55 mm to satisfy bending, then evaluates the eye using the original 40 mm pin.
   Evaluated with the pin actually adopted, the eye-shear expression gives 80 MPa against an
   allowable of 65 MPa — a 23 percent exceedance of the source's own stated limit. This system
   instead enlarges the eye's outer diameter until the check passes, and reports having done so.
2. **An omitted failure mode.** The cotter joint procedure verifies crushing of the socket but
   never crushing between the cotter and the spigot. Evaluated at the source's own final answer,
   the omitted check gives 167 MPa against 110 MPa allowed. Leutwiler (1917), writing
   independently 18 years earlier, lists this exact mode as one of ten, with an algebraically
   identical expression — confirmation by a second, independent source is what establishes this
   as an omission rather than a preference.
3. **A constant printed incorrectly.** The bolt tightening load is printed as 284*d* kN, while the
   worked example on the same page computes 56.8 kN for an M20 bolt — a result consistent only
   with a constant of 2840*d* newtons, a factor of ten different from what is printed. The source
   refutes itself on its own page.

None of these three were found by inspection; all three surfaced because the system evaluates
every applicable check on every run and prints the arithmetic, making a disagreement between a
computed number and a printed one impossible to miss.

### 7.3 Verification Coverage

Four of the six joints are fully verified against the literature (proportions and checks); two are
partially verified. The flange coupling's seven checks are verified twice over, but its empirical
proportions are not independently verifiable: Leutwiler states explicitly that no standard set of
flange-coupling proportions was ever agreed industry-wide, and published tables reflect individual
manufacturers' practice — the system reports this proportion set as a convention, not a verified
value. The sleeve-and-cotter joint's checks are verified by correspondence with the closely related
cotter joint, but no book among four searched treats its proportions by name; this gap is likewise
reported on every run rather than papered over.

### 7.4 Finite Element Cross-Check

The method is first validated on a case with a known answer (a 20 mm bar, 10 kN tension): formula
31.83 MPa vs. computed 32.22 MPa, 1.2 percent apart. On the knuckle joint's eye rod, the computed
stress is 11.5 percent higher than the hand formula (52.0 vs. 57.9 MPa), expected because the hand
formula treats the rod as a plain bar in tension and does not represent the stress concentration
at the pin bore that the finite element model resolves directly; both values remain below the 75
MPa allowable. On a separate component, refining the mesh sixteen-fold moved the computed peak
between 157 and 191 MPa without settling — the system's convergence check flags this as NOT
CONVERGED rather than reporting a number, correctly identifying a mesh singularity rather than a
physical stress.

---

## 8. Discussion

The results support the division of responsibility set out in Section 5.2: a natural-language
interface was provided without any part of the design becoming unverifiable, and the requirement
that every check be evaluated and its arithmetic printed is what made the three discrepancies of
Section 7.2 visible in the first place. Assessed against the six stated objectives (Section 1.3),
five are met without qualification; the sixth, confirming the exported assembly opens correctly
inside a specific commercial CAD package (Siemens NX), is met in file structure — the AP214 schema
and four separate named solids were confirmed by direct inspection of the exported file — but has
not yet been confirmed by observing the file open in that software on a licensed workstation, and
that distinction is recorded rather than assumed closed.

The system's limits are stated plainly rather than discovered by a reader: static loading only
(no fatigue or stress-concentration factors beyond what finite element analysis happens to show);
nominal dimensions only (no tolerances or fits, so the sheet is a design drawing, not yet a
manufacturing one); two of six joints carry proportions with no supporting source, declared on
every run; nut thread stripping is not checked.

---

## 9. Conclusion and Future Work

A system has been developed that accepts a machine-joint requirement in ordinary English and
returns a complete design: every dimension computed from a published formula, every applicable
failure mode verified against allowable stress, every component generated as an exact solid, and a
first-angle drawing sheet with dimensions and a title block. Six joints are implemented across 44
distinct failure checks, covered by 290 automated tests. The verification exercise against
published literature produced an unanticipated result: three errors in the source material itself,
surfaced not by inspection but because every check is evaluated and printed on every run. The
division of responsibility between language interpretation and deterministic, traceable
engineering is the element of this work most generally applicable beyond the six joints
implemented here.

Future work: riveted and welded joints (same architecture, no structural change required);
fatigue loading via an endurance limit and stress concentration factors; tolerances and fits on
the drawing sheet; verification of the two remaining unsupported proportion sets against a design
data handbook; a journal script for direct construction inside Siemens NX; and a bill of materials
with costing. As a direction rather than a present claim, the same English-to-verified-design
translation layer generalises to any catalogue of standard mechanical parts, which is what would
make a product or an industrial collaboration around this pipeline realistic to propose once the
joint library is broad enough to cover a real design office's day-to-day parts.

---

## References

1. NPTEL, IIT Kharagpur — *Design of Machine Elements I*, Module 4 (Lessons 1–4).
2. W. C. Unwin — *The Elements of Machine Design*, 1899 (gib and cotter joint, p. 179).
3. H. J. Leutwiler — *Elements of Machine Design*, 1917 (Art. 98: cotter-joint failure modes;
   Art. 275: flange coupling).
4. Bureau of Indian Standards — SP 46 (engineering drawing practice); IS 2048 (parallel keys and
   keyways); IS 1363/1364 (hexagon bolts, screws and nuts); IS 2693 (cast iron flange couplings).

---

*Note on provenance: every figure in this draft is reproduced from `report/facts.json`
(generated by running the actual software) and the already-built, already-rebuilt SGSITS report
chapters; nothing above is a new, unverified number. Not yet done: a reference-formatting pass to
a specific target venue's citation style, and the author/affiliation block needs enrolment numbers
confirmed (Dharmendra's is unresolved between `D03` and `D04`, see `MAJOR-PROJECT.md`).*
