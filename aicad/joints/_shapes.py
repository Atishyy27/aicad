"""Small sketch-and-extrude helpers shared by every joint."""
from __future__ import annotations

import math

import cadquery as cq


def disc(diameter: float, thickness: float, z0: float) -> cq.Workplane:
    """Circle on the XY plane, extruded up from height z0."""
    return cq.Workplane("XY").workplane(offset=z0).circle(diameter / 2).extrude(thickness)


def hexagon(across_flats: float, thickness: float, z0: float) -> cq.Workplane:
    """Regular hexagon on the XY plane, extruded up from z0."""
    across_corners = across_flats / math.cos(math.radians(30))
    return cq.Workplane("XY").workplane(offset=z0).polygon(6, across_corners).extrude(thickness)


def rod_along_x(diameter: float, x0: float, length: float) -> cq.Workplane:
    """Circle on the YZ plane, extruded along +X starting at x0."""
    return cq.Workplane("YZ").workplane(offset=x0).circle(diameter / 2).extrude(length)


def box(x0, x1, y0, y1, z0, z1) -> cq.Workplane:
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0).translate(
        ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    )


def hole_z(diameter: float, span: float) -> cq.Workplane:
    return disc(diameter, 2 * span, -span)


def hole_x(diameter: float, z: float, span: float) -> cq.Workplane:
    return rod_along_x(diameter, -span, 2 * span).translate((0, 0, z))
