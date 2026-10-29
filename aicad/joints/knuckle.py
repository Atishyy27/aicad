"""Knuckle joint: sizing and geometry for 5 parts.

Axes: the knuckle pin runs along Z, the two rods run along X, origin at the pin
centre. The single-eye rod sits on the -X side, the fork on the +X side.
Every part is built the way you would in NX by hand: sketch a circle or a
rectangle, extrude it, join solids, then cut the holes.
"""
from __future__ import annotations

import math

from ..design import (DEFAULT_DESIGN_FACTOR, Check, Design, ceil_mm, check_positive, load_data,
                      next_preferred, sizing_load, stresses_from, times)

NAME = "knuckle"
TITLE = "Knuckle joint"
DATA = load_data(NAME)
PARTS = DATA["parts"]
COLORS = {
    "single_eye_rod": (0.30, 0.55, 0.85),
    "fork": (0.85, 0.45, 0.25),
    "knuckle_pin": (0.75, 0.75, 0.75),
    "collar": (0.35, 0.70, 0.40),
    "taper_pin": (0.90, 0.80, 0.20),
}
LABELS = {
    "D": "rod diameter",
    "d": "pin diameter",
    "d2": "eye outer diameter",
    "d3": "pin head and collar diameter",
    "t": "eye thickness",
    "t1": "fork plate thickness",
    "t2": "pin head thickness",
    "collar_t": "collar thickness",
    "taper_d": "taper pin diameter (big end)",
    "clearance": "gap between eye and fork base",
    "fork_base": "fork base length",
    "rod_len": "rod length shown",
}


