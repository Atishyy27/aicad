"""Socket and spigot cotter joint: sizing and geometry for 3 parts.

Axes: rods along X, the cotter drives down along Z through a rectangular slot,
origin at the centre of the slot. Cotter thickness t runs along Y, its width b
along X. The spigot rod is on the -X side, the socket rod on the +X side.
"""
from __future__ import annotations

import math

from ..design import Check, Design, ceil_mm, check_positive, load_data, next_preferred, stresses_from, times

NAME = "cotter"
TITLE = "Socket and spigot cotter joint"
DATA = load_data(NAME)
PARTS = DATA["parts"]
COLORS = {
    "spigot": (0.30, 0.55, 0.85),
    "socket": (0.85, 0.45, 0.25),
    "cotter": (0.90, 0.80, 0.20),
}
LABELS = {
    "d": "rod diameter",
    "d1": "spigot diameter",
    "d2": "socket outer diameter",
    "d3": "spigot collar diameter",
    "d4": "socket collar diameter",
    "a": "spigot end beyond slot",
    "c": "socket end beyond slot",
    "b": "cotter width",
    "t": "cotter thickness",
    "t1": "spigot collar thickness",
    "bore_clearance": "gap at the bottom of the socket bore",
    "end_wall": "solid socket beyond the bore",
    "overhang": "cotter sticks out past the collar",
    "rod_len": "rod length shown",
}

# which dimension to raise, 1 mm at a time, when a check fails
_FIX = {
    "spigot tension": "d1",
    "socket tension": "d2",
    "cotter shear": "b",
    "spigot crushing": "t",
    "socket crushing": "d4",
    "spigot end shear": "a",
    "socket end shear": "c",
    "spigot collar crushing": "d3",
    "spigot collar shear": "t1",
}


def _checks(P, dm, s):
    d, d1, d2, d3, d4 = dm["d"], dm["d1"], dm["d2"], dm["d3"], dm["d4"]
    a, c, b, t, t1 = dm["a"], dm["c"], dm["b"], dm["t"], dm["t1"]
    q = math.pi / 4
    return [
        Check("rod tension", P / (q * d**2), s["tension"], "P / (pi/4 d^2)"),
        Check("spigot tension", P / (q * d1**2 - d1 * t), s["tension"], "P / (pi/4 d1^2 - d1 t)"),
        Check("socket tension", P / (q * (d2**2 - d1**2) - (d2 - d1) * t), s["tension"],
              "P / (pi/4 (d2^2 - d1^2) - (d2 - d1) t)"),
        Check("cotter shear", P / (2 * b * t), s["shear"], "P / (2 b t)"),
        Check("spigot crushing", P / (d1 * t), s["crushing"], "P / (d1 t)"),
        Check("socket crushing", P / ((d4 - d1) * t), s["crushing"], "P / ((d4 - d1) t)"),
        Check("spigot end shear", P / (2 * a * d1), s["shear"], "P / (2 a d1)"),
        Check("socket end shear", P / (2 * (d4 - d1) * c), s["shear"], "P / (2 (d4 - d1) c)"),
        Check("spigot collar crushing", P / (q * (d3**2 - d1**2)), s["crushing"], "P / (pi/4 (d3^2 - d1^2))"),
        Check("spigot collar shear", P / (math.pi * d1 * t1), s["shear"], "P / (pi d1 t1)"),
    ]


def _keep_walls(dm):
    """Geometry sanity: every outer diameter must leave a real wall."""
    dm["d2"] = max(dm["d2"], dm["d1"] + 4)
    dm["d3"] = max(dm["d3"], dm["d1"] + 4)
    dm["d4"] = max(dm["d4"], dm["d2"] + 4)


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
            for c in failing:
                dm[_FIX[c.name]] += 1
            _keep_walls(dm)
        else:
            notes.append("Could not satisfy every check within 500 mm of adjustment.")
        for key in props:
            if dm[key] != start[key]:
                notes.append(f"{key} raised from {start[key]:g} to {dm[key]:g} mm so every check passes.")

    m = DATA["modelling_choices"]
    dm["bore_clearance"] = times(m["bore_clearance"], d)
    dm["end_wall"] = times(m["socket_end_wall"], d)
    dm["overhang"] = times(m["cotter_overhang"], d)
    dm["rod_len"] = m["rod_length"]["times"] * d
    dm = {k: round(v, 3) for k, v in dm.items()}

    rules = {"d": "given by user" if rod_diameter_mm is not None
             else "rod in tension: d = sqrt(4P / (pi sigma_t)), rounded up to a preferred size"}
    for key, p in props.items():
        rules[key] = f"{key} = {p['times']} x d, rounded up to whole mm ({p['meaning']}) [{p['source']}]"

    return Design(
        joint=NAME, load_n=P, stresses=s, dims=dm, rules=rules, checks=checks,
        notes=notes, verified_against_book=DATA["verified_against_book"], raw=raw,
    )


