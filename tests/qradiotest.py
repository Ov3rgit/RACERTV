"""Rival driver radio must be session-aware, and it is ON SCREEN ONLY.

In practice and qualifying rival cards carry lap/pace chatter rather than
race-battle lines, and practice has no 'pole'.

REWRITTEN WHEN RIVAL RADIO WENT SILENT. Asked for: "completely disregard the
driver and rival audios ... to free up audio space and commentary space for
the race engineer and commentators". This file used to assert that rivals
were SPOKEN in a native language; that is exactly what was removed. Every
check now reads the CARDS, because a check on spoken rival lines would pass
vacuously forever now that nothing is spoken.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"  # tests: no disk deck state

import sys, random
sys.path.insert(0, r"D:\R3EOverlay")
import r3e_data as R
from r3e_overlay import Overlay
from lines import RIVAL_QUALI
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])


def newo():
    o = headless_overlay(fake_tts=True)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    # Every rival is a native-voice driver, the case that used to be voiced
    # in its own language. It must now be a silent card like everyone else.
    o.tts.native_lang = lambda persona, seed: "fr"
    o.cards = []
    _real = o._air_bubble
    o._air_bubble = lambda m, _o=o: (_o.cards.append(m), _real(m))[1]
    return o


def rival_cards(o):
    return [m["text"] for m in o.cards
            if not m.get("engineer") and not m.get("driver")]


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


# ---- QUALI: rival radio is a card, never a voice --------------------------
print("===== QUALI RIVAL RADIO =====")
o = newo()
s = make_shared(1, ncars=4)           # qualifying
rival_laps(o, s)
voiced = [p for p, t in o.tts.spoken if p not in ("ENGINEER", "COMMENTATOR", "PUNDIT")]
assert not voiced, "a rival was VOICED in qualifying: %s" % sorted(set(voiced))
print("  no rival voice in qualifying, native-language drivers included: OK")
_c = rival_cards(o)
print("  rival cards: %d" % len(_c))
assert _c, "no rival radio card appeared in qualifying at all"
print("  rival radio still appears, as cards: OK")

# ---- PRACTICE: no 'pole' shouts -------------------------------------------
print("\n===== PRACTICE: NO 'POLE' =====")
o = newo()
o.tts.native_lang = lambda persona, seed: None   # English so we can read it
s = make_shared(0, ncars=4)           # practice
rival_laps(o, s)
spoken = rival_cards(o)          # the CARDS -- nothing is spoken any more
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
leak = [t for t in rival_cards(o)
        if ("overtak" in t.lower() or "past me" in t.lower()
            or "stay behind" in t.lower() or "in my mirrors" in t.lower())]
assert not leak, f"race-battle rival line in quali: {leak}"
print("  no race-overtake rival lines in non-race: OK")

print("\nALL RIVAL-RADIO SESSION CHECKS PASSED")
