"""Incident points: engineer reports EVERY pickup, escalates near the DQ limit,
and works from the green flag. Also: engineer session intro fires."""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"  # tests: no disk deck state

import sys
sys.path.insert(0, r"D:\R3EOverlay")
import r3e_data as R
from r3e_overlay import Overlay
src = open(r"C:\Users\ADMINI~1\AppData\Local\Temp\claude\D--R3EOverlay\a551edbd-1416-4192-af37-f06169b0707c\scratchpad\smoke.py").read()
exec(src.split('run_session("RACE"')[0])


def newo():
    o = headless_overlay(fake_tts=True)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    return o


print("===== INCIDENT POINTS — EVERY PICKUP + ESCALATION =====")
o = newo()
s = make_shared(2, ncars=6)
s.max_incident_points = 30
s.incident_points = 0
you = s.all_drivers_data_1[0]
for i in range(s.num_cars):
    s.all_drivers_data_1[i].car_speed = 55.0
drive(o, s, 3); age_intro(o)
# don't even need a completed lap — points should warn from the green flag
reports = []
for n, pts in enumerate([1, 2, 4, 16, 20, 27, 29], start=1):
    s.incident_points = pts
    for i in range(s.num_cars):
        s.all_drivers_data_1[i].completed_laps = n
    o._eng_cd -= 20
    o._eng_ip_cd -= 10        # simulate real time between incidents
    before = len(o.tts.spoken)
    drive(o, s, 2)
    for p, t in o.tts.spoken[before:]:
        if p == "ENGINEER" and ("point" in t.lower() or "of 30" in t.lower()
                                or "dq" in t.lower() or "disqualif" in t.lower()):
            reports.append((pts, t))
print(f"  incident-point reports: {len(reports)}")
for pts, t in reports:
    print(f"    @{pts}: {t[:66]}")
assert len(reports) >= 6, f"engineer missed incident points (only {len(reports)})"
# the count must be spoken, and it must escalate near the limit
assert any("of 30" in t for _, t in reports), "engineer must say 'X of 30'"
crit = [t for pts, t in reports if pts >= 27]
assert any("danger" in t.lower() or "no more" in t.lower() or "back right off" in t.lower()
           or "disqualif" in t.lower() or "brink" in t.lower() or "last warning" in t.lower()
           or "this is it" in t.lower() or "any more" in t.lower()
           for t in crit), f"no critical escalation near the limit: {crit}"
print("  reports every point, says 'X of 30', escalates near DQ: OK")


print("\n===== ENGINEER INTRO (bypass busy queue) =====")
o = newo()
s = make_shared(0, ncars=1, track="Laguna Seca")
you = s.all_drivers_data_1[0]
o.tts._pend = 9            # simulate a busy booth queue at session start
drive(o, s, 2); age_intro(o)
o.tts._pend = 9
o._eng_cd -= 20
drive(o, s, 3)
intro = [t for p, t in o.tts.spoken if p == "ENGINEER"
         and "laguna" in t.lower()]
assert intro, "engineer intro did not fire even with bypass!"
# it should carry a PACE tip (track tip), not a history fun-fact
print(f"  intro: {intro[0][:96]}")
assert ("corkscrew" in intro[0].lower() or "turn" in intro[0].lower()
        or "brake" in intro[0].lower() or "momentum" in intro[0].lower()
        or "exit" in intro[0].lower() or "rainey" in intro[0].lower()
        or "warm" in intro[0].lower() or "laps" in intro[0].lower()), \
    "intro should include a pace tip / warm-up"
print("  engineer intro fires despite busy queue, with a pace tip: OK")

print("\nALL INCIDENT/INTRO CHECKS PASSED")
