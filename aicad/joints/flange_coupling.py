"""Protected type rigid flange coupling: sizing and geometry.

Sized from the torque it must transmit (given directly, or from power and speed).
Parts: two shafts, two flanged hubs, one sunk key per shaft, and n bolts with nuts.
Axes: shafts along X, the two flange faces meet at x = 0.
"""
from __future__ import annotations

import math

from ..design import Check, Design, ceil_mm, check_positive, load_data, next_preferred, stresses_from, times

NAME = "flange_coupling"
TITLE = "Protected type rigid flange coupling"
DATA = load_data(NAME)
BOLT_SIZES = [6, 8, 10, 12, 16, 20, 24, 30, 36]
MAX_BOLTS = max(r["bolts"] for r in DATA["bolt_count_rule"])

COLORS = {
    "shaft_left": (0.55, 0.58, 0.62), "shaft_right": (0.55, 0.58, 0.62),
    "flange_left": (0.30, 0.55, 0.85), "flange_right": (0.85, 0.45, 0.25),
    "key_left": (0.90, 0.80, 0.20), "key_right": (0.90, 0.80, 0.20),
    **{f"bolt_{i}": (0.72, 0.72, 0.75) for i in range(1, MAX_BOLTS + 1)},
    **{f"nut_{i}": (0.35, 0.70, 0.40) for i in range(1, MAX_BOLTS + 1)},
}
LABELS = {
    "d": "shaft diameter", "D_hub": "hub outside diameter", "L_hub": "hub length",
    "tf": "flange thickness", "Dp": "bolt circle diameter", "D_flange": "flange outside diameter",
    "rim": "protecting rim thickness", "rim_h": "rim height", "w": "key width", "t": "key thickness",
    "l_key": "key length", "n_bolts": "number of bolts", "d_bolt": "bolt diameter",
    "torque_nmm": "torque transmitted (N mm)", "shaft_len": "shaft stub shown",
}
CHECK_PARTS = {
    "shaft shear": ["shaft_left", "shaft_right"],
    "hub shear": ["flange_left", "flange_right"],
    "flange shear at hub": ["flange_left", "flange_right"],
    "key shear": ["key_left", "key_right"],
    "key crushing": ["key_left", "key_right"],
    "bolt shear": [f"bolt_{i}" for i in range(1, MAX_BOLTS + 1)],
    "bolt crushing": [f"bolt_{i}" for i in range(1, MAX_BOLTS + 1)],
}
_FIX = {"hub shear": "D_hub", "flange shear at hub": "tf", "key shear": "l_key",
        "key crushing": "t", "bolt crushing": "tf"}


def parts_for(dims: dict) -> list[str]:
    n = int(dims["n_bolts"])
    return (["shaft_left", "shaft_right", "flange_left", "flange_right", "key_left", "key_right"]
            + [f"bolt_{i}" for i in range(1, n + 1)] + [f"nut_{i}" for i in range(1, n + 1)])


PARTS = parts_for({"n_bolts": 4})  # a typical set; parts_for(dims) is the real list


def bolt_count(shaft_mm: float) -> int:
    for rule in DATA["bolt_count_rule"]:
        if shaft_mm <= rule["up_to_shaft_mm"]:
            return rule["bolts"]
    return DATA["bolt_count_rule"][-1]["bolts"]


def _checks(T, dm, s):
    d, D, tf, Dp = dm["d"], dm["D_hub"], dm["tf"], dm["Dp"]
    w, t, l, n, db = dm["w"], dm["t"], dm["l_key"], dm["n_bolts"], dm["d_bolt"]
    b, k = DATA["bolt_stresses_mpa"], DATA["key_stresses_mpa"]
    return [
        Check("shaft shear", 16 * T / (math.pi * d**3), s["shear"], "16T / (pi d^3)"),
        Check("hub shear", 16 * T * D / (math.pi * (D**4 - d**4)), s["shear"], "16T D_hub / (pi (D_hub^4 - d^4))"),
        Check("flange shear at hub", 2 * T / (math.pi * D**2 * tf), s["shear"], "2T / (pi D_hub^2 tf)"),
        Check("key shear", 2 * T / (l * w * d), k["shear"], "2T / (l_key w d)"),
        Check("key crushing", 4 * T / (l * t * d), k["crushing"], "4T / (l_key t d)"),
        Check("bolt shear", 8 * T / (math.pi * db**2 * n * Dp), b["shear"], "8T / (pi d_bolt^2 n_bolts Dp)"),
        Check("bolt crushing", 2 * T / (n * db * tf * Dp), b["crushing"], "2T / (n_bolts d_bolt tf Dp)"),
    ]


