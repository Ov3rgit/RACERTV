"""Engineer must call CAR DAMAGE: light contact (small health drop), severe
(box to repair), a SEPARATE later hit re-reports, and N/A (-1) stays silent."""
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


def dmg_lines(spoken, since=0):
    out = []
    for p, t in spoken[since:]:
        if p != "ENGINEER":
            continue
        low = t.lower()
        # reassurance ("no damage, car's healthy") is NOT a damage report
        if "no damage" in low or "healthy" in low or "good shape" in low:
            continue
        if ("damage" in low or "box" in low or "repair" in low or "hurt" in low
                or "contact" in low or "to the pit" in low or "replac" in low):
            out.append(t)
    return out


print("===== CAR DAMAGE REPORTING =====")

# A) LIGHT damage: aero health drops 6% (the kind the old >12% gate missed)
o = headless_overlay(fake_tts=True)
o._show_caption = lambda *a, **k: None
o.radio_msgs = []
s = make_shared(2)
for f in ("engine", "transmission", "aerodynamics", "suspension"):
    setattr(s.car_damage, f, 1.0)
green_running(o, s)
drive(o, s, 1)                       # baseline captured at full health
s.car_damage.aerodynamics = 0.94     # 6% loss — light contact
before = len(o.tts.spoken)
for _ in range(4):
    o._eng_cd -= 40.0
    drive(o, s, 1)
light = dmg_lines(o.tts.spoken, before)
assert light, "engineer never called a 6% aero-damage hit (old gate missed this)"
print(f"  [light] 6% hit called: OK -> {light[0]}")

# B) SEVERE: suspension collapses to 0.45 -> a BOX/repair call
s.car_damage.suspension = 0.45
before = len(o.tts.spoken)
for _ in range(8):
    o._eng_cd -= 40.0
    drive(o, s, 1)
sev = dmg_lines(o.tts.spoken, before)
assert any("box" in t.lower() or "repair" in t.lower() or "pit" in t.lower()
           for t in sev), f"no box/repair call for severe suspension: {sev}"
print(f"  [severe] box-to-repair call: OK -> {sev[0]}")

# C) RE-ARM: a SEPARATE later contact on the same part (aero) reports again
s.car_damage.aerodynamics = 0.80     # further 14% drop after the first report
before = len(o.tts.spoken)
for _ in range(8):
    o._eng_cd -= 40.0
    o._eng_dmg_cd["aero"] -= 60.0     # let the per-part cooldown elapse
    drive(o, s, 1)
again = dmg_lines(o.tts.spoken, before)
assert again, "a separate later aero hit was NOT re-reported"
print(f"  [re-arm] separate later hit re-reported: OK -> {again[0]}")

# D) N/A: damage model OFF (-1.0) must stay completely silent
o = headless_overlay(fake_tts=True)
o._show_caption = lambda *a, **k: None
o.radio_msgs = []
s = make_shared(2)
for f in ("engine", "transmission", "aerodynamics", "suspension"):
    setattr(s.car_damage, f, -1.0)   # N/A
green_running(o, s)
before = len(o.tts.spoken)
for _ in range(6):
    o._eng_cd -= 40.0
    drive(o, s, 1)
quiet = dmg_lines(o.tts.spoken, before)
assert not quiet, f"engineer invented damage with model OFF (-1): {quiet}"
print("  [n/a] damage model off -> silent: OK")

# E) THE REAL CRASH: damage does NOT arrive on a quiet car in a stable field.
# It arrives with places lost and every gap swinging — and those calls sit
# above damage in the ladder and return first. Cases A-D all passed while a
# real crash went unmentioned, because they change ONE thing at a time.
# Reported from an actual race: "lost my bumper, the engineer said nothing."
o = headless_overlay(fake_tts=True)
o._show_caption = lambda *a, **k: None
o.radio_msgs = []
s = make_shared(2)
for f in ("engine", "transmission", "aerodynamics", "suspension"):
    setattr(s.car_damage, f, 1.0)
you = s.all_drivers_data_1[0]
you.place = 3
green_running(o, s)
drive(o, s, 1)                        # baseline at full health
before = len(o.tts.spoken)
s.car_damage.aerodynamics = 0.45      # big hit: bodywork gone
you.place = 6                         # and it cost three places
for d in s.all_drivers_data_1[:s.num_cars]:
    if d is not you and d.place in (4, 5, 6):
        d.place -= 1
vs = you.driver_info.slot_id
for i in range(12):                   # gaps moving, as they do after a shunt
    o.interval[vs] = 1.2 + 0.35 * i
    o._eng_cd -= 40.0
    drive(o, s, 1)
crash = dmg_lines(o.tts.spoken, before)
assert crash, (
    "THE STARVATION CASE: the player lost bodywork AND three places, and the "
    "engineer never mentioned the damage — the place/gap calls above it in "
    "the ladder ate every tick. He said: "
    + " || ".join(t for p, t in o.tts.spoken[before:] if p == "ENGINEER"))
assert any("box" in t.lower() or "repair" in t.lower() or "pit" in t.lower()
           for t in crash), (
    f"damage was called but with no instruction on what to do: {crash}")
print(f"  [crash] damage called amid place loss + moving gaps: OK -> {crash[0]}")

# F) THE THROTTLE MUST NOT EAT IT. Cases A-E all cheat with `o._eng_cd -= 40`
# every tick, which disables the RADIO_ENG_CD spacing entirely — so none of
# them could see the actual bug: the damage block re-baselines _eng_dmg BEFORE
# the line is emitted, so when the spacing dropped that line (a silent
# `continue` in the emit loop) the damage was marked reported and never fired
# again. A visibly broken car, and an engineer who never mentions it.
# NO _eng_cd relaxation here. That is the entire point of this case.
o = headless_overlay(fake_tts=True)
o._show_caption = lambda *a, **k: None
o.radio_msgs = []
s = make_shared(2)
for f in ("engine", "transmission", "aerodynamics", "suspension"):
    setattr(s.car_damage, f, 1.0)
green_running(o, s)
drive(o, s, 1)
o._eng_cd = time.time()               # he has JUST spoken: spacing is active
before = len(o.tts.spoken)
s.car_damage.aerodynamics = 0.90      # contact, while he is still cooling down
for _ in range(10):
    drive(o, s, 1)                    # no cooldown relaxation
throttled = dmg_lines(o.tts.spoken, before)
assert throttled, (
    "damage landed while the engineer was inside RADIO_ENG_CD and was dropped "
    "by the spacing — and the block had already re-baselined, so it can never "
    "fire again. The car is broken and he never says a word.")
print(f"  [throttle] damage survives the spacing: OK -> {throttled[0]}")

print("\nALL DAMAGE CHECKS PASSED")
