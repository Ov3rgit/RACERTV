"""Track limits + incident count must reach the engineer in OFFLINE races.

cut_track_warnings / incident_points / max_incident_points are SERVER fields
(-1 = N/A per r3e.h), so racing offline vs AI they never move. The engineer
used to say nothing about limits or incidents at all in that (very common)
case. He now keeps his own tally and escalates on it.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import sys
sys.path.insert(0, r"D:\R3EOverlay")
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])
import re
from lines import ENGINEER_LINES


def _chunks(pool):
    """Longest literal run of each template (between {placeholders}), so an
    EMITTED (already-formatted) line can be matched back to its pool."""
    out = []
    for t in pool:
        c = max((p.strip() for p in re.split(r"\{[^}]*\}", t)), key=len)
        if len(c) >= 10:
            out.append(c)
    return out


def from_pool(text, pool):
    return any(c in text for c in _chunks(pool))


def newo(offline=True):
    o = headless_overlay(fake_tts=True)
    s = make_shared(2)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    if offline:                       # vs AI: every server field is N/A
        s.incident_points = -1
        s.max_incident_points = -1
        s.cut_track_warnings = -1
    for i in range(s.num_cars):
        s.all_drivers_data_1[i].car_speed = 60.0
    drive(o, s, 3)
    age_intro(o)
    for i in range(s.num_cars):
        s.all_drivers_data_1[i].completed_laps = 2
    drive(o, s, 2)
    return o, s


def do_off(o, s):
    """One confirmed excursion: lap invalidates at speed, then pace collapses."""
    you = s.all_drivers_data_1[0]
    n = len(o.tts.spoken)
    you.car_speed = 60.0
    you.current_lap_valid = 1
    o._eng_cd -= 40
    o._eng_off_cd = -1e9
    drive(o, s, 1)
    you.current_lap_valid = 0
    drive(o, s, 1)
    you.car_speed = 8.0
    o._eng_cd -= 40
    drive(o, s, 2)
    return [t for p, t in o.tts.spoken[n:] if p == "ENGINEER"]


print("===== OFFLINE TRACK LIMITS (server fields N/A) =====")
o, s = newo()
said = []
for i in range(6):
    said.append(do_off(o, s))
    assert said[-1], f"off {i+1} produced NO engineer warning!"
    print(f"  off {i+1}: {said[-1][0][:72]}")
assert o._own_cuts == 6, f"own cut tally wrong: {o._own_cuts}"
print("  own tally counted all six: OK")

# escalation: the count must be SPOKEN, and the later ones must differ in tone
flat = [x for grp in said for x in grp]
assert any(from_pool(t, ENGINEER_LINES["warn_limits_repeat"]) for t in flat), \
    "no repeat-tier limits warning fired"
assert any(from_pool(t, ENGINEER_LINES["warn_limits_serious"]) for t in flat), \
    "no serious-tier limits warning fired"
assert any("2" in t or "3" in t or "4" in t for t in flat), \
    "the running count is never spoken"
print("  escalated through repeat -> serious tiers: OK")
assert "{" not in "".join(flat), "unformatted placeholder leaked"
print("  no unformatted placeholders: OK")


print("\n===== OFFLINE INCIDENT TALLY =====")
o, s = newo()
for _ in range(3):
    do_off(o, s)
n = len(o.tts.spoken)
s.all_drivers_data_1[0].car_speed = 60.0
s.all_drivers_data_1[0].current_lap_valid = 1
o._eng_off_cd = -1e9          # 25s+ since the off (reflective window)
o._own_inc_cd = -1e9
for _ in range(4):
    o._eng_cd -= 40
    drive(o, s, 1)
tally = [t for p, t in o.tts.spoken[n:]
         if p == "ENGINEER" and from_pool(t, ENGINEER_LINES["incident_tally"])]
assert tally, "no incident tally after 3 incidents!"
print(f"  tally aired: {tally[0][:72]}")
assert "3" in tally[0], "tally doesn't state the count"
print("  states the running count: OK")

# It must NOT echo the off it just happened alongside. do_off() clears
# _eng_off_cd so offs can be staged back-to-back, so re-arm it here (as a
# real off does) and tick immediately: the tally must stay quiet.
o2, s2 = newo()
for _ in range(3):
    do_off(o2, s2)
import time as _t
o2._eng_off_cd = _t.time()        # the off JUST happened
o2._own_inc_cd = -1e9
n2 = len(o2.tts.spoken)
s2.all_drivers_data_1[0].car_speed = 60.0
s2.all_drivers_data_1[0].current_lap_valid = 1
for _ in range(4):
    o2._eng_cd -= 40
    drive(o2, s2, 1)
echo = [t for p, t in o2.tts.spoken[n2:]
        if p == "ENGINEER" and from_pool(t, ENGINEER_LINES["incident_tally"])]
assert not echo, f"tally echoed the limits warning instead of waiting: {echo}"
print("  does not echo the limits call: OK")


print("\n===== ONLINE (server publishes the counters) =====")
o, s = newo(offline=False)
s.max_incident_points = 20
s.cut_track_warnings = 0
n = len(o.tts.spoken)
s.incident_points = 4                     # server awards points
o._eng_cd -= 40
drive(o, s, 3)
pts = [t for p, t in o.tts.spoken[n:] if p == "ENGINEER"]
assert pts, "server incident points produced no engineer call"
assert "4" in pts[0] and "20" in pts[0], f"server figures not quoted: {pts[0]}"
print(f"  server points call: {pts[0][:72]}")

n = len(o.tts.spoken)
s.cut_track_warnings = 1                  # server limits counter ticks
o._eng_cd -= 40
o._eng_off_cd = -1e9
drive(o, s, 3)
cut = [t for p, t in o.tts.spoken[n:] if p == "ENGINEER"]
assert cut, "server cut_track_warnings produced no engineer call"
print(f"  server limits call: {cut[0][:72]}")

print("\nALL TRACK-LIMITS / INCIDENT CHECKS PASSED")
