"""Shared pieces for sizing any joint: checks, the design record, rounding."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


def load_data(joint: str) -> dict:
    return json.loads((DATA_DIR / f"{joint}.json").read_text())


@dataclass
class Check:
    name: str
    stress_mpa: float
    allowable_mpa: float
    formula: str

    @property
    def passed(self) -> bool:
        return self.stress_mpa <= self.allowable_mpa + 1e-9


@dataclass
class Design:
    joint: str
    load_n: float | None
    stresses: dict
    dims: dict = field(default_factory=dict)
    rules: dict = field(default_factory=dict)
    checks: list[Check] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    verified_against_book: bool = False
    raw: dict = field(default_factory=dict)

    @property
    def all_passed(self) -> bool:
        return all(c.passed for c in self.checks)


def next_preferred(x: float, sizes: list[float]) -> float:
    for size in sizes:
        if size >= x - 1e-9:
            return float(size)
    raise ValueError(f"needs {x:.1f} mm, larger than the biggest size in the table ({sizes[-1]} mm)")


def ceil_mm(x: float) -> float:
    return float(math.ceil(x - 1e-9))


def times(entry: dict, base: float) -> float:
    return max(entry["times"] * base, entry.get("min_mm", 0))


def stresses_from(data: dict, tension=None, shear=None, crushing=None) -> dict:
    s = data["default_stresses_mpa"]
    return {
        "tension": tension or s["tension"],
        "shear": shear or s["shear"],
        "crushing": crushing or s["crushing"],
        "bending": tension or s.get("bending", s["tension"]),
    }


def check_positive(load_n, **dims):
    if load_n is not None and load_n <= 0:
        raise ValueError("load must be positive")
    for k, v in dims.items():
        if v is not None and v <= 0:
            raise ValueError(f"{k} must be positive")
