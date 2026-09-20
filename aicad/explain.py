"""Explain any number the tool produced: the formula, the numbers put into it, and the result.

Also computes utilisation (worst stress / allowable) per part, for the weak-spot view.
"""
from __future__ import annotations

import math
import re

from .design import Check, Design

_IDENT = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*)\b")


def _fmt(v: float) -> str:
    return f"{v:,.0f}" if abs(v) >= 1000 else f"{v:g}"


def substitute(formula: str, values: dict) -> str:
    """'4P / (pi D^2)' -> '4 × 50,000 / (π × 30²)'. Unknown symbols are left as they are."""
    s = re.sub(r"(\d)([A-Za-z])", r"\1 × \2", formula)

    def repl(m):
        name = m.group(1)
        if name == "pi":
            return "π"
        if name in values and values[name] is not None:
            return _fmt(values[name])
        return name

    s = _IDENT.sub(repl, s)
    s = s.replace("^2", "²").replace("^3", "³")
    prev = None
    while prev != s:  # repeat: each pass can only insert one × per overlapping pair
        prev = s
        s = re.sub(r"(\d|\)|²|³)\s+(\(|π|\d)", r"\1 × \2", s)
        s = re.sub(r"π\s+(\d|\()", r"π × \1", s)
    return s


def check_values(design: Design) -> dict:
    return {"P": design.load_n, **design.dims}


def explain_check(design: Design, check: Check) -> str:
    worked = substitute(check.formula.split(",")[0], check_values(design))
    extra = ""
    if "," in check.formula:  # e.g. "..., M = P/2 (t1/3 + t/4)"
        rest = check.formula.split(",", 1)[1].strip()
        extra = f" where {rest} = {substitute(rest.split('=', 1)[1].strip(), check_values(design))}"
    pct = 100 * check.stress_mpa / check.allowable_mpa
    verdict = "pass" if check.passed else "FAIL"
    return (f"{check.name}: {check.formula.split(',')[0]} = {worked}{extra} = {check.stress_mpa:.1f} MPa, "
            f"allowed {check.allowable_mpa:g} MPa, so {verdict} ({pct:.0f}% of the allowed stress used)")


def explain_dim(design: Design, joint, key: str) -> str:
    if key not in design.dims:
        raise KeyError(key)
    v = design.dims[key]
    label = joint.LABELS.get(key, key)
    P = design.load_n
    s = design.stresses
    lines = [f"{key} ({label}) = {v:g} mm."]
    raw = design.raw

    if key in ("D", "d") and "rod_tension" in raw and (joint.NAME != "knuckle" or key == "D"):
        lines.append(f"Rod in tension: diameter = √(4P / (π σt)) = √(4 × {_fmt(P or 0)} / (π × {s['tension']:g})) "
                     f"= {raw['rod_tension']:.2f} mm, rounded up to the next preferred size, {v:g} mm.")
    elif joint.NAME == "knuckle" and key == "d" and P is not None:
        lines.append(f"Starts equal to the rod diameter, {design.dims['D']:g} mm.")
        lines.append(f"Double shear needs √(2P / (π τ)) = √(2 × {_fmt(P)} / (π × {s['shear']:g})) = "
                     f"{raw['pin_shear']:.2f} mm.")
        lines.append(f"Bending needs √(16P (t1/3 + t/4 per mm of d) / (π σb)) = {raw['pin_bending']:.2f} mm.")
        lines.append(f"The largest requirement governs: {design.rules.get('d', '')}.")
    elif joint.NAME == "nut_bolt" and key == "d":
        lines.append(design.rules.get("d", ""))
    else:
        rule = design.rules.get(key)
        lines.append(rule if rule else f"A modelling choice from aicad/data/{joint.NAME}.json, not a design-book rule.")
    for n in design.notes:
        if n.startswith(f"{key} raised"):
            lines.append(n)
    uses = [c for c in design.checks if key in re.findall(r"\b[A-Za-z][A-Za-z0-9_]*\b", c.formula)]
    if uses:
        lines.append("Used in: " + "; ".join(explain_check(design, c) for c in uses))
    if not design.verified_against_book:
        lines.append("The rule values are not yet checked against the design book.")
    return " ".join(lines)


def find_symbol(question: str, design: Design, joint) -> str | None:
    """Map 'why is the pin 45 mm' or 'explain d2' to a dimension key."""
    q = question.lower()
    for key in sorted(design.dims, key=len, reverse=True):
        if re.search(rf"\b{re.escape(key.lower())}\b", q):
            return key
    q_words = re.findall(r"[a-z]+", q)

    def hit(w):
        return any(qw == w or (len(qw) >= 4 and (w.startswith(qw) or qw.startswith(w[:5]))) for qw in q_words)

    best, best_score = None, 0
    for key, label in joint.LABELS.items():
        words = [w for w in re.findall(r"[a-z]+", label.lower()) if len(w) > 2]
        score = sum(1 for w in words if hit(w))
        if score > best_score:
            best, best_score = key, score
    if best is None:
        nums = re.findall(r"\d+(?:\.\d+)?", q)
        for n in nums:
            for key, v in design.dims.items():
                if math.isclose(float(n), v, abs_tol=1e-6):
                    return key
    return best


def utilisation(design: Design, joint) -> dict:
    """part -> (worst utilisation 0..n, governing check name) or (None, None) if no check covers it."""
    from .joints import parts_of
    out: dict = {p: (None, None) for p in parts_of(joint, design.dims)}
    mapping = getattr(joint, "CHECK_PARTS", {})
    for c in design.checks:
        u = c.stress_mpa / c.allowable_mpa
        for part in mapping.get(c.name, []):
            if part not in out:   # e.g. a coupling check lists bolt_1..6 but this design has 3
                continue
            cur = out[part][0]
            if cur is None or u > cur:
                out[part] = (u, c.name)
    return out


def utilisation_colour(u: float | None) -> tuple[float, float, float]:
    """green (low) -> yellow (0.75) -> red (1.0 and above); grey when not checked."""
    if u is None:
        return (0.6, 0.6, 0.6)
    u = max(0.0, min(u, 1.0))
    if u <= 0.75:
        f = u / 0.75
        return (0.15 + 0.8 * f, 0.7, 0.2)
    f = (u - 0.75) / 0.25
    return (0.95, 0.7 * (1 - f) + 0.1 * f, 0.2 * (1 - f))