def design(
    load_n=None,
    rod_diameter_mm=None,
    tension_mpa=None,
    shear_mpa=None,
    crushing_mpa=None,
    bending_mode=None,
    design_factor=None,
    **_ignored,
) -> Design:
    if load_n is None and rod_diameter_mm is None:
        raise ValueError("give a load or a rod diameter")
    check_positive(load_n, rod_diameter=rod_diameter_mm)
    s = stresses_from(DATA, tension_mpa, shear_mpa, crushing_mpa)
    sizes = DATA["preferred_diameters_mm"]
    props = DATA["proportions"]
    k_t, k_t1 = props["eye_thickness_t"]["times"], props["fork_thickness_t1"]["times"]
    bending_mode = bending_mode or DATA["pin_bending"]["mode"]
    factor = float(design_factor if design_factor is not None else DEFAULT_DESIGN_FACTOR)
    P = load_n
    Pd = sizing_load(P, factor)
    raw, notes = {}, []

    if rod_diameter_mm is not None:
        D = float(rod_diameter_mm)
    else:
        raw["rod_tension"] = math.sqrt(4 * Pd / (math.pi * s["tension"]))
        D = next_preferred(raw["rod_tension"], sizes)

    # every thickness comes from the ROD diameter (NPTEL IIT KGP M4L2 fig 4.2.3.1), rounded up to a
    # whole mm before anything is sized off it, so the pin is checked against the plate actually cut;
    # the pin is sized separately and raised when shear or bending needs it
    t_eye, t_fork = ceil_mm(k_t * D), ceil_mm(k_t1 * D)
    d = props["pin_diameter_d"]["times"] * D
    governing = "pin = rod diameter"
    if P is not None:
        raw["pin_shear"] = math.sqrt(2 * Pd / (math.pi * s["shear"]))
        if raw["pin_shear"] > d + 1e-9:
            d, governing = next_preferred(raw["pin_shear"], sizes), "pin double shear"
        # sigma_b = 16 P (t1/3 + t/4) / (pi d^3), with t and t1 fixed by the rod diameter
        raw["pin_bending"] = (16 * Pd * (t_fork / 3 + t_eye / 4) / (math.pi * s["bending"])) ** (1 / 3)
        if bending_mode == "size" and raw["pin_bending"] > d + 1e-9:
            d, governing = next_preferred(raw["pin_bending"], sizes), "pin bending"
            notes.append(
                f"Pin raised to {d:g} mm for bending (needs {raw['pin_bending']:.1f} mm), the same step the "
                "NPTEL worked problem takes. Set pin_bending.mode to 'check_only' to keep the pin equal to the rod."
            )

    # the hole has to fit the final pin, so the eye and fork must grow with it. The NPTEL
    # worked problem raises the pin for bending but then checks the eye against the original
    # pin size; done that way its own eye-shear check fails, so we grow the eye instead.
    d2 = props["eye_outer_diameter_d2"]["times"] * D
    if P is not None and d > props["pin_diameter_d"]["times"] * D:
        grown = False
        for _ in range(400):
            trial = dict(D=D, d=d, d2=d2, t=t_eye, t1=t_fork)
            if all(c.passed for c in _checks(Pd, trial, s) if c.name.startswith(("eye", "fork"))):
                break
            d2 += 1
            grown = True
        if grown:
            notes.append(f"Eye and fork outer diameter grown to {d2:g} mm because the bigger pin "
                         "leaves less metal around the hole.")

    dims = {
        "D": D,
        "d": d,
        "d2": d2,
        "d3": next_preferred(props["head_collar_diameter_d3"]["times"] * D, sizes),
        "t": t_eye,
        "t1": t_fork,
        "t2": ceil_mm(props["head_thickness_t2"]["times"] * D),
    }
    m = DATA["modelling_choices"]
    dims["collar_t"] = ceil_mm(times(m["collar_thickness"], d))
    dims["taper_d"] = ceil_mm(times(m["taper_pin_diameter"], D))
    dims["clearance"] = ceil_mm(times(m["fork_clearance"], d))
    dims["fork_base"] = times(m["fork_base_length"], d)
    dims["rod_len"] = m["rod_length"]["times"] * dims["d2"]
    dims = {k: round(v, 3) for k, v in dims.items()}

    def rule(key, prop_key, rounding="rounded up to a whole mm"):
        p = props[prop_key]
        return f"{key} = {p['times']} x D, the rod diameter ({p['meaning']}), {rounding} [{p['source']}]"

    rules = {
        "D": "given by user" if rod_diameter_mm is not None
        else "rod in tension: D = sqrt(4P / (pi sigma_t)), rounded up to a preferred size",
        "d": f"governed by {governing}",
        "d2": rule("d2", "eye_outer_diameter_d2"),
        "d3": rule("d3", "head_collar_diameter_d3", "rounded up to a preferred size"),
        "t": rule("t", "eye_thickness_t"),
        "t1": rule("t1", "fork_thickness_t1"),
        "t2": rule("t2", "head_thickness_t2"),
    }

    checks = _checks(P, dims, s) if P is not None else []

    if factor > 1 and P is not None:
        notes.insert(0, f"Sized for {factor:g} x the given load ({Pd:,.0f} N), then checked at {P:,.0f} N. "
                        "That margin is why the checks sit below their limits.")
    return Design(
        joint=NAME, load_n=P, stresses=s, dims=dims, rules=rules, checks=checks, notes=notes,
        design_factor=factor, verified_against_book=DATA["verified_against_book"], raw=raw,
    )


def _checks(P, dims, s):
    D, dd, d2, t, t1 = dims["D"], dims["d"], dims["d2"], dims["t"], dims["t1"]
    M = P / 2 * (t1 / 3 + t / 4)
    return [
        Check("rod tension", 4 * P / (math.pi * D**2), s["tension"], "4P / (pi D^2)"),
        Check("pin double shear", P / (2 * math.pi / 4 * dd**2), s["shear"], "P / (2 pi/4 d^2)"),
        Check("pin bending", 32 * M / (math.pi * dd**3), s["bending"], "32M / (pi d^3), M = P/2 (t1/3 + t/4)"),
        Check("eye tension", P / ((d2 - dd) * t), s["tension"], "P / ((d2 - d) t)"),
        Check("eye shear", P / ((d2 - dd) * t), s["shear"], "P / ((d2 - d) t)"),
        Check("eye crushing", P / (dd * t), s["crushing"], "P / (d t)"),
        Check("fork tension", P / ((d2 - dd) * 2 * t1), s["tension"], "P / ((d2 - d) 2 t1)"),
        Check("fork shear", P / ((d2 - dd) * 2 * t1), s["shear"], "P / ((d2 - d) 2 t1)"),
        Check("fork crushing", P / (dd * 2 * t1), s["crushing"], "P / (d 2 t1)"),
    ]


