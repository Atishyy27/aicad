"""Command line: python -m aicad "knuckle joint for 50 kN"

Asks for anything missing, shows the dimensions and strength checks, then
builds the parts on confirmation. --yes skips every question and fails if
something is missing.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from .joints import REGISTRY
from .parse import parse, parse_rules


def _ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        return ""


def _fill_missing(spec) -> None:
    tries = 0
    while spec.joint is None and tries < 5:
        tries += 1
        answer = _ask(f"Which joint? ({', '.join(REGISTRY)}) > ")
        spec.joint = parse_rules(answer + " joint").joint
    if spec.joint is None:
        return
    if spec.joint == "nut_bolt":
        while spec.load_n is None and spec.bolt_size is None and tries < 10:
            tries += 1
            answer = _ask("Load it must carry, e.g. 20 kN, or a bolt size like M12 > ")
            got = parse_rules(answer if any(c.isalpha() for c in answer) else answer + " kN")
            spec.load_n, spec.bolt_size = got.load_n, got.bolt_size
        return
    while spec.load_n is None and spec.rod_diameter_mm is None and tries < 10:
        tries += 1
        answer = _ask("Load it must carry, e.g. 50 kN (press Enter to give the rod diameter instead) > ")
        if answer:
            spec.load_n = parse_rules(answer if any(c.isalpha() for c in answer) else answer + " kN").load_n
            continue
        answer = _ask("Rod diameter in mm > ")
        if answer:
            spec.rod_diameter_mm = parse_rules(answer if "mm" in answer else answer + " mm").rod_diameter_mm


def _show(design, joint) -> None:
    print(f"\n{joint.TITLE}: dimensions (mm)")
    for k, v in design.dims.items():
        print(f"  {k:<12} {v:>8g}   {joint.LABELS.get(k, k)}")
    if design.checks:
        print("\nStrength checks")
        for c in design.checks:
            mark = "ok  " if c.passed else "FAIL"
            print(f"  {mark} {c.name:<24} {c.stress_mpa:7.1f} MPa  (allowed {c.allowable_mpa:g})")
    else:
        print("\nStrength checks skipped: no load given.")
    for n in design.notes:
        print(f"\nNote: {n}")
    if not design.verified_against_book:
        print(f"\nRules are UNVERIFIED against the design book (see aicad/data/{joint.NAME}.json).")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="aicad", description="Sentence in, CAD parts out.")
    ap.add_argument("request", nargs="*", help='e.g. "knuckle joint for 50 kN"')
    ap.add_argument("--yes", action="store_true", help="no questions; fail if info is missing")
    ap.add_argument("--out", type=Path, help="output folder (default: out/<joint>-<time>)")
    ap.add_argument("--parser", choices=["auto", "rules", "ai"], default="auto",
                    help="auto: AI if available, else rules (default). rules: offline only. ai: AI only")
    ap.add_argument("--no-freecad", action="store_true", help="skip the FreeCAD file and drawing sheet")
    ap.add_argument("--open", action="store_true", help="open the result in FreeCAD when done")
    ap.add_argument("--model", help="AI model: for Claude Code an alias like haiku, sonnet, opus "
                    "or a full id; for an API key the provider's model id. Default: haiku")
    args = ap.parse_args(argv)
    if args.model:
        import os
        for var in ("AICAD_CLAUDE_MODEL", "AICAD_ANTHROPIC_MODEL", "AICAD_GEMINI_MODEL"):
            os.environ[var] = args.model

    text = " ".join(args.request) or ("" if args.yes else _ask("What should I make? > "))
    try:
        spec = parse(text, mode=args.parser)
    except RuntimeError as exc:
        print(f"AI parsing failed: {exc}", file=sys.stderr)
        return 5
    shown = {k: v for k, v in spec.design_kwargs().items() if v is not None}
    print(f"Understood ({spec.source}): joint={spec.joint} {shown}")
    for n in spec.notes:
        print(f"  note: {n}")

    if spec.joint is None and not args.yes:
        print("That is not one of the library joints. For any other part, try the experimental AI-written CAD:")
        print(f'  python -m aicad.codegen "{text}"')
    if spec.missing():
        if args.yes:
            print("Missing: " + ", ".join(spec.missing()), file=sys.stderr)
            return 2
        _fill_missing(spec)
        if spec.missing():
            print("Still missing: " + ", ".join(spec.missing()), file=sys.stderr)
            return 2

    if not spec.supported():
        print(f"'{spec.joint}' is recognised but not built yet. Built so far: {', '.join(REGISTRY)}.")
        print('For other parts, the experimental AI-written CAD path: python -m aicad.codegen "<part with sizes in mm>"')
        return 3
    joint = REGISTRY[spec.joint]

    try:
        design = joint.design(**spec.design_kwargs())
    except ValueError as exc:
        print(f"Cannot size this joint: {exc}", file=sys.stderr)
        return 4

    _show(design, joint)
    if not design.all_passed:
        print("\nWARNING: at least one strength check fails for these dimensions.")

    if not args.yes and _ask(f"\nBuild these {len(joint.PARTS)} parts? [Y/n] > ").lower() in ("n", "no"):
        print("Stopped. Nothing written.")
        return 0

    from .export import export_all  # heavy imports only when building

    tag = f"{spec.load_n / 1000:g}kN" if spec.load_n else (
        f"M{spec.bolt_size}" if spec.bolt_size else f"D{spec.rod_diameter_mm:g}")
    out = args.out or Path("out") / f"{joint.NAME}_{tag}_{datetime.now():%Y%m%d-%H%M%S}"
    print("\nBuilding solids...")
    export_all(joint.build_parts(design.dims), design, joint, out, request=text)

    fc = None
    if not args.no_freecad:
        from .freecad_pack import run_pack
        print("Making the FreeCAD file and drawing sheet...")
        fc = run_pack(out, joint, design, text)
        if not fc.get("ok"):
            print(f"  FreeCAD step skipped: {fc.get('reason') or fc.get('error', '')[:300]}")

    print(f"\nDone: {out.resolve()}")
    print("  parts/*.step    one file per part")
    print("  assembly.step   all parts in position (opens in NX, FreeCAD, Onshape, Fusion)")
    print("  viewer.html     double-click to rotate it in a browser (works offline)")
    print("  report.md       every dimension, its rule, and the strength checks")
    if fc and fc.get("ok"):
        print(f"  {joint.NAME}.FCStd  FreeCAD file with the parts tree and an editable drawing page")
        print(f"  drawing.svg     A3 first-angle sheet, scale {fc.get('sheet_scale')} (open in a browser, print to PDF)")
        if fc.get("dxf"):
            print("  drawing.dxf     the same views for AutoCAD / LibreCAD")
    if args.open and fc and fc.get("fcstd"):
        from .freecad_pack import open_in_freecad
        open_in_freecad(Path(fc["fcstd"]))

    if not args.yes:
        from .redesign import follow_up
        print("\nAsk a follow-up, e.g. 'make it 80 kN', 'why is the pin 45 mm', 'how much load can this take',")
        print("'make it lighter'. Press Enter to finish.")
        while True:
            q = _ask("follow-up > ")
            if not q:
                break
            r = follow_up(spec, q, mode=args.parser)
            print(f"\n[{r.kind}] {r.message}\n")
            if r.kind == "change" and r.spec is not None and _ask("Rebuild with this? [Y/n] > ").lower() not in ("n", "no"):
                spec = r.spec
                joint = REGISTRY[spec.joint]
                design = joint.design(**spec.design_kwargs())
                out = Path("out") / f"{joint.NAME}_{datetime.now():%Y%m%d-%H%M%S}"
                export_all(joint.build_parts(design.dims), design, joint, out, request=f"{text} | {q}")
                if not args.no_freecad:
                    from .freecad_pack import run_pack
                    run_pack(out, joint, design, f"{text} | {q}")
                print(f"Rebuilt: {out.resolve()}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
