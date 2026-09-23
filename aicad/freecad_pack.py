"""Build a FreeCAD file and a 2D drawing sheet from an output folder.

Two halves:
  * run_pack() runs in our normal Python. It finds FreeCAD and calls it headless.
  * the __main__ block runs INSIDE FreeCAD's own Python (freecadcmd). It imports
    assembly.step, names and colours the parts, adds an A3 TechDraw sheet with
    front / top / right / isometric views and a dimension table, saves
    <joint>.FCStd, and exports the sheet as SVG and DXF.
"""
from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def find_freecadcmd() -> str | None:
    env = os.environ.get("FREECAD_CMD")
    if env and Path(env).exists():
        return env
    candidates = [
        "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd",
        # Debian and Ubuntu put it here under its own name, off the PATH: the package
        # freecad-python3 ships /usr/lib/freecad/bin/freecadcmd-python3 and nothing in
        # /usr/bin. Without this the Hugging Face Space would silently lose drawings and FEA.
        "/usr/lib/freecad/bin/freecadcmd-python3",
        "/usr/lib/freecad/bin/freecadcmd",
        "/usr/bin/freecadcmd",
        *sorted(glob.glob(r"C:\Program Files\FreeCAD*\bin\freecadcmd.exe"), reverse=True),
        *sorted(glob.glob(r"C:\Program Files\FreeCAD*\bin\FreeCADCmd.exe"), reverse=True),
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return (shutil.which("freecadcmd") or shutil.which("FreeCADCmd")
            or shutil.which("freecadcmd-python3"))


def run_pack(out: Path, joint, design, request: str, timeout: float = 600) -> dict:
    exe = find_freecadcmd()
    if exe is None:
        return {"ok": False, "reason": "FreeCAD not found (install it or set FREECAD_CMD)"}
    out = Path(out).resolve()
    from .joints import parts_of
    parts_named = parts_of(joint, design.dims)
    job = {
        "out": str(out),
        "joint": joint.NAME,
        "title": joint.TITLE,
        "request": request,
        "colors": joint.COLORS,
        "part_names": list(parts_named),
        "dims": [[k, joint.LABELS.get(k, k), v] for k, v in design.dims.items()],
        "load_n": design.load_n,
        "duty": design.duty,
        "verified": design.verified_against_book,
        "date": __import__("datetime").date.today().isoformat(),
        "dim_specs": joint.drawing_dims(design.dims) if hasattr(joint, "drawing_dims") else [],
    }
    (out / "freecad_job.json").write_text(json.dumps(job, indent=1))
    env = dict(os.environ, AICAD_JOB=str(out / "freecad_job.json"))
    done = subprocess.run([exe, str(Path(__file__).resolve())], capture_output=True, text=True,
                          timeout=timeout, env=env)
    result_file = out / "freecad_result.json"
    if result_file.exists():
        result = json.loads(result_file.read_text())
        result["ok"] = result.get("ok", False)
        return result
    return {"ok": False, "reason": f"freecadcmd exited {done.returncode}", "log": (done.stdout + done.stderr)[-800:]}


def open_in_freecad(path: Path) -> None:
    """Launch the FreeCAD app on a file. Only called when the user passes --open."""
    if sys.platform == "darwin":
        subprocess.Popen(["open", "-a", "FreeCAD", str(path)])
    elif os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", str(path)])


# ------------------------------------------------------------ inside FreeCAD

def _mark(stage):  # pragma: no cover - runs under freecadcmd
    """Print a marker before each stage. A segfault kills the process without a traceback,
    so the last marker printed is the call that crashed. This is how the container's
    "freecadcmd exited -11" was turned into a named step."""
    import sys
    print(f"AICAD-STAGE {stage}", flush=True)
    sys.stdout.flush()


def _inside_freecad():  # pragma: no cover - runs under freecadcmd
    import FreeCAD
    _mark(f"start FreeCAD {FreeCAD.Version()[0]}.{FreeCAD.Version()[1]}.{FreeCAD.Version()[2]}")
    import Import
    import TechDraw

    job = json.loads(Path(os.environ["AICAD_JOB"]).read_text())
    out = Path(job["out"])
    result: dict = {"ok": False}
    try:
        doc = FreeCAD.newDocument(job["joint"])
        # Two ways to read the STEP file, and the choice is not cosmetic.
        #
        # Import.insert goes through ImportOCAF2, which also reads colours and writes them onto
        # each object's view properties. With no GUI those properties are not there to write to,
        # and FreeCAD 0.20 does not raise, it segfaults partway through the shape loop. That is
        # exactly what the server showed: "import step", then ImportOCAF2 counting 6 shapes to
        # 100%, then signal 11. A segfault cannot be caught, so the choice is made up front.
        #
        # Part.insert reads the same geometry with no colour handling at all. The sheet only
        # needs shapes, so nothing that matters is lost; the saved file just has plain colours.
        gui = bool(getattr(FreeCAD, "GuiUp", False))
        _mark(f"import step via {'Import (colours)' if gui else 'Part (no colours, headless)'}")
        if gui:
            Import.insert(str(out / "assembly.step"), doc.Name)
        else:
            # Read each part from its own STEP file and label it. Reading the assembly in one
            # go with Part.insert works, but names every object assembly, assembly001 and so on,
            # which throws away the part names the saved file is meant to carry.
            import Part as _Part
            for name in job.get("part_names") or []:
                f = out / "parts" / f"{name}.step"
                if not f.exists():
                    continue
                shp = _Part.Shape()          # read first: once attached, Shape is immutable
                shp.read(str(f))
                obj = doc.addObject("Part::Feature", name)
                obj.Shape = shp
                obj.Label = name
        _mark("recompute")
        doc.recompute()
        _mark("collect parts")
        parts = [o for o in doc.Objects if o.TypeId == "Part::Feature" and o.Shape.Solids]

        # Colour is a view property and only exists when the GUI is up. Under freecadcmd there
        # is no GUI, and on FreeCAD 0.20 reaching for ViewObject there crashes the process
        # outright rather than returning nothing, which is what killed this on the server
        # (freecadcmd exited -11, right after the STEP import). GuiUp is the reliable guard;
        # hasattr is not, because the attribute exists and dies on access.
        if getattr(FreeCAD, "GuiUp", False):
            _mark("colour parts")
            for o in parts:
                rgb = job["colors"].get(o.Label)
                if rgb and getattr(o, "ViewObject", None):
                    o.ViewObject.ShapeColor = tuple(rgb)
        else:
            _mark("no GUI, skipping colours")
        result["parts"] = sorted(o.Label for o in parts)

        import Part
        _mark("make compound")
        comp = Part.makeCompound([o.Shape for o in parts])
        _mark("build sheet")
        sheet_svg, sheet_scale = build_sheet(comp, job)
        (out / "drawing.svg").write_text(sheet_svg)
        result["svg"] = str(out / "drawing.svg")
        result["sheet_scale"] = _scale_label(sheet_scale)

        res = FreeCAD.getResourceDir()
        tpl_path = next(
            (p for p in (
                os.path.join(res, "Mod/TechDraw/Templates/ISO/A3_Landscape_TD.svg"),
                os.path.join(res, "share/Mod/TechDraw/Templates/ISO/A3_Landscape_TD.svg"),
                *glob.glob(os.path.join(res, "**/A3_Landscape_TD.svg"), recursive=True),
                *glob.glob(os.path.join(res, "**/A3_Landscape*.svg"), recursive=True),
            ) if os.path.exists(p)),
            None,
        )
        page = doc.addObject("TechDraw::DrawPage", "Sheet")
        tpl = doc.addObject("TechDraw::DrawSVGTemplate", "Template")
        tpl.Template = tpl_path
        page.Template = tpl
        texts = dict(tpl.EditableTexts)
        for key in list(texts):
            low = key.lower()
            if "title" in low and "sub" not in low:
                texts[key] = job["title"]
            elif "author" in low or "drawn" in low or "creator" in low:
                texts[key] = "aicad (AI in CAD)"
            elif "scale" in low:
                texts[key] = "see views"
        tpl.EditableTexts = texts

        # overall size decides a scale that fits four views on A3
        bb = parts[0].Shape.BoundBox
        for o in parts[1:]:
            bb.add(o.Shape.BoundBox)
        biggest = max(bb.XLength, bb.YLength, bb.ZLength)
        scale = next(s for s in (2, 1.5, 1, 0.75, 0.5, 0.4, 0.25, 0.2, 0.1, 0.05) if biggest * s <= 150)

        grp = doc.addObject("TechDraw::DrawProjGroup", "Views")
        page.addView(grp)
        grp.Source = parts
        grp.ScaleType = "Custom"
        grp.Scale = scale
        grp.addProjection("Front")
        grp.addProjection("Top")
        grp.addProjection("Right")
        grp.X, grp.Y = 150, 170

        iso = doc.addObject("TechDraw::DrawViewPart", "Isometric")
        page.addView(iso)
        iso.Source = parts
        iso.Direction = FreeCAD.Vector(1, -1, 1)
        iso.ScaleType = "Custom"
        iso.Scale = scale * 0.8
        iso.X, iso.Y = 330, 200

        lines = [f"{sym} = {val:g}  ({meaning})" for sym, meaning, val in job["dims"]]
        header = [job["title"], job.get("duty", ""),
                  "All dimensions in mm." + ("" if job["verified"] else " Rules UNVERIFIED vs book.")]
        note = doc.addObject("TechDraw::DrawViewAnnotation", "DimensionTable")
        page.addView(note)
        note.Text = header + [""] + lines
        note.TextSize = 3.5
        note.X, note.Y = 330, 105

        doc.recompute()
        fcstd = out / f"{job['joint']}.FCStd"
        doc.saveAs(str(fcstd))
        result["fcstd"] = str(fcstd)
        result["scale"] = scale
        result["views"] = [v.Label for v in grp.Views] + ["Isometric"]
        for kind, fn in (("dxf", "writeDXFPage"),):
            target = out / f"drawing.{kind}"
            try:
                getattr(TechDraw, fn)(page, str(target))
                if target.exists() and target.stat().st_size > 0:
                    result[kind] = str(target)
            except Exception as exc:
                result[f"{kind}_error"] = f"{exc.__class__.__name__}: {exc}"
        result["ok"] = True
    except Exception as exc:
        import traceback
        result["error"] = traceback.format_exc()[-1500:]
    (out / "freecad_result.json").write_text(json.dumps(result, indent=1))


# ------------------------------------------------------------ A3 sheet (inside FreeCAD)

A3_W, A3_H = 420.0, 297.0
STD_SCALES = [5, 2, 1, 0.5, 0.4, 0.2, 0.1, 0.05, 0.02]  # 5:1 ... 1:50


def _scale_label(s: float) -> str:
    return f"{s:g}:1" if s >= 1 else f"1:{1 / s:g}"


def _view_basis(n, up):
    import FreeCAD
    N = FreeCAD.Vector(*n).normalize()
    U = FreeCAD.Vector(*up)
    V = (U - N * U.dot(N)).normalize()
    H = V.cross(N)
    return H, V, N


def _project(comp, n, up, hidden=True):
    """Rotate so the wanted horizontal/vertical/viewer axes become X/Y/Z, then project
    along Z. Returns (svg_group, (xmin, xmax, ymin, ymax)) in view coordinates."""
    import FreeCAD
    import TechDraw
    H, V, N = _view_basis(n, up)
    m = FreeCAD.Matrix(H.x, H.y, H.z, 0, V.x, V.y, V.z, 0, N.x, N.y, N.z, 0, 0, 0, 0, 1)
    shape = comp.copy()
    shape.transformShape(m)
    _mark("projectToSVG")
    svg = (TechDraw.projectToSVG(shape, FreeCAD.Vector(0, 0, 1), "ShowHiddenLines") if hidden
           else TechDraw.projectToSVG(shape, FreeCAD.Vector(0, 0, 1)))
    _mark("projectEx")
    edges = TechDraw.projectEx(shape, FreeCAD.Vector(0, 0, 1))
    _mark("projected ok")
    bbs = [e.BoundBox for e in edges if not e.isNull()]
    x0 = min(b.XMin for b in bbs); x1 = max(b.XMax for b in bbs)
    y0 = min(b.YMin for b in bbs); y1 = max(b.YMax for b in bbs)
    return svg, (x0, x1, y0, y1)


def _style(svg: str, s: float) -> str:
    """Line weights on paper: visible 0.35 mm, hidden 0.18 mm dashed (SP 46 style)."""
    import re
    out = []
    for grp in re.split(r"(?=<g)", svg):
        if not grp.strip():
            continue
        hidden = "stroke-dasharray" in grp.split(">", 1)[0]
        head = re.sub(r'stroke-width="[^"]*"', f'stroke-width="{(0.18 if hidden else 0.35) / s:.4f}"', grp, count=1)
        head = re.sub(r'stroke-dasharray="[^"]*"', f'stroke-dasharray="{2.0 / s:.3f},{1.0 / s:.3f}"', head, count=1)
        out.append(head)
    return "".join(out)


def _place(svg, bb, s, cx, cy):
    x0, x1, y0, y1 = bb
    mx, my = (x0 + x1) / 2, -(y0 + y1) / 2  # projectToSVG flips y
    return (f'<g transform="translate({cx - s * mx:.3f},{cy - s * my:.3f}) scale({s})">'
            f'{_style(svg, s)}</g>')


def _text(x, y, txt, size=3.5, anchor="start", weight="normal"):
    safe = str(txt).replace("&", "&amp;").replace("<", "&lt;")
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" font-family="Helvetica, Arial, sans-serif" '
            f'text-anchor="{anchor}" font-weight="{weight}" fill="#000">{safe}</text>')


