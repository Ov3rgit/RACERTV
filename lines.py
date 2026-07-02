"""
Dialogue pools for the RaceRoom overlay (team radio + booth commentary).

The actual CONTENT lives in lines_data/*.json — one file per pool — so the
pools can grow huge, be edited without touching code, be validated, and one
day be community-extensible. This module is just the loader: it reads every
JSON file and exposes each as an UPPERCASE module attribute, so
`from lines import COMMENTARY_LINES, PERSONAS, ...` works exactly as before.

RacerTV broadcast booth — the two on-air characters. RacerTV is an IN-WORLD
channel of the RaceRoom universe (NOT an imitation of real F1 broadcasters), so
players treat them as game characters with their own identity, names and banter.
{comm}/{pundit} in any line fill with their names so they address each other.

Tuning/config (CAT_INTENSITY, PUNDIT_AFTER, ENG_EMOTION, colours) intentionally
stays in the engine.
"""
import json
import os
import string
import sys

if getattr(sys, "frozen", False):        # PyInstaller: data sits next to the exe
    _BASE = os.path.dirname(sys.executable)
else:
    _BASE = os.path.dirname(os.path.abspath(__file__))
_DATA = os.path.join(_BASE, "lines_data")

_FMT = string.Formatter()


def _check(name, obj, path=""):
    """Fail LOUDLY at import if a template is malformed (unbalanced braces,
    non-identifier field names) — a bad line must break the build/tests, not
    crash the booth mid-race months later."""
    if isinstance(obj, str):
        try:
            for _, field, _, _ in _FMT.parse(obj):
                if field is not None and field != "" and not field.isidentifier():
                    raise ValueError(f"bad placeholder {{{field}}}")
        except ValueError as ex:
            raise ValueError(f"{name}{path}: {ex} in template: {obj[:80]!r}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _check(name, v, f"{path}[{i}]")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            _check(name, v, f"{path}[{k!r}]")


def _load():
    mod = sys.modules[__name__]
    if not os.path.isdir(_DATA):
        raise FileNotFoundError(
            f"lines_data/ not found at {_DATA} — the dialogue JSON files must "
            "sit next to " + ("the exe" if getattr(sys, "frozen", False)
                              else "lines.py"))
    n = 0
    for fn in sorted(os.listdir(_DATA)):
        if not fn.endswith(".json"):
            continue
        name = os.path.splitext(fn)[0].upper()
        with open(os.path.join(_DATA, fn), encoding="utf-8") as f:
            obj = json.load(f)
        _check(name, obj)
        setattr(mod, name, obj)
        n += 1
    if n == 0:
        raise FileNotFoundError(f"lines_data/ at {_DATA} contains no .json files")


_load()
