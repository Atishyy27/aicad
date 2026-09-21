"""Gib and cotter joint: sizing and geometry for 4 parts (or 5 with two gibs).

A plain cotter, driven hard, pushes the two sides of a strap apart. The gib is the
other half of the same slot with hooked ends that lap over the strap and hold it
together, so a steeper taper can be used (Unwin 1899, page 179).

Axes: rods along X. The rod comes in from -X, ends in a square block, and the strap
wraps it and carries on to +X. The gib and cotter are driven down along Z through a
slot: breadth b along X, thickness t along Y.

Sizing: Unwin gives the thickness and the way the breadth is split. Everything else
is sized by a strength check, not by an invented ratio. The checks are the
socket-and-spigot set (NPTEL IIT Kharagpur, module 4 lesson 2, verified in
tests/test_book_problems.py) with the circular areas replaced by square ones.
"""
from __future__ import annotations

import math

from ..design import (DEFAULT_DESIGN_FACTOR, Check, Design, ceil_mm, check_positive, load_data,
                      next_preferred, sizing_load, stresses_from)

NAME = "gib_and_cotter"
TITLE = "Gib and cotter joint"
DATA = load_data(NAME)
PARTS = ["rod", "strap", "cotter", "gib"]
COLORS = {
    "rod": (0.30, 0.55, 0.85),
    "strap": (0.85, 0.45, 0.25),
    "cotter": (0.90, 0.80, 0.20),
    "gib": (0.45, 0.75, 0.45),
    "gib_2": (0.35, 0.65, 0.40),
}
LABELS = {
    "d": "rod diameter",
    "B": "rod end square side",
    "Bo": "strap outer square side",
    "t": "gib and cotter thickness",
    "b": "total breadth of gib and cotter",
    "cotter_b": "breadth of the cotter alone",
    "gib_b": "breadth of each gib",
    "a": "rod end beyond the slot",
    "c": "strap beyond the slot",
    "hook": "how far the gib hook laps over the strap",
    "hook_h": "height of the gib hook",
    "xs": "slot centre from the strap shoulder",
    "L": "strap length",
    "overhang": "gib and cotter stand proud",
    "rod_len": "round rod shown each side",
}

# which dimension to raise, 1 mm at a time, when a check fails
_FIX = {
    "rod end tension": "B",
    "rod end crushing": "B",
    "strap tension": "Bo",
    "strap crushing": "Bo",
    "gib and cotter shear": "b",
    "rod end shear": "a",
    "strap end shear": "c",
}


def _checks(P, dm, s):
    """The socket-and-spigot checks on a square section.

    Round joint            -> this joint
    pi/4 d1^2              -> B^2          (rod end)
    pi/4 (d2^2 - d1^2)     -> Bo^2 - B^2   (strap wall)
    (d2 - d1)              -> Bo - B       (strap wall thickness, both sides together)
    """
    d, B, Bo, t, b, a, c = (dm[k] for k in ("d", "B", "Bo", "t", "b", "a", "c"))
    wall = Bo - B
    return [
        Check("rod tension", P / (math.pi / 4 * d**2), s["tension"], "P / (pi/4 d^2)"),
        Check("rod end tension", P / (B**2 - B * t), s["tension"], "P / (B^2 - B t)"),
        Check("strap tension", P / ((Bo**2 - B**2) - wall * t), s["tension"],
              "P / ((Bo^2 - B^2) - (Bo - B) t)"),
        Check("gib and cotter shear", P / (2 * b * t), s["shear"], "P / (2 b t)"),
        Check("rod end crushing", P / (B * t), s["crushing"], "P / (B t)"),
        Check("strap crushing", P / (wall * t), s["crushing"], "P / ((Bo - B) t)"),
        Check("rod end shear", P / (2 * a * B), s["shear"], "P / (2 a B)"),
        Check("strap end shear", P / (2 * c * wall), s["shear"], "P / (2 c (Bo - B))"),
    ]


def _keep_walls(dm):
    """Keep the shape buildable: the strap has to be thicker than nothing, and the
    slot has to fit inside the rod end."""
    dm["B"] = max(dm["B"], dm["t"] + 4)
    dm["Bo"] = max(dm["Bo"], dm["B"] + 6)


