"""Score the sentence parser against eval/golden_requests.json.

  python -m aicad.eval_parse            rules only (offline, free)
  python -m aicad.eval_parse --ai       rules, AI alone, and AI with rules filling its gaps
                                        (one AI call per sentence; both AI scores use the same answer)

A field counts as correct when it matches within 0.5 %. A field the golden set
leaves out must come back empty, so an invented value counts as wrong.
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from .parse import _FIELDS, ai_backends, merge, parse_ai, parse_rules

GOLDEN = Path(__file__).resolve().parent.parent / "eval" / "golden_requests.json"


def _same(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    if isinstance(b, str) or isinstance(a, str):
        return a == b
    return abs(float(a) - float(b)) <= 0.005 * max(abs(float(b)), 1e-9)


def score(parser, items) -> dict:
    rows, field_ok, field_n, exact = [], {f: 0 for f in _FIELDS}, {f: 0 for f in _FIELDS}, 0
    t0 = time.time()
    for it in items:
        try:
            spec = parser(it["text"])
            got = {f: getattr(spec, f) for f in _FIELDS}
            err = None
        except Exception as exc:
            got, err = {f: None for f in _FIELDS}, f"{exc.__class__.__name__}: {exc}"[:120]
        wrong = [f for f in _FIELDS if not _same(got[f], it["expect"].get(f))]
        for f in _FIELDS:
            field_n[f] += 1
            field_ok[f] += f not in wrong
        exact += not wrong
        rows.append({"id": it["id"], "text": it["text"], "wrong": wrong, "got": got, "error": err})
    return {
        "exact": exact, "n": len(items), "seconds": round(time.time() - t0, 1),
        "per_field": {f: f"{field_ok[f]}/{field_n[f]}" for f in _FIELDS}, "rows": rows,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ai", action="store_true", help="also score the AI path (spends a little plan usage)")
    args = ap.parse_args(argv)
    items = json.loads(GOLDEN.read_text())["items"]
    results = {"rules": score(parse_rules, items)}
    if args.ai:
        backends = ai_backends()
        if not backends:
            print("No AI backend found (no API key, no `claude` on PATH).")
        else:
            b = backends[0]
            cache = {}

            def ai_only(t):
                try:
                    cache[t] = parse_ai(t, b)
                except Exception:
                    cache[t] = None  # same as the tool: a failed AI call falls back to rules
                    raise
                return cache[t]

            def hybrid(t):
                return merge(cache[t], parse_rules(t)) if cache.get(t) else parse_rules(t)

            results[b] = score(ai_only, items)
            results[f"{b}+rules"] = score(hybrid, items)

    for name, r in results.items():
        print(f"\n== {name}: {r['exact']}/{r['n']} sentences fully correct, {r['seconds']} s")
        print("   per field: " + ", ".join(f"{k} {v}" for k, v in r["per_field"].items()))
        for row in r["rows"]:
            if row["wrong"] or row["error"]:
                print(f"   #{row['id']:<2} wrong {row['wrong']}  {row['error'] or ''}  <- {row['text']}")
    out = GOLDEN.parent / f"results_{datetime.now():%Y%m%d-%H%M%S}.json"
    out.write_text(json.dumps(results, indent=1, default=str))
    print(f"\nSaved {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
