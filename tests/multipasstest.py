"""MULTI-PASS + PODIUM PRIORITY + BOOTH OBJECTIVE AWARENESS.

Each of these three had working-looking code that never actually spoke:
  * a driver gaining 2+ places at once hit NO branch (the loss branch wants
    cpd >= pv+2, the gain branch wants exactly cpd == pv-1) -> silence
  * a pass for the lead/podium was prio 2, the same as a P12 swap
  * the booth's objective reaction was gated on `not cands`, i.e. suppressed
    by any other candidate in the tick -- and objectives resolve at exactly
    the moments something else is happening

So these assert the LINE IS ACTUALLY SAID, not that the code is reachable.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import os
import sys

sys.path.insert(0, r"D:\R3EOverlay")
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "smoke.py")).read()
exec(_src.split('run_session("RACE"')[0])

NCARS = 8


def build():
    o = headless_overlay(fake_tts=True)
    s = make_shared(2, ncars=NCARS)
    s.number_of_laps = 12
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    for i, d in enumerate(s.all_drivers_data_1[:NCARS]):
        d.car_speed = 60.0
        d.place = i + 1
        d.completed_laps = 3
    return o, s


def settle(o, s, ticks=8):
    """Drive past the start. `grid_sort` suppresses place-change calls for 8s
    after the green -- correct behaviour (the lights-out shuffle is not a
    series of heroic overtakes), but it means a test that fires a pass
    immediately sees nothing. Age the green flag, then drive."""
    for _ in range(ticks):
        drive(o, s, 1)
    o._green_at = time.time() - 60.0


def texts(o):
    return " || ".join(t for _p, t in o.tts.spoken)


# ---- 1. a double pass is CALLED -------------------------------------------
o, s = build()
settle(o, s)
mover = s.all_drivers_data_1[4]          # P5
before = len(o.tts.spoken)
# P5 -> P3 in one move; the two cars it passed stay on track (not pitting)
for d in s.all_drivers_data_1[:NCARS]:
    if d.place in (3, 4):
        d.place += 1
mover.place = 3
for _ in range(10):   # places need PLACE_CONFIRM_TICKS to confirm
    drive(o, s, 1)
said = " || ".join(t for _p, t in o.tts.spoken[before:])
assert any(w in said for w in ("places at once", "cars in one move", "Double move",
                               "picked up", "splits them", "TWO", "positions in a",
                               "dispatched", "outside of the pair")), (
    "a driver took two cars in one move and the booth said nothing:\n" + said)
print("  double pass is called: OK")

# ---- 2. the passed cars being IN THE PITS is not a heroic move ------------
o, s = build()
settle(o, s)
before = len(o.tts.spoken)
for d in s.all_drivers_data_1[:NCARS]:
    if d.place in (3, 4):
        d.place += 1
        d.in_pitlane = 1                 # they pitted -- this is a cycle
s.all_drivers_data_1[4].place = 3
for _ in range(10):   # places need PLACE_CONFIRM_TICKS to confirm
    drive(o, s, 1)
said = " || ".join(t for _p, t in o.tts.spoken[before:])
assert "in one move" not in said and "places at once" not in said, (
    "a pit cycle was commentated as a double overtake:\n" + said)
print("  pit cycle is NOT called a double pass: OK")

# ---- 3. the booth reacts when a target is SET, in the right terms ---------
# A newly-SET target is deliberately only picked up ~60% of the time (the
# booth noticing every single one would be as tiresome as noticing none), so
# one attempt is not a test -- it's a coin flip. Retry until it fires; 12
# attempts at p=0.6 fails by chance about once in 10^5 runs, and never fires
# at all if the wiring is broken.
said = ""
for _attempt in range(12):
    o, s = build()
    settle(o, s)
    before = len(o.tts.spoken)
    o._obj_booth = ("set", "defend", "Hans Gruber", __import__("time").time())
    for _ in range(6):
        drive(o, s, 1)
    said = " || ".join(t for _p, t in o.tts.spoken[before:])
    if "defend this position" in said:
        break
else:
    raise AssertionError(
        "booth never picked up the pit wall's DEFEND brief in 12 attempts "
        "(so this is the wiring, not the 60% gate). Last heard:\n" + said)
print("  booth calls a defend brief: OK")

# ---- 4. ...and when it is MET (a payoff is always worth calling) ----------
o, s = build()
settle(o, s)
before = len(o.tts.spoken)
o._obj_booth = ("met", "position", "Hans Gruber", __import__("time").time())
for _ in range(6):
    drive(o, s, 1)
said = " || ".join(t for _p, t in o.tts.spoken[before:])
assert any(w in said for w in ("job done", "just hit it", "delighted",
                               "delivers exactly", "ticked it off",
                               "precisely what was needed")), (
    "booth did not call the objective being MET:\n" + said)
print("  booth calls a met objective: OK")

print("\nMULTI-PASS + OBJECTIVE AWARENESS CHECKS PASSED")

# ---- 5. the objective CHIME fires for each lifecycle event -----------------
# Wired inside _obj_notice, which is the one place all three events pass
# through. The call is wrapped in try/except (audio must never break the
# objective), so FakeTts records chimes rather than no-opping -- otherwise an
# AttributeError would be swallowed and this would pass with the sound dead.
o, s = build()
settle(o, s)
o.tts.chimed = []
o._obj = {"kind": "position", "target_name": "Hans Gruber", "hud": "P3"}
o._obj_notice("set", time.time())
assert o.tts.chimed == ["set"], f"no 'set' chime: {o.tts.chimed}"

o._obj = {"kind": "position", "target_name": "Hans Gruber", "hud": "P3"}
o._obj_done(time.time(), "obj_met_pass", {"drv": "Hans Gruber", "pos": 3})
assert "met" in o.tts.chimed, f"no 'met' chime on success: {o.tts.chimed}"

o._obj = {"kind": "position", "target_name": "Hans Gruber", "hud": "P3"}
o._obj_fail(time.time(), "obj_miss_pass", {"drv": "Hans Gruber", "pos": 5})
assert "miss" in o.tts.chimed, f"no 'miss' chime on failure: {o.tts.chimed}"
assert o.tts.chimed == ["set", "met", "miss"], (
    f"the three events must chime DIFFERENTLY, in order: {o.tts.chimed}")
print("  objective chimes fire for set/met/miss: OK")

print("\nMULTI-PASS + OBJECTIVE + CHIME CHECKS PASSED")
