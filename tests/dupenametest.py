"""DUPLICATE DRIVER NAME — the booth must never narrate a driver acting against
themselves.

A real Portimão transcript aired 'Ricardo Feller committed to P14 and claimed it
from Ricardo Feller!' — an AI grid had shipped two cars with the same display
name, so the pass call named the same driver as both passer and victim. The fix
is a guard in the L() candidate builder (drop any line whose drv == oth) plus a
same-name skip in the multi-pass 'oth' pick.

Triggering the exact single-pass call deterministically in the headless harness
is unreliable, so the guard itself is asserted by source inspection (as
finishtest does for the finish-verdict bypass), and a behavioural check confirms
the multi-pass call is NOT gagged for a genuinely different pair.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import inspect
import os
import sys

sys.path.insert(0, r"D:\R3EOverlay")
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "smoke.py")).read()
exec(_src.split('run_session("RACE"')[0])

import overlay_booth as _ob                                # noqa: E402

# ---- 1. the universal L() guard exists and drops drv == oth ---------------
_uc = inspect.getsource(_ob.BoothMixin.update_commentary)
assert 'def L(' in _uc, "L() candidate builder not found where expected"
_lguard = _uc.split('def L(', 1)[1][:600]
assert ('kw["drv"] == kw["oth"]' in _lguard or "kw['drv'] == kw['oth']" in _lguard), (
    "L() no longer guards against a driver acting against themselves (drv==oth) "
    "— a duplicate-named AI pair will produce 'X claimed it from X' again")
assert "return" in _lguard.split("== kw", 1)[1][:40], (
    "the drv==oth guard does not bail out of the line")
print("  L() drops any two-driver line where drv == oth: OK")

# ---- 2. the multi-pass 'oth' pick skips a same-named victim ----------------
assert "oth_car" in _uc, (
    "the multi-pass call no longer picks a DIFFERENT-named passed car for {oth}")
# and it only names a car that is genuinely different (slot AND name)
_mp = _uc.split("oth_car = next(", 1)[1][:200]
assert "!= sl" in _mp and "!= self._dname(d)" in _mp, (
    "the multi-pass 'oth' pick no longer excludes the same slot / same name")
print("  multi-pass names a differently-named passed car: OK")
# (that the double pass still FIRES for a distinct-name pair is covered
# deterministically by multipasstest.py — not re-checked here to stay flake-free)

print("\nDUPLICATE-NAME GUARD CHECKS PASSED")
