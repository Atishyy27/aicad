"""Score AI-written CAD against parts with known answers.

  python -m aicad.eval_codegen      (spends AI calls: 1 to 2 per part)

For each part: did the tool's own gates pass, and is the part actually right
(bounding box and volume within 1 % of the hand-worked answer)? The gap between
the two is the interesting number: a part can pass the gates and still be wrong.
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import cadquery as cq

from .codegen import generate

FILE = Path(__file__).resolve().parent.parent / "eval" / "codegen_requests.json"


def _close(a, b, tol=0.01):
    return abs(a - b) <= tol * max(abs(b), 1e-9)


def main() -> int:
    items = json.loads(FILE.read_text())["items"]
    out_root = Path("out") / f"codegen_eval_{datetime.now():%Y%m%d-%H%M%S}"
    rows = []
    for it in items:
        t0 = time.time()
        try:
            r = generate(it["text"], out_root=out_root)
        except Exception as exc:
            rows.append({"id": it["id"], "gates": False, "right": False, "error": str(exc)[:200]})
            print(f"#{it['id']}: AI call failed: {exc}")
            continue
        row = {"id": it["id"], "gates": r["ok"], "attempts": len(r["attempts"]), "seconds": round(time.time() - t0)}
        if r["ok"]:
            s = cq.importers.importStep(str(Path(r["out"]) / "part.step")).val()
            bb = s.BoundingBox()
            got_bbox = sorted([bb.xlen, bb.ylen, bb.zlen])
            row.update(volume=round(s.Volume(), 2), bbox=[round(b, 2) for b in got_bbox],
                       bbox_ok=all(_close(g, w) for g, w in zip(got_bbox, sorted(it["bbox"]))),
                       volume_ok=_close(s.Volume(), it["volume"]), out=r["out"])
            row["right"] = row["bbox_ok"] and row["volume_ok"]
        else:
            row.update(right=False, reasons=r["attempts"][-1]["reasons"])
        rows.append(row)
        print(f"#{it['id']}: gates {'PASS' if row['gates'] else 'FAIL'} in {row.get('attempts')} attempt(s), "
              f"actually right: {row['right']}  (volume {row.get('volume')} vs {it['volume']}, "
              f"bbox {row.get('bbox')} vs {sorted(it['bbox'])})  {row.get('seconds')} s")
    n = len(rows)
    gates = sum(r["gates"] for r in rows)
    right = sum(r["right"] for r in rows)
    silent = sum(r["gates"] and not r["right"] for r in rows)
    print(f"\nPassed the tool's gates: {gates}/{n}. Actually right: {right}/{n}. "
          f"Passed the gates but wrong: {silent}/{n}.")
    res = FILE.parent / f"codegen_results_{datetime.now():%Y%m%d-%H%M%S}.json"
    res.write_text(json.dumps(rows, indent=1))
    print(f"Saved {res}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
