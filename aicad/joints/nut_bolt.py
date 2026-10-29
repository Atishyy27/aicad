"""Hex bolt, washer and nut: sizing from a standard table and geometry for 3 parts.

Axis along Z. The bolt head sits below z = 0, the clamped thickness (grip) runs
from z = 0 up, then the washer, then the nut. Threads are cosmetic rings cut around
the shank at the pitch, not a true helix; strength checks use the stress area.
"""
from __future__ import annotations

import math

from ..design import (DEFAULT_DESIGN_FACTOR, Check, Design, check_positive, load_data, sizing_load,
                      stresses_from, times)

NAME = "nut_bolt"
TITLE = "Hex bolt, nut and washer"
DATA = load_data(NAME)
PARTS = DATA["parts"]
COLORS = {
    "bolt": (0.70, 0.70, 0.72),
    "washer": (0.35, 0.70, 0.40),
    "nut": (0.85, 0.45, 0.25),
}
LABELS = {
    "d": "nominal (major) diameter",
    "pitch": "thread pitch",
    "stress_area": "tensile stress area (mm^2)",
    "s": "width across flats",
    "k": "head height",
    "m": "nut height",
    "washer_in": "washer hole diameter",
    "washer_out": "washer outer diameter",
    "washer_h": "washer thickness",
    "grip": "clamped thickness",
    "L": "bolt length",
}


def _size_key(n: int) -> str:
    return f"M{n}"


def design(load_n=None, bolt_size=None, grip_mm=None, tension_mpa=None, shear_mpa=None, crushing_mpa=None, design_factor=None, **_ignored) -> Design:
    if load_n is None and bolt_size is None:
        raise ValueError("give a load or a bolt size like M12")
    check_positive(load_n, grip=grip_mm)
    s = stresses_from(DATA, tension_mpa, shear_mpa, crushing_mpa)
    table = DATA["sizes"]
    factor = float(design_factor if design_factor is not None else DEFAULT_DESIGN_FACTOR)
    P = load_n
    Pd = sizing_load(P, factor)
    raw, notes = {}, []

    if bolt_size is not None:
        key = _size_key(int(bolt_size))
        if key not in table:
            raise ValueError(f"{key} is not in the table ({', '.join(table)})")
        how = "given by user"
    else:
        raw["stress_area_needed"] = Pd / s["tension"]
        key = next((k for k, v in table.items() if v["stress_area"] >= raw["stress_area_needed"] - 1e-9), None)
        if key is None:
            biggest = list(table)[-1]
            n = math.ceil(raw["stress_area_needed"] / table[biggest]["stress_area"])
            raise ValueError(
                f"needs {raw['stress_area_needed']:.0f} mm^2 of stress area; the largest size in the table is "
                f"{biggest} ({table[biggest]['stress_area']:g} mm^2). Split the load over at least {n} bolts."
            )
        how = f"smallest size whose stress area >= P / sigma_t = {raw['stress_area_needed']:.1f} mm^2"

    row = dict(table[key])
    m = DATA["modelling_choices"]
    grip = grip_mm if grip_mm is not None else times(m["default_grip"], row["d"])
    step = m["length_round_to_mm"]
    L_needed = grip + row["washer_h"] + row["m"] + m["thread_ends_past_nut_pitches"] * row["pitch"]
    L = step * math.ceil(L_needed / step - 1e-9)
    dims = {**row, "grip": float(grip), "L": float(L)}

    rules = {k: f"{key} table value [{DATA['verify_note'].split('.')[0]}, UNVERIFIED]" for k in row}
    rules["d"] = f"{key}: {how}"
    rules["grip"] = "given by user" if grip_mm is not None else "default 2 x d when not given"
    rules["L"] = f"grip + washer + nut + {m['thread_ends_past_nut_pitches']} pitches, rounded up to {step} mm"

    checks = []
    if P is not None:
        checks = _checks(P, dims, s)
        notes.append("Nut thread stripping is not checked yet.")
        # NPTEL IIT Kharagpur, Design of Machine Elements I, module 4 lesson 4, section 4.4.1.1.
        # The page prints the relation as "284 d kN", but its own worked example reads 56.8 kN
        # for M20, so the constant is 2840 d newtons. Reported, not checked: tightening load
        # depends on how the joint is actually made up.
        p1 = 2840 * dims["d"]
        notes.append(
            f"Tightening: screwing the nut up leak-tight on a gasket puts about "
            f"{p1:,.0f} N in this bolt before your load arrives, roughly "
            f"{p1 / dims['stress_area']:.0f} MPa on its own (half that if it need not be "
            f"leak-tight). The checks below ignore it, so use a torque wrench and a bolt "
            f"grade that can take both.")

    if P is not None and bolt_size is not None and any(not c.passed for c in checks):
        need = Pd / s["tension"]
        fits = next((k for k, v in table.items() if v["stress_area"] >= need), None)
        worst = max(c.stress_mpa / c.allowable_mpa for c in checks)
        if fits:
            notes.insert(0, f"{key} is too small for this load: the busiest check is {worst:.1f} times its "
                            f"allowed stress. {fits} would carry it, or split the load over "
                            f"{math.ceil(need / row['stress_area'])} x {key}.")
        else:
            n_needed = math.ceil(need / table[list(table)[-1]]['stress_area'])
            notes.insert(0, f"{key} is far too small for this load ({worst:.1f} times its allowed stress) and "
                            f"even {list(table)[-1]} cannot carry it alone: use at least {n_needed} bolts.")
    if factor > 1 and P is not None and bolt_size is None:
        notes.insert(0, f"Sized for {factor:g} x the given load ({Pd:,.0f} N), then checked at {P:,.0f} N.")
    return Design(
        joint=NAME, load_n=P, stresses=s, dims=dims, rules=rules, checks=checks, notes=notes,
        design_factor=factor, verified_against_book=DATA["verified_against_book"], raw=raw,
    )


