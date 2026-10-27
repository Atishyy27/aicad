#!/usr/bin/env bash
# Rebuilds the presentation (PDF + PPTX) and the printable speaker notes.
# Run after editing report/make_deck.py or report/notes.py.
#   bash report/rebuild-deck.sh

RL_NAME=rebuild-deck
source ~/Desktop/codes_masti/masti/cnc/runlog.sh

PROJ="$HOME/Desktop/codes_masti/masti/projects/ai-cad"
PY="$PROJ/.venv/bin/python"

rl_step "Check the interpreter and the inputs are there"
rl_check "venv python exists" test -x "$PY"
rl_check "make_deck.py exists" test -f "$PROJ/report/make_deck.py"
rl_check "notes.py exists" test -f "$PROJ/report/notes.py"
rl_check "Brave exists (the renderer)" test -x "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
rl_check "pdftoppm on PATH (splits the PDF for the pptx)" command -v pdftoppm

rl_step "Count the speaker notes, so a renumbering mistake shows here"
rl_run "$PY" -c "import sys; sys.path.insert(0,'$PROJ/report'); from notes import NOTES; ks=sorted(NOTES); print('notes:',len(ks),'first',ks[0],'last',ks[-1]); print('gaps:', [i for i in range(ks[0],ks[-1]+1) if i not in NOTES] or 'none')"

rl_step "Build the deck: PDF then PPTX"
cd "$PROJ" || rl_say "could not cd into $PROJ"
rl_run "$PY" report/make_deck.py

rl_step "Build the printable speaker notes PDF"
rl_run "$PY" report/make_notes_pdf.py

rl_step "Report what landed"
rl_run ls -lh "$PROJ/report/AI-in-CAD-Major-Project-Presentation.pdf" \
              "$PROJ/report/AI-in-CAD-Major-Project-Presentation.pptx" \
              "$PROJ/report/AI-in-CAD-Speaker-Notes.pdf"
rl_run "$PY" -c "import pypdf,sys; p='$PROJ/report/AI-in-CAD-Major-Project-Presentation.pdf'; print('deck pages:', len(pypdf.PdfReader(p).pages))"

rl_finish