def build_parts(dims: dict):
    import cadquery as cq

    from ._shapes import box, disc, hole_x, hole_z, rod_along_x, soften

    D, d, d2, d3 = dims["D"], dims["d"], dims["d2"], dims["d3"]
    t, t1, t2 = dims["t"], dims["t1"], dims["t2"]
    collar_t, taper_d = dims["collar_t"], dims["taper_d"]
    clearance, base_len, rod_len = dims["clearance"], dims["fork_base"], dims["rod_len"]

    inner = t / 2
    outer = t / 2 + t1
    span = outer + t2 + collar_t + d2
    base_x = d2 / 2 + clearance

    eye_rod = (
        disc(d2, t, -t / 2)
        .union(rod_along_x(D, -(d2 / 2 + rod_len), d2 / 2 + rod_len))
        .cut(hole_z(d, span))
        .clean()
    )

    # a forged fork has no sharp outer corners: the plate rims and the long edges of the base
    # share one radius, so the plates run into the base without a step
    r_fork = max(2.0, round(min(0.4 * t1, 0.15 * d2)))

    def plate(z0, outer_face):
        p = disc(d2, t1, z0).union(box(0, base_x, -d2 / 2, d2 / 2, z0, z0 + t1)).clean()
        return soften(p, lambda w: w.faces(outer_face).edges().fillet(r_fork))

    base = box(base_x, base_x + base_len, -d2 / 2, d2 / 2, -outer, outer)
    base = soften(base, lambda w: w.edges("|X").fillet(r_fork))
    base = soften(base, lambda w: w.faces(">X").edges().fillet(r_fork / 2))

    fork = (
        plate(inner, ">Z")
        .union(plate(-outer, "<Z"))
        .union(base)
        .union(rod_along_x(D, base_x + base_len / 2, base_len / 2 + rod_len))
        .cut(hole_z(d, span))
        .clean()
    )

    collar_bottom = -outer - collar_t
    taper_z = -outer - collar_t / 2
    pin = (
        disc(d, outer - collar_bottom, collar_bottom)
        .union(disc(d3, t2, outer))
        .cut(hole_x(taper_d, taper_z, span))
        .clean()
    )

    collar = (
        disc(d3, collar_t, collar_bottom)
        .cut(hole_z(d, span))
        .cut(hole_x(taper_d, taper_z, span))
        .clean()
    )

    length = d3 + 2 * max(taper_d, 3.0)
    r_big = taper_d / 2
    r_small = r_big - length / (2 * DATA["modelling_choices"]["taper_ratio_on_diameter"])
    cone = cq.Solid.makeCone(
        r_big, r_small, length, pnt=cq.Vector(-length / 2, 0, taper_z), dir=cq.Vector(1, 0, 0)
    )

    # finish the edges the way a machined part leaves the shop: chamfered rod ends and bores,
    # rounded eye and fork faces, a radius where the rod runs into the eye
    e = max(1.5, round(0.06 * D))
    eye_rod = soften(eye_rod, lambda w: w.faces(">Z or <Z").edges().fillet(max(e, round(0.12 * t))))
    eye_rod = soften(eye_rod, lambda w: w.faces("<X").chamfer(e))
    eye_rod = soften(eye_rod, lambda w: w.edges(cq.selectors.BoxSelector(
        (-d2 / 2 - D, -d2, -d2), (-d2 / 2 + D / 2, d2, d2))).edges("not %CIRCLE").fillet(e))
    fork = soften(fork, lambda w: w.faces(">X").chamfer(e))
    pin = soften(pin, lambda w: w.faces("<Z").chamfer(e))
    pin = soften(pin, lambda w: w.faces(">Z").edges().fillet(e))
    collar = soften(collar, lambda w: w.faces(">Z or <Z").edges().chamfer(e / 2))

    return {
        "single_eye_rod": eye_rod,
        "fork": fork,
        "knuckle_pin": pin,
        "collar": collar,
        "taper_pin": cq.Workplane("XY").add(cone),
    }


