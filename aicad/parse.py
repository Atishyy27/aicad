"""Turn a request sentence into a joint spec.

Order of attempts in "auto" mode:
  1. an API key (ANTHROPIC_API_KEY, then GEMINI_API_KEY)
  2. Claude Code on this machine (`claude -p`, uses the logged-in account)
  3. plain pattern matching (always available, offline)
Whatever the AI returns is checked: every number must be traceable to a number
(or number word) in the sentence, otherwise it is dropped and the tool asks.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
from dataclasses import dataclass, field

_JOINTS = [
    ("gib_and_cotter", r"\bgib\b"),
    ("sleeve_and_cotter", r"\bsleeve\b"),
    ("cotter", r"\bcott?er\b|\bsocket\b|\bspigot\b"),
    ("knuckle", r"\bk?nuc?kle\b|\bknukle\b"),
    ("nut_bolt", r"\bnut\b|\bbolts?\b|\bm\d{1,2}\b"),
]
JOINT_NAMES = [j for j, _ in _JOINTS]
_NUM = r"(\d+(?:\.\d+)?)"
_LOAD = re.compile(_NUM + r"\s*(kilo\s?newtons?|kn|newtons?|n|tonnes?|tons?|kgf|kg)\b", re.I)
_DIA = re.compile(_NUM + r"\s*mm\b", re.I)
_GRIP = re.compile(r"\b(?:grip|clamp(?:ed|ing)?|plates?|thickness)\b\D{0,20}?" + _NUM + r"\s*mm", re.I)
_GRIP_AFTER = re.compile(_NUM + r"\s*mm\s*(?:grip|clamp(?:ed|ing)?|thick|plates?)\b", re.I)
_BOLT = re.compile(r"\bm\s?(\d{1,2})\b", re.I)
_STRESS = {
    "tension_mpa": re.compile(r"\b(?:tensile|tension)\b\D{0,15}?" + _NUM + r"\s*mpa", re.I),
    "shear_mpa": re.compile(r"\bshear\b\D{0,15}?" + _NUM + r"\s*mpa", re.I),
    "crushing_mpa": re.compile(r"\b(?:crushing|compressive|bearing)\b\D{0,15}?" + _NUM + r"\s*mpa", re.I),
}
_G = 9.80665
_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "twelve": 12, "fifteen": 15, "twenty": 20, "twenty-five": 25,
    "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80,
    "ninety": 90, "hundred": 100, "half": 0.5,
}


@dataclass
class Spec:
    joint: str | None = None
    load_n: float | None = None
    rod_diameter_mm: float | None = None
    bolt_size: int | None = None
    grip_mm: float | None = None
    tension_mpa: float | None = None
    shear_mpa: float | None = None
    crushing_mpa: float | None = None
    source: str = "rules"
    notes: list[str] = field(default_factory=list)

    def missing(self) -> list[str]:
        out = []
        if self.joint is None:
            out.append("joint type")
        elif self.joint == "nut_bolt":
            if self.load_n is None and self.bolt_size is None:
                out.append("load or bolt size")
        elif self.load_n is None and self.rod_diameter_mm is None:
            out.append("load or rod diameter")
        return out

    def supported(self) -> bool:
        from .joints import REGISTRY
        return self.joint in REGISTRY

    def design_kwargs(self) -> dict:
        return {k: getattr(self, k) for k in (
            "load_n", "rod_diameter_mm", "bolt_size", "grip_mm", "tension_mpa", "shear_mpa", "crushing_mpa")}


def _to_newtons(value: float, unit: str) -> float:
    u = unit.lower().replace(" ", "")
    if u in ("kn", "kilonewton", "kilonewtons"):
        return value * 1000
    if u in ("n", "newton", "newtons"):
        return value
    if u in ("tonne", "tonnes", "ton", "tons"):
        return value * 1000 * _G
    if u in ("kg", "kgf"):
        return value * _G
    raise ValueError(unit)


def parse_rules(text: str) -> Spec:
    spec = Spec()
    low = text.lower()
    for name, pattern in _JOINTS:
        if re.search(pattern, low):
            spec.joint = name
            break
    m = _LOAD.search(text)
    if m:
        spec.load_n = _to_newtons(float(m.group(1)), m.group(2))
    m = _BOLT.search(text)
    if m:
        spec.bolt_size = int(m.group(1))
    m = _GRIP.search(text) or _GRIP_AFTER.search(text)
    if m:
        spec.grip_mm = float(m.group(1))
    if spec.joint != "nut_bolt":
        m = _DIA.search(text)
        if m:
            spec.rod_diameter_mm = float(m.group(1))
    for field_name, rx in _STRESS.items():
        m = rx.search(text)
        if m:
            setattr(spec, field_name, float(m.group(1)))
    return spec


# ---------------------------------------------------------------- AI paths

_JOINT_MEANINGS = (
    "Joint labels: 'knuckle' = knuckle joint / pin joint with an eye and a fork; "
    "'cotter' = socket and spigot cotter joint (any 'socket', 'spigot' or plain 'cotter joint'); "
    "'sleeve_and_cotter' = sleeve and cotter joint; 'gib_and_cotter' = gib and cotter joint; "
    "'nut_bolt' = any bolt, nut, nut-bolt, hex bolt or metric size like M12. "
)
_SYSTEM = (
    "You extract a mechanical joint request into JSON. The request is in English. "
    + _JOINT_MEANINGS +
    f"joint must be one of {JOINT_NAMES} or null. load_n is the axial load in newtons "
    "(convert kN x1000, tonnes x9806.65, kgf x9.80665). rod_diameter_mm is the rod diameter in mm. "
    "bolt_size is the metric bolt number (M12 -> 12). grip_mm is the clamped thickness in mm. "
    "tension_mpa, shear_mpa, crushing_mpa are allowable stresses in MPa. "
    "Use null for anything not stated. Never invent a number."
)
_FIELDS = ["joint", "load_n", "rod_diameter_mm", "bolt_size", "grip_mm", "tension_mpa", "shear_mpa", "crushing_mpa"]
_SCHEMA = {
    "type": "object",
    "properties": {
        "joint": {"type": ["string", "null"], "enum": JOINT_NAMES + [None]},
        **{f: {"type": ["number", "null"]} for f in _FIELDS[1:]},
    },
    "required": _FIELDS,
}


def _numbers_in(text: str) -> list[float]:
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)]
    nums += [v for w, v in _NUMBER_WORDS.items() if re.search(rf"\b{w}\b", text.lower())]
    return nums


def _traceable(value: float, text: str, factors=(1,)) -> bool:
    for n in _numbers_in(text):
        for f in factors:
            if abs(n * f - value) <= 0.01 * max(abs(value), 1e-9):
                return True
    return False


_LOAD_FACTORS = (1, 1000, _G, 1000 * _G)


def spec_from_ai_json(raw: dict, text: str, source: str) -> Spec:
    spec = Spec(source=source)
    joint = raw.get("joint")
    spec.joint = joint if joint in JOINT_NAMES else None
    for key in _FIELDS[1:]:
        v = raw.get(key)
        if v is None:
            continue
        v = float(v)
        if v <= 0:
            spec.notes.append(f"AI gave non-positive {key}={v:g}; dropped")
            continue
        factors = _LOAD_FACTORS if key == "load_n" else (1,)
        if not _traceable(v, text, factors):
            spec.notes.append(f"AI gave {key}={v:g}, which is not in the request; dropped")
            continue
        setattr(spec, key, int(v) if key == "bolt_size" else v)
    return spec


def _ask_anthropic(text: str, key: str, timeout: float) -> dict:
    """UNTESTED against the live API: no key existed when this was written."""
    body = {
        "model": os.environ.get("AICAD_ANTHROPIC_MODEL", "claude-haiku-4-5"),
        "max_tokens": 400,
        "system": _SYSTEM + " Reply with the JSON object only.",
        "messages": [{"role": "user", "content": f"Request: {text}"}],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        payload = json.load(r)
    txt = "".join(b.get("text", "") for b in payload["content"])
    return json.loads(txt[txt.find("{"): txt.rfind("}") + 1])


def _ask_gemini(text: str, key: str, timeout: float) -> dict:
    """UNTESTED against the live API: no key existed when this was written."""
    model = os.environ.get("AICAD_GEMINI_MODEL", "gemini-2.5-flash")
    body = {
        "systemInstruction": {"parts": [{"text": _SYSTEM}]},
        "contents": [{"parts": [{"text": f"Request: {text}"}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        payload = json.load(r)
    return json.loads(payload["candidates"][0]["content"]["parts"][0]["text"])


def claude_code_available() -> bool:
    return shutil.which("claude") is not None


def _ask_claude_code(text: str, timeout: float, runner=subprocess.run) -> dict:
    """Headless Claude Code on the logged-in account. Tools off, only local settings loaded
    (from an empty temp folder) so the user's hooks and project instructions do not run."""
    cmd = [
        shutil.which("claude") or "claude",  # on Windows this resolves to claude.cmd
        "-p", f"Request: {text}",
        "--output-format", "json",
        "--json-schema", json.dumps(_SCHEMA),
        "--tools", "",
        "--model", os.environ.get("AICAD_CLAUDE_MODEL", "haiku"),
        "--no-session-persistence",
        "--setting-sources", "local",
        "--system-prompt", _SYSTEM,
    ]
    with tempfile.TemporaryDirectory() as tmp:
        done = runner(cmd, capture_output=True, text=True, timeout=timeout, cwd=tmp)
    if done.returncode != 0:
        raise RuntimeError(f"claude exited {done.returncode}: {done.stderr.strip()[:200]}")
    payload = json.loads(done.stdout)
    if payload.get("is_error"):
        raise RuntimeError(f"claude reported an error: {str(payload.get('result'))[:200]}")
    out = payload.get("structured_output")
    if out is None:
        res = payload.get("result", "")
        out = json.loads(res[res.find("{"): res.rfind("}") + 1])
    return out


