# -*- coding: utf-8 -*-
"""THREE VOICES ON THE AUDIO CHANNEL. EVERYONE ELSE IS A CARD.

Asked for, and then reported still broken: *"i said i wanted to completely
disregard the driver and rival audios, but yet when the rival cards pop up
then i hear audio, the reason i wanted to take out the audio was to free up
audio space and commentary space for the race engineer and commentators"*.

Every radio persona used to reach tts.speak, so a rival's line waited in the
same queue as Miles, Brett and the engineer and made each of them wait. A
rival card also stamped the shared radio cooldown, holding the engineer back
behind a message nobody could hear. FACTORtv's design -- the one the user
singled out -- is three voices and everything else on screen.

Driven through a whole simulated race, recording every voice the overlay
asks the audio engine for. Not a unit check of one branch: the point is that
NOTHING, by any path, voices a rival.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import sys

sys.path.insert(0, r"D:\R3EOverlay")
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])

fails = []
VOICED = {"COMMENTATOR", "PUNDIT", "ENGINEER"}


def check(ok, what, detail=""):
    print("  [%s] %s%s" % ("OK" if ok else "FAIL", what,
                           ("  " + str(detail)) if detail else ""))
    if not ok:
        fails.append(what)


o = headless_overlay(fake_tts=True)
o._show_caption = lambda *a, **k: None
o.radio_msgs = []
voices = []
_real = o.tts.speak
o.tts.speak = lambda t, p, *a, **k: (voices.append(p), _real(t, p, *a, **k))[1]
cards = []
_real_air = o._air_bubble
o._air_bubble = lambda m: (cards.append(m), _real_air(m))[1]

N = 10
s = make_shared(2, ncars=N)
s.session_phase = 5
s.number_of_laps = 12
for i, d in enumerate(s.all_drivers_data_1[:N]):
    d.car_speed, d.place, d.completed_laps = 60.0, i + 1, 3
    d.lap_distance_fraction = 0.5 - i * 0.01
    d.time_delta_front = 0.4
s.car_speed = 60.0
drive(o, s, 5)
age_intro(o)

# A busy stretch: passes all over the field, so rivals have every reason to
# key the mic, with the cooldowns aged so nothing is held back by spacing.
import random as _r                                       # noqa: E402
_r.seed(4)
cards_before = 0
for tick in range(400):
    if tick % 12 == 0:
        a = _r.randint(1, N - 1)
        da = next(d for d in s.all_drivers_data_1[:N] if d.place == a)
        db = next(d for d in s.all_drivers_data_1[:N] if d.place == a + 1)
        da.place, db.place = a + 1, a
        da.lap_distance_fraction, db.lap_distance_fraction = (
            db.lap_distance_fraction, da.lap_distance_fraction)
    o.driver_radio_cd = {}
    # ...and the rival cards' own global clock (RADIO_RIVAL_CD, which
    # rivalpacetest owns). This file is about WHETHER a rival gets a card
    # rather than a voice; spacing is somebody else's check, and leaving
    # it in made this one depend on how fast the box ran the loop.
    o._rival_card_t = 0.0
    drive(o, s, 1)
    age_place_hold(o)

rival_cards = [m for m in o.radio_msgs if not m.get("engineer")
               and not m.get("driver")]
_ever = getattr(o, "_radio_recent", [])
print("\n1. NOBODY BUT THE BOOTH AND THE ENGINEER IS VOICED")
check(bool(voices), "the race produced audio at all", len(voices))
stray = sorted(set(voices) - VOICED)
check(not stray, "no rival or driver persona reached the audio engine", stray)

print("\n2. RIVAL RADIO STILL APPEARS -- AS CARDS")
# Recorded at the card itself. A first version read the radio's recent-lines
# log, which in this harness is shared with the booth and was full of Miles.
_rivals = [m for m in cards if not m.get('engineer') and not m.get('driver')]
check(bool(_rivals), 'rivals still key the mic -- as cards on screen',
      '%d rival cards' % len(_rivals))

print("\n3. A RIVAL CARD DOES NOT HOLD THE ENGINEER BACK")
src_r = open(r"D:\R3EOverlay\overlay_radio.py", encoding="utf-8").read()
check("if eng_emitted:\n            self.last_radio_t = now" in src_r,
      "only the engineer's own lines start the shared radio cooldown")

print("\n" + ("FAILED: %d" % len(fails) if fails else "ALL PASSED"))
sys.exit(1 if fails else 0)
