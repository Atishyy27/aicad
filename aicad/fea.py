"""Finite-element stress on one part, using FreeCAD's CalculiX solver, to compare with the
hand calculation the tool already did.

This is not ANSYS. It is a single linear-static run on one part, with boundary conditions the
tool chooses. Read it as a second opinion on the textbook formula, not as proof.

    python -m aicad.fea "knuckle joint for 50 kN"

Validation: a 20 mm bar pulled by 10 kN gives 32.22 MPa against the hand answer 31.83 MPa,
a 1.2 % difference, which is the edge effect at the fixed face (tests/test_fea.py).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from .freecad_pack import find_freecadcmd

# For each joint: which part to analyse, how to hold it, where to push, and which of the
# tool's own checks the result should be compared with.
CASES = {
    "knuckle": {
        "part": "single_eye_rod",
        "fix": {"kind": "cylinder", "dia": "d"},          # the bore, where the pin bears
        "load": {"kind": "plane_end", "axis": "x", "pick": "min"},   # the far end of the rod
        "direction": [-1, 0, 0],
        "compare": "rod tension",
        "note": "Eye rod held at the pin bore, pulled at the rod end.",
    },
    "cotter": {
        "part": "spigot",
        "fix": {"kind": "plane_normal", "axis": "x", "inside": "slot"},
        "load": {"kind": "plane_end", "axis": "x", "pick": "min"},
        "direction": [-1, 0, 0],
        "compare": "rod tension",
        "note": "Spigot held at the cotter slot faces, pulled at the rod end.",
    },
    "sleeve_and_cotter": {
        "part": "rod_left",
        "fix": {"kind": "plane_normal", "axis": "x", "inside": "slot"},
        "load": {"kind": "plane_end", "axis": "x", "pick": "min"},
        "direction": [-1, 0, 0],
        "compare": "rod tension",
        "note": "Rod held at its cotter slot faces, pulled at the rod end.",
    },
    "gib_and_cotter": {
        "part": "rod",
        # the cotter bears on the far wall of the slot, which is the wall the "rod end shear"
        # check says could tear out
        "fix": {"kind": "plane_near", "axis": "x", "at": {"xs": 1, "b": 0.5}},
        "load": {"kind": "plane_end", "axis": "x", "pick": "min"},
        "direction": [-1, 0, 0],
        "compare": "rod tension",
        "note": "Rod held at the far wall of the cotter slot, pulled at the round rod end.",
    },
    "nut_bolt": {
        "part": "bolt",
        "fix": {"kind": "plane_normal", "axis": "z", "pick": "min"},  # under the head
        "load": {"kind": "plane_end", "axis": "z", "pick": "max"},
        "direction": [0, 0, 1],
        "compare": "bolt tension",
        "note": "Bolt held under the head, pulled at the end of the shank.",
    },
}

_SCRIPT = Path(__file__).with_name("_fea_runner.py")


def available() -> bool:
    return find_freecadcmd() is not None


def run(joint, design, out_dir: Path, timeout: float = 900, converge_check: bool = True) -> dict:
    """Run one linear-static analysis and compare it with the matching hand calculation."""
    name = joint.NAME
    if name not in CASES:
        return {"ok": False, "reason": f"no finite-element case defined for {name} yet"}
    exe = find_freecadcmd()
    if exe is None:
        return {"ok": False, "reason": "FreeCAD not found (install it or set FREECAD_CMD)"}

    case = CASES[name]
    out_dir = Path(out_dir).resolve()
    step = out_dir / "parts" / f"{case['part']}.step"
    if not step.exists():
        return {"ok": False, "reason": f"{step.name} not found; build the joint first"}

    check = next((c for c in design.checks if c.name == case["compare"]), None)
    load = design.load_n or 0.0
    job = {
        "step": str(step),
        "out": str(out_dir),
        "force_n": load,
        "direction": case["direction"],
        "fix": case["fix"],
        "load_face": case["load"],
        "dims": design.dims,
        "material": {"E": "210000 MPa", "nu": "0.30", "rho": "7850 kg/m^3"},
        "mesh_mm": max(2.0, round(min(design.dims.get("d", 20), design.dims.get("D", 20)) / 6, 1)),
    }
    job_file = out_dir / "fea_job.json"
    job_file.write_text(json.dumps(job, indent=1))
    env = dict(os.environ, AICAD_FEA_JOB=str(job_file))
    done = subprocess.run([exe, str(_SCRIPT)], capture_output=True, text=True, timeout=timeout, env=env)
    result_file = out_dir / "fea_result.json"
    if not result_file.exists():
        return {"ok": False, "reason": f"freecadcmd exited {done.returncode}",
                "log": (done.stdout + done.stderr)[-600:]}
    r = json.loads(result_file.read_text())

    # When the finite-element peak sits well above the hand calculation, the question is whether
    # it is a real concentration or an artefact of the mesh and of clamping a face rigidly. The
    # test is to solve again on a finer mesh and see whether the peak stays put.
    #
    # Measured on the gib and cotter rod at four mesh sizes (6.0, 4.0, 2.5, 1.6 mm), the peak
    # read 157, 180, 175 and 191 MPa across a 16x increase in nodes: wandering by about 10%,
    # not settling. A single refinement step is therefore a weak test and can report "stable"
    # by luck, which is why the step here is a halving and the band is tight.
    if r.get("ok") and check is not None and converge_check:
        ratio = r["max_von_mises"] / max(check.stress_mpa, 1e-9)
        if ratio > 1.5:
            job["mesh_mm"] = round(job["mesh_mm"] * 0.5, 2)
            job_file.write_text(json.dumps(job, indent=1))
            subprocess.run([exe, str(_SCRIPT)], capture_output=True, text=True,
                           timeout=timeout, env=env)
            fine = json.loads(result_file.read_text())
            if fine.get("ok"):
                moved = 100 * (fine["max_von_mises"] - r["max_von_mises"]) / r["max_von_mises"]
                r["fine_mesh_mpa"] = round(fine["max_von_mises"], 1)
                r["fine_mesh_nodes"] = fine["mesh_nodes"]
                r["peak_moved_pct"] = round(moved, 1)
                r["converged"] = abs(moved) <= 5
                if not r["converged"]:
                    r["warning"] = (
                        f"The peak moved {moved:+.0f}% when the mesh was halved "
                        f"({r['mesh_nodes']:,} to {fine['mesh_nodes']:,} nodes, "
                        f"{r['max_von_mises']:.0f} to {fine['max_von_mises']:.0f} MPa), so it "
                        f"has not settled. Read it as a concentration at a sharp corner or at "
                        f"the face the tool clamped, not as a design stress. Design to the hand "
                        f"calculation.")

    if r.get("ok") and check is not None:
        r["hand_mpa"] = round(check.stress_mpa, 2)
        r["hand_check"] = check.name
        r["difference_pct"] = round(100 * (r["max_von_mises"] - check.stress_mpa) / check.stress_mpa, 1)
        r["allowable_mpa"] = check.allowable_mpa
        r["passes_allowable"] = r["max_von_mises"] <= check.allowable_mpa
    r["part"] = case["part"]
    r["note"] = case["note"]
    r["force_n"] = load
    return r


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="aicad.fea", description="Finite-element check on one part.")
    ap.add_argument("request", nargs="+")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)
    text = " ".join(args.request)

    from .export import export_all
    from .joints import REGISTRY
    from .parse import parse_rules

    spec = parse_rules(text)
    if spec.missing() or not spec.supported():
        print(f"Cannot read that request: {spec.missing() or spec.joint}", file=sys.stderr)
        return 2
    joint = REGISTRY[spec.joint]
    design = joint.design(**spec.design_kwargs())
    out = args.out or Path("out") / f"fea_{joint.NAME}_{datetime.now():%Y%m%d-%H%M%S}"
    print("Building the part...")
    export_all(joint.build_parts(design.dims), design, joint, out, request=text)
    print("Meshing and solving with CalculiX (a minute or two)...")
    r = run(joint, design, out)
    if not r.get("ok"):
        print(f"Finite-element run failed: {r.get('reason') or r.get('error', '')[:300]}", file=sys.stderr)
        return 1
    print(f"\nPart: {r['part']}  ({r['note']})")
    print(f"Mesh: {r['mesh_nodes']:,} nodes")
    print(f"Finite element, highest von Mises stress: {r['max_von_mises']:.1f} MPa")
    if "hand_mpa" in r:
        print(f"Hand calculation ({r['hand_check']}):          {r['hand_mpa']:.1f} MPa")
        print(f"Difference: {r['difference_pct']:+.1f} %")
        print(f"Allowed: {r['allowable_mpa']:g} MPa, so the finite element result "
              f"{'passes' if r['passes_allowable'] else 'FAILS'}")
    if r.get("warning"):
        print(f"\nNOT CONVERGED: {r['warning']}")
    elif r.get("converged"):
        print(f"Settled: halving the mesh to {r['fine_mesh_nodes']:,} nodes moved the peak "
              f"{r['peak_moved_pct']:+.0f}% ({r['fine_mesh_mpa']:.0f} MPa), within 5%.")
    print("\nThis is one linear-static run on one part with boundary conditions the tool chose. "
          "Stress next to a fixed face is always overstated.")
    print(f"Files: {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
