# Study Doc: Every Question the Panel Is Likely to Ask, and the Full Answer

*Organised by the five Phase II rubric criteria (ME46998, Mid Term Evaluation-II), not by chapter,
so reading this is reading the viva itself, not a separate essay to translate later. Every number
and claim here was verified against the actual code, the actual sources, or the actual rubric
PDF this session; nothing is invented to sound good. Answer in your own words, not memorised
sentences, the structure is what matters.*

---

## Criterion 1: Final Analysis
*Rubric's own words for the top band: "comprehensive and insightful analysis; demonstrates deep
understanding and critical thinking."*

**Q: What did your critical thinking actually produce here, beyond building working software?**
A: Three documented errors in published, decades-old design literature, each one traced to a
specific page and a specific number, each one reproduced by an automated test so it can't quietly
disappear later. That is the direct product of one rule we never broke: never trust a result
without printing the arithmetic that produced it.

**Q: You are calling things "errors" in a book written by IIT Kharagpur faculty. Isn't that a
strong claim for a student project?**
A: We don't rest that claim on our own judgement anywhere. The knuckle joint eye-shear issue is
the source's own worked example failing its own stated allowable by 23 percent, arithmetic anyone
can redo from the numbers printed on that page. The omitted crushing check is confirmed by a
second, fully independent book, Leutwiler 1917, written 18 years before NPTEL exists as a course,
listing the identical formula as one of ten standard failure modes. The bolt constant error is the
source's own worked example contradicting its own printed formula by a factor of one hundred. In each case
the source refutes itself or disagrees with an independent peer; we are reporting that, not
asserting our own superiority.

**Q: How do you know these aren't mistakes on your side instead of the book's?**
A: Because each one is checkable by a reader with no laptop at all: take the book's own printed
numbers, substitute them into the book's own printed formula, and the arithmetic itself produces
the contradiction. We didn't need our software to find this, our software just happened to be the
first thing that actually ran every check on every design and noticed the mismatch.

**Q: Your finite element result is 11.5 percent higher than your hand-calculated formula on the
knuckle eye rod. Doesn't a mismatch between your two methods undermine your own analysis?**
A: It would if we hid it or rounded it away; stating it instead is the point. The formula treats
the rod as a plain bar in tension and has no way to represent the stress concentration at the pin
bore. The finite element model sees that concentration directly, so a higher reading there is
expected, not a flaw. The control that proves the method itself is sound is the validation case
first, a plain 20 mm bar with no bore, where the two methods agree to 1.2 percent.

**Q: What observation would actually convince you that one of your three findings is wrong?**
A: A third independent source, ideally a currently used design data handbook, that explicitly
states the omitted cotter-crushing check does not apply to this geometry, or that the 40 mm pin
really was the one carried forward in the original worked solution despite what is printed. Absent
that, the arithmetic as it stands says what it says.

---

## Criterion 2: Final Results Obtained
*Rubric's own words: "accurate, well-presented, and thoroughly validated; aligns with objectives."*

**Q: Walk us through your results. Are they accurate?**
A: Six joints, 44 applicable failure checks between them, all satisfied at the stated load. For
the worked example, a knuckle joint at 50 kN: rod from direct tension comes to 32.57 mm, rounded
up to the standard 35 mm; the pin is sized twice, 25.75 mm for shear, 43.72 mm for bending, and
the larger wins, becoming 45 mm, because a pin sized on shear alone would pass its own check and
still bend in service. All nine failure checks on that joint then pass at the real load, busiest
at 76 percent of allowable.

**Q: How do your results align with the objectives you actually set out to meet?**
A: Five of our six stated objectives are met without qualification: interpreting plain English,
sizing and verifying with iteration, the drawing sheet, verification against literature, and
browser use without install. The sixth, the exported file opening correctly inside NX10 itself, is
confirmed correct in file structure, AP214 schema, four separate named solids rather than one
fused body, which is exactly what an NX10 assembly import needs, but it has not yet been watched
opening on a lab machine, and we say that plainly rather than assume it.

**Q: What validates your finite element results specifically, not just the hand formula?**
A: A known-answer test run first: a plain 20 mm bar under 10 kN tension, hand formula 31.83 MPa,
finite element result 32.22 MPa, 1.2 percent apart, which is close enough to trust the method
before applying it to a harder geometry. There is also a self-check built in: if refining the mesh
moves the computed peak by more than 5 percent after it already exceeded 1.5 times the hand value,
the system reports NOT CONVERGED rather than a number, because a peak that never settles is a
mesh artefact at a sharp corner, not a real stress; we saw this directly on one component, where
the peak wandered between 157 and 191 MPa across a sixteen-fold mesh refinement.

**Q: Your busiest check sits at 67 to 79 percent of allowable, never near 100. Isn't that
over-designed, wasted material?**
A: It's deliberate, not accidental margin. Every joint is sized for 1.25 times the load actually
requested, then every check is reported at the real load, not the inflated design load. That gap
is the safety margin a designer is expected to leave, made visible as a number instead of hidden
inside a vague "factor of safety" statement.

