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

**Read this before trusting a number.** Every proportion, table value and allowable stress in
here is still unverified against a design book. The finite-element check is one linear-static
run on one part, not a full analysis. Use it to learn and to demonstrate, not to manufacture.

Source: https://github.com/Atishyy27/aicad
