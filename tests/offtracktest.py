"""Player off-track coverage:
  1) ENGINEER stays SILENT on a full-speed lap-invalidation (a harmless painted
     kerb clip — the false "you ran over the track limits" complaint), but DOES
     warn when the lap-invalid edge comes with a real speed collapse (grass/
     gravel offs that don't tick cut_track_warnings).
  2) BOOTH gives a lighter 'ran wide' note on a MODERATE off (pace dip, no spin).
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"  # tests: no disk deck state

import sys
sys.path.insert(0, r"D:\R3EOverlay")
import r3e_data as R
from r3e_overlay import Overlay
src = open(r"C:\Users\ADMINI~1\AppData\Local\Temp\claude\D--R3EOverlay\a551edbd-1416-4192-af37-f06169b0707c\scratchpad\smoke.py").read()
exec(src.split('run_session("RACE"')[0])

OFFKW = ("track limits", "white line", "keep it on the track", "on the road",
         "kerbs", "limits", "tidy")
WIDEKW = ("runs wide", "ran wide", "wide goes", "run-off", "escape road",
          "off the track", "off-line", "scruffy", "misses the apex",
          "out onto the run", "wheels off", "untidy", "deep")


def fresh_green_race():
    o = headless_overlay(fake_tts=True)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    s = make_shared(2, ncars=6)
    drive(o, s, 2)
    for i in range(s.num_cars):
        s.all_drivers_data_1[i].car_speed = 50.0
    drive(o, s, 3)
    age_intro(o)
    drive(o, s, 2)
    you = s.all_drivers_data_1[0]
    for lap in range(1, 3):
        for i in range(s.num_cars):
            s.all_drivers_data_1[i].completed_laps = lap
            s.all_drivers_data_1[i].lap_distance_fraction = 0.2
        you.car_speed = 55.0
        drive(o, s, 1)
        o._eng_cd -= 30.0
        drive(o, s, 1)
    o._green_at -= 12.0          # past the grid-sort suppression window
    o._incident_until = 0.0      # no lingering start/incident window (ms-fast test)
    return o, s, you


print("===== ENGINEER: full-speed kerb clip (lap invalid, no cut) stays SILENT =====")
o, s, you = fresh_green_race()
assert s.cut_track_warnings == 0
before = len(o.tts.spoken)
you.current_lap_valid = 0        # lap goes invalid — full-speed paint clip
you.car_speed = 55.0             # NO speed loss: not a real off
o._eng_cd -= 30.0
drive(o, s, 1)
o._eng_cd -= 30.0
drive(o, s, 1)
if o._eng_off_watch is not None:
    o._eng_off_watch[0] -= 5.0   # push the confirm window into the past
o._eng_cd -= 30.0
drive(o, s, 1)
eng_new = [t for p, t in o.tts.spoken[before:] if p == "ENGINEER"]
clip_warn = [t for t in eng_new if any(k in t.lower() for k in OFFKW)]
assert not clip_warn, \
    "engineer scolded a harmless full-speed clip: %r" % clip_warn
print("  engineer stayed quiet on the clean clip: OK")

print("\n===== ENGINEER: lap-invalid off WITH a speed collapse (no cut-warning) =====")
o, s, you = fresh_green_race()
assert s.cut_track_warnings == 0
before = len(o.tts.spoken)
you.current_lap_valid = 0        # lap goes invalid (off into grass) — NO cut bump
you.car_speed = 55.0             # watch opens at this reference speed
o._eng_cd -= 30.0
drive(o, s, 1)
you.car_speed = 20.0             # pace collapses mid-window: a genuine off
o._eng_cd -= 30.0
drive(o, s, 1)
eng_new = [t for p, t in o.tts.spoken[before:] if p == "ENGINEER"]
assert any(any(k in t.lower() for k in OFFKW) for t in eng_new), \
    "engineer did NOT warn on lap-invalid off (no cut): %r" % eng_new
print("  engineer warned on lap-invalid off:")
print("     ", next(t for t in eng_new if any(k in t.lower() for k in OFFKW)))

print("\n===== BOOTH: moderate run-wide (pace dip, no spin) =====")
o, s, you = fresh_green_race()
before = len(o.tts.spoken)
# lap-invalid edge at speed -> opens the off-watch capturing ref ~55
you.current_lap_valid = 0
you.car_speed = 55.0
drive(o, s, 1)
# moderate dip: 38/55 = 69% -> between the 58% collapse and 85% clean-clip lines
you.car_speed = 38.0
drive(o, s, 1)
assert o._off_watch is not None, "off-watch closed early (was it called a big off?)"
o._off_watch[0] -= 5.0           # push the watch deadline into the past
you.car_speed = 50.0             # recovered; min dip (38) already recorded
drive(o, s, 1)
booth_new = [t for p, t in o.tts.spoken[before:] if p in ("PUNDIT", "COMMENTATOR")]
wide = [t for t in booth_new if any(k in t.lower() for k in WIDEKW)]
assert wide, "booth did NOT comment on the moderate run-wide: %r" % booth_new
assert "{" not in wide[0], "placeholder leaked: %r" % wide[0]
print("  booth noted the run-wide:")
print("     ", wide[0])

print("\n===== BOOTH: clean flat-out kerb clip stays SILENT =====")
o, s, you = fresh_green_race()
before = len(o.tts.spoken)
you.current_lap_valid = 0
you.car_speed = 55.0
drive(o, s, 1)
you.car_speed = 54.0             # ~98% -> a clean clip, no real loss
drive(o, s, 1)
if o._off_watch is not None:
    o._off_watch[0] -= 5.0
you.car_speed = 55.0
drive(o, s, 1)
booth_new = [t for p, t in o.tts.spoken[before:] if p in ("PUNDIT", "COMMENTATOR")]
wide = [t for t in booth_new if any(k in t.lower() for k in WIDEKW)]
assert not wide, "booth wrongly narrated a clean kerb clip: %r" % wide
print("  booth stayed quiet on the clean clip: OK")

print("\nALL OFF-TRACK COVERAGE CHECKS PASSED")
