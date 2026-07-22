"""TIGHT GAP AWARENESS + INCIDENT-ALERT VARIETY (two things a real two-race
transcript exposed):

  * the engineer cried wolf — "here he comes, defend hard" / "he'll lunge" — with
    the car a full SECOND back, way too far to make a move stick. The threat call
    now needs the car inside STRIKE_GAP (0.8s).
  * a crash-happy AI field looped the same anonymous incident sting ("someone's
    off the track!") up to four times a race. The sting picker is now a shuffle-
    bag: every clip airs before any repeat.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import os
import sys

sys.path.insert(0, r"D:\R3EOverlay")
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "smoke.py")).read()
exec(_src.split('run_session("RACE"')[0])
from overlay_common import STRIKE_GAP                       # noqa: E402

NCARS = 8


def race(my_place=5):
    o = headless_overlay(fake_tts=True)
    s = make_shared(2, ncars=NCARS)
    s.number_of_laps = 20
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    o._obj_reset()
    o._obj_damaged = False
    you = s.all_drivers_data_1[0]
    for i, d in enumerate(s.all_drivers_data_1[:NCARS]):
        d.car_speed = 60.0
        d.place = i + 1
        d.completed_laps = 4
    you.place = my_place
    s.all_drivers_data_1[my_place - 1].place = 1
    o._racing = True
    return o, s, you


print("===== 1. the engineer only cries 'here he comes' in striking range =====")
o, s, you = race(my_place=5)
base = {"kind": "defend", "target_name": "Rossi", "goal_pos": 5, "laps": 6,
        "lap0": you.completed_laps, "hud": "Hold P5", "_trend": -1,
        "_laps_left": 4}


def nudge_with_gap(gap):
    o._obj = dict(base, _gap=gap)
    o._obj_nudge_t = 0.0
    o._obj_nudge_i = 1                 # -> slot 2: the live-trend branch
    return o._obj_nudge(s, you, time.time())[0]


far = nudge_with_gap(1.9)             # closing, but a second-plus back
assert far == "obj_nudge_holding", (
    f"the engineer cried wolf from 1.9s back — got {far}, expected a calm hold")
print("  closing from 1.9s -> calm holding check-in, NOT a threat call: OK")

near = nudge_with_gap(0.4)            # genuinely on your gearbox
assert near == "obj_nudge_threat", (
    f"a car 0.4s back and closing wasn't flagged as a threat: {near}")
print("  closing inside 0.4s -> 'here he comes, defend': OK")

# the boundary is STRIKE_GAP and it is TIGHT
assert nudge_with_gap(STRIKE_GAP + 0.1) == "obj_nudge_holding"
assert nudge_with_gap(STRIKE_GAP - 0.1) == "obj_nudge_threat"
print(f"  threat threshold is a tight {STRIKE_GAP}s: OK")


print("\n===== 2. incident alerts cycle the whole pool before repeating =====")
from tts import Tts, STING_LINES                            # noqa: E402
t = Tts.__new__(Tts)                  # bypass heavy __init__; only the bag is used
pool_n = len(STING_LINES["alert"])
assert pool_n >= 16, f"the alert pool is too small to hide repeats: {pool_n}"
clips = [(f"clip{i}.wav", f"alert line {i}") for i in range(pool_n)]
seen = [t._sting_choose("alert", clips)[0] for _ in range(pool_n)]
assert len(set(seen)) == pool_n, (
    f"a sting repeated before the pool was exhausted: {pool_n - len(set(seen))} "
    f"repeat(s) in the first {pool_n} draws")
print(f"  all {pool_n} alerts air before any repeat: OK")
# ...and across the bag boundary it never repeats the very last one back-to-back
nxt = t._sting_choose("alert", clips)[0]
assert nxt != seen[-1], "a sting repeated immediately across the bag refill"
print("  no back-to-back repeat across the bag refill: OK")

print("\nGAP-AWARENESS + ALERT-VARIETY CHECKS PASSED")
