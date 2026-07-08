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

print("\nALL DAMAGE CHECKS PASSED")
