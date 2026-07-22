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
print("  multi-pass names a differently-named passed car: OK")

# ---- 3. behavioural: a genuine (distinct-name) double pass is still called -
NCARS = 8
o = headless_overlay(fake_tts=True)
s = make_shared(2, ncars=NCARS)
s.number_of_laps = 20
o._show_caption = lambda *a, **k: None
o.radio_msgs = []
for i, d in enumerate(s.all_drivers_data_1[:NCARS]):
    d.car_speed = 60.0
    d.place = i + 1
    d.completed_laps = 3
for _ in range(8):
    drive(o, s, 1)
o._green_at = time.time() - 60.0
before = len(o.tts.spoken)
mover = s.all_drivers_data_1[4]           # P5 -> P3
for d in s.all_drivers_data_1[:NCARS]:
    if d.place in (3, 4):
        d.place += 1
mover.place = 3
for _ in range(10):
    drive(o, s, 1)
said = " || ".join(t for _p, t in o.tts.spoken[before:])
assert any(w in said for w in ("places at once", "cars in one move", "in one move",
                               "Double move", "picked up", "TWO", "positions in a",
                               "dispatched", "up to P3", "pair of them")), (
    "a clean double pass was no longer narrated:\n" + said)
print("  a distinct-name double pass is still narrated: OK")

print("\nDUPLICATE-NAME GUARD CHECKS PASSED")
