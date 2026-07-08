"""Rival driver radio must be session-aware: in practice/quali, foreign-voice
rivals use lap/pace chatter (not race-battle lines), and practice has no 'pole'.
Race-battle rival lines must never fire in non-race sessions."""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"  # tests: no disk deck state

import sys, random
sys.path.insert(0, r"D:\R3EOverlay")
import r3e_data as R
from r3e_overlay import Overlay
from lines import NATIVE_RADIO, NATIVE_RADIO_QUALI, RIVAL_QUALI
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])


def newo():
    o = headless_overlay(fake_tts=True)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    # force EVERY rival to be a French native-voice driver
    o.tts.native_lang = lambda persona, seed: "fr"
    return o


def rival_laps(o, s, fast=True):
    # make rival slot 1 complete improving laps so it emits pole/pb q_events
    you = s.all_drivers_data_1[0]
    rv = s.all_drivers_data_1[1]
    drive(o, s, 2); age_intro(o)
    for lap in range(1, 5):
        for i in range(s.num_cars):
            s.all_drivers_data_1[i].completed_laps = lap
            s.all_drivers_data_1[i].current_lap_valid = 1
        # rival sets an improving (fast) lap
        t = 90.0 - lap * 0.3 if fast else 95.0
        rv.sector_time_previous_self[0] = 30.0
        rv.sector_time_previous_self[1] = 60.0
        rv.sector_time_previous_self[2] = t
        rv.car_speed = 60.0
        drive(o, s, 1)
        o.last_radio_t = 0.0
        drive(o, s, 1)


race_fr = set(t for t, _ in NATIVE_RADIO["fr"])
quali_fr = set(t for t, _ in NATIVE_RADIO_QUALI["fr"])

# ---- QUALI: native rival uses QUALI chatter, not race battle lines ----------
print("===== QUALI NATIVE RIVAL CHATTER =====")
o = newo()
s = make_shared(1, ncars=4)           # qualifying
rival_laps(o, s)
spoken = [t for p, t in o.tts.spoken if p not in ("ENGINEER",)]
native_spoken = [t for t in spoken if t in race_fr or t in quali_fr]
print(f"  native rival lines: {len(native_spoken)}")
for t in native_spoken[:4]:
    print(f"    {t}")
assert native_spoken, "no native rival chatter fired"
race_leak = [t for t in native_spoken if t in race_fr]
assert not race_leak, f"RACE-battle native chatter leaked into quali: {race_leak}"
assert all(t in quali_fr for t in native_spoken), "non-quali native line used"
print("  quali native rival chatter is session-appropriate (no battle lines): OK")

# ---- PRACTICE: no 'pole' shouts -------------------------------------------
print("\n===== PRACTICE: NO 'POLE' =====")
o = newo()
o.tts.native_lang = lambda persona, seed: None   # English so we can read it
s = make_shared(0, ncars=4)           # practice
rival_laps(o, s)
spoken = [t for p, t in o.tts.spoken if p not in ("ENGINEER",)]
pole_lines = set(RIVAL_QUALI["pole"])
pole_shouts = [t for t in spoken if t in pole_lines or "pole" in t.lower()]
print(f"  rival 'pole' shouts in practice: {len(pole_shouts)}")
for t in pole_shouts[:3]:
    print(f"    OOPS: {t}")
assert not pole_shouts, f"rival shouted 'pole' in PRACTICE: {pole_shouts}"
print("  no 'pole' in practice rival radio: OK")

# ---- NON-RACE: no race-battle rival lines (overtaken/taunt/caught) ----------
print("\n===== NON-RACE: NO RACE-BATTLE RIVAL LINES =====")
from lines import PERSONAS
battle_lines = set()
for persona in PERSONAS.values():
    for cat in ("overtaken", "taunt", "caught", "crash"):
        for l in persona.get(cat, []):
            battle_lines.add(l.replace("{pos}", "").replace("{who}", ""))
o = newo()
o.tts.native_lang = lambda persona, seed: None
s = make_shared(1, ncars=4)
rival_laps(o, s)
# crude: ensure none of the spoken lines are race-overtake phrased
leak = [t for p, t in o.tts.spoken if p not in ("ENGINEER", "COMMENTATOR", "PUNDIT")
        and ("overtak" in t.lower() or "past me" in t.lower()
             or "stay behind" in t.lower() or "in my mirrors" in t.lower())]
assert not leak, f"race-battle rival line in quali: {leak}"
print("  no race-overtake rival lines in non-race: OK")

print("\nALL RIVAL-RADIO SESSION CHECKS PASSED")