def design(load_n=None, rod_diameter_mm=None, tension_mpa=None, shear_mpa=None,
           crushing_mpa=None, design_factor=None, gibs=None, **_ignored) -> Design:
    if load_n is None and rod_diameter_mm is None:
        raise ValueError("give a load or a rod diameter")
    check_positive(load_n, rod_diameter=rod_diameter_mm)
    s = stresses_from(DATA, tension_mpa, shear_mpa, crushing_mpa)
    factor = float(design_factor if design_factor is not None else DEFAULT_DESIGN_FACTOR)
    n_gibs = int(gibs if gibs is not None else DATA["gibs"])
    if n_gibs not in (1, 2):
        raise ValueError("a gib and cotter joint has one or two gibs")
    P = load_n
    Pd = sizing_load(P, factor)
    raw, notes = {}, []

    if rod_diameter_mm is not None:
        d = float(rod_diameter_mm)
    else:
        raw["rod_tension"] = math.sqrt(4 * Pd / (math.pi * s["tension"]))
        d = next_preferred(raw["rod_tension"], DATA["preferred_diameters_mm"])

    # Unwin gives t as a fraction of the breadth b, and b comes from double shear, so
    # start from the shear equation with t = 0.25 b substituted:  P = 2 b (0.25 b) tau.
    k_t = DATA["proportions"]["t"]["times_b"]
    if P is not None:
        raw["breadth_from_shear"] = math.sqrt(Pd / (2 * k_t * s["shear"]))
        b = ceil_mm(raw["breadth_from_shear"])
    else:
        b = ceil_mm(1.6 * d)
        notes.append("No load given, so the breadth is a proportion only; give a load to size it.")
    t = ceil_mm(k_t * b)

    dm = {"d": d, "B": ceil_mm(1.2 * d), "Bo": ceil_mm(1.8 * d), "t": t, "b": b,
          "a": ceil_mm(0.5 * d), "c": ceil_mm(0.5 * d)}
    _keep_walls(dm)
    start = dict(dm)

    checks = []
    if P is not None:
        for _ in range(600):
            checks = _checks(Pd, dm, s)
            failing = [c for c in checks if not c.passed and c.name in _FIX]
            if not failing:
                break
            for key in {_FIX[c.name] for c in failing}:
                dm[key] += 1
            dm["t"] = ceil_mm(k_t * dm["b"])
            _keep_walls(dm)
        else:
            notes.append("Could not satisfy every check within 600 mm of adjustment.")
        for key in ("B", "Bo", "b", "a", "c"):
            if dm[key] != start[key]:
                notes.append(f"{LABELS[key]} ({key}) raised from {start[key]:g} to {dm[key]:g} mm "
                             "so every check passes.")

    split = DATA["breadth_split"][str(n_gibs)]
    dm["cotter_b"] = round(split["cotter"] * dm["b"], 3)
    dm["gib_b"] = round(split["gib"] * dm["b"], 3)
    dm["gibs"] = n_gibs

    m = DATA["modelling_choices"]
    dm["hook"] = ceil_mm(m["gib_hook"]["times_t"] * dm["t"])
    dm["hook_h"] = ceil_mm(m["hook_height"]["times_t"] * dm["t"])
    # Layout along X. The strap mouth is x = 0 and the rod comes in from -X.
    #   0 .. c          strap metal before the slot: this is what shears out (check "strap end shear")
    #   c .. c+b        the slot, holding the gib and cotter
    #   c+b .. c+b+a    rod end metal past the slot: this is what shears out ("rod end shear")
    # The rod tip then sits inside the closed end of the strap.
    dm["xs"] = dm["c"] + dm["b"] / 2
    dm["rod_end_len"] = dm["xs"] + dm["b"] / 2 + dm["a"]
    dm["end_wall"] = ceil_mm(m["end_wall"]["times_B"] * dm["B"])
    dm["clearance"] = m["clearance_mm"]
    dm["L"] = dm["rod_end_len"] + dm["clearance"] + dm["end_wall"]
    dm["overhang"] = max(m["cotter_overhang"]["times"] * d, m["cotter_overhang"]["min_mm"])
    dm["rod_len"] = m["rod_length"]["times"] * d
    dm["taper_one_in"] = DATA["taper"]["one_in"]
    dm = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in dm.items()}

    rules = {
        "d": "given by user" if rod_diameter_mm is not None
             else "rod in tension: d = sqrt(4P / (pi sigma_t)), rounded up to a preferred size",
        "b": f"double shear with t = {k_t} b substituted: b = sqrt(P / (2 x {k_t} x tau)) "
             f"[breadth from Unwin 1899 p179, shear equation from NPTEL M4L2]",
        "t": f"t = {k_t} x b [Unwin 1899 p179 figs 130-131]",
        "cotter_b": f"{split['cotter']} x b [Unwin 1899 p179 fig {130 if n_gibs == 1 else 131}]",
        "gib_b": f"{split['gib']} x b, {n_gibs} gib(s) [Unwin 1899 p179 fig {130 if n_gibs == 1 else 131}]",
        "taper_one_in": f"1 in {DATA['taper']['one_in']} [Unwin 1899 p179: {DATA['taper']['range']}]",
        "xs": "c + b/2: the slot starts one shear length in from the strap mouth",
        "rod_end_len": "c + b + a: the rod end reaches a past the slot",
        "L": "rod end + clearance + end wall, so the strap closes over the rod tip",
    }
    for key, why in DATA["sized_by_check"].items():
        rules[key] = f"{why} [sized by check, not by a book proportion]"

    if P is not None:
        checks = _checks(P, dm, s)        # report at the real load
        if factor > 1:
            notes.insert(0, f"Sized for {factor:g} x the given load ({Pd:,.0f} N), then checked at "
                            f"{P:,.0f} N. That margin is why the checks sit below their limits.")
        notes.append(DATA["why_a_gib"])
    return Design(
        joint=NAME, load_n=P, stresses=s, dims=dm, rules=rules, checks=checks, notes=notes,
        design_factor=factor, verified_against_book=DATA["verified_against_book"], raw=raw,
    )


