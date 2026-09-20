"""Sleeve and cotter joint: sizing and geometry for 5 parts.

Axes: rods along X, the sleeve centred on the origin, two cotters driven down
along Z through slots at x = -xc and x = +xc. Cotter thickness t runs along Y,
width b along X. Each rod has an enlarged end (d2) inside the sleeve.
"""
from __future__ import annotations

import math

from ..design import Check, Design, ceil_mm, check_positive, load_data, next_preferred, stresses_from, times

NAME = "sleeve_and_cotter"
TITLE = "Sleeve and cotter joint"
DATA = load_data(NAME)
PARTS = DATA["parts"]
COLORS = {
    "rod_left": (0.30, 0.55, 0.85),
    "rod_right": (0.40, 0.65, 0.90),
    "sleeve": (0.85, 0.45, 0.25),
    "cotter_left": (0.90, 0.80, 0.20),
    "cotter_right": (0.95, 0.85, 0.30),
}
LABELS = {
    "d": "rod diameter",
    "d2": "enlarged rod end diameter",
    "d1": "sleeve outer diameter",
    "t": "cotter thickness",
    "b": "cotter width",
    "a": "rod end beyond slot",
    "c": "sleeve end beyond slot",
    "gap": "gap between rod ends",
    "xc": "slot centre from sleeve centre",
    "L": "sleeve length",
    "overhang": "cotter sticks out past the sleeve",
    "rod_len": "rod length shown",
}
_FIX = {
    "rod end tension": "d2",
    "sleeve tension": "d1",
    "cotter shear": "b",
    "rod end crushing": "t",
    "sleeve crushing": "d1",
    "rod end shear": "a",
    "sleeve end shear": "c",
}


def _checks(P, dm, s):
    d, d1, d2, t, b, a, c = (dm[k] for k in ("d", "d1", "d2", "t", "b", "a", "c"))
    q = math.pi / 4
    return [
        Check("rod tension", P / (q * d**2), s["tension"], "P / (pi/4 d^2)"),
        Check("rod end tension", P / (q * d2**2 - d2 * t), s["tension"], "P / (pi/4 d2^2 - d2 t)"),
        Check("sleeve tension", P / (q * (d1**2 - d2**2) - (d1 - d2) * t), s["tension"],
              "P / (pi/4 (d1^2 - d2^2) - (d1 - d2) t)"),
        Check("cotter shear", P / (2 * b * t), s["shear"], "P / (2 b t)"),
        Check("rod end crushing", P / (d2 * t), s["crushing"], "P / (d2 t)"),
        Check("sleeve crushing", P / ((d1 - d2) * t), s["crushing"], "P / ((d1 - d2) t)"),
        Check("rod end shear", P / (2 * a * d2), s["shear"], "P / (2 a d2)"),
        Check("sleeve end shear", P / (2 * (d1 - d2) * c), s["shear"], "P / (2 (d1 - d2) c)"),
    ]


def _keep_walls(dm):
    dm["d2"] = max(dm["d2"], dm["d"] + 2)
    dm["d1"] = max(dm["d1"], dm["d2"] + 6)


def design(load_n=None, rod_diameter_mm=None, tension_mpa=None, shear_mpa=None, crushing_mpa=None, **_ignored) -> Design:
    if load_n is None and rod_diameter_mm is None:
        raise ValueError("give a load or a rod diameter")
    check_positive(load_n, rod_diameter=rod_diameter_mm)
    s = stresses_from(DATA, tension_mpa, shear_mpa, crushing_mpa)
    P = load_n
    raw, notes = {}, []

    if rod_diameter_mm is not None:
        d = float(rod_diameter_mm)
    else:
        raw["rod_tension"] = math.sqrt(4 * P / (math.pi * s["tension"]))
        d = next_preferred(raw["rod_tension"], DATA["preferred_diameters_mm"])

    props = DATA["proportions"]
    dm = {"d": d}
    for key, p in props.items():
        dm[key] = ceil_mm(p["times"] * d)
    _keep_walls(dm)
    start = dict(dm)

    checks = []
    if P is not None:
        for _ in range(500):
            checks = _checks(P, dm, s)
            failing = [c for c in checks if not c.passed and c.name in _FIX]
            if not failing:
                break
            for key in {_FIX[c.name] for c in failing}:
                dm[key] += 1
            _keep_walls(dm)
        else:
            notes.append("Could not satisfy every check within 500 mm of adjustment.")
        for key in props:
            if dm[key] != start[key]:
                notes.append(f"{key} raised from {start[key]:g} to {dm[key]:g} mm so every check passes.")

    m = DATA["modelling_choices"]
    dm["gap"] = times(m["rod_gap"], d)
    dm["xc"] = dm["gap"] / 2 + dm["a"] + dm["b"] / 2
    dm["L"] = 2 * (dm["xc"] + dm["b"] / 2 + dm["c"])
    dm["overhang"] = times(m["cotter_overhang"], d)
    dm["rod_len"] = m["rod_length"]["times"] * d
    dm = {k: round(v, 3) for k, v in dm.items()}

    rules = {"d": "given by user" if rod_diameter_mm is not None
             else "rod in tension: d = sqrt(4P / (pi sigma_t)), rounded up to a preferred size",
             "L": "2 (xc + b/2 + c), from the slot layout",
             "xc": "gap/2 + a + b/2"}
    for key, p in props.items():
        rules[key] = f"{key} = {p['times']} x d, rounded up to whole mm ({p['meaning']}) [{p['source']}]"

    return Design(
        joint=NAME, load_n=P, stresses=s, dims=dm, rules=rules, checks=checks,
        notes=notes, verified_against_book=DATA["verified_against_book"], raw=raw,
    )