def _arrow(x, y, dx, dy, size=2.5):
    """Filled arrowhead with its tip at (x, y), pointing along (dx, dy)."""
    import math
    n = math.hypot(dx, dy) or 1.0
    ux, uy = dx / n, dy / n
    bx, by = x - ux * size, y - uy * size
    px, py = -uy * size * 0.3, ux * size * 0.3
    return f'<polygon points="{x:.2f},{y:.2f} {bx + px:.2f},{by + py:.2f} {bx - px:.2f},{by - py:.2f}" fill="#000"/>'


def _dimension(a, b, orient, offset, text):
    """a, b: sheet points. Draws extension lines, a dimension line with arrows, and the value."""
    thin = 'stroke="#000" stroke-width="0.18" fill="none"'
    out = []
    if orient == "h":
        base = (min(a[1], b[1]) if offset < 0 else max(a[1], b[1])) if offset else (a[1] + b[1]) / 2
        yl = base + offset
        x1, x2 = sorted((a[0], b[0]))
        if offset:
            for p in (a, b):
                ext = yl + (1.5 if offset > 0 else -1.5)
                out.append(f'<line x1="{p[0]:.2f}" y1="{p[1] + (1 if offset > 0 else -1):.2f}" x2="{p[0]:.2f}" y2="{ext:.2f}" {thin}/>')
        out.append(f'<line x1="{x1:.2f}" y1="{yl:.2f}" x2="{x2:.2f}" y2="{yl:.2f}" {thin}/>')
        out += [_arrow(x1, yl, -1, 0), _arrow(x2, yl, 1, 0)]
        out.append(_text((x1 + x2) / 2, yl - 1.2, text, 3.2, "middle"))
    else:
        base = (min(a[0], b[0]) if offset < 0 else max(a[0], b[0])) if offset else (a[0] + b[0]) / 2
        xl = base + offset
        y1, y2 = sorted((a[1], b[1]))
        if offset:
            for p in (a, b):
                ext = xl + (1.5 if offset > 0 else -1.5)
                out.append(f'<line x1="{p[0] + (1 if offset > 0 else -1):.2f}" y1="{p[1]:.2f}" x2="{ext:.2f}" y2="{p[1]:.2f}" {thin}/>')
        out.append(f'<line x1="{xl:.2f}" y1="{y1:.2f}" x2="{xl:.2f}" y2="{y2:.2f}" {thin}/>')
        out += [_arrow(xl, y1, 0, -1), _arrow(xl, y2, 0, 1)]
        tx = xl - 1.2
        ty = (y1 + y2) / 2
        safe = str(text).replace("&", "&amp;").replace("<", "&lt;")
        out.append(f'<text x="{tx:.2f}" y="{ty:.2f}" font-size="3.2" font-family="Helvetica, Arial, sans-serif" '
                   f'text-anchor="middle" transform="rotate(-90 {tx:.2f} {ty:.2f})" fill="#000">{safe}</text>')
    return "".join(out)