def build_parts(dims: dict):
    import cadquery as cq

    from ._shapes import box, rod_along_x

    d, d1, d2, d3, d4 = (dims[k] for k in ("d", "d1", "d2", "d3", "d4"))
    a, c, b, t, t1 = (dims[k] for k in ("a", "c", "b", "t", "t1"))
    clr, wall, over, rod_len = dims["bore_clearance"], dims["end_wall"], dims["overhang"], dims["rod_len"]

    span = d4 + 2 * over + 10
    x_face = -b / 2 - c            # socket end face; spigot collar bears on it
    spigot_end = b / 2 + a
    bore_end = spigot_end + clr
    slot = box(-b / 2, b / 2, -t / 2, t / 2, -span, span)

    spigot = (
        rod_along_x(d, x_face - t1 - rod_len, rod_len + t1 / 2)
        .union(rod_along_x(d3, x_face - t1, t1))
        .union(rod_along_x(d1, x_face - t1 / 2, spigot_end - (x_face - t1 / 2)))
        .cut(slot)
        .clean()
    )

    body_end = bore_end + wall
    socket = (
        rod_along_x(d2, x_face, body_end - x_face)
        .union(rod_along_x(d4, x_face, (b / 2 + c) - x_face))
        .union(rod_along_x(d, body_end - wall / 2, rod_len + wall / 2))
        .cut(rod_along_x(d1, x_face - 1, bore_end - x_face + 1))
        .cut(slot)
        .clean()
    )

    H = d4 + 2 * over
    taper = DATA["modelling_choices"]["cotter_taper_on_width"]
    cotter = (
        cq.Workplane("XZ")
        .polyline([(-b / 2, -H / 2), (b / 2 - H / taper, -H / 2), (b / 2, H / 2), (-b / 2, H / 2)])
        .close()
        .extrude(t / 2, both=True)
    )

    return {"spigot": spigot, "socket": socket, "cotter": cotter}


def drawing_dims(dims: dict) -> list[dict]:
    d, d2, d4, b, c, t1 = (dims[k] for k in ("d", "d2", "d4", "b", "c", "t1"))
    H = d4 + 2 * dims["overhang"]
    x_face = -b / 2 - c
    x_rod = x_face - t1 - dims["rod_len"] + 4
    body_end = b / 2 + dims["a"] + dims["bore_clearance"] + dims["end_wall"]
    return [
        {"view": "FRONT VIEW", "p1": [x_rod, 0, -d / 2], "p2": [x_rod, 0, d / 2], "orient": "v", "offset": -7, "text": f"Ø{d:g}"},
        {"view": "FRONT VIEW", "p1": [b / 2 + c, 0, -d4 / 2], "p2": [b / 2 + c, 0, d4 / 2], "orient": "v", "offset": 7, "text": f"Ø{d4:g}"},
        {"view": "FRONT VIEW", "p1": [-b / 2, 0, H / 2], "p2": [b / 2, 0, H / 2], "orient": "h", "offset": -6, "text": f"{b:g}"},
        {"view": "TOP VIEW (PLAN)", "p1": [body_end, -d2 / 2, 0], "p2": [body_end, d2 / 2, 0], "orient": "v", "offset": 7, "text": f"Ø{d2:g}"},
    ]


def explode(dims: dict) -> dict:
    L = dims["d4"]
    return {"spigot": (-1.2 * L, 0, 0), "socket": (0.6 * L, 0, 0), "cotter": (0, 0, 1.5 * L)}


CHECK_PARTS = {
    "rod tension": ["spigot", "socket"],
    "spigot tension": ["spigot"], "spigot crushing": ["spigot"], "spigot end shear": ["spigot"],
    "spigot collar crushing": ["spigot"], "spigot collar shear": ["spigot"],
    "socket tension": ["socket"], "socket crushing": ["socket"], "socket end shear": ["socket"],
    "cotter shear": ["cotter"],
}