# rod axis and pin axis in every view
CENTRE_LINES = {"FRONT VIEW": "hv", "TOP VIEW (PLAN)": "hv", "LEFT SIDE VIEW": "hv"}


def drawing_dims(dims: dict) -> list[dict]:
    """Dimensions drawn on the sheet: view name, two 3D points, direction, paper offset (mm).
    orient "note" is a leader callout from the point p1."""
    D, d2, d3, t, t1, t2 = (dims[k] for k in ("D", "d2", "d3", "t", "t1", "t2"))
    d, collar_t, taper_d = dims["d"], dims["collar_t"], dims["taper_d"]
    outer = t / 2 + t1
    x_rod = -(d2 / 2 + dims["rod_len"]) + 4
    taper_z = -outer - collar_t / 2
    taper_len = d3 + 2 * max(taper_d, 3.0)
    return [
        {"view": "FRONT VIEW", "p1": [taper_len / 2, 0, taper_z], "orient": "note", "to": (14, 10),
         "text": f"TAPER PIN Ø{taper_d:g}, TAPER 1:50"},
        {"view": "FRONT VIEW", "p1": [d3 / 2, 0, outer + t2 / 2], "orient": "note", "to": (16, -10),
         "text": f"KNUCKLE PIN Ø{d:g}, HEAD Ø{d3:g}x{t2:g}"},
        {"view": "FRONT VIEW", "p1": [-d3 / 2, 0, taper_z], "orient": "note", "to": (-14, 10),
         "text": f"COLLAR Ø{d3:g}x{collar_t:g}"},
        {"view": "LEFT SIDE VIEW", "p1": [0, d2 / 2, -t / 2], "p2": [0, d2 / 2, t / 2], "orient": "v", "offset": -7,
         "text": f"{t:g}"},
        {"view": "LEFT SIDE VIEW", "p1": [0, d2 / 2, t / 2], "p2": [0, d2 / 2, outer], "orient": "v", "offset": -13,
         "text": f"{t1:g}"},
        {"view": "TOP VIEW (PLAN)", "p1": [-d / 2, d2 / 2, 0], "p2": [d / 2, d2 / 2, 0], "orient": "h", "offset": 14,
         "text": f"Ø{d:g}"},
        {"view": "FRONT VIEW", "p1": [x_rod, 0, -D / 2], "p2": [x_rod, 0, D / 2], "orient": "v", "offset": -7, "text": f"Ø{D:g}"},
        {"view": "LEFT SIDE VIEW", "p1": [0, -d2 / 2, -outer], "p2": [0, -d2 / 2, outer], "orient": "v", "offset": 7, "text": f"{2 * outer:g}"},
        {"view": "FRONT VIEW", "p1": [-d3 / 2, 0, outer + t2], "p2": [d3 / 2, 0, outer + t2], "orient": "h", "offset": -6, "text": f"Ø{d3:g}"},
        {"view": "TOP VIEW (PLAN)", "p1": [-d2 / 2, -d2 / 2, 0], "p2": [d2 / 2, -d2 / 2, 0], "orient": "h", "offset": 7, "text": f"Ø{d2:g}"},
    ]


def explode(dims: dict) -> dict:
    """Where each part moves in the exploded view (mm)."""
    L = dims["d2"]
    return {"single_eye_rod": (-1.0 * L, 0, 0), "fork": (0.5 * L, 0, 0), "knuckle_pin": (0, 0, 2.2 * L),
            "collar": (0, 0, -1.3 * L), "taper_pin": (0, 0, -2.0 * L)}


# which parts each strength check is about (for the weak-spot view)
CHECK_PARTS = {
    "rod tension": ["single_eye_rod", "fork"],
    "pin double shear": ["knuckle_pin"],
    "pin bending": ["knuckle_pin"],
    "eye tension": ["single_eye_rod"], "eye shear": ["single_eye_rod"], "eye crushing": ["single_eye_rod"],
    "fork tension": ["fork"], "fork shear": ["fork"], "fork crushing": ["fork"],
}
