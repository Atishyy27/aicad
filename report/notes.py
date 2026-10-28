"""Speaker notes, one per slide, in the order the deck runs.

Written to be glanced at while talking, not read out. Each opens with who is presenting,
per the split the team agreed: Ansh takes the introduction and the literature review, Bhavya
what was built, Atishay the worked example and the output, Dharmendra the verification, and
Ankur the validation and the close.
"""

NOTES: dict[int, str] = {
 1: """ANSH.
Good morning. Our major project is the Strategic Application of Artificial Intelligence in CAD.
We are five: Ankur, myself, Atishay, Bhavya and Dharmendra, guided by Dr. Rawal.
In one line: you type a sentence like "knuckle joint for 50 kN", and the software designs that
joint completely, checks every way it can break, builds the 3D parts and draws the sheet. It
takes about ten seconds.
I will cover the problem and the literature. Bhavya takes what we built, Atishay the worked
example and the output, Dharmendra the verification, Ankur the validation.""",

 2: """ANSH. Section opener. Say only: first, why this problem is worth solving at all.""",

 3: """ANSH.
Designing a standard joint is not creative work, it is a fixed recipe. For a knuckle joint you
find the rod from tension, size the pin twice, once for shear and once for bending, take the
larger, derive seven more dimensions from the rod, then check nine ways it can fail.
Change the load and you do all of it again from the start.
The thinking is five minutes. The arithmetic is the afternoon.
CAD removed the drawing work but not this. A modeller will happily draw a pin too thin to
survive, because it does not know what a pin is.
Our aim: keep every formula exactly as the textbook has it, and remove only the repetition.""",

 4: """ANSH. Section opener. Say: these are the three books the whole project stands on.""",

 5: """ANSH.
Three sources. NPTEL from IIT Kharagpur gives the full design procedure for the cotter and
knuckle joints, the proportions and the failure modes. Unwin, 1899, gives the gib and cotter
joint, which the course does not cover. Leutwiler, 1917, lists ten ways a cotter joint fails
and analyses the flange coupling.
Two of them are out of copyright, so anyone can open them and check us.
If asked why three sources for six joints: two of them cover the same joint deliberately. That
overlap is exactly what let us find three mistakes in the books, which Dharmendra will show.
We also used SP 46 for first angle projection and the IS codes for keys, bolts and couplings.""",

 6: """ANSH.
Three existing approaches, and what each leaves open.
Parametric CAD regenerates a model when parameters change, but it does not decide the
parameters. It will regenerate an unsafe model as readily as a safe one.
Language models writing CAD code produce geometry fast, but no dimension can be traced to a
calculation and no failure mode is checked.
Expert systems are reliable but hide the calculation, so you cannot check a result against a
published source.
So the gap is not modelling and not language. It is the connection between them.""",

 7: """BHAVYA. Section opener. Say: now what we actually built.""",

 8: """BHAVYA.
Five stages. It reads the sentence into parameters. It sizes the joint starting from the
governing formula, then rounds up to a standard size as the book directs. It checks every
failure mode against the allowable stress, and where one fails it grows that dimension a
millimetre at a time until it passes. It builds each part as an exact solid. It draws the sheet.
Design rules are stored as data, not code, which is why the software can tell you the source of
any dimension at the moment it computes it.""",

 9: """BHAVYA.
This is the most important slide in the deck.
The AI only reads the sentence. It never picks a dimension and never performs a check.
Reading "50 kN" as 50,000 newtons is a language problem, and that is what a language model is
good at. Choosing the pin diameter is an engineering problem with one correct answer from a
formula, so that stays with ordinary deterministic code traceable to a page in a book.
There is also a safeguard: any number the model returns that was not in the original sentence is
thrown away and the user is told.
If asked why not let AI generate the whole model: because then no number could be checked
against anything, and geometry you cannot justify is useless in a design review.""",

10: """BHAVYA.
Six joints, 44 failure checks in total, and every check is satisfied.
The busiest check across all six sits between 67 and 79 percent of allowable. That is
deliberate, not luck: each joint is sized for 1.25 times the load you asked for, then the
stresses are reported at the real load. Margin stays in hand rather than being spent on paper.
The gib and cotter joint needed a decision. Unwin gives the breadth and thickness but no strap
proportions. Rather than borrow a ratio from elsewhere or invent one, every dimension the source
does not give is sized against a failure check until it passes.""",

11: """ATISHAY. Section opener. Say: let me take one joint end to end, with real numbers.""",

12: """ATISHAY.
Knuckle joint, 50 kN. Three calculations decide everything.
Rod from direct tension gives 32.57, so the rod becomes 35, the next standard size.
The pin is sized twice. Double shear asks for 25.75. Bending asks for 43.95. We take the larger,
so the pin becomes 45.
Bending asks for nearly 1.7 times what shear asks for. A pin sized on shear alone would pass its
own check and bend in service. The textbook takes the same step.
Everything else follows from the rod diameter using the book proportions, each with its source
printed beside it.""",

13: """ATISHAY.
All nine failure modes, evaluated at the real 50 kN, not the design load.
Nine of nine are satisfied. The busiest is shear of the eye at 76 percent of its allowable.
The point to make: none of this is stored. Ask for 80 kN and every number in this table changes
and the pin is re-sized. It is not a library of readymade models.""",

14: """ATISHAY.
Every run prints its working: the values before rounding, the size adopted, the rule and the
source behind each proportion, every check with the numbers substituted, and the mass of each
part.
Why that matters: a reviewer does not have to trust the result. Any line can be recomputed by
hand from the formula printed next to it.
It is also the reason the findings later in this deck exist. Printing every check is what made
the errors in the books visible.""",

15: """ATISHAY. Section opener. Say: and this is what comes out of it.""",

16: """ATISHAY.
A first angle A3 sheet with front view, side view, plan, an isometric, dimension lines and a
title block. Produced by driving FreeCAD without opening its interface.
Alongside it: a STEP file for every part and one for the assembly, which opens in NX,
SolidWorks, Fusion and Onshape, a DXF for AutoCAD, and an editable FreeCAD file.
STEP is a neutral format, so the output is not locked to our software.
Next slide shows exactly what that NX claim rests on.""",

17: """ATISHAY.
One of our stated objectives is that the output opens in commercial CAD, specifically NX10,
since that is what we are taught on in the lab. Here is what we actually checked, not what we
assumed.
We opened the exported file as text and read it directly. The schema line reads AUTOMOTIVE
DESIGN, AP214, which is the exact STEP format NX10 reads natively. Inside it, four separate
named parts, rod, strap, cotter, gib, each its own solid, not fused into one body. That is the
structure an assembly import needs.
We are saying this plainly: opening it inside NX10 itself still needs a lab machine, which
none of us has done yet. If asked, say exactly that, do not claim it was opened when it was not.
We verified the file is built correctly; we have not yet watched NX10 read it.""",

18: """ATISHAY.
The assembled model, which rotates in the browser, and the same joint coloured by how close each
part is to its limit.
The colouring is useful because it puts the weakest member in front of you without reading a
table.""",

19: """DHARMENDRA. Section opener. Say: now, how do we know any of this is correct.""",

20: """DHARMENDRA.
Every proportion and every check was compared against the three sources.
Knuckle and cotter are fully verified. The cotter joint is verified twice over, against two
independent books.
Two entries are honest limitations rather than gaps. For the flange coupling all seven checks
are verified twice, but the proportions cannot be verified, because Leutwiler records that no
standard set of flange coupling proportions was ever agreed and that published tables are
individual manufacturers' practice. For the sleeve and cotter joint we searched four books and
none covers it by name.
Where no source exists, the software says so on every single run rather than implying one.""",

21: """DHARMENDRA.
The first of three errors we found in the published sources.
The knuckle worked problem raises the pin from 40 to 55 millimetres to satisfy bending, then
checks the eye using the original 40 millimetre pin.
Put the pin it actually adopted into its own expression and you get 80 MPa against an allowable
of 65. Its own answer fails its own check by 23 percent.
Our software instead enlarges the outer diameter of the eye until the check passes, and reports
that it has done so.""",

22: """DHARMENDRA.
Two more.
The cotter procedure checks crushing of the socket but never crushing between the cotter and the
spigot. At its own final answer that omitted check reads 167 MPa against 110 allowed. Leutwiler
lists it as one of ten failure modes, which is what makes it an omission and not a preference.
Second, the bolt tightening constant is printed as 284 d kilonewtons, but the worked example on
the same page gives 56.8 kN for an M20 bolt. That only works if the constant is 2840 d newtons.
The page refutes itself, and it is out by a factor of one hundred.
We found none of these by reading. We found them because the software computes every check and
prints the arithmetic.""",

23: """ANKUR. Section opener. Say: finally, how the work is validated and what it does not do.""",

24: """ANKUR.
An independent finite element cross check.
First validated on a case with a known answer: a 20 mm bar in tension, formula 31.83, computed
32.22, a difference of 1.2 percent.
On the knuckle eye rod: formula 52.0, computed 57.9, about 11.5 percent higher. That is expected,
because the formula treats the rod as a plain bar and ignores the stress raised at the pin bore.
Both stay under the 75 MPa allowable.
The important part: a peak that never settles is not a stress. On one part the computed peak
moved between 157 and 191 MPa as we refined the mesh sixteen fold. So the software re-solves on
a finer mesh and reports NOT CONVERGED when the number will not settle, and tells you to design
to the hand calculation.""",

25: """ANKUR.
290 automated tests run on every change: the arithmetic, the geometry, the parsing, the drawing
and the analysis.
The row that matters most is the last one. There are tests that assert the three errors in the
books are real. Without them, someone could later correct our software back to the printed
answers and every other test would still pass.
One test found something no dimension check could: comparing the solids pairwise caught a gib
hook modelled 1.25 millimetres inside the strap, occupying metal another part already occupied,
while every individual dimension was correct.""",

26: """ANKUR.
What it does not do, said before anyone asks.
Static loading only, so no fatigue and no stress concentration factors. Nominal dimensions only,
so no tolerances or fits, which means the sheet is not yet a manufacturing drawing. Two of the
six joints have proportions with no book behind them, and the software says so every run. Nut
thread stripping is not checked.
Future scope: riveted and welded joints follow the same pattern, then fatigue, then tolerances
and fits, then a journal script so the assembly builds inside NX rather than being imported.""",

27: """ANKUR.
Six objectives, set out at the start, each checked against the evidence rather than restated as
done.
Five of six are met without qualification: reading plain English, sizing and verifying with
iteration, the drawing sheet, verification against literature, and browser use without install.
The sixth, opening the exported file inside NX10 itself, is met in structure, AP214 schema, four
separate solids, but not yet confirmed by watching it actually open there.
If asked why show this at all instead of just claiming six for six: because recording the gap
honestly is itself part of what Objective 5 asked for. A scorecard that hides its one open item
would undercut the exact thing it is trying to demonstrate.""",

28: """ANKUR.
The timeline.
Green is finished, amber is where we stand today, grey is what we propose for semester eight.
Everything you have seen in this presentation is in the green and amber blocks.
Phase one was the literature and the design procedure. Phase two was the sizing engine and all
six joints with their forty-four checks. Phase three, where we are now, is the solid modelling,
the drawing sheet, the verification against the three books, the finite element cross check,
the tests and the deployment.
Semester eight is a proposal taken from the limits on the previous slide, to be agreed with our
guide: riveted and welded joints, fatigue, tolerances and fits, the two proportion sets that
still have no source, an NX journal and a bill of materials.
We are not giving week-by-week dates because we have not fixed them.""",

29: """ANKUR.
To close.
Every dimension this software produces can be traced to a formula, and every formula to a page
in a book. That is the difference between a tool that designs and one that only draws.
The language model reads the requirement. The engineering stays deterministic, checked, and open
to inspection.
Six joints, 44 checks, 290 tests, and three errors found in published literature along the way.
Thank you. We are happy to take questions.""",
}
