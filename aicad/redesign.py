"""Follow-up requests on an existing design.

  change   "make it 80 kN", "shear 50 MPa", "rod 40 mm", "use M20", "change it to a cotter joint"
  explain  "why is the pin 45 mm", "explain d2"
  limit    "how much load can this take", "max load"   (for the exact dimensions shown)
  optimise "make it lighter", "cheapest material"        (see optimise.py)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

from .explain import explain_dim, find_symbol
from .joints import REGISTRY
from .parse import Spec, parse

_EXPLAIN = re.compile(r"\b(why|explain|how (?:is|was|did)|where does|what decides|reason)\b", re.I)
_LIMIT = re.compile(r"\b(max(?:imum)?\s+load|how much (?:load|force)|load capacity|what load can|"
                    r"strongest load|carry at most|safe load)\b", re.I)
_MARGIN = re.compile(r"margin|\bsafety\b|\bsafer\b|factor of safety|design factor|\bfos\b|\bstronger\b|"
                     r"more capacity|less stressed|headroom", re.I)
_OPTIMISE = re.compile(r"\b(light(?:er|est)?|cheap(?:er|est)?|optimi[sz]e|lowest mass|less material|best material)\b", re.I)


@dataclass
class FollowUp:
    kind: str                      # change | explain | limit | optimise | unclear
    message: str
    spec: Spec | None = None       # new spec for "change"
    changes: list[str] = field(default_factory=list)
    value: float | None = None     # newtons for "limit"
    governing: str | None = None


def max_load(joint, design) -> tuple[float, str]:
    """Largest load these exact dimensions carry with every check passing, and the check that limits it.
    Every stress here is proportional to the load, so one evaluation at a reference load is enough."""
    ref = 1000.0
    checks = joint._checks(ref, design.dims, design.stresses)
    ratios = [(c.allowable_mpa / c.stress_mpa, c.name) for c in checks if c.stress_mpa > 0]
    r, name = min(ratios)
    return ref * r, name


def _diff(old, new) -> list[str]:
    out = []
    for k in sorted(set(old.dims) | set(new.dims), key=lambda k: list(new.dims).index(k) if k in new.dims else 99):
        a, b = old.dims.get(k), new.dims.get(k)
        if a != b:
            out.append(f"{k}: {a:g} -> {b:g}" if a is not None and b is not None else f"{k}: {a} -> {b}")
    return out


def follow_up(current: Spec, text: str, mode: str = "auto", runner=None) -> FollowUp:
    joint = REGISTRY.get(current.joint or "")
    design = joint.design(**current.design_kwargs()) if joint else None

    if design is not None and _EXPLAIN.search(text):
        key = find_symbol(text, design, joint)
        if key:
            return FollowUp("explain", explain_dim(design, joint, key))
        return FollowUp("unclear", "Which dimension? Name it (for example d2) or describe it (for example the pin).")

    if design is not None and _LIMIT.search(text):
        P, name = max_load(joint, design)
        msg = (f"With these exact dimensions the joint carries at most {P:,.0f} N ({P / 1000:.1f} kN). "
               f"The first check to reach its limit is {name}.")
        if design.load_n:
            msg += f" The current load, {design.load_n:,.0f} N, uses {100 * design.load_n / P:.0f}% of that."
        return FollowUp("limit", msg, value=P, governing=name)

    if _MARGIN.search(text):
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:x|times)?", text)
        want = float(m.group(1)) if m and 1.0 <= float(m.group(1)) <= 5.0 else (current.design_factor or 1.25) + 0.25
        want = round(min(want, 4.0), 2)
        new = replace(current, design_factor=want, notes=[])
        j = REGISTRY.get(new.joint or "")
        if j is None:
            return FollowUp("unclear", "Pick a joint first.")
        nd = j.design(**new.design_kwargs())
        worst = max((c.stress_mpa / c.allowable_mpa for c in nd.checks), default=0)
        msg = (f"Design factor set to {want:g}: it is now sized for {want:g} times your load, so the busiest "
               f"check sits at {100 * worst:.0f}% of its allowed stress instead of near 100%. "
               f"Everything gets bigger and heavier as a result.")
        if design is not None:
            moved = _diff(design, nd)
            if moved:
                msg += " Dimensions that moved: " + ", ".join(moved) + "."
        return FollowUp("change", msg, spec=new, changes=[f"design factor: {current.design_factor or 1.25} -> {want:g}"])

    if design is not None and _OPTIMISE.search(text):
        from .optimise import optimise
        return optimise(current, text)

    kwargs = {"mode": mode} if runner is None else {"mode": mode, "runner": runner}
    delta = parse(text, **kwargs)
    new = replace(current, notes=[])
    changed_fields = []
    if delta.joint and delta.joint != current.joint and re.search(
            r"\b(change|switch|make it|instead|convert)\b", text, re.I):
        new.joint = delta.joint
        changed_fields.append(f"joint: {current.joint} -> {delta.joint}")
    for key in ("load_n", "rod_diameter_mm", "bolt_size", "grip_mm", "tension_mpa", "shear_mpa", "crushing_mpa"):
        v = getattr(delta, key)
        if v is not None and v != getattr(current, key):
            changed_fields.append(f"{key}: {getattr(current, key)} -> {v}")
            setattr(new, key, v)
    if not changed_fields:
        return FollowUp("unclear", "I could not find a change, a why-question or a load question in that. "
                                   "Try: 'make it 80 kN', 'why is the pin 45 mm', 'how much load can this take'.")

    new_joint = REGISTRY.get(new.joint or "")
    if new_joint is None:
        return FollowUp("unclear", f"'{new.joint}' is not built yet.", spec=None, changes=changed_fields)
    try:
        new_design = new_joint.design(**new.design_kwargs())
    except ValueError as exc:
        return FollowUp("unclear", f"Cannot size that: {exc}", changes=changed_fields)
    dims_changed = _diff(design, new_design) if (design is not None and new_joint is joint) else []
    msg = "Changed " + "; ".join(changed_fields) + "."
    if dims_changed:
        msg += " Dimensions that moved: " + ", ".join(dims_changed) + "."
    elif new_joint is joint:
        msg += " No dimension had to change: the current sizes already satisfy it."
    if not new_design.all_passed:
        msg += " Warning: at least one check now fails."
    return FollowUp("change", msg, spec=new, changes=changed_fields + dims_changed)
