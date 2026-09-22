# Putting this on Hugging Face

You run these. The token is yours and I must never see it.

Corrected 22 Sep 2026, twice. This venv is a uv venv and has no `pip` in it, so the install
line uses `uv pip install --python .venv/bin/python`. The earlier version of this file also used
`hf repo create --repo-type space --space_sdk docker`, which is not the current syntax: the command is `hf repos create --type
space --sdk docker`. It also told you to copy the Space README over the project README at the
repo root, which would have destroyed it, and to push the whole git history to a public Space.
The staging folder below avoids all three.

## 1. Account and token

Make a free account at https://huggingface.co, then create a token at
https://huggingface.co/settings/tokens with **write** access.

## 2. Install the client and log in

    cd /Users/atishay/Desktop/codes_masti/masti/projects/ai-cad
    uv pip install --python .venv/bin/python huggingface_hub
    .venv/bin/hf auth login

Paste the token when it asks. A pass looks like `Login successful`. If it says
`Invalid token`, the token was made read-only: make another one with write access.

## 3. Build the folder that goes up

Only four things belong on the Space: the code, the project file, the Dockerfile and the Space
README. Not the reference books, not `out/`, not the tests, not the git history.

    rm -rf /tmp/aicad-space
    mkdir -p /tmp/aicad-space
    cd /Users/atishay/Desktop/codes_masti/masti/projects/ai-cad
    cp -R aicad pyproject.toml /tmp/aicad-space/
    cp space/Dockerfile space/README.md /tmp/aicad-space/
    find /tmp/aicad-space -name "__pycache__" -type d -exec rm -rf {} +
    du -sh /tmp/aicad-space

A pass is roughly 1 MB or less. If it is tens of megabytes, something large was copied in and
you should look at what before uploading. Measured on 22 Sep 2026: 1.3 MB, 34 files.

Already done and checked on this machine: the client is installed, the folder is staged, and a
knuckle, a gib and cotter and a flange coupling were built using only the staged copy, to prove
nothing it needs was left behind. All three sized, passed every check and wrote a full file set.

## 4. Create the Space and upload

Replace `<your-username>` with your Hugging Face username in both lines.

    .venv/bin/hf repos create aicad --type space --sdk docker
    .venv/bin/hf upload <your-username>/aicad /tmp/aicad-space . --repo-type=space --commit-message "aicad first deploy"

The first command prints the Space URL. The second prints one line per file and ends with the
commit URL. If it says the repo already exists, that is fine, skip straight to the upload.

**The Space is public.** Anything in `/tmp/aicad-space` is readable by anyone with the link.
That is the code and nothing else, which is why step 3 builds the folder by hand.

## 5. Watch the build

Open the Space URL and click **Logs**. The first build takes roughly ten minutes because
FreeCAD is large. When it says **Running**, the link works and you can share it.

## 6. To push a change later

Same upload command, plus `--delete="*"` so files you removed locally also disappear there:

    .venv/bin/hf upload <your-username>/aicad /tmp/aicad-space . --repo-type=space --delete="*" --commit-message "update"

## What works there and what does not

| feature | on the Space |
|---|---|
| reading your request | rules only, unless you add an `ANTHROPIC_API_KEY` secret in Space settings |
| sizing, every failure check, explanations, follow-ups | yes |
| 3D model, exploded and weak-spot views, STEP files | yes |
| drawing sheet, FreeCAD file, stress run | only if the FreeCAD packages install cleanly |
| AI-written CAD code | no: it needs Claude Code logged in on your machine |

## Still untested, and the one thing most likely to break

There is no Docker on this Mac, so this image has never been built. The likeliest failure is
FreeCAD. On Debian the package `freecad-python3` installs the command as
`/usr/lib/freecad/bin/freecadcmd-python3` and puts nothing in `/usr/bin`, so a plain lookup for
`freecadcmd` finds nothing and the drawings and stress run vanish with no error. The Dockerfile
now sets `FREECAD_CMD` to that exact path, and the tool also looks there by itself. Verified
against the Debian bookworm file list for that package, not guessed.

If the build fails, copy the build log from the Space page and send it to me.
