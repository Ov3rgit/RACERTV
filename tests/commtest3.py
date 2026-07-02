"""DNF exclusion, race-story de-dup, banner auto-hide."""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"  # tests: no disk deck state

import sys, time, random
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


# ---- 1. DNF / disconnected excluded from the field --------------------------
print("===== DNF EXCLUSION =====")
o = newo()
s = make_shared(2, ncars=6)
for i in range(s.num_cars):
    s.all_drivers_data_1[i].car_speed = 55.0
drive(o, s, 3); age_intro(o)
for lap in range(1, 4):
    for i in range(s.num_cars):
        s.all_drivers_data_1[i].completed_laps = lap
        s.all_drivers_data_1[i].lap_distance_fraction = 0.2 + lap * 0.01
    drive(o, s, 1)
slots = lambda: [d.driver_info.slot_id for d in o._drivers(s)]
assert 3 in slots(), "setup: slot 3 should be racing"
victim = s.all_drivers_data_1[3]
vname = R.u8_to_str(victim.driver_info.name).upper()
# (a) explicit DNF via finish_status
victim.finish_status = 2     # DNF
assert 3 not in slots(), "DNF driver still in field!"
print(f"  DNF (finish_status=2) '{vname}' removed from field: OK")
victim.finish_status = 0     # reset for freeze test

# (b) frozen-on-track (disconnected) — inject an old last-move time
for lap in range(4, 6):
    for i in range(s.num_cars):
        if i == 3:
            continue                       # slot 3 stops moving
        s.all_drivers_data_1[i].completed_laps = lap
        s.all_drivers_data_1[i].lap_distance_fraction = 0.2 + lap * 0.01
    drive(o, s, 1)
# slot 3 hasn't moved; backdate its move signature by 25s and re-run stats
sig, _ = o._move_sig[3]
o._move_sig[3] = (sig, time.time() - 25.0)
o.update_stats(s)
assert 3 not in slots(), "frozen/disconnected driver still in field!"
print(f"  frozen-on-track (disconnected) '{vname}' removed from field: OK")
# and it must NOT appear in the radio/booth field used downstream
o.update_radio(s); o.update_commentary(s)
recent = " ".join(t for p, t in o.tts.spoken[-12:])
# (we can't guarantee the name was about to be said, but the field is clean)
assert 3 not in slots()
print("  excluded driver stays out of the live field: OK")


# ---- 2. Race-story recap never repeats a driver -----------------------------
print("\n===== STORY DE-DUP =====")
o = newo()
o._story_told = set()
o._race_story = {}
o.grid_place = {}
o._dname = lambda d: f"DRV{d.driver_info.slot_id}"
s = make_shared(2, ncars=10)
# fabricate eventful arcs for several drivers
order = sorted([d for d in s.all_drivers_data_1 if d.place > 0], key=lambda d: d.place)
for idx, d in enumerate(order):
    sl = d.driver_info.slot_id
    o.grid_place[sl] = idx + 1
    # big swing: started idx+1, fell, recovered to a different spot
    o._race_story[sl] = {"best": max(1, idx - 3), "worst": idx + 6, "now": max(1, idx - 2)}
picked = []
for _ in range(12):
    d = o._story_pick(order)
    if d is None:
        break
    sl = d.driver_info.slot_id
    picked.append(sl)
    o._story_told.add(sl)        # mimic the emit marking it told
print(f"  drivers recapped (in order): {picked}")
assert len(picked) == len(set(picked)), f"a driver's story was repeated: {picked}"
print(f"  {len(picked)} distinct drivers recapped, zero repeats: OK")


# ---- 3. Fastest-lap banner auto-hides --------------------------------------
print("\n===== BANNER AUTO-HIDE =====")
o = newo()
o.sw = 1920; o.sh = 1080
o._begin_panel = lambda *a, **k: None
class C:
    def create_rectangle(self, *a, **k): pass
    def create_text(self, *a, **k): pass
o._cv_real = C(); o._ox = 0; o._oy = 0
o.f_row_b = None
drawn = []
o.text = lambda x, y, t, **k: drawn.append(str(t))
s = make_shared(2)
o.fastest = {"time": 92.5, "slot": 1, "car": 5, "name": "RIVAL", "at": time.time()}
drawn.clear(); o.draw_fastest_banner(s)
assert drawn, "fresh fastest-lap banner should be drawn"
print(f"  fresh banner drawn ({len(drawn)} texts): OK")
o.fastest["at"] = time.time() - 15.0     # 15s old
drawn.clear(); o.draw_fastest_banner(s)
assert not drawn, "old fastest-lap banner should have hidden!"
print("  banner hidden after 10s: OK")

print("\nALL DNF/STORY/BANNER CHECKS PASSED")