def parts_for(dims: dict) -> list[str]:
    return ["rod", "strap", "cotter"] + (["gib", "gib_2"] if dims.get("gibs") == 2 else ["gib"])


# ------------------------------------------------------------------ geometry

def _gib_x_positions(dims):
    """Where each piece sits across the breadth, left edge first.

    One gib:  [gib][    cotter    ]
    Two gibs: [gib][ cotter ][gib]
    """
    x0 = dims["xs"] - dims["b"] / 2
    g, c = dims["gib_b"], dims["cotter_b"]
    if dims.get("gibs") == 2:
        return {"gib": x0, "cotter": x0 + g, "gib_2": x0 + g + c}
    return {"gib": x0, "cotter": x0 + g}


def build_parts(dims: dict):
    import cadquery as cq

    from ._shapes import box, rod_along_x

    d, B, Bo, t = (dims[k] for k in ("d", "B", "Bo", "t"))
    a, c, xs, L = dims["a"], dims["c"], dims["xs"], dims["L"]
    over, rod_len, hook, hook_h = dims["overhang"], dims["rod_len"], dims["hook"], dims["hook_h"]
    span = Bo + 2 * over + 20
    H = Bo + 2 * over                       # how far the gib and cotter stand out in Z
    pos = _gib_x_positions(dims)

    def square_along_x(side, x0, length):
        return box(x0, x0 + length, -side / 2, side / 2, -side / 2, side / 2)

    # Square-cornered slot, deliberately. Leutwiler 1917 article 98 notes that cotter slots are
    # often made with semi-circular edges, to avoid sharp corners that start cracks and to add
    # shearing area at the sides. Rounding was tried here and dropped: filleting the cutting
    # solid SHRINKS it, so metal is left exactly where the cotter sits, and the overlap test
    # caught that. Doing it properly means an obround slot with the ends pushed out past b,
    # which moves the a and c dimensions the two shear checks are measured from. The
    # finite-element run could not settle the question either way, because its peak sits at the
    # face the solver clamps. Left square until there is a reason better than a guess.
    slot = box(xs - dims["b"] / 2, xs + dims["b"] / 2, -t / 2, t / 2, -span, span)

    # the rod: round stock from -X, a square end that reaches into the strap, slotted
    rod = (
        square_along_x(B, -B * 0.6, dims["rod_end_len"] + B * 0.6)
        .union(rod_along_x(d, -rod_len - B * 0.6, rod_len + B * 0.6 + 1))
        .cut(slot)
        .clean()
    )
    # the strap: square tube wrapping the rod end, closed at +X, carrying on as round stock
    r = min(dims.get("corner_r", 0) or 0, Bo / 4)
    strap = square_along_x(Bo, 0, L)
    if r:
        strap = strap.edges("|X").fillet(r)
    strap = (
        strap.cut(square_along_x(B + 0.6, -1, dims["rod_end_len"] + dims["clearance"] + 1))
        .union(rod_along_x(d, L - 1, rod_len + 1))
        .cut(slot)
        .clean()
    )

    def plate(x0, width, taper=False):
        if not taper:
            return box(x0, x0 + width, -t / 2, t / 2, -H / 2, H / 2)
        # tapered on its breadth, the way a cotter is driven
        shrink = H / dims["taper_one_in"]
        return (
            cq.Workplane("XZ")
            .polyline([(x0, -H / 2), (x0 + width - shrink, -H / 2),
                       (x0 + width, H / 2), (x0, H / 2)])
            .close()
            .extrude(t / 2, both=True)
        )

    def hooked(x0, width):
        """A gib: a plain plate whose lips lap over the outside of the strap.

        The lip sits ON the strap face (z = Bo/2), never inside it, or the two parts
        would occupy the same metal.
        """
        body = plate(x0, width)
        z0 = Bo / 2
        z1 = min(H / 2, z0 + hook_h)
        lip = box(x0 - hook, x0, -t / 2, t / 2, z0, z1)
        lip2 = box(x0 - hook, x0, -t / 2, t / 2, -z1, -z0)
        return body.union(lip).union(lip2).clean()

    parts = {
        "rod": rod,
        "strap": strap,
        "cotter": plate(pos["cotter"], dims["cotter_b"], taper=True),
        "gib": hooked(pos["gib"], dims["gib_b"]),
    }
    if dims.get("gibs") == 2:
        parts["gib_2"] = hooked(pos["gib_2"], dims["gib_b"])
    return parts


