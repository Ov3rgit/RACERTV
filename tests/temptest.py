"""Engineer must read live TYRE and BRAKE temperatures: overheating tyres, cold
tyres, and hot brakes — each against the car's own optimal/cold/hot refs. And it
must stay SILENT when the temp model is off (all zero/N-A, the harness default)."""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"  # tests: no disk deck state

import sys
sys.path.insert(0, r"D:\R3EOverlay")
import r3e_data as R
from r3e_overlay import Overlay
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])


def green_running(o, s):
    for i in range(s.num_cars):
        s.all_drivers_data_1[i].car_speed = 55.0
        s.all_drivers_data_1[i].completed_laps = 3
    drive(o, s, 3)
    age_intro(o)
    drive(o, s, 1)


def set_tyre(s, idxs, center, opt=90.0, cold=70.0, hot=100.0):
    for i in idxs:
        t = s.tire_temp[i]
        for k in range(3):
            t.current_temp[k] = center
        t.optimal_temp = opt
        t.cold_temp = cold
        t.hot_temp = hot


def set_brake(s, idxs, cur, opt=350.0, cold=200.0, hot=500.0):
    for i in idxs:
        b = s.brake_temp[i]
        b.current_temp = cur
        b.optimal_temp = opt
        b.cold_temp = cold
        b.hot_temp = hot


def eng_since(o, before):
    return [t for p, t in o.tts.spoken[before:] if p == "ENGINEER"]


def fresh():
    o = headless_overlay(fake_tts=True)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    return o


print("===== TYRE & BRAKE TEMPERATURE =====")

# A) OVERHEATING fronts -> a "cooking the fronts" call
o = fresh()
s = make_shared(2)
set_tyre(s, (0, 1), 112.0)          # fronts well over the 100 hot ref
set_tyre(s, (2, 3), 90.0)           # rears at optimal
green_running(o, s)
before = len(o.tts.spoken)
for _ in range(6):
    o._eng_cd -= 40.0
    o._eng_temp_cd -= 100.0
    drive(o, s, 1)
hot = [t for t in eng_since(o, before) if "front" in t.lower()
       and ("cook" in t.lower() or "over temp" in t.lower()
            or "overheat" in t.lower() or "too hot" in t.lower()
            or "temps climbing" in t.lower() or "dirty air" in t.lower()
            or "turbulence" in t.lower())]
assert hot, f"no overheating-front call: {eng_since(o, before)}"
print(f"  [hot]  overheating fronts called: OK -> {hot[0]}")

# B) COLD tyres -> a warm-up call
o = fresh()
s = make_shared(2)
set_tyre(s, (0, 1, 2, 3), 60.0)     # all four below the 70 cold ref
green_running(o, s)
before = len(o.tts.spoken)
for _ in range(6):
    o._eng_cd -= 40.0
    o._eng_temp_cd -= 100.0
    drive(o, s, 1)
cold = [t for t in eng_since(o, before) if "cold" in t.lower()
        or "up to temp" in t.lower() or "working temp" in t.lower()
        or "not much heat" in t.lower()]
assert cold, f"no cold-tyre warm-up call: {eng_since(o, before)}"
print(f"  [cold] cold-tyre warm-up called: OK -> {cold[0]}")

# C) HOT BRAKES -> a fade-risk call
o = fresh()
s = make_shared(2)
set_tyre(s, (0, 1, 2, 3), 90.0)     # tyres fine so brakes win the tick
set_brake(s, (0, 1), 560.0)         # fronts over the 500 hot ref
set_brake(s, (2, 3), 350.0)         # rears at optimal
green_running(o, s)
before = len(o.tts.spoken)
for _ in range(8):
    o._eng_cd -= 40.0
    o._eng_brake_cd -= 100.0
    drive(o, s, 1)
brk = [t for t in eng_since(o, before) if "brake" in t.lower()]
assert brk, f"no hot-brake call: {eng_since(o, before)}"
print(f"  [brake] hot-brake call: OK -> {brk[0]}")

# D) temp model OFF (all zero = N/A) -> NO temperature lines at all
o = fresh()
s = make_shared(2)                  # tyre_temp / brake_temp left at 0
green_running(o, s)
before = len(o.tts.spoken)
for _ in range(8):
    o._eng_cd -= 40.0
    o._eng_temp_cd -= 100.0
    o._eng_brake_cd -= 100.0
    drive(o, s, 1)
bad = [t for t in eng_since(o, before)
       if ("cook" in t.lower() or "overheat" in t.lower()
           or "cold, mate" in t.lower() or "working temp" in t.lower()
           or "brakes are" in t.lower() or "brakes getting" in t.lower())]
assert not bad, f"temp warnings fired with model OFF: {bad}"
print("  [n/a]  temp model off -> silent: OK")


def eng_temp_lines(o, before):
    return [t for t in eng_since(o, before) if "engine" in t.lower()
            or "water temp" in t.lower() or "bonnet" in t.lower()
            or "cooling" in t.lower() or "cook it" in t.lower()
            or "temperatures in check" in t.lower()]


# E) ENGINE overheating: a large SUSTAINED rise above the warmed-up baseline
o = fresh()
s = make_shared(2)
s.engine_temp = 95.0
s.engine_oil_temp = 95.0
green_running(o, s)                 # completed_laps=3 (>=2): baseline ~95 captured
drive(o, s, 1)
s.engine_temp = 122.0               # +27C sustained rise -> cooling problem
s.engine_oil_temp = 122.0
before = len(o.tts.spoken)
for _ in range(10):                 # arm the sustain timer, then age it past 4s
    o._eng_cd -= 40.0
    drive(o, s, 1)
    if o._eng_engtemp_hot_since is not None:
        o._eng_engtemp_hot_since -= 10.0
ehot = eng_temp_lines(o, before)
assert ehot, f"no engine-overheat call on a sustained rise: {eng_since(o, before)}"
assert "damage" not in ehot[0].lower() and "knock" not in ehot[0].lower(), \
    f"used the damage variant with no damage present: {ehot[0]}"
print(f"  [engine] sustained overheat called: OK -> {ehot[0]}")

# F) ENGINE overheating WITH damage present -> the damage-aware variant
o = fresh()
s = make_shared(2)
s.engine_temp = 95.0
s.engine_oil_temp = 95.0
green_running(o, s)
drive(o, s, 1)
o._eng_flags["dmg_aero"] = True     # aero damage already reported earlier
s.engine_temp = 122.0
s.engine_oil_temp = 122.0
before = len(o.tts.spoken)
for _ in range(10):
    o._eng_cd -= 40.0
    drive(o, s, 1)
    if o._eng_engtemp_hot_since is not None:
        o._eng_engtemp_hot_since -= 10.0
edmg = eng_temp_lines(o, before)
assert edmg, f"no engine-overheat call with damage: {eng_since(o, before)}"
assert ("damage" in edmg[0].lower() or "cooling" in edmg[0].lower()
        or "knock" in edmg[0].lower()), \
    f"didn't use the damage-aware variant: {edmg[0]}"
print(f"  [engine] damage-aware overheat called: OK -> {edmg[0]}")

# G) ENGINE temp model OFF (0) -> silent
o = fresh()
s = make_shared(2)                  # engine_temp left at 0
green_running(o, s)
before = len(o.tts.spoken)
for _ in range(8):
    o._eng_cd -= 40.0
    drive(o, s, 1)
assert not eng_temp_lines(o, before), "engine warning fired with temp model off"
print("  [engine] temp model off -> silent: OK")

print("\nALL TEMPERATURE CHECKS PASSED")