def ai_backends() -> list[str]:
    found = []
    if os.environ.get("ANTHROPIC_API_KEY"):
        found.append("anthropic-api")
    if os.environ.get("GEMINI_API_KEY"):
        found.append("gemini-api")
    if claude_code_available():
        found.append("claude-code")
    return found


def parse_ai(text: str, backend: str, timeout: float = 45, runner=subprocess.run) -> Spec:
    if backend == "anthropic-api":
        raw = _ask_anthropic(text, os.environ["ANTHROPIC_API_KEY"], timeout)
    elif backend == "gemini-api":
        raw = _ask_gemini(text, os.environ["GEMINI_API_KEY"], timeout)
    elif backend == "claude-code":
        raw = _ask_claude_code(text, timeout, runner=runner)
    else:
        raise ValueError(backend)
    return spec_from_ai_json(raw, text, source=backend)


_MERGE_FIELDS = ["joint", "load_n", "rod_diameter_mm", "bolt_size", "grip_mm", "tension_mpa", "shear_mpa", "crushing_mpa"]


def merge(ai: Spec, rules: Spec) -> Spec:
    """AI answer first. A field the AI left empty is filled from the rules, with a note.
    Fields where both have a value but disagree keep the AI value, with a note."""
    out = Spec(**{f: getattr(ai, f) for f in _MERGE_FIELDS}, source=f"{ai.source}+rules", notes=list(ai.notes))
    for key in _MERGE_FIELDS:
        a, r = getattr(ai, key), getattr(rules, key)
        if a is None and r is not None:
            setattr(out, key, r)
            out.notes.append(f"AI left {key} empty; filled from rules: {r}")
        elif a is not None and r is not None and a != r and not (
            isinstance(a, float) and isinstance(r, float) and abs(a - r) <= 0.01 * abs(r)
        ):
            out.notes.append(f"AI and rules disagree on {key}: AI {a}, rules {r}; using AI")
    if not any(n.startswith("AI left") or n.startswith("AI and rules") for n in out.notes):
        out.source = ai.source
    return out


def parse(text: str, mode: str = "auto", runner=subprocess.run) -> Spec:
    """mode: 'rules' (offline), 'ai' (AI + rules fill-in, error if no AI works),
    'auto' (AI + rules fill-in, else rules alone)."""
    rules = parse_rules(text)
    if mode == "rules":
        return rules
    errors = []
    for backend in ai_backends():
        try:
            spec = parse_ai(text, backend, runner=runner)
        except Exception as exc:  # network, quota, bad JSON, CLI missing: try the next one
            errors.append(f"{backend}: {exc.__class__.__name__}: {exc}"[:200])
            continue
        spec = merge(spec, rules)
        spec.notes = errors + spec.notes if errors else spec.notes
        return spec
    if mode == "ai":
        raise RuntimeError("no AI backend worked: " + ("; ".join(errors) or "none configured"))
    rules.notes = [f"AI unavailable, used rules ({e})" for e in errors] or rules.notes
    return rules
