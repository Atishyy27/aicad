"""How each joint is sized, in one place: joints take a load, the coupling takes a torque."""

# a typical design for each joint
SIZING = {
    "knuckle": {"load_n": 50_000},
    "cotter": {"load_n": 35_000},
    "sleeve_and_cotter": {"load_n": 50_000},
    "nut_bolt": {"load_n": 20_000},
    "flange_coupling": {"torque_nm": 500},
}

# a small design for each joint (geometry must still build)
SMALL = {
    "knuckle": {"load_n": 2_000},
    "cotter": {"load_n": 2_000},
    "sleeve_and_cotter": {"load_n": 2_000},
    "nut_bolt": {"load_n": 2_000},
    "flange_coupling": {"torque_nm": 50},
}

# a sweep across sizes for each joint
SWEEP = {
    "knuckle": [{"load_n": kn * 1000} for kn in (1, 2, 5, 10, 20, 50, 100, 150, 200, 300)],
    "cotter": [{"load_n": kn * 1000} for kn in (1, 2, 5, 10, 20, 50, 100, 150, 200, 300)],
    "sleeve_and_cotter": [{"load_n": kn * 1000} for kn in (1, 2, 5, 10, 20, 50, 100, 150, 200, 300)],
    "nut_bolt": [{"load_n": kn * 1000} for kn in (1, 2, 5, 10, 20, 40, 50)],
    "flange_coupling": [{"torque_nm": nm} for nm in (50, 100, 250, 500, 1000, 2000, 3000, 5000)],
}


def cases(registry):
    return [(name, kw) for name in registry for kw in SWEEP[name]]
