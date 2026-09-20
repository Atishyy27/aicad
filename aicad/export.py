"""Write the part files, the assembly, an offline browser viewer and a report."""
from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path

from .design import Design

VIEWER_JS = Path(__file__).parent / "vendor" / "model-viewer.min.js"


def export_all(parts: dict, design: Design, joint, out: Path, request: str) -> Path:
    import cadquery as cq

    out = Path(out)
    (out / "parts").mkdir(parents=True, exist_ok=True)

    for name, wp in parts.items():
        cq.exporters.export(wp, str(out / "parts" / f"{name}.step"))

    assy = cq.Assembly(name=f"{joint.NAME}_assembly")
    for name, wp in parts.items():
        assy.add(wp, name=name, color=cq.Color(*joint.COLORS[name], 1.0))
    assy.export(str(out / "assembly.step"))  # default mode keeps parts separate
    assy.export(str(out / "assembly.glb"))

    exploded64 = None
    if hasattr(joint, "explode"):
        moves = joint.explode(design.dims)
        ex = cq.Assembly(name=f"{joint.NAME}_exploded")
        for name, wp in parts.items():
            ex.add(wp, name=name, color=cq.Color(*joint.COLORS[name], 1.0),
                   loc=cq.Location(cq.Vector(*moves.get(name, (0, 0, 0)))))
        ex.export(str(out / "exploded.glb"))
        exploded64 = base64.b64encode((out / "exploded.glb").read_bytes()).decode()

    stress64 = None
    if getattr(joint, "CHECK_PARTS", None) and design.checks:
        from .explain import utilisation, utilisation_colour
        util = utilisation(design, joint)
        heat = cq.Assembly(name=f"{joint.NAME}_weak_spots")
        for name, wp in parts.items():
            heat.add(wp, name=name, color=cq.Color(*utilisation_colour(util[name][0]), 1.0))
        heat.export(str(out / "weak_spots.glb"))
        stress64 = base64.b64encode((out / "weak_spots.glb").read_bytes()).decode()

    glb64 = base64.b64encode((out / "assembly.glb").read_bytes()).decode()
    (out / "viewer.html").write_text(_viewer_html(glb64, request, joint, exploded64, stress64))
    (out / "report.md").write_text(report(design, request, joint))
    return out