def _cotter(b, t, H, x, taper):
    import cadquery as cq
    return (
        cq.Workplane("XZ")
        .polyline([(x - b / 2, -H / 2), (x + b / 2 - H / taper, -H / 2), (x + b / 2, H / 2), (x - b / 2, H / 2)])
        .close()
        .extrude(t / 2, both=True)
    )


def build_parts(dims: dict):
    from ._shapes import box, rod_along_x

    d, d1, d2, t, b = (dims[k] for k in ("d", "d1", "d2", "t", "b"))
    gap, xc, L, over, rod_len = dims["gap"], dims["xc"], dims["L"], dims["overhang"], dims["rod_len"]
    span = d1 + 2 * over + 10
    H = d1 + 2 * over
    taper = DATA["modelling_choices"]["cotter_taper_on_width"]

    def slot(x):
        return box(x - b / 2, x + b / 2, -t / 2, t / 2, -span, span)

    rod_right = (
        rod_along_x(d2, gap / 2, L / 2 - gap / 2)
        .union(rod_along_x(d, L / 2 - 1, rod_len + 1))
        .cut(slot(xc))
        .clean()
    )
    rod_left = (
        rod_along_x(d2, -L / 2, L / 2 - gap / 2)
        .union(rod_along_x(d, -L / 2 - rod_len, rod_len + 1))
        .cut(slot(-xc))
        .clean()
    )
    sleeve = (
        rod_along_x(d1, -L / 2, L)
        .cut(rod_along_x(d2, -L / 2 - 1, L + 2))
        .cut(slot(-xc))
        .cut(slot(xc))
        .clean()
    )
    return {
        "rod_left": rod_left,
        "rod_right": rod_right,
        "sleeve": sleeve,
        "cotter_left": _cotter(b, t, H, -xc, taper),
        "cotter_right": _cotter(b, t, H, xc, taper),
    }


def drawing_dims(dims: dict) -> list[dict]:
    d, d1, b, xc, L, over, rod_len = (dims[k] for k in ("d", "d1", "b", "xc", "L", "overhang", "rod_len"))
    H = d1 + 2 * over
    x_end = -L / 2 - rod_len
    return [
        {"view": "FRONT VIEW", "p1": [x_end + 4, 0, -d / 2], "p2": [x_end + 4, 0, d / 2], "orient": "v", "offset": -7, "text": f"Ø{d:g}"},
        {"view": "FRONT VIEW", "p1": [L / 2, 0, -d1 / 2], "p2": [L / 2, 0, d1 / 2], "orient": "v", "offset": 7, "text": f"Ø{d1:g}"},
        {"view": "FRONT VIEW", "p1": [-L / 2, 0, -d1 / 2], "p2": [L / 2, 0, -d1 / 2], "orient": "h", "offset": 12, "text": f"{L:g}"},
        {"view": "FRONT VIEW", "p1": [xc - b / 2, 0, H / 2], "p2": [xc + b / 2, 0, H / 2], "orient": "h", "offset": -6, "text": f"{b:g}"},
    ]


def explode(dims: dict) -> dict:
    L = dims["d1"]
    return {"rod_left": (-1.4 * L, 0, 0), "rod_right": (1.4 * L, 0, 0), "sleeve": (0, 0, 0),
            "cotter_left": (0, 0, 1.4 * L), "cotter_right": (0, 0, 1.4 * L)}


CHECK_PARTS = {
    "rod tension": ["rod_left", "rod_right"],
    "rod end tension": ["rod_left", "rod_right"], "rod end crushing": ["rod_left", "rod_right"],
    "rod end shear": ["rod_left", "rod_right"],
    "sleeve tension": ["sleeve"], "sleeve crushing": ["sleeve"], "sleeve end shear": ["sleeve"],
    "cotter shear": ["cotter_left", "cotter_right"],
}
