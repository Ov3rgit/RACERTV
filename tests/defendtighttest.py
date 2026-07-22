"""DEFEND OBJECTIVE — tighter offer threshold, and a real sustained gap before
it's called won.

Two things a driver flagged after several races:
  1. a 'hold him off' objective was being OFFERED against a car that was never
     really a threat (a couple of seconds back). OBJ_DEFEND_NEAR tightened from
     3.5s to 1.5s — genuinely close only.
  2. once clear, the objective resolved the instant the gap ticked past a
     threshold, off a single tick — a car that yo-yos back inside range (a tow,
     a backmarker) shouldn't bank the win early. It now needs a real gap
     (OBJ_DEFEND_CLEAR_GAP, 3.0s) sustained for OBJ_DEFEND_CLEAR_HOLD (7.0s).
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import sys

sys.path.insert(0, r"D:\R3EOverlay")
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])
from overlay_objective import (OBJ_DEFEND_NEAR, OBJ_DEFEND_CLEAR_GAP,  # noqa: E402
    OBJ_DEFEND_CLEAR_HOLD)


def race(ncars=8, laps=20, my_place=5):
    o = headless_overlay(fake_tts=True)
    s = make_shared(2, ncars=ncars)
    s.number_of_laps = laps
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    o._obj_reset()
    o._obj_damaged = False
    you = s.all_drivers_data_1[0]
    for i, d in enumerate(s.all_drivers_data_1[:ncars]):
        d.car_speed = 60.0
        d.place = i + 1
        d.completed_laps = 4
    you.place = my_place
    s.all_drivers_data_1[my_place - 1].place = 1
    o._racing = True
    return o, s, you


def pace(o, slot, t):
    o.recent_laps[slot] = [t, t, t]


def offer(o, s, t=None):
    order = sorted((d for d in s.all_drivers_data_1[:s.num_cars] if d.place > 0),
                   key=lambda d: d.place)
    pm = {d.place: d for d in order}
    o._obj_last_t = 0.0
    return o.objective_event(s, order, pm, time.time() if t is None else t)


def opm(s):
    order = sorted((d for d in s.all_drivers_data_1[:s.num_cars] if d.place > 0),
                   key=lambda d: d.place)
    return order, {d.place: d for d in order}


print("===== OFFER: tightened to a genuinely close car =====")
assert OBJ_DEFEND_NEAR <= 1.5, f"OBJ_DEFEND_NEAR was not tightened: {OBJ_DEFEND_NEAR}"

# a chaser 2.0s back (faster pace, would have offered under the old 3.5s
# threshold) must NOT get a defend objective now
o, s, you = race(my_place=5)
behind = s.all_drivers_data_1[5]              # P6, directly behind
pace(o, you.driver_info.slot_id, 90.0)
pace(o, behind.driver_info.slot_id, 88.0)     # chaser is faster
o.interval = {behind.driver_info.slot_id: 2.0}
got = offer(o, s)
assert not (got and got[0] == "obj_set_defend"), (
    f"a chaser 2.0s back (outside the tightened threshold) still got a defend "
    f"objective offered: {got}")
print("  a chaser 2.0s back does NOT warrant a defend objective: OK")

# the same chaser at 1.2s (genuinely close) DOES warrant one
o, s, you = race(my_place=5)
behind = s.all_drivers_data_1[5]
pace(o, you.driver_info.slot_id, 90.0)
pace(o, behind.driver_info.slot_id, 88.0)
o.interval = {behind.driver_info.slot_id: 1.2}
got = offer(o, s)
assert got and got[0] == "obj_set_defend", (
    f"a chaser 1.2s back and faster should warrant a defend objective: {got}")
print("  a chaser 1.2s back and faster DOES warrant a defend objective: OK")


print("\n===== RESOLUTION: needs a real, SUSTAINED gap to call it won =====")
assert OBJ_DEFEND_CLEAR_GAP >= 3.0 and OBJ_DEFEND_CLEAR_HOLD >= 5.0, (
    "the clear-gap / hold constants look unchanged from the loose defaults")

# a gap just past the clear threshold, held for less than the hold window,
# must NOT resolve yet
o, s, you = race(my_place=5)
you.place = 5
mk = s.all_drivers_data_1[5]                   # the car behind (P6)
o._obj = {"kind": "defend", "target_slot": mk.driver_info.slot_id,
          "target_name": "Marco", "goal_pos": 5, "gap_target": 3.0, "laps": 6,
          "lap0": you.completed_laps, "hud": "Hold P5 from Marco"}
o.interval = {mk.driver_info.slot_id: OBJ_DEFEND_CLEAR_GAP + 0.2}
order, pm = opm(s)
base = time.time()
res = o._obj_check(s, order, pm, base)
assert res is None, f"resolved instantly off a single tick past the gap: {res}"
res = o._obj_check(s, order, pm, base + OBJ_DEFEND_CLEAR_HOLD - 2.0)
assert res is None, (
    f"resolved before the hold window elapsed ({OBJ_DEFEND_CLEAR_HOLD - 2.0}s "
    f"< {OBJ_DEFEND_CLEAR_HOLD}s): {res}")
print("  clear gap under the hold window does NOT resolve yet: OK")

# a yo-yo (the chaser gets a tow and closes back within range) resets the
# clock -- it must NOT bank the win off the earlier, now-lapsed gap
o.interval = {mk.driver_info.slot_id: 1.0}     # chaser is back on it
res = o._obj_check(s, order, pm, base + OBJ_DEFEND_CLEAR_HOLD - 1.0)
assert res is None and o._obj is not None, (
    f"a yo-yo (chaser closed back up) still resolved the objective: {res}")
print("  a chaser closing back up resets the hold — no early win: OK")

# now hold the clear gap continuously for the full window -> MET
o.interval = {mk.driver_info.slot_id: OBJ_DEFEND_CLEAR_GAP + 0.5}
c0 = time.time() + 1000.0
o._obj_check(s, order, pm, c0)                        # re-arm
res = o._obj_check(s, order, pm, c0 + OBJ_DEFEND_CLEAR_HOLD + 0.5)
assert res and res[0] == "obj_met_defend_clear", (
    f"a genuinely sustained clear gap did not resolve as met: {res}")
assert o._obj is None
print(f"  a sustained clear gap resolves as won: OK -> {res[0]}")

print("\nDEFEND-TIGHTENING CHECKS PASSED")