def design(torque_nm=None, power_kw=None, speed_rpm=None, rod_diameter_mm=None, shaft_diameter_mm=None,
           tension_mpa=None, shear_mpa=None, crushing_mpa=None, **_ignored) -> Design:
    shaft_given = shaft_diameter_mm or rod_diameter_mm
    if torque_nm is None and not (power_kw and speed_rpm) and shaft_given is None:
        raise ValueError("give a torque, or power and speed, or a shaft diameter")
    check_positive(None, torque=torque_nm, power=power_kw, speed=speed_rpm, shaft=shaft_given)
    s = stresses_from(DATA, tension_mpa, shear_mpa, crushing_mpa)
    raw, notes = {}, []

    T = None
    if torque_nm is not None:
        T = float(torque_nm) * 1000.0
    elif power_kw and speed_rpm:
        T = 9.5493e6 * float(power_kw) / float(speed_rpm)
        raw["torque_from_power"] = T
        notes.append(f"Torque from power and speed: T = 9.5493e6 x {power_kw:g} / {speed_rpm:g} = {T:,.0f} N mm.")

    if shaft_given is not None:
        d = float(shaft_given)
    else:
        raw["shaft_torsion"] = (16 * T / (math.pi * s["shear"])) ** (1 / 3)
        d = next_preferred(raw["shaft_torsion"], DATA["preferred_diameters_mm"])

    p = DATA["proportions"]
    dm = {
        "d": d,
        "D_hub": ceil_mm(p["hub_diameter"]["times"] * d),
        "L_hub": ceil_mm(p["hub_length"]["times"] * d),
        "tf": ceil_mm(p["flange_thickness"]["times"] * d),
        "Dp": ceil_mm(p["bolt_circle"]["times"] * d),
        "D_flange": ceil_mm(p["flange_diameter"]["times"] * d),
        "rim": ceil_mm(p["rim_thickness"]["times"] * d),
        "w": ceil_mm(p["key_width"]["times"] * d),
        "t": ceil_mm(p["key_thickness"]["times"] * d),
    }
    dm["l_key"] = dm["L_hub"]
    dm["n_bolts"] = bolt_count(d)
    m = DATA["modelling_choices"]
    dm["rim_h"] = times(m["rim_height"], d)
    dm["shaft_len"] = times(m["shaft_length"], d)

    checks = []
    if T is not None:
        raw["bolt_from_shear"] = math.sqrt(8 * T / (math.pi * dm["n_bolts"] * DATA["bolt_stresses_mpa"]["shear"] * dm["Dp"]))
        dm["d_bolt"] = float(next((b for b in BOLT_SIZES if b >= raw["bolt_from_shear"]), BOLT_SIZES[-1]))
        start = dict(dm)
        for _ in range(500):
            checks = _checks(T, dm, s)
            failing = [c for c in checks if not c.passed]
            if not failing:
                break
            for c in failing:
                if c.name in _FIX:
                    dm[_FIX[c.name]] += 1
                elif c.name == "bolt shear":
                    bigger = [b for b in BOLT_SIZES if b > dm["d_bolt"]]
                    if bigger:
                        dm["d_bolt"] = float(bigger[0])
                elif c.name == "shaft shear" and shaft_given is not None:
                    notes.append("The shaft diameter you gave is too small for this torque.")
                    break
            else:
                dm["D_hub"] = max(dm["D_hub"], dm["d"] + 8)
                dm["D_flange"] = max(dm["D_flange"], dm["Dp"] + 2.5 * dm["d_bolt"])
                continue
            break
        for k in ("D_hub", "tf", "l_key", "t", "d_bolt"):
            if dm[k] != start[k]:
                notes.append(f"{k} raised from {start[k]:g} to {dm[k]:g} so every check passes.")
    else:
        dm["d_bolt"] = float(next(b for b in BOLT_SIZES if b >= 0.25 * d))
        notes.append("No torque given: bolt size from proportions only, and no checks were run.")

    dm["torque_nmm"] = round(T, 1) if T else 0.0
    dm = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in dm.items()}

    rules = {
        "d": "given by user" if shaft_given is not None
        else "shaft in torsion: d = cube root(16T / (pi tau)), rounded up to a preferred size",
        "n_bolts": f"{dm['n_bolts']} bolts, from the shaft-size rule in flange_coupling.json",
        "d_bolt": "from bolt shear: d_bolt = sqrt(8T / (pi n_bolts tau_bolt Dp)), rounded up to a standard size",
        "l_key": "the key runs the full hub length",
        "torque_nmm": "given, or 9.5493e6 x kW / rpm",
    }
    for key, prop in (("D_hub", "hub_diameter"), ("L_hub", "hub_length"), ("tf", "flange_thickness"),
                      ("Dp", "bolt_circle"), ("D_flange", "flange_diameter"), ("rim", "rim_thickness"),
                      ("w", "key_width"), ("t", "key_thickness")):
        pr = p[prop]
        rules[key] = f"{key} = {pr['times']} x d, rounded up to whole mm ({pr['meaning']}) [{pr['source']}]"

    return Design(joint=NAME, load_n=None, stresses=s, dims=dm, rules=rules, checks=checks,
                  notes=notes, verified_against_book=DATA["verified_against_book"], raw=raw)


