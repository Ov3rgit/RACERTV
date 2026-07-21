"""Grammar: a count of 1 must read singular in spoken lines.

Race-ending objectives always clamp their deadline to a single lap (overlay_objective
only lets a fresh target through at the flag when laps == 1), and the engineer's
timed-race clock line divides down to '1 minute' in the final minute. The line pools
hardcode the plural noun ('{laps} laps', '{mins} minutes') because they read right for
every count >= 2, so 1 was the one ungrammatical case that aired as '1 laps' / '1
minutes'. _safe_format now collapses it. Guard both the fix and its non-firing cases.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from overlay_common import _safe_format

# ---- 1. the count of 1 collapses to singular -----------------------------
cases = [
    ("Hold it to the flag, {laps} laps.", {"laps": 1}, "1 lap", "1 laps"),
    ("Clock's at {mins} minutes, keep going.", {"mins": 1}, "1 minute", "1 minutes"),
    ("P{pos} for {laps} laps of smooth driving.", {"pos": 1, "laps": 1},
     "1 lap of", "1 laps of"),
]
for tmpl, kw, want, bad in cases:
    out = _safe_format(tmpl, kw)
    assert want in out and bad not in out, f"'{bad}' still airs: {out!r}"
print("  count of 1 reads singular: OK")

# ---- 2. legitimate plurals are left untouched ----------------------------
for n in (2, 3, 5, 11, 21):
    out = _safe_format("get within {laps} laps", {"laps": n})
    assert f"{n} laps" in out, f"plural {n} was mangled: {out!r}"
print("  counts >= 2 (incl. 11/21) untouched: OK")

# ---- 3. end-to-end: the objective set-line never emits '1 laps' ----------
# The offer clamps a race-ending target to a single lap; the spoken line must
# still be grammatical no matter which template the pool picks.
import json  # noqa: E402
_p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                  "lines_data", "engineer_lines.json")
with open(_p, encoding="utf-8") as _f:
    _eng = json.load(_f).get("obj_set_leadhome") or []
assert _eng, "obj_set_leadhome pool missing"
for tmpl in (_eng if isinstance(_eng, list) else [_eng]):
    out = _safe_format(tmpl, {"laps": 1, "drv": "the field", "pos": 1})
    assert "1 laps" not in out, f"leadhome set-line airs '1 laps': {out!r}"
print("  every leadhome set-line is singular at the flag: OK")

print("\nPLURAL GRAMMAR CHECKS PASSED")
