"""HOLD THE LEAD HOME + RUNAWAY LEADER COVERAGE.

Two things a real race exposed:

1. Leading comfortably produced NO objective at all. chase/position needs a car
   ahead (there isn't one) and defend needs someone inside OBJ_DEFEND_NEAR, so
   the closing laps of a win -- the moment the race should feel like it is
   being closed out -- were silent. Driver's words: "the only objective I was
   hoping for at the end was 'hold the lead to the finish', that way the whole
   race would have felt complete."

2. With the win settled, the booth narrated the leader and nothing else. From
   the log, back to back: "with daylight", "the gap is growing", "simply has
   more", "engine turned down", "pacing themselves", "running their own race".
   One subject, six ways, while the actual racing behind went uncovered.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import os
import sys

sys.path.insert(0, r"D:\R3EOverlay")
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "smoke.py")).read()
exec(_src.split('run_session("RACE"')[0])

NCARS = 8


def build(total_laps=10, done=7):
    o = headless_overlay(fake_tts=True)
    s = make_shared(2, ncars=NCARS)
    s.number_of_laps = total_laps
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    for i, d in enumerate(s.all_drivers_data_1[:NCARS]):
        d.car_speed = 60.0
        d.place = i + 1
        d.completed_laps = done
    for _ in range(8):
        drive(o, s, 1)
    o._green_at = time.time() - 60.0
    return o, s


# ---- 1. leading in the closing laps DOES get a target ---------------------
o, s = build()
you = s.all_drivers_data_1[0]
you.place = 1
vs = you.driver_info.slot_id
o.recent_laps[vs] = [92.0, 92.1, 92.0]
for d in s.all_drivers_data_1[1:NCARS]:
    o.recent_laps[d.driver_info.slot_id] = [93.0, 93.1, 93.0]
o.interval[s.all_drivers_data_1[1].driver_info.slot_id] = 8.0   # big lead
o._obj = None
o._obj_last_t = 0.0
ev = None
for _ in range(20):
    ev = o.objective_event(s, [d for d in s.all_drivers_data_1[:NCARS]],
                           {d.place: d for d in s.all_drivers_data_1[:NCARS]},
                           time.time())
    if ev:
        break
assert ev and ev[0] == "obj_set_leadhome", (
    f"leading with 3 laps left produced no hold-the-lead target: {ev}")
assert o._obj["hud"] == "Hold the lead to the flag"
print(f"  leading in the closing laps sets a target: OK -> {ev[0]}")

# ---- 2. it RESOLVES as a win when the laps run out -----------------------
o._obj["lap0"] = you.completed_laps
you.completed_laps += o._obj["laps"]
res = o._obj_check(s, [d for d in s.all_drivers_data_1[:NCARS]],
                   {d.place: d for d in s.all_drivers_data_1[:NCARS]},
                   time.time())
assert res and res[0] == "obj_met_leadhome", f"holding the lead did not resolve as met: {res}"
print("  holding it to the flag resolves as a win: OK")

# ---- 3. ...and as a loss if the lead is surrendered ----------------------
o, s = build()
you = s.all_drivers_data_1[0]
you.place = 1
o._obj = {"kind": "leadhome", "target_slot": 1, "target_name": "Hans Gruber",
          "goal_pos": 1, "gap_target": None, "laps": 3,
          "lap0": you.completed_laps, "hud": "Hold the lead to the flag"}
you.place = 2                                    # lost it
o.cplace[you.driver_info.slot_id] = 2            # confirmed (fails read confirmed place)
# a surrendered lead must STAY lost through the hold window before it fails — a
# place that swaps straight back mid-fight is not a lost lead. Arm, then fire.
_ord = [d for d in s.all_drivers_data_1[:NCARS]]
_pm = {d.place: d for d in s.all_drivers_data_1[:NCARS]}
_b = time.time()
o._obj_check(s, _ord, _pm, _b)
res = o._obj_check(s, _ord, _pm, _b + 12.0)
assert res and res[0] == "obj_miss_leadhome", f"losing the lead did not resolve as missed: {res}"
print("  losing the lead resolves as missed: OK")

# ---- 4. a runaway win is called ONCE, not on repeat ----------------------
o, s = build()
o._comm_flags["runaway"] = False
before = len(o.tts.spoken)
o.tts._pend = 0
for i in range(6):
    o._comm_close_t = 0.0                        # allow the 15s slot each time
    o._comm_cd = 0.0
    drive(o, s, 1)
lines = [t for _p, t in o.tts.spoken[before:]]
runaway = [t for t in lines if "daylight" in t.lower()
           or "race of one" in t.lower() or "gap is growing" in t.lower()
           or "simply has more" in t.lower()]
assert len(runaway) <= 1, (
    "the booth narrated the runaway leader %d times in a row -- that is the "
    "whole final phase of the broadcast being one subject:\n  %s"
    % (len(runaway), "\n  ".join(runaway)))
print(f"  runaway leader narrated at most once: OK ({len(runaway)})")

print("\nLEAD-HOME + RUNAWAY CHECKS PASSED")
