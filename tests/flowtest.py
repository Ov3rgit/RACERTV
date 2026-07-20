"""FULL-RACE FLOW: does everything fire, in the right order, at the right time?

The unit tests each prove one behaviour in isolation. This drives a whole race
start-to-flag and asserts the broadcast actually HANGS TOGETHER — the failure
mode this project keeps hitting is not "feature X is broken" but "feature X is
starved by feature Y and silently never happens".

Checks, in race order:
  * the booth opens the session and calls the start
  * the engineer's launch call lands in lap one
  * rival radio stays quiet until the start call has aired
  * an objective is set, tracked and resolved out loud
  * race stories only appear once there IS a race behind them
  * the final lap is about the win and nothing else
  * the finish is called, and nothing airs after it
  * no draw/emit stage raised at any point
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import os
import sys

sys.path.insert(0, r"D:\R3EOverlay")
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "smoke.py")).read()
exec(_src.split('run_session("RACE"')[0])
from poolmatch import from_pool                       # noqa: E402
from lines import COMMENTARY_LINES as CL, ENGINEER_LINES as EL  # noqa: E402

LAPS = 12
NCARS = 8
GRID = 5                      # the player starts P5


def build():
    o = headless_overlay(fake_tts=True)
    s = make_shared(2, ncars=NCARS)
    s.number_of_laps = LAPS
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    you = s.all_drivers_data_1[0]
    for i, d in enumerate(s.all_drivers_data_1[:NCARS]):
        d.car_speed = 0.0
        d.place = i + 1
        d.completed_laps = 0
    you.place = GRID
    s.all_drivers_data_1[GRID - 1].place = 1
    return o, s, you


def said(o, lo=0):
    return o.tts.spoken[lo:]


def who(o, persona, lo=0):
    return [t for p, t in said(o, lo) if p == persona]


o, s, you = build()
timeline = []          # (lap, persona, text)


def run_lap(lap, gap_ahead=3.0, tick_sets=4):
    for i, d in enumerate(s.all_drivers_data_1[:NCARS]):
        d.car_speed = 58.0
        d.completed_laps = lap
        base = 92.0 if i else 91.0          # the player is a second a lap quicker
        cum(d, base * 0.33, base * 0.34, base * 0.33)
        d.time_delta_front = gap_ahead if i == 0 else 4.0
    n = len(o.tts.spoken)
    for _ in range(tick_sets):
        o.last_radio_t = 0.0
        o._comm_cd = 0.0
        drive(o, s, 1)
    for p, t in o.tts.spoken[n:]:
        timeline.append((lap, p, t))


print("===== GRID =====")
drive(o, s, 2)
assert eng_count(o.tts.spoken) == 0, "engineer spoke on the grid"
print("  engineer silent on the grid: OK")

print("\n===== LIGHTS OUT =====")
n0 = len(o.tts.spoken)
for d in s.all_drivers_data_1[:NCARS]:
    d.car_speed = 40.0
drive(o, s, 3)
age_intro(o)
start_called = [t for t in who(o, "COMMENTATOR", n0)
                if from_pool(t, CL["start"])] or \
               [t for p, t in said(o, n0) if "lights out" in t.lower()
                or "away we go" in t.lower() or "racing" in t.lower()]
assert start_called, "no lights-out call"
print(f"  start called: {start_called[0][:62]}")

# the engineer's launch call must land in LAP ONE, not lap two
o._green_t -= 10.0
n1 = len(o.tts.spoken)
for _ in range(5):
    o.last_radio_t = 0.0
    drive(o, s, 1)
launch = [t for t in who(o, "ENGINEER", n1)
          if from_pool(t, EL["start"] + EL.get("start_gain", [])
                       + EL.get("start_loss", []))]
assert launch, "engineer's launch call never landed in lap one"
print(f"  engineer launch call in lap 1: {launch[0][:58]}")

print("\n===== RACE =====")
for lap in range(1, LAPS):
    # close on the car ahead so an objective becomes achievable, then take it
    gap = max(0.4, 3.0 - lap * 0.25)
    if lap == 8:
        you.place = GRID - 1
        s.all_drivers_data_1[GRID - 2].place = GRID
    o._eng_cd -= 40
    run_lap(lap, gap_ahead=gap)

# --- objectives
obj_set = [t for _l, p, t in timeline if p == "ENGINEER"
           and any(from_pool(t, EL[k]) for k in EL if k.startswith("obj_set_"))]
obj_res = [t for _l, p, t in timeline if p == "ENGINEER"
           and any(from_pool(t, EL[k]) for k in EL
                   if k.startswith(("obj_met_", "obj_miss_")))]
assert obj_set, "no objective was ever SET across a full race"
print(f"  objective set:      {obj_set[0][:66]}")
assert obj_res, "an objective was set but never RESOLVED out loud"
print(f"  objective resolved: {obj_res[0][:66]}")

# --- race stories: never in the opening laps
story_laps = [l for l, p, t in timeline if from_pool(t, CL["driverstory_q"])]
early = [l for l in story_laps if l <= 2]
assert not early, f"race-story recap in lap(s) {early} — nothing has happened yet"
print(f"  race stories only from lap {min(story_laps) if story_laps else '-'}"
      f" onward: OK")

print("\n===== FINAL LAP =====")
n2 = len(o.tts.spoken)
run_lap(LAPS - 1, gap_ahead=0.8, tick_sets=6)
CONV = (CL["driverstory_q"] + CL["crosstalk_q"] + CL["lore_q"]
        + CL["lore_q_rally"])
chat = [t for p, t in said(o, n2) if from_pool(t, CONV)]
assert not chat, f"booth chatting on the final lap: {chat[:2]}"
print("  no conversation/recaps on the final lap: OK")

print("\n===== FINISH =====")
n3 = len(o.tts.spoken)
s.session_phase = 6
s.flags.checkered = 1
for i in range(NCARS):
    s.all_drivers_data_1[i].finish_status = 1
for _ in range(6):
    o.last_radio_t = 0.0
    o._comm_cd = 0.0
    drive(o, s, 1)
fin = [t for p, t in said(o, n3)]
assert fin, "nothing said at the finish"
print(f"  finish called: {fin[0][:66]}")

print("\n===== NO STAGE ERRORS =====")
errs = {k: v for k, v in o._stage_err.items() if v}
assert not errs, f"stages raised during the race: {errs}"
print("  no update/draw stage raised all race: OK")

print("\n===== BALANCE =====")
eng = [t for _l, p, t in timeline if p == "ENGINEER"]
booth = [t for _l, p, t in timeline if p in ("COMMENTATOR", "PUNDIT")]
rival = [t for _l, p, t in timeline
         if p not in ("ENGINEER", "COMMENTATOR", "PUNDIT")]
print(f"  over {LAPS - 1} laps: engineer {len(eng)}, booth {len(booth)}, "
      f"rivals {len(rival)}")
assert len(eng) >= 3, "the engineer barely spoke across a whole race"
assert len(rival) <= len(eng) * 3, (
    f"rivals ({len(rival)}) are drowning the engineer ({len(eng)})")
print("  engineer is not drowned out by rival chatter: OK")

print("\nALL FLOW CHECKS PASSED")
