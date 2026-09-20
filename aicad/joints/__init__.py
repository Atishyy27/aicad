"""Registry of joints the tool can build. Add a module here to add a joint."""
from __future__ import annotations

from . import cotter, knuckle, nut_bolt, sleeve_and_cotter

REGISTRY = {m.NAME: m for m in (knuckle, cotter, sleeve_and_cotter, nut_bolt)}


def get(name: str):
    if name not in REGISTRY:
        raise KeyError(name)
    return REGISTRY[name]