def _checks(P, dims, s):
    return [
        Check("bolt tension", P / dims["stress_area"], s["tension"], "P / stress_area"),
        Check("head shear", P / (math.pi * dims["d"] * dims["k"]), s["shear"], "P / (pi d k)"),
    ]


def _thread_rings(wp, d, pitch, z_start, z_end):
    """Cut shallow V grooves at the pitch between z_start and z_end, never past the nominal diameter."""
    import cadquery as cq

    n = min(40, int((z_end - z_start) / pitch))
    if n < 1:
        return wp
    r, depth, half = d / 2, 0.3 * pitch, 0.35 * pitch
    pts = [(r + 0.2, z_start)]
    for i in range(n):
        zc = z_start + (i + 0.5) * pitch
        pts += [(r, zc - half), (r - depth, zc), (r, zc + half)]
    pts += [(r + 0.2, z_start + n * pitch)]
    cutter = cq.Workplane("XZ").polyline(pts).close().revolve(360, (0, 0, 0), (0, 1, 0))
    return wp.cut(cutter).clean()


def build_parts(dims: dict):
    from ._shapes import disc, hexagon, hole_z, soften

    d, s, k, m, pitch = dims["d"], dims["s"], dims["k"], dims["m"], dims["pitch"]
    w_in, w_out, w_h = dims["washer_in"], dims["washer_out"], dims["washer_h"]
    grip, L = dims["grip"], dims["L"]
    span = L + k + 10

    head = soften(hexagon(s, k, -k), lambda w: w.faces("<Z").chamfer(0.08 * s))
    shank = soften(disc(d, L, 0), lambda w: w.faces(">Z").chamfer(0.75 * pitch))
    bolt = head.union(shank).clean()
    z_start = max(pitch, L - min(2 * d + 6, L))
    bolt = soften(bolt, lambda w: _thread_rings(w, d, pitch, z_start, L - pitch))
    washer = disc(w_out, w_h, grip).cut(hole_z(w_in, span)).clean()
    blank = soften(hexagon(s, m, grip + w_h), lambda w: w.faces(">Z or <Z").chamfer(0.06 * s))
    nut = blank.cut(hole_z(d, span)).clean()
    return {"bolt": bolt, "washer": washer, "nut": nut}


def drawing_dims(dims: dict) -> list[dict]:
    d, s, k, m, grip, L, wh = (dims[x] for x in ("d", "s", "k", "m", "grip", "L", "washer_h"))
    rc = s / math.cos(math.radians(30)) / 2  # across-corners radius, seen in the front view
    return [
        {"view": "FRONT VIEW", "p1": [rc, 0, 0], "p2": [rc, 0, L], "orient": "v", "offset": 8, "text": f"{L:g}"},
        {"view": "FRONT VIEW", "p1": [-rc, 0, -k], "p2": [-rc, 0, 0], "orient": "v", "offset": -7, "text": f"{k:g}"},
        {"view": "FRONT VIEW", "p1": [-rc, 0, grip + wh], "p2": [-rc, 0, grip + wh + m], "orient": "v", "offset": -7, "text": f"{m:g}"},
        {"view": "FRONT VIEW", "p1": [-d / 2, 0, grip / 2], "p2": [d / 2, 0, grip / 2], "orient": "h", "offset": 0, "text": f"M{d:g}"},
        {"view": "LEFT SIDE VIEW", "p1": [0, s / 2, -k], "p2": [0, -s / 2, -k], "orient": "h", "offset": 7, "text": f"{s:g} A/F"},
    ]


def explode(dims: dict) -> dict:
    L = dims["s"]
    return {"bolt": (0, 0, -1.5 * L), "washer": (0, 0, 0.6 * L), "nut": (0, 0, 1.6 * L)}


CHECK_PARTS = {"bolt tension": ["bolt"], "head shear": ["bolt"]}