def _viewer_html(glb64: str, request: str, joint, exploded64: str | None = None, stress64: str | None = None) -> str:
    js = VIEWER_JS.read_text() if VIEWER_JS.exists() else ""
    script = (f'<script type="module">{js}</script>' if js else
              '<script type="module" src="https://cdn.jsdelivr.net/npm/@google/model-viewer/dist/model-viewer.min.js"></script>')
    legend = "".join(
        f'<li><span style="background:rgb({int(r*255)},{int(g*255)},{int(b*255)})"></span>{n.replace("_", " ")}</li>'
        for n, (r, g, b) in joint.COLORS.items()
    )
    safe_request = request.replace("<", "&lt;").replace(">", "&gt;")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{joint.TITLE} Viewer</title>
{script}
<style>
:root{{--bg:#f6f6f4;--fg:#1c1c1c;--muted:#666}}
@media (prefers-color-scheme: dark){{:root{{--bg:#161616;--fg:#eee;--muted:#aaa}}}}
body{{margin:0;font-family:system-ui,sans-serif;background:var(--bg);color:var(--fg)}}
header{{padding:12px 16px}} h1{{font-size:18px;margin:0}} p{{margin:4px 0;color:var(--muted);font-size:14px}}
model-viewer{{width:100%;height:75vh;background:transparent}}
ul{{display:flex;flex-wrap:wrap;gap:12px;list-style:none;padding:0 16px;margin:8px 0;font-size:14px}}
li span{{display:inline-block;width:12px;height:12px;border-radius:2px;margin-right:6px;vertical-align:-1px}}
</style></head><body>
<header><h1>{joint.TITLE}, {len(joint.COLORS)} parts</h1><p>Request: {safe_request}</p>
<p>Drag to rotate, scroll to zoom. Exact geometry is in assembly.step and parts/*.step. Works offline.</p></header>
{_toggle(exploded64, stress64)}
<model-viewer id="mv" src="data:model/gltf-binary;base64,{glb64}" camera-controls auto-rotate shadow-intensity="0.6" exposure="1.1"></model-viewer>
<ul>{legend}</ul>
{_toggle_script(glb64, exploded64, stress64)}
</body></html>
"""


def _toggle(exploded64, stress64=None):
    if not exploded64 and not stress64:
        return ""
    btn = 'style="margin-right:8px;padding:6px 12px"'
    out = f'<div style="padding:0 16px"><button onclick="show(0)" {btn}>Assembled</button>'
    if exploded64:
        out += f'<button onclick="show(1)" {btn}>Exploded</button>'
    if stress64:
        out += (f'<button onclick="show(2)" {btn}>Weak spots</button>'
                '<span id="legend" style="display:none;font-size:13px">'
                '<span style="color:#2cb335">green</span> = lots of margin, '
                '<span style="color:#e0b020">yellow</span> = about 75% of the limit, '
                '<span style="color:#e03020">red</span> = at the limit, grey = not checked</span>')
    return out + "</div>"


def _toggle_script(glb64, exploded64, stress64=None):
    if not exploded64 and not stress64:
        return ""
    uri = "data:model/gltf-binary;base64,"
    models = [uri + glb64, uri + (exploded64 or glb64), uri + (stress64 or glb64)]
    return ("<script>const M=" + "[" + ",".join(f"'{m}'" for m in models) + "];"
            "function show(i){document.getElementById('mv').src=M[i];"
            "const l=document.getElementById('legend');if(l)l.style.display=i===2?'inline':'none';}</script>")


def report(design: Design, request: str, joint) -> str:
    lines = [f"# {joint.TITLE} report", "", f"Generated {datetime.now():%Y-%m-%d %H:%M}. Request: {request}", ""]
    if not design.verified_against_book:
        lines += [f"> **UNVERIFIED:** the rules and default stresses in aicad/data/{joint.NAME}.json "
                  "have not yet been checked against the design book.", ""]
    if design.load_n is not None:
        lines.append(f"Load P = {design.load_n:,.0f} N")
    s = design.stresses
    lines += [
        f"Allowable stresses: tension {s['tension']} MPa, shear {s['shear']} MPa, crushing {s['crushing']} MPa",
        "", "## Dimensions (mm)", "", "| symbol | meaning | value | rule |", "|---|---|---|---|",
    ]
    for k, v in design.dims.items():
        lines.append(f"| {k} | {joint.LABELS.get(k, k)} | {v:g} | {design.rules.get(k, f'modelling choice, see {joint.NAME}.json')} |")
    lines += ["", "## Strength checks", ""]
    if not design.checks:
        lines.append("Skipped: no load was given.")
    else:
        lines += ["| check | formula | stress (MPa) | allowable (MPa) | result |", "|---|---|---|---|---|"]
        for c in design.checks:
            lines.append(f"| {c.name} | {c.formula} | {c.stress_mpa:.1f} | {c.allowable_mpa:g} | {'pass' if c.passed else 'FAIL'} |")
    if design.checks and getattr(joint, "CHECK_PARTS", None):
        from .explain import explain_check, utilisation
        lines += ["", "## Weak spots (how close each part is to its limit)", "",
                  "| part | worst check | share of allowed stress used |", "|---|---|---|"]
        for part, (u, c) in utilisation(design, joint).items():
            lines.append(f"| {part} | {c or 'not checked'} | {f'{100 * u:.0f}%' if u is not None else '-'} |")
        lines += ["", "## Working", ""] + [f"- {explain_check(design, c)}" for c in design.checks]
    if design.notes:
        lines += ["", "## Notes", ""] + [f"- {n}" for n in design.notes]
    return "\n".join(lines) + "\n"