def build_sheet(comp, job) -> str:
    """First-angle A3 sheet: front (top-left), left side view (right of front),
    plan (below front), isometric, dimension table and title block."""
    views = {
        "FRONT VIEW": ((0, -1, 0), (0, 0, 1)),
        "LEFT SIDE VIEW": ((-1, 0, 0), (0, 0, 1)),
        "TOP VIEW (PLAN)": ((0, 0, 1), (0, 1, 0)),
    }
    proj = {k: _project(comp, n, up) for k, (n, up) in views.items()}
    iso = _project(comp, (1, -1, 1), (0, 0, 1), hidden=False)

    # regions (x0, y0, x1, y1) on the sheet, inside the 20/10 mm borders
    R = {
        "FRONT VIEW": (25, 18, 190, 120),
        "LEFT SIDE VIEW": (195, 18, 290, 120),
        "TOP VIEW (PLAN)": (25, 128, 190, 230),
        "ISOMETRIC": (195, 128, 290, 230),
    }

    def fit(bb, reg, pad=10):
        w, h = bb[1] - bb[0], bb[3] - bb[2]
        rw, rh = reg[2] - reg[0] - pad, reg[3] - reg[1] - pad - 6
        return min(rw / max(w, 1e-6), rh / max(h, 1e-6))

    s_ortho = next(s for s in STD_SCALES if all(s <= fit(proj[k][1], R[k]) for k in proj))
    s_iso = next(s for s in STD_SCALES if s <= fit(iso[1], R["ISOMETRIC"]))

    body, placed = [], {}
    for k, (svg, bb) in list(proj.items()) + [("ISOMETRIC", iso)]:
        reg = R[k]
        s = s_iso if k == "ISOMETRIC" else s_ortho
        cx, cy = (reg[0] + reg[2]) / 2, (reg[1] + reg[3]) / 2 - 3
        body.append(_place(svg, bb, s, cx, cy))
        body.append(_text(cx, reg[3] - 2, k + ("" if k != "ISOMETRIC" else f" ({_scale_label(s)})"), 3, "middle", "bold"))
        placed[k] = (s, cx, cy, bb)

    def to_sheet(view, p):
        import FreeCAD
        n, up = views[view]
        H, V, _ = _view_basis(n, up)
        P = FreeCAD.Vector(*p)
        u, v = P.dot(H), P.dot(V)
        s, cx, cy, (x0, x1, y0, y1) = placed[view]
        return (cx + s * (u - (x0 + x1) / 2), cy + s * (y0 + y1) / 2 - s * v)

    for spec in job.get("dim_specs", []):
        if spec["view"] in views:
            a, b = to_sheet(spec["view"], spec["p1"]), to_sheet(spec["view"], spec["p2"])
            body.append(_dimension(a, b, spec["orient"], spec["offset"], spec["text"]))

    # frame: 20 mm filing margin on the left, 10 mm elsewhere
    frame = [
        f'<rect x="0" y="0" width="{A3_W}" height="{A3_H}" fill="#fff"/>',
        f'<rect x="20" y="10" width="{A3_W - 30}" height="{A3_H - 20}" fill="none" stroke="#000" stroke-width="0.7"/>',
    ]

    # dimension table, right column
    tx, ty = 298, 18
    rows = [("symbol", "value", "meaning")] + [(sym, f"{val:g}", meaning) for sym, meaning, val in job["dims"]]
    table = [f'<rect x="{tx - 2}" y="{ty - 5}" width="{A3_W - 10 - tx + 2}" height="{11 + 5.2 * len(rows)}" fill="none" stroke="#000" stroke-width="0.35"/>']
    for i, (a, b, c) in enumerate(rows):
        y = ty + 5.2 * i
        w = "bold" if i == 0 else "normal"
        table += [_text(tx, y, a, 3, weight=w), _text(tx + 27, y, b, 3, weight=w), _text(tx + 40, y, c[:30], 2.6, weight=w)]
    table.append(_text(tx, ty + 5.2 * len(rows) + 1, "All dimensions in mm", 2.6))

    # title block, bottom right
    bx0, by0, bx1, by1 = 236, 237, A3_W - 10, A3_H - 10
    tb = [
        f'<rect x="{bx0}" y="{by0}" width="{bx1 - bx0}" height="{by1 - by0}" fill="none" stroke="#000" stroke-width="0.7"/>',
        f'<line x1="{bx0}" y1="{by0 + 14}" x2="{bx1}" y2="{by0 + 14}" stroke="#000" stroke-width="0.35"/>',
        f'<line x1="{bx0}" y1="{by0 + 26}" x2="{bx1}" y2="{by0 + 26}" stroke="#000" stroke-width="0.35"/>',
        f'<line x1="{bx0 + 92}" y1="{by0 + 14}" x2="{bx0 + 92}" y2="{by1}" stroke="#000" stroke-width="0.35"/>',
        _text((bx0 + bx1) / 2, by0 + 9.5, job["title"].upper(), 6, "middle", "bold"),
        _text(bx0 + 3, by0 + 21, job.get("duty", ""), 3.2),
        _text(bx0 + 95, by0 + 21, f"Scale {_scale_label(s_ortho)}  |  FIRST ANGLE (SP 46)  |  All dims in mm", 3.2),
        _text(bx0 + 3, by0 + 33, "SGSITS Indore, Dept. of Mechanical Engineering", 3),
        _text(bx0 + 3, by0 + 39, "Major Project: Strategic Application of AI in CAD", 3),
        _text(bx0 + 95, by0 + 33, f"Date {job.get('date', '')}   Drawn by aicad", 3),
        _text(bx0 + 95, by0 + 39, ("Rules checked against design book" if job["verified"] else "Rules UNVERIFIED vs design book"), 3,
              weight="normal" if job["verified"] else "bold"),
        _text(bx0 + 3, by0 + 46, ("Request: " + job["request"])[:95], 2.4),
    ]

    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{A3_W}mm" height="{A3_H}mm" '
            f'viewBox="0 0 {A3_W} {A3_H}">' + "".join(frame + body + table + tb) + "</svg>"), s_ortho


def _running_inside_freecad() -> bool:
    try:
        import FreeCAD  # noqa: F401  (only importable under freecadcmd / FreeCAD)
        return True
    except ImportError:
        return False


if os.environ.get("AICAD_JOB") and _running_inside_freecad():
    _inside_freecad()
