#!/usr/bin/env python3
"""Make the reference books searchable.

    python tools/reference_library.py add <file.pdf> [more.pdf ...]   OCR if needed, index it
    python tools/reference_library.py remove <name>                   drop a book from the library
    python tools/reference_library.py list                            what is in the library
    python tools/reference_library.py find "cotter joint"             search every book
    python tools/reference_library.py page <book> <page>              print one page of text

Books live in reference/ and are gitignored: they stay on this machine. Text pages go to
reference/.text/<book>/page-NNNN.txt so a search can point at a real page number.

Needs poppler (pdftotext, pdftoppm) and tesseract for scanned books:
    brew install poppler tesseract
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "reference"
TEXT = REF / ".text"
INDEX = TEXT / "index.json"


def _run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def _load() -> dict:
    return json.loads(INDEX.read_text()) if INDEX.exists() else {}


def _save(ix: dict):
    TEXT.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps(ix, indent=1))


ENGINEERING_WORDS = ("design", "machine", "element", "mechanic", "engineer", "strength", "material",
                    "drawing", "cad", "khurmi", "bhandari", "shigley", "spotts", "handbook", "data book",
                    "thermodynam", "manufactur", "kinematic", "vibration", "fluid", "theory", "text")


def looks_like_a_book(pdf: Path, pages: int) -> bool:
    """A textbook is long and usually says so in its name. Short files are reports, resumes, tickets."""
    name = pdf.stem.lower()
    return pages >= 80 or any(w in name for w in ENGINEERING_WORDS)


def confirm(items: list[tuple[Path, int, bool]]) -> list[Path]:
    """Show what is about to be copied into the project and ask. Books stay on this machine,
    but they still land inside the project folder, so a stray shell glob should not do it silently."""
    print("\nAbout to copy into reference/ and index:")
    for pdf, pages, booky in items:
        mark = "book " if booky else "NOT A BOOK?"
        print(f"  {mark:12s} {pages:>5} pages  {pdf.name}")
    odd = [i for i in items if not i[2]]
    if odd:
        print(f"\n{len(odd)} of {len(items)} do not look like engineering books "
              "(short, and nothing bookish in the name).")
    try:
        answer = input("Add [a]ll, only the [b]ooks, or [n]othing? [b] ").strip().lower() or "b"
    except EOFError:
        answer = "b"
    if answer.startswith("n"):
        return []
    if answer.startswith("a"):
        return [i[0] for i in items]
    return [i[0] for i in items if i[2]]


def remove(name: str) -> None:
    ix = _load()
    if name not in ix:
        sys.exit(f"not in the library: {name}")
    shutil.rmtree(TEXT / name, ignore_errors=True)
    pdf = REF / ix[name]["file"]
    if pdf.exists():
        pdf.unlink()
    ix.pop(name)
    _save(ix)
    print(f"removed {name}")


def add(pdf: Path) -> None:
    pdf = Path(pdf)
    if pdf.parent != REF:
        REF.mkdir(exist_ok=True)
        target = REF / pdf.name
        if not target.exists():
            shutil.copy2(pdf, target)
        pdf = target
    name = pdf.stem[:60]
    out = TEXT / name
    out.mkdir(parents=True, exist_ok=True)
    pages = int(re.search(r"Pages:\s+(\d+)", _run(["pdfinfo", str(pdf)]).stdout).group(1))
    print(f"{pdf.name}: {pages} pages")

    # try the text layer first; fall back to OCR for scans
    _run(["pdftotext", "-layout", str(pdf), str(out / "all.txt")])
    whole = (out / "all.txt").read_text(errors="ignore") if (out / "all.txt").exists() else ""
    if len(whole.strip()) > 200 * pages:
        print("  text layer found, splitting by page")
        for i in range(1, pages + 1):
            r = _run(["pdftotext", "-layout", "-f", str(i), "-l", str(i), str(pdf), "-"])
            (out / f"page-{i:04d}.txt").write_text(r.stdout)
    else:
        if not shutil.which("tesseract"):
            sys.exit("This book is scanned and tesseract is not installed: brew install tesseract")
        print("  scanned book, running OCR (a few minutes)")
        for i in range(1, pages + 1):
            img = out / f"p{i:04d}"
            _run(["pdftoppm", "-r", "300", "-gray", "-png", "-f", str(i), "-l", str(i), str(pdf), str(img)])
            got = sorted(out.glob(f"p{i:04d}*.png"))
            if not got:
                continue
            _run(["tesseract", str(got[0]), str(out / f"page-{i:04d}"), "--psm", "1", "-l", "eng"])
            got[0].unlink()
            if i % 25 == 0:
                print(f"  {i}/{pages}")
    (out / "all.txt").unlink(missing_ok=True)
    ix = _load()
    ix[name] = {"file": pdf.name, "pages": pages}
    _save(ix)
    print(f"  indexed as '{name}'")


def find(term: str, limit: int = 40) -> None:
    ix = _load()
    if not ix:
        sys.exit("Nothing indexed yet: python tools/reference_library.py add <file.pdf>")
    hits = 0
    for name in ix:
        for page in sorted((TEXT / name).glob("page-*.txt")):
            text = page.read_text(errors="ignore")
            for line in text.splitlines():
                if re.search(term, line, re.I):
                    print(f"{name} p{int(page.stem.split('-')[1])}: {line.strip()[:120]}")
                    hits += 1
                    if hits >= limit:
                        print("...")
                        return
    print(f"{hits} line(s)")


def page(name: str, number: int) -> None:
    f = TEXT / name / f"page-{int(number):04d}.txt"
    if not f.exists():
        sys.exit(f"no such page: {f}")
    print(f.read_text(errors="ignore"))


def main(argv=None) -> int:
    args = (argv or sys.argv[1:])
    if not args:
        print(__doc__)
        return 1
    cmd, rest = args[0], args[1:]
    if cmd == "add":
        paths = [Path(f).expanduser() for f in rest]
        missing = [p for p in paths if not p.exists()]
        if missing:
            sys.exit("no such file: " + ", ".join(str(m) for m in missing))
        items = []
        for f in paths:
            try:
                pages = int(re.search(r"Pages:\s+(\d+)", _run(["pdfinfo", str(f)]).stdout).group(1))
            except Exception:
                pages = 0
            items.append((f, pages, looks_like_a_book(f, pages)))
        for f in confirm(items):
            add(f)
    elif cmd == "list":
        ix = _load()
        for name, meta in ix.items():
            got = len(list((TEXT / name).glob("page-*.txt")))
            print(f"{name}: {meta['pages']} pages, {got} indexed  ({meta['file']})")
        if not ix:
            print("empty")
    elif cmd == "remove":
        remove(rest[0])
    elif cmd == "find":
        find(" ".join(rest))
    elif cmd == "page":
        page(rest[0], int(rest[1]))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
