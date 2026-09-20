"""Pick the lightest or cheapest material that passes every check, and show the trade-off.

Mass comes from the solid volumes CadQuery computes for the real parts, times density.
"""
from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path

from .joints import REGISTRY

MATERIALS = json.loads((Path(__file__).parent / "data" / "materials.json").read_text())


def _volume_mm3(joint, dims) -> float:
    """Volume of the joint itself: the display rod stubs are cut to 1 mm so they do not skew the comparison."""
    dims = dict(dims)
    if "rod_len" in dims:
        dims["rod_len"] = 1.0
    return sum(p.val().Volume() for p in joint.build_parts(dims).values())


def compare(spec) -> list[dict]:
    joint = REGISTRY[spec.joint]
    rows = []
    for m in MATERIALS["materials"]:
        s = replace(spec, tension_mpa=m["tension"], shear_mpa=m["shear"], crushing_mpa=m["crushing"], notes=[])
        try:
            d = joint.design(**s.design_kwargs())
        except ValueError as exc:
            rows.append({"material": m["name"], "ok": False, "reason": str(exc)})
            continue
        vol = _volume_mm3(joint, d.dims)
        mass = vol * 1e-9 * m["density"]
        rows.append({
            "material": m["name"], "is_grade": m.get("is_grade", ""), "ok": d.all_passed, "mass_kg": mass,
            "cost_inr": mass * m["rate_inr_per_kg"], "rate": m["rate_inr_per_kg"],
            "size": d.dims.get("D", d.dims.get("d")), "spec": s,
        })
    return rows


def optimise(spec, text: str):
    from .redesign import FollowUp
    goal = "cost" if re.search(r"\bcheap", text, re.I) else "mass"
    rows = [r for r in compare(spec) if r.get("ok")]
    if not rows:
        return FollowUp("unclear", "No material in the table passes every check for this load.")
    key = "cost_inr" if goal == "cost" else "mass_kg"
    rows.sort(key=lambda r: r[key])
    best = rows[0]
    table = "; ".join(f"{r['material']}: {r['mass_kg']:.2f} kg, Rs {r['cost_inr']:,.0f}" for r in rows)
    msg = (f"{'Cheapest' if goal == 'cost' else 'Lightest'} passing choice: {best['material']} "
           f"({best['is_grade']}) at {best['mass_kg']:.2f} kg, material cost about Rs {best['cost_inr']:,.0f} "
           f"at Rs {best['rate']:g}/kg. All passing options: {table}. "
           f"Stresses and rates are UNVERIFIED.")
    return FollowUp("change", msg, spec=best["spec"],
                    changes=[f"material: {best['material']} ({best['is_grade']})",
                             f"goal: lowest {'cost' if goal == 'cost' else 'mass'}"])
