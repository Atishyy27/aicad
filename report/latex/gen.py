"""Write every project-derived table and listing for the LaTeX report. No number is typed by hand.

    PYTHONUTF8=1 .venv/Scripts/python.exe report/latex/gen.py
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

from aicad.joints import REGISTRY, parts_of  # noqa: E402
from aicad.optimise import MATERIALS, compare  # noqa: E402
from aicad.parse import Spec  # noqa: E402

TAB = HERE / "tables"
LST = HERE / "listings"
TAB.mkdir(exist_ok=True)
LST.mkdir(exist_ok=True)
FACTS = json.loads((ROOT / "report" / "facts.json").read_text(encoding="utf-8"))


def esc(s) -> str:
    s = str(s)
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"),
                 ("_", r"\_"), ("{", r"\{"), ("}", r"\}"), ("~", r"\~{}"), ("^", r"\^{}")):
        s = s.replace(a, b)
    return s.replace("\u00d8", "diam. ").replace("\u03c0", "pi")


BS = chr(92)
R = ">{" + BS + "raggedright" + BS + "arraybackslash}"
RL = ">{" + BS + "raggedleft" + BS + "arraybackslash}"
PREFIX = {"materials": "t5", "joints": "t7", "raw": "t7", "dims": "t7", "checks": "t7", "bhandari": "t7"}


def table(name: str, caption: str, colspec: str, head: list[str], rows: list[list[str]],
          size: str = r"\footnotesize") -> None:
    body = " \\\\\n".join(" & ".join(r) for r in rows)
    tex = (f"\\begin{{table}}[htbp]\n\\centering{size}\n\\caption{{{caption}}}\\label{{tab:{name}}}\n"
           f"\\begin{{tabularx}}{{\\textwidth}}{{{colspec}}}\n\\toprule\n{' & '.join(head)} \\\\\n\\midrule\n"
           f"{body} \\\\\n\\bottomrule\n\\end{{tabularx}}\n\\end{{table}}\n")
    (TAB / f"{PREFIX[name]}_{name}.tex").write_text(tex, encoding="utf-8")


def worst(d) -> float:
    return max(c.stress_mpa / c.allowable_mpa for c in d.checks)


# ---------------------------------------------------------------- Table 7.1, six joints
DUTIES = {
    "knuckle": dict(load_n=50000),
    "cotter": dict(load_n=35000),
    "sleeve_and_cotter": dict(load_n=50000),
    "gib_and_cotter": dict(load_n=50000),
    "nut_bolt": dict(load_n=20000, bolt_size=24, grip_mm=30),
    "flange_coupling": dict(torque_nm=500),
}
designs = {n: REGISTRY[n].design(**kw) for n, kw in DUTIES.items()}
rows, total_checks, ws = [], 0, []
for n, d in designs.items():
    j = REGISTRY[n]
    total_checks += len(d.checks)
    ws.append(round(worst(d) * 100))
    rows.append([esc(j.TITLE), esc(d.duty), str(len(parts_of(j, d.dims))), str(len(d.checks)),
                 str(round(worst(d) * 100)), "all satisfied" if d.all_passed else "FAILS"])
table("joints", "Design results for the six joints at the duties adopted", R+"X"+R+"Xrr"+RL+"p{2.4cm}"+R+"p{2cm}",
      ["Joint", "Duty adopted", r"Parts", r"Checks", r"Busiest check, \% of allowable", "Outcome"], rows)

# ---------------------------------------------------------------- Tables 7.2 to 7.4, knuckle
k = REGISTRY["knuckle"].design(load_n=50000)
D, dpin = k.dims["D"], k.dims["d"]
table("raw", r"Governing calculations for a knuckle joint carrying 50 kN, before rounding", "Xrl",
      ["Expression", "Computed, mm", "Effect"],
      [["Rod in direct tension", f"{k.raw['rod_tension']:.2f}", f"rod diameter adopted as {D:g} mm"],
       ["Pin in double shear", f"{k.raw['pin_shear']:.2f}",
        "not governing" if k.raw['pin_shear'] < k.raw['pin_bending'] else "governs"],
       ["Pin in bending", f"{k.raw['pin_bending']:.2f}",
        f"governs; pin diameter adopted as {dpin:g} mm" if k.raw['pin_bending'] >= k.raw['pin_shear']
        else "not governing"]])

LABELS = REGISTRY["knuckle"].LABELS
rows = []
for key, v in list(k.dims.items())[:10]:
    rule = k.rules.get(key, "")
    rule = re.sub(r"\s+", " ", rule)
    rows.append([f"\\texttt{{{esc(key)}}}", esc(LABELS.get(key, key)), f"{v:g}", esc(rule)])
table("dims", "Dimensions computed for the knuckle joint, with the rule behind each", R+"p{1.3cm}"+R+"p{3.6cm}r"+R+"X",
      ["Symbol", "Meaning", "Value, mm", "Rule and source"], rows, r"\scriptsize")

rows = []
for c in k.checks:
    rows.append([esc(c.name), f"\\texttt{{{esc(c.formula)}}}", f"{c.stress_mpa:g}",
                 f"{c.allowable_mpa:g}", str(round(100 * c.stress_mpa / c.allowable_mpa)),
                 "safe" if c.passed else "FAILS"])
table("checks", "Failure checks for the knuckle joint, evaluated at the actual load of 50 kN",
      R+"p{2.4cm}"+R+"Xrrr"+R+"p{1.2cm}", ["Failure mode", "Expression", "Stress, MPa", "Allowable, MPa", r"Utilisation, \%",
                 "Result"], rows)

# ---------------------------------------------------------------- Bhandari Ex 4.5
b = REGISTRY["knuckle"].design(load_n=50000, tension_mpa=80, shear_mpa=40, crushing_mpa=80,
                               design_factor=1.0)
book = {"D": 30, "D1": 35, "t": 40, "t1": 25, "d": 40, "d2": 80, "d3": 60}
rows, match = [], 0
for key, bv in book.items():
    sv = b.dims[key]
    ok = abs(sv - bv) < 1e-6
    match += ok
    rows.append([f"\\texttt{{{key}}}", esc(LABELS.get(key, key)), f"{bv:g}", f"{sv:g}", "yes" if ok else "NO"])
chk = {c.name: c for c in b.checks}
for nm, bv in (("eye tension", 31.25), ("fork tension", 25.0)):
    sv = chk[nm].stress_mpa
    ok = abs(sv - bv) < 0.01
    match += ok
    rows.append([esc(nm), "stress, MPa", f"{bv:g}", f"{sv:.2f}".rstrip("0").rstrip("."), "yes" if ok else "NO"])
table("bhandari", r"Bhandari Example 4.5 (50 kN, 30C8, factor of safety 5) against the software "
      r"run with the same inputs", "llrrl",
      ["Quantity", "Meaning", "Book", "Software", "Agrees"], rows)

# ---------------------------------------------------------------- 5.8 materials
by = {m["name"]: m for m in MATERIALS["materials"]}
res = compare(Spec(joint="knuckle", load_n=50000.0))
ok = [r for r in res if r.get("ok")]
light = min(ok, key=lambda r: r["mass_kg"])["material"] if ok else None
cheap = min(ok, key=lambda r: r["cost_inr"])["material"] if ok else None
rows = []
for r in res:
    m = by[r["material"]]
    if "size" not in r:
        rows.append([esc(r["material"]), esc(m["is_grade"]), str(m["tension"]), str(m["shear"]),
                     str(m["crushing"]), "--", "--", "--"])
        continue
    tag = " (lightest)" if r["material"] == light else (" (cheapest)" if r["material"] == cheap else "")
    rows.append([esc(r["material"] + tag), esc(m["is_grade"]), str(m["tension"]), str(m["shear"]),
                 str(m["crushing"]), f"{r['size']:g}", f"{r['mass_kg']:.2f}", f"{r['cost_inr']:,.0f}"])
table("materials", r"Knuckle joint for 50 kN designed in each material offered, as computed by the "
      "software", "Xlrrrrrr",
      ["Material", "Grade", r"$\sigma_t$, MPa", r"$\tau$, MPa", r"$\sigma_c$, MPa", "D, mm",
       "Mass, kg", "Cost, Rs"], rows)

# ---------------------------------------------------------------- numbers for the text
tests = FACTS["tests"].split()[0]
macros = {
    "NChecks": total_checks, "NTests": tests, "WorstMin": min(ws), "WorstMax": max(ws),
    "KnuckleRod": f"{D:g}", "KnucklePin": f"{dpin:g}", "BhandariMatch": match,
    "BhandariOf": len(book) + 2,
    "SizingLoad": f"{50000 * k.design_factor:,.0f}".replace(",", "{,}"),
}
(TAB / "nums.tex").write_text("".join(f"\\newcommand{{\\{k_}}}{{{v}}}\n" for k_, v in macros.items()),
                              encoding="utf-8")

# ---------------------------------------------------------------- Appendix B listings
src = (ROOT / "aicad" / "joints" / "knuckle.py").read_text(encoding="utf-8")
lines = src.splitlines()
tree = ast.parse(src)


def fn(name):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise KeyError(name)


def clean(text: str) -> str:
    return text.encode("ascii", "replace").decode().replace("?", "~") if False else \
        "".join(ch if ord(ch) < 128 else "?" for ch in text)


d_node = fn("design")
seg = lines[d_node.lineno - 1:d_node.end_lineno]
start = next(i for i, l in enumerate(seg) if l.strip().startswith("s = stresses_from"))
end = next(i for i, l in enumerate(seg) if l.strip().startswith("dims = {k: round"))
sizing = [l for l in seg[start:end + 1] if l.strip()]
(LST / "knuckle_sizing.txt").write_text(clean("\n".join(sizing)) + "\n", encoding="utf-8")
c_node = fn("_checks")
(LST / "knuckle_checks.txt").write_text(
    clean("\n".join(lines[c_node.lineno - 1:c_node.end_lineno])) + "\n", encoding="utf-8")
print("tables:", sorted(p.name for p in TAB.glob("*.tex")))
print("macros:", macros)
print("bhandari matches", match, "of", len(book) + 2)