def drawing_dims(dims: dict) -> list[dict]:
    d, B, Bo, L, xs, b = (dims[k] for k in ("d", "B", "Bo", "L", "xs", "b"))
    H = Bo + 2 * dims["overhang"]
    return [
        {"view": "FRONT VIEW", "p1": [-dims["rod_len"] + 4, 0, -d / 2],
         "p2": [-dims["rod_len"] + 4, 0, d / 2], "orient": "v", "offset": -7, "text": f"Ø{d:g}"},
        {"view": "FRONT VIEW", "p1": [L, 0, -Bo / 2], "p2": [L, 0, Bo / 2],
         "orient": "v", "offset": 8, "text": f"{Bo:g}"},
        {"view": "FRONT VIEW", "p1": [0, 0, -Bo / 2], "p2": [L, 0, -Bo / 2],
         "orient": "h", "offset": 12, "text": f"{L:g}"},
        {"view": "FRONT VIEW", "p1": [xs - b / 2, 0, H / 2], "p2": [xs + b / 2, 0, H / 2],
         "orient": "h", "offset": -6, "text": f"{b:g}"},
        {"view": "LEFT SIDE VIEW", "p1": [0, -B / 2, 0], "p2": [0, B / 2, 0],
         "orient": "h", "offset": 8, "text": f"{B:g} sq"},
    ]


def explode(dims: dict) -> dict:
    s = dims["Bo"]
    out = {"rod": (-1.4 * s, 0, 0), "strap": (1.0 * s, 0, 0), "cotter": (0, 0, 1.5 * s),
           "gib": (0, 0, 1.5 * s)}
    if dims.get("gibs") == 2:
        out["gib_2"] = (0, 0, 1.5 * s)
    return out


CHECK_PARTS = {
    "rod tension": ["rod"],
    "rod end tension": ["rod"],
    "rod end crushing": ["rod"],
    "rod end shear": ["rod"],
    "strap tension": ["strap"],
    "strap crushing": ["strap"],
    "strap end shear": ["strap"],
    "gib and cotter shear": ["cotter", "gib"],
}
