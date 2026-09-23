#!/usr/bin/env bash
# Stage and deploy aicad to Vercel. Run from anywhere.
#
# Written after a one-liner broke: `cp -R aicad $STAGE/` creates $STAGE as a copy of aicad
# when $STAGE does not exist, which silently flattened the folder and dropped the Dockerfile.
# The deploy then failed with "Container service must specify an entrypoint". Staging is
# rebuilt from scratch every time here, and the contents are checked before anything is sent.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAGE="${AICAD_STAGE:-/tmp/aicad-vercel}"

rm -rf "$STAGE"
mkdir -p "$STAGE"
cp -R "$SRC/aicad" "$STAGE/aicad"
cp "$SRC/pyproject.toml" "$STAGE/"
cp "$SRC/vercel/Dockerfile.vercel" "$STAGE/"
cp "$SRC/space/README.md" "$STAGE/README.md"
find "$STAGE" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

for f in Dockerfile.vercel pyproject.toml README.md aicad/web.py aicad/data/knuckle.json; do
  [ -e "$STAGE/$f" ] || { echo "STAGING BROKEN: $f missing"; exit 1; }
done
echo "staged $(du -sh "$STAGE" | cut -f1), $(find "$STAGE" -type f | wc -l | tr -d ' ') files"

cd "$STAGE"
npx --yes vercel@latest deploy --prod --yes 2>&1 | tail -40 > /tmp/aicad-deploy-last.log || true
if grep -qiE "deploy_failed|fetch failed|^Error:" /tmp/aicad-deploy-last.log; then
  echo "DEPLOY FAILED:"; grep -iE "deploy_failed|reason|Error:" /tmp/aicad-deploy-last.log | head -5; exit 1
fi
grep -oE "https://aicad-vercel\.vercel\.app" /tmp/aicad-deploy-last.log | head -1
echo "DEPLOY OK"
