"""Timed-race end-of-race awareness: booth + engineer announce minutes to go,
and lap races announce '5 laps to go'."""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"  # tests: no disk deck state

import sys
sys.path.insert(0, r"D:\R3EOverlay")
import r3e_data as R
from r3e_overlay import Overlay
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])


def newo(ncars=6):
    o = headless_overlay(fake_tts=True)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    return o


# ---- TIMED race: booth + engineer count down the minutes -------------------
print("===== TIMED RACE CLOCK =====")
o = newo()
s = make_shared(2)
s.number_of_laps = -1          # timed race
s.session_time_duration = 1200.0
s.session_time_remaining = 1200.0
you = s.all_drivers_data_1[0]
for i in range(s.num_cars):
    s.all_drivers_data_1[i].car_speed = 55.0
drive(o, s, 3); age_intro(o)
# wind the clock down through the milestones
lap = 0
for secs in (700, 590, 290, 110, 55):
    s.session_time_remaining = secs
    lap += 1
    for i in range(s.num_cars):
        s.all_drivers_data_1[i].completed_laps = lap
    for _ in range(3):
        o._comm_cd = 0.0
        o._eng_cd -= 20
        drive(o, s, 1)
booth = [t for p, t in o.tts.spoken if p in ("COMMENTATOR", "PUNDIT")
         and ("minute" in t.lower() or "clock" in t.lower())]
eng = [t for p, t in o.tts.spoken if p == "ENGINEER"
       and ("minute" in t.lower() or "clock" in t.lower())]
print(f"  booth clock callouts: {len(booth)}")
for t in booth: print(f"    [booth] {t[:62]}")
print(f"  engineer clock callouts: {len(eng)}")
for t in eng: print(f"    [eng]   {t[:62]}")
assert booth, "booth never mentioned the clock winding down!"
assert eng, "engineer never mentioned minutes to go!"
# both should hit the 5-min and the 1-min marks
assert any("5 minutes" in t for t in booth + eng), "missing 5-minute callout"
assert any("1 minute" in t for t in booth + eng), "missing 1-minute callout"
print("  TIMED race end awareness (booth + engineer): OK")


# ---- LAP race: '5 laps to go' is announced ---------------------------------
print("\n===== LAP RACE '5 TO GO' =====")
o = newo()
s = make_shared(2)
s.number_of_laps = 12
you = s.all_drivers_data_1[0]
for i in range(s.num_cars):
    s.all_drivers_data_1[i].car_speed = 55.0
drive(o, s, 3); age_intro(o)
for lap in range(1, 9):        # leader reaches lap 7 -> 5 to go
    for i in range(s.num_cars):
        s.all_drivers_data_1[i].completed_laps = lap
    for _ in range(2):
        o._comm_cd = 0.0
        o._eng_cd -= 20
        drive(o, s, 1)
five = [t for p, t in o.tts.spoken if "5 laps" in t.lower()
        or "five laps" in t.lower() or "5 to go" in t.lower()]
print(f"  '5 laps to go' callouts: {len(five)}")
for t in five[:4]: print(f"    {t[:62]}")
assert five, "nobody announced 5 laps to go!"
print("  LAP race '5 to go' awareness: OK")

print("\nALL END-AWARENESS CHECKS PASSED")