**Q: Give it a different load right now. What happens?**
A: Every dimension in the table changes and the pin, rod and every proportion are re-sized from
scratch; nothing is a stored or pre-built answer. This is directly demonstrable live on the laptop
during the viva.

---

## Criterion 3: Conclusion and Future Scope
*Rubric's own words: "well-articulated conclusion; clearly defines future work with practical
implications."*

**Q: Give us the conclusion of this whole project in one sentence.**
A: Every dimension this software produces can be traced to a formula, and every formula to a page
in a book, which is the actual difference between a tool that designs and one that only draws.

**Q: What specifically is left for semester 8?**
A: Riveted and welded joints, fatigue loading with an endurance limit and stress concentration
factor, tolerances and fits on the drawing sheet so it becomes a manufacturing drawing rather than
a design one, verification of the two proportion sets that still carry no supporting source, a
journal script for direct NX assembly, and a bill of materials with costing.

**Q: You say riveted and welded joints "need no change to the architecture." Is that really true,
or are you underselling the remaining work?**
A: True for the architecture, not true for the effort. The five-stage pipeline, read, size, check,
model, draw, and the pattern of storing rules as data rather than code, apply unchanged. What is
real, new work is the formulas themselves: riveted and welded joints fail in different ways and
need their own failure-check set written and verified against a source, the same depth of work the
six current joints already went through.

**Q: Why can't fatigue analysis be done right now, if the engine already exists?**
A: Static loading and fatigue loading are different calculations, not a toggle on the same one.
Fatigue needs an endurance limit specific to the material and a stress concentration factor at
each geometric discontinuity, neither of which the current failure-check set carries, so it is
correctly scoped as future work rather than quietly assumed covered.

---

## Criterion 4: Presentation Skills and Viva-Voce
*Rubric's own words: "confident delivery; clear articulation; engages the audience; handles
questions adeptly."*

**Q: Who presents what, and why that split?**
A: Ansh: the problem and the literature review. Bhavya: what was built and the AI/engineering
boundary. Atishay: the worked example, the output, and the NX10 file check. Dharmendra: the
verification and the three findings. Ankur: validation, limits, the objectives scorecard, the
timeline, and the close. Each person owns the section they can defend in depth, not a slice handed
out by slide count.

**Q: Did you train a model?**
A: No, said flatly, no hedge. An off-the-shelf language model is given one narrow job, reading a
sentence into a joint type and a load. Every dimension and every failure check after that comes
from ordinary code written against formulas in the three books. Nothing anywhere is trained.

**Q: Isn't this just a rules engine with a chatbot bolted on?**
A: Push back on "just." Reading free-text English reliably across different phrasings is a
genuinely hard language problem a rules engine cannot do well. Choosing a pin diameter has exactly
one correct answer from a formula, which is why that stays as deterministic code rather than
anything a model decides. The division between the two is the actual design decision this project
is built on, not an accident of implementation.

**Q: Where is the novelty, when NX and SolidWorks already do parametric modelling?**
A: Parametric CAD regenerates whatever parameters it is given and does not question them; it will
draw an unsafe pin as readily as a safe one. The novelty here is the translation layer from a
one-line English requirement to a verified, correctly sized design, not the solid modelling
itself, which deliberately uses an existing, proven kernel (CadQuery on OCCT) rather than
reinventing one.

**Q: [Per-presenter, the one hard question each of you should expect]**
A: See the separate viva-prep sheet (`AI-in-CAD-Viva-Prep.pdf`) for the targeted hard question and
cold answer for each of the five sections; it is not duplicated here to keep this doc to the
cross-cutting questions everyone should own.

---

## Criterion 5: Project Report in Hard Copy
*Rubric's own words: "well-structured report; clear writing; comprehensive content; properly
formatted and referenced."*

**Q: Is your report properly referenced?**
A: Every proportion and every failure check in it carries the book and page or article number it
came from, not a generic bibliography citation. Two of the three books, Unwin 1899 and Leutwiler
1917, are out of copyright, so any reader can open the same page and check the claim directly.

**Q: Why three sources instead of relying on one standard textbook?**
A: Because NPTEL alone gives the full procedure for only two of the six joints. Unwin is the only
source, after searching four books, that covers the gib and cotter joint at all. Leutwiler is the
one that independently confirms the omitted cotter-crushing check. Each source earns its place by
covering something the others do not, not by padding the bibliography.

**Q: Is the report finished and print-ready?**
A: The content is complete at 50 pages, built against the department's own two template PDFs, and
Chapter 7 closes with an objectives-revisited section scoring all six stated objectives against
evidence. Not yet done: the hard copy itself has not been printed, and a full end-to-end pass
checking every citation and cross-reference for formatting consistency has not been run.

---

### Quick numbers, for the one-line version of any answer above

6 joints · 44 checks, all satisfied · 3 errors found in published sources, each independently
confirmed · 290 automated tests, including tests that would fail if any of the 3 findings were
reverted · FEA validated to 1.2 percent before trusting it on the real joint · 5 of 6 stated
objectives met without qualification, 1 met in file structure and not yet observed in NX10.
