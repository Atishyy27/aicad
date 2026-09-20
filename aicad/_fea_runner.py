"""Runs inside FreeCAD (freecadcmd), driven by a JSON job written by aicad/fea.py.

Imports one part, picks the faces to hold and to push, meshes with gmsh, solves with
CalculiX, and writes the highest von Mises stress back as JSON.
"""
import json
import os
import traceback

try:
    import FreeCAD as App
    import ObjectsFem
    import Part
    from femmesh import gmshtools
    from femtools import ccxtools
except ImportError:  # not inside FreeCAD
    App = None


def _planar(faces):
    return [(i + 1, f) for i, f in enumerate(faces) if str(f.Surface).startswith("<Plane")]


def _cylindrical(faces):
    return [(i + 1, f) for i, f in enumerate(faces) if "Cylinder" in str(f.Surface)]


def _axis_value(face, axis):
    c = face.CenterOfMass
    return {"x": c.x, "y": c.y, "z": c.z}[axis]


def _normal_along(face, axis):
    try:
        n = face.normalAt(0, 0)
    except Exception:
        return False
    v = {"x": abs(n.x), "y": abs(n.y), "z": abs(n.z)}[axis]
    return v > 0.9


def pick_faces(shape, rule, dims):
    """Return face numbers matching a rule from aicad/fea.py CASES."""
    faces = shape.Faces
    kind = rule["kind"]
    if kind == "cylinder":
        want = dims[rule["dia"]]
        return [i for i, f in _cylindrical(faces) if abs(2 * f.Surface.Radius - want) < 0.6]
    if kind == "plane_end":
        axis, pick = rule["axis"], rule["pick"]
        cands = [(i, f) for i, f in _planar(faces) if _normal_along(f, axis)]
        if not cands:
            return []
        best = (min if pick == "min" else max)(cands, key=lambda t: _axis_value(t[1], axis))
        return [best[0]]
    if kind == "plane_normal":
        axis = rule["axis"]
        cands = [(i, f) for i, f in _planar(faces) if _normal_along(f, axis)]
        if rule.get("inside") == "slot":
            mid = (shape.BoundBox.XMin + shape.BoundBox.XMax) / 2 if axis == "x" else 0
            cands.sort(key=lambda t: abs(_axis_value(t[1], axis) - mid))
            return [i for i, _ in cands[:2]]
        if rule.get("pick"):
            best = (min if rule["pick"] == "min" else max)(cands, key=lambda t: _axis_value(t[1], axis))
            return [best[0]]
        return [i for i, _ in cands]
    return []


def main():
    job = json.loads(open(os.environ["AICAD_FEA_JOB"]).read())
    out = os.path.join(job["out"], "fea_result.json")
    res = {"ok": False}
    try:
        doc = App.newDocument("fea")
        shape = Part.Shape()
        shape.read(job["step"])
        part = doc.addObject("Part::Feature", "Part")
        part.Shape = shape
        doc.recompute()

        fixed = pick_faces(shape, job["fix"], job["dims"])
        loaded = pick_faces(shape, job["load_face"], job["dims"])
        res["fixed_faces"], res["loaded_faces"] = fixed, loaded
        if not fixed or not loaded:
            raise RuntimeError("could not find faces to hold (%s) or push (%s)" % (fixed, loaded))

        an = ObjectsFem.makeAnalysis(doc, "Analysis")
        solver = ObjectsFem.makeSolverCalculiXCcxTools(doc, "Solver")
        solver.AnalysisType = "static"
        solver.GeometricalNonlinearity = "linear"
        an.addObject(solver)

        mat = ObjectsFem.makeMaterialSolid(doc, "Material")
        m = mat.Material
        m["Name"] = "Steel"
        m["YoungsModulus"] = job["material"]["E"]
        m["PoissonRatio"] = job["material"]["nu"]
        m["Density"] = job["material"]["rho"]
        mat.Material = m
        an.addObject(mat)

        fix = ObjectsFem.makeConstraintFixed(doc, "Fixed")
        fix.References = [(part, "Face%d" % i) for i in fixed]
        an.addObject(fix)

        force = ObjectsFem.makeConstraintForce(doc, "Force")
        force.References = [(part, "Face%d" % i) for i in loaded]
        force.Force = App.Units.Quantity("%s N" % job["force_n"])   # FreeCAD stores force in mN
        d = job["direction"]
        try:
            force.DirectionVector = App.Vector(*d)
            force.Reversed = False
        except Exception:
            pass
        an.addObject(force)

        mesh = ObjectsFem.makeMeshGmsh(doc, "Mesh")
        mesh.Shape = part
        mesh.CharacteristicLengthMax = "%s mm" % job["mesh_mm"]
        an.addObject(mesh)
        doc.recompute()
        err = gmshtools.GmshTools(mesh).create_mesh()
        res["mesh_nodes"] = mesh.FemMesh.NodeCount
        if err:
            res["mesh_warning"] = str(err)[:300]

        fea = ccxtools.FemToolsCcx(an, solver)
        fea.update_objects()
        fea.setup_working_dir()
        fea.setup_ccx()
        fea.check_prerequisites()
        fea.purge_results()
        fea.write_inp_file()
        fea.ccx_run()
        fea.load_results()
        results = [o for o in doc.Objects if o.isDerivedFrom("Fem::FemResultObject")]
        if not results:
            raise RuntimeError("the solver produced no results")
        vm = results[0].vonMises
        disp = getattr(results[0], "DisplacementLengths", []) or [0]
        res.update(ok=True, max_von_mises=max(vm), mean_von_mises=sum(vm) / len(vm),
                   max_displacement_mm=max(disp), nodes=len(vm))
    except Exception:
        res["error"] = traceback.format_exc()[-1500:]
    open(out, "w").write(json.dumps(res, indent=1))


if os.environ.get("AICAD_FEA_JOB") and App is not None:
    main()
