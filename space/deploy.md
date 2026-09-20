# Putting this on Hugging Face (about 10 minutes)

You run these; they need your account and a token I must never see.

1. Make a free account at https://huggingface.co, then create a token at
   https://huggingface.co/settings/tokens with **write** access.

2. Install the client and log in:

       pip install --user huggingface_hub
       hf auth login          # paste the token when asked

3. Create the Space and push this folder to it:

       cd ~/Desktop/codes_masti/masti/projects/ai-cad
       hf repo create aicad --repo-type space --space_sdk docker
       cp space/Dockerfile space/README.md .
       git add Dockerfile README.md && git commit -m "space: docker build"
       git remote add space https://huggingface.co/spaces/<your-username>/aicad
       git push space master:main

The Space builds itself and gives you a public link to share. First build takes about
10 minutes because FreeCAD is large.

## What works there and what does not

| feature | on the Space |
|---|---|
| reading your request | rules only, unless you add an `ANTHROPIC_API_KEY` secret in Space settings |
| sizing, checks, explanations, follow-ups | yes |
| 3D model, exploded and weak-spot views, STEP files | yes |
| drawing sheet, FreeCAD file, FEA | only if the FreeCAD packages install cleanly in the build |
| AI-written CAD code | no: it needs Claude Code logged in on your machine |

**Untested here.** There is no Docker on this Mac, so the image has never been built. If the
build fails, send me the build log from the Space page and I will fix the Dockerfile.
