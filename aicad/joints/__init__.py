"""Registry of joints the tool can build. Add a module here to add a joint."""
from __future__ import annotations

from . import cotter, flange_coupling, gib_and_cotter, knuckle, nut_bolt, sleeve_and_cotter

REGISTRY = {m.NAME: m for m in (knuckle, cotter, sleeve_and_cotter, gib_and_cotter, nut_bolt,
                                flange_coupling)}


def parts_of(joint, dims) -> list[str]:
    """Part names for a design: some joints (the coupling) vary with the number of bolts."""
    return joint.parts_for(dims) if hasattr(joint, "parts_for") else joint.PARTS


def get(name: str):
    if name not in REGISTRY:
        raise KeyError(name)
    return REGISTRY[name]
