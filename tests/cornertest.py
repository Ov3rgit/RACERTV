"""Auto corner detection: the overlay learns a track's corner POSITIONS from the
player's speed trace, names them 'Turn N' (universal), maps a lap fraction to the
right corner, falls back to the real sector before corners are learned, and the
engineer places an overtake ('great move into Turn 2'). Works in any session."""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"  # tests: no disk deck state

import sys
sys.path.insert(0, r"D:\R3EOverlay")
import r3e_data as R
from r3e_overlay import Overlay
src = open(r"C:\Users\ADMINI~1\AppData\Local\Temp\claude\D--R3EOverlay\a551edbd-1416-4192-af37-f06169b0707c\scratchpad\smoke.py").read()
exec(src.split('run_session("RACE"')[0])

CORNERS = [0.20, 0.50, 0.80]            # three real corners on our fake track


def speed_at(frac):
    # 60 m/s flat out, dropping to ~8 within +-0.03 of each corner centre
    v = 60.0
    for c in CORNERS:
        d = abs(frac - c)
        d = min(d, 1.0 - d)
        if d < 0.03:
            v = min(v, 8.0 + 600.0 * d)
    return v


def run_lap(o, s, steps=120):
    me = s.all_drivers_data_1[0]
    for k in range(steps):
        frac = (k + 0.5) / steps
        me.lap_distance_fraction = frac
        me.car_speed = speed_at(frac)
        me.track_sector = 1 if frac < 0.34 else 2 if frac < 0.67 else 3
        s.car_speed = me.car_speed
        o.update_stats(s)
    # cross the line -> wrap (rebuild happens on the next tick's wrap detection)
    me.lap_distance_fraction = 0.001
    me.car_speed = speed_at(0.0)
    s.car_speed = me.car_speed
    o.update_stats(s)


print("===== AUTO CORNER DETECTION =====")
o = headless_overlay(fake_tts=True)
o._show_caption = lambda *a, **k: None
o.radio_msgs = []
s = make_shared(2, ncars=4, track="Fictional Test Circuit")
for i in range(s.num_cars):
    s.all_drivers_data_1[i].car_speed = 50.0
    s.all_drivers_data_1[i].completed_laps = 1
drive(o, s, 2)
age_intro(o)

# A) before any lap is learned, location falls back to the real sector
s.all_drivers_data_1[0].track_sector = 3
where0 = o._where_on_track(s, 0.8)
assert where0 == "in the final sector", f"early fallback wrong: {where0!r}"
print(f"  [fallback] pre-learning -> sector: OK -> {where0}")

# B) drive two full laps; the detector should learn ~3 corners near our centres
run_lap(o, s)
run_lap(o, s)
fracs = o._corner_fracs
assert len(fracs) == 3, f"expected 3 corners, learned {len(fracs)}: {fracs}"
for cf, want in zip(fracs, CORNERS):
    assert abs(cf - want) < 0.04, f"corner {cf:.3f} not near {want}"
print(f"  [detect] learned 3 corners at {[round(f,2) for f in fracs]}: OK")

# C) a fraction at each corner names the right Turn number
for idx, c in enumerate(CORNERS, start=1):
    w = o._where_on_track(s, c)
    assert w == f"into Turn {idx}", f"frac {c} -> {w!r}, wanted Turn {idx}"
print("  [name] each corner -> correct 'Turn N': OK")

# C2) ROBUSTNESS: a whole slow lap (out-lap / traffic, half speed everywhere)
# must NOT corrupt the profile — max-per-bin ignores it, so the 3 corners stand.
me = s.all_drivers_data_1[0]
for k in range(120):
    frac = (k + 0.5) / 120
    me.lap_distance_fraction = frac
    me.car_speed = speed_at(frac) * 0.5      # crawling round
    s.car_speed = me.car_speed
    o.update_stats(s)
me.lap_distance_fraction = 0.001
o.update_stats(s)
assert len(o._corner_fracs) == 3, \
    f"a slow lap corrupted detection: {len(o._corner_fracs)} corners {o._corner_fracs}"
print("  [robust] a full slow lap didn't corrupt the 3 corners: OK")

# D) a fraction on a straight (no nearby corner) -> sector fallback, not a corner
s.all_drivers_data_1[0].track_sector = 2
w = o._where_on_track(s, 0.35)
assert "Turn" not in w and "sector" in w, f"straight should fall back: {w!r}"
print(f"  [straight] mid-straight -> sector, not a corner: OK -> {w}")

# E) integration: an overtake AT a corner -> engineer places it
o2 = headless_overlay(fake_tts=True)
o2._show_caption = lambda *a, **k: None
o2.radio_msgs = []
s2 = make_shared(2, ncars=6, track="Fictional Test Circuit")
for i in range(s2.num_cars):
    s2.all_drivers_data_1[i].car_speed = 55.0
    s2.all_drivers_data_1[i].completed_laps = 2
for place, sl in enumerate([1, 2, 3, 4, 0, 5], start=1):
    s2.all_drivers_data_1[sl].place = place           # player P5
drive(o2, s2, 3)
age_intro(o2)
# graft learned corners onto o2 and park the player at Turn 2 (frac 0.50)
o2._corner_fracs = [0.20, 0.50, 0.80]
o2._corner_laps_seen = 2
o2._corner_key = (R.u8_to_str(s2.track_name), s2.layout_id)
for d in s2.all_drivers_data_1:
    d.lap_distance_fraction = 0.50
# several passes at the corner; the located variant is intentionally ~70% (so it
# isn't robotic), so collect over a few overtakes and confirm placement appears.
before = len(o2.tts.spoken)
orders = ([1, 2, 3, 0, 4, 5], [1, 2, 3, 4, 0, 5]) * 5   # alternate P4 / P5
for od in orders:
    for place, sl in enumerate(od, start=1):
        s2.all_drivers_data_1[sl].place = place
    o2._eng_place_cd -= 100.0
    for _ in range(8):
        o2._eng_cd -= 40.0
        drive(o2, s2, 1)
eng = [t for p, t in o2.tts.spoken[before:] if p == "ENGINEER"]
located = [t for t in eng if "turn 2" in t.lower()]
assert any("p4" in t.lower() for t in eng), \
    f"engineer didn't acknowledge the overtakes: {eng}"
assert located, f"overtake never placed at the corner over many passes: {eng}"
print(f"  [overtake] pass placed at the corner: OK -> {located[0]}")

print("\nALL CORNER CHECKS PASSED")