def build_parts(dims: dict):
    import cadquery as cq

    from ._shapes import box, hexagon, rod_along_x

    d, D, L, tf = dims["d"], dims["D_hub"], dims["L_hub"], dims["tf"]
    Dp, Df, rim, rim_h = dims["Dp"], dims["D_flange"], dims["rim"], dims["rim_h"]
    w, t, l_key, n, db = dims["w"], dims["t"], dims["l_key"], int(dims["n_bolts"]), dims["d_bolt"]
    shaft_len = dims["shaft_len"]
    m = DATA["modelling_choices"]
    clr = times(m["clearance"], d)
    af, hh, nh = m["bolt_head_across_flats"]["times"] * db, m["bolt_head_height"]["times"] * db, m["nut_height"]["times"] * db
    span = Df + 2 * shaft_len

    def bolt_holes(diameter):
        cut = None
        for i in range(n):
            a = 2 * math.pi * i / n
            hole = rod_along_x(diameter, -span, 2 * span).translate((0, Dp / 2 * math.cos(a), Dp / 2 * math.sin(a)))
            cut = hole if cut is None else cut.union(hole)
        return cut

    def keyway(x0, length):
        """Half-depth slot in the hub bore and in the shaft, on the +Z side."""
        return box(x0, x0 + length, -w / 2, w / 2, d / 2 - t / 2, d / 2 + t / 2)

    # flanges: hub + flange disc, bored, keyway cut, bolt holes cut
    left = (rod_along_x(D, -(tf + L), L)
            .union(rod_along_x(Df, -tf, tf))
            .union(rod_along_x(Df, 0, rim_h).cut(rod_along_x(Df - 2 * rim, -1, rim_h + 2)))  # protecting rim
            .cut(rod_along_x(d + 2 * clr, -span, 2 * span))
            .cut(keyway(-(tf + L), L + tf))
            .cut(bolt_holes(db + 2 * clr))
            .clean())
    right = (rod_along_x(D, tf, L)
             .union(rod_along_x(Df - 2 * rim - 2 * clr, 0, tf))
             .cut(rod_along_x(d + 2 * clr, -span, 2 * span))
             .cut(keyway(0, L + tf))
             .cut(bolt_holes(db + 2 * clr))
             .clean())

    parts = {
        "shaft_left": rod_along_x(d, -(tf + L + shaft_len), L + tf + shaft_len).cut(keyway(-(tf + L), L)).clean(),
        "shaft_right": rod_along_x(d, 0, L + tf + shaft_len).cut(keyway(tf, L)).clean(),
        "flange_left": left,
        "flange_right": right,
        "key_left": box(-(tf + L), -tf, -w / 2, w / 2, d / 2 - t / 2, d / 2 + t / 2),
        "key_right": box(tf, tf + L, -w / 2, w / 2, d / 2 - t / 2, d / 2 + t / 2),
    }
    for i in range(n):
        a = 2 * math.pi * i / n
        y, z = Dp / 2 * math.cos(a), Dp / 2 * math.sin(a)
        shank = rod_along_x(db, -tf, 2 * tf)
        head = (cq.Workplane("YZ").workplane(offset=-tf - hh).polygon(6, af / math.cos(math.radians(30)))
                .extrude(hh))
        nut = (cq.Workplane("YZ").workplane(offset=tf).polygon(6, af / math.cos(math.radians(30))).extrude(nh)
               .cut(rod_along_x(db, tf - 1, nh + 2)))
        parts[f"bolt_{i + 1}"] = shank.union(head).clean().translate((0, y, z))
        parts[f"nut_{i + 1}"] = nut.translate((0, y, z))
    return parts


def drawing_dims(dims: dict) -> list[dict]:
    d, D, L, tf, Df, Dp = dims["d"], dims["D_hub"], dims["L_hub"], dims["tf"], dims["D_flange"], dims["Dp"]
    x_end = -(tf + L + dims["shaft_len"])
    return [
        {"view": "FRONT VIEW", "p1": [x_end + 4, 0, -d / 2], "p2": [x_end + 4, 0, d / 2], "orient": "v", "offset": -7, "text": f"Ø{d:g}"},
        {"view": "FRONT VIEW", "p1": [-tf, 0, -Df / 2], "p2": [-tf, 0, Df / 2], "orient": "v", "offset": -14, "text": f"Ø{Df:g}"},
        {"view": "FRONT VIEW", "p1": [-(tf + L), 0, -D / 2], "p2": [0, 0, -D / 2], "orient": "h", "offset": 10, "text": f"{L + tf:g}"},
        {"view": "LEFT SIDE VIEW", "p1": [0, -Dp / 2, 0], "p2": [0, Dp / 2, 0], "orient": "h", "offset": 8, "text": f"Ø{Dp:g} PCD"},
    ]


def explode(dims: dict) -> dict:
    Df, n = dims["D_flange"], int(dims["n_bolts"])
    out = {"shaft_left": (-1.6 * Df, 0, 0), "shaft_right": (1.6 * Df, 0, 0),
           "flange_left": (-0.7 * Df, 0, 0), "flange_right": (0.7 * Df, 0, 0),
           "key_left": (-1.0 * Df, 0, 0.8 * Df), "key_right": (1.0 * Df, 0, 0.8 * Df)}
    for i in range(1, n + 1):
        out[f"bolt_{i}"] = (-1.8 * Df, 0, 0)
        out[f"nut_{i}"] = (1.8 * Df, 0, 0)
    return out
