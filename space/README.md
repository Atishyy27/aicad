---
title: aicad
emoji: 🔩
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Type a machine joint in plain English, get checked CAD and a drawing
---

# aicad

Type what you need, for example "knuckle joint for 50 kN". The app sizes the joint with
textbook design formulas, checks every way it can fail, builds the parts as exact solids, and
draws a first-angle A3 sheet.

Built for the SGSITS Indore mechanical major project, "Strategic application of AI in CAD".

**What is checked against a book, and what is not.** The knuckle and the socket-and-spigot
cotter joint are verified against NPTEL IIT Kharagpur, Design of Machine Elements I, module 4,
and the cotter joint again against Leutwiler, Elements of Machine Design, 1917. The gib and
cotter comes from Unwin, Elements of Machine Design, 1899, page 179. Every check on the flange
coupling and the sleeve joint is verified, but their empirical proportions are not, and cannot
be: Leutwiler records that no standard flange coupling proportions were ever agreed, so the
published tables are manufacturers' practice. Each dimension in the report names its own source.

The finite-element check is one linear-static run on one part, not a full analysis. It tells you
when it has not converged. Use this to learn and to demonstrate, not to manufacture.

Source: https://github.com/Atishyy27/aicad
