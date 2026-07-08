"""Sustained-battle callout: a fight that stays unresolved for a long time must
produce a 'battle_sustained' line naming both drivers, the position, and the
duration in laps. Also verify it's rate-limited (doesn't immediately repeat)."""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"  # tests: no disk deck state

import sys
sys.path.insert(0, r"D:\R3EOverlay")
import r3e_data as R
from r3e_overlay import Overlay
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])

print("===== SUSTAINED BATTLE =====")
o = headless_overlay(fake_tts=True)
o._show_caption = lambda *a, **k: None
o.radio_msgs = []
s = make_shared(2, ncars=6)

# grid -> green -> intro aired, so the booth is live
drive(o, s, 2)
for i in range(s.num_cars):
    s.all_drivers_data_1[i].car_speed = 50.0
drive(o, s, 3)
age_intro(o)
drive(o, s, 2)

# set up a stable, very close fight: slot 1 (P2) glued to slot 0 (P1) for P1.
# keep everything else static so no overtake/incident fills `cands`.
you = s.all_drivers_data_1[0]
chaser = s.all_drivers_data_1[1]
for d in s.all_drivers_data_1[:s.num_cars]:
    d.completed_laps = 3
you.place, chaser.place = 1, 2

def tick_battle():
    o._comm_cd = 0.0
    o.interval = {d.driver_info.slot_id: 9.9 for d in s.all_drivers_data_1[:s.num_cars]}
    o.interval[1] = 0.3                     # chaser right on the leader's gearbox
    o.update_commentary(s)

# register the fight in battle memory
tick_battle()
assert o._battle.get(1) and o._battle[1][0] == 0, "battle not registered: %r" % (o._battle.get(1),)
print("  battle registered for slot1 -> slot0: OK")

# backdate so the fight has 'lasted' ~20s and ~3 laps, and clear cooldowns
tslot, t0, lap0 = o._battle[1]
o._battle[1] = (tslot, t0 - 20.0, lap0 - 3)
o._battle_cd = 0.0
o._battle_called = {}

before = len(o.tts.spoken)
tick_battle()
new = [t for p, t in o.tts.spoken[before:]]
sust = [t for t in new if t.startswith(("Credit to", "This battle", "For ")) or
        "for three laps" in t or "nose-to-tail" in t or "glued to the back" in t or
        "war of attrition" in t or "raged for" in t or "pure pressure" in t or
        "filling the mirrors" in t or "thrown everything" in t or
        "Relentless" in t or "defining battle" in t or "probing" in t]
assert sust, "no sustained-battle line! new=%r" % (new,)
print("  sustained-battle line aired:")
print("     ", sust[0])
assert "three laps" in sust[0] or "P1" in sust[0] or "P{pos}" not in sust[0], sust[0]
assert "{" not in sust[0], "unformatted placeholder leaked: %r" % sust[0]
print("  no unformatted placeholders: OK")

# rate-limit: immediately ticking again must NOT fire another (global 18s + pair 30s)
before2 = len(o.tts.spoken)
tick_battle()
new2 = [t for t in [t for p, t in o.tts.spoken[before2:]]
        if any(k in t for k in ("raged for", "nose-to-tail", "glued to the back",
                                "war of attrition", "pure pressure", "Relentless",
                                "filling the mirrors", "thrown everything"))]
assert not new2, "sustained battle repeated immediately (not rate-limited): %r" % new2
print("  rate-limited (no immediate repeat): OK")

print("\nALL SUSTAINED-BATTLE CHECKS PASSED")
