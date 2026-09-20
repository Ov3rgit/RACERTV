# -*- coding: utf-8 -*-
"""RIVAL CARDS KEEP THEIR OWN CLOCK, AND LAP ONE IS NO LONGER MUTED.

Two reports, one cause between them:

    "the rival radio cards are firing one way one ontop of another, i think
     its because before we gated the driver cards till lap 2, remove that
     gate as it was done when there was audio and let it send naturally"

When rival radio was VOICED, two things paced it that no longer exist.

1. A rival line stamped `last_radio_t`, the shared radio cooldown. Making
   rivals silent correctly stopped that -- a card nobody can hear must not
   hold the ENGINEER's next line back -- but it also left rival cards with no
   global spacing at all. Only the 30s per-driver cooldown was left, and on a
   full grid twenty drivers on separate 30s clocks still produce a card every
   second and a half. Hence "one on top of another".

2. Saying a line took TIME. A caption takes none.

So the cards get a clock of their own: RADIO_RIVAL_CD, checked and stamped
through `_rival_card_ok` / `_rival_card_stamp`. FACTORtv, where rival radio
has been silent from the start, runs the same rule at 38s.

The lap-one hold goes the other way. It was written about the AUDIO channel
-- driver voices over the top of the start call were noise -- and silent
cards cannot talk over anything. Lap one is the busiest lap of the race, so
the hold was suppressing exactly the material worth showing.

THE PACING CHECKS USE REAL TIME, deliberately: the busy stretch below runs in
well under a second of wall clock, so a 20s cooldown means "at most one card"
and a 0s cooldown means "as many as the events allow". The difference between
those two runs is the whole mechanism, and removing the gate collapses it.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import random as _r
import sys

sys.path.insert(0, r"D:\R3EOverlay")
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])

fails = []


def check(ok, what, detail=""):
    print("  [%s] %s%s" % ("OK" if ok else "FAIL", what,
                           ("  " + str(detail)) if detail else ""))
    if not ok:
        fails.append(what)


def busy_race(rival_cd, laps=3, ticks=400, seed=4):
    """A stretch of racing with passes all over the field, returning the
    rival cards it produced. `driver_radio_cd` is cleared every tick so the
    PER-DRIVER cooldown is out of the way and the only thing left pacing the
    cards is the global rule under test."""
    _r.seed(seed)
    o = headless_overlay(fake_tts=True)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    o.RADIO_RIVAL_CD = rival_cd
    N = 10
    s = make_shared(2, ncars=N)
    s.session_phase = 5
    s.number_of_laps = 12
    for i, d in enumerate(s.all_drivers_data_1[:N]):
        d.car_speed, d.place, d.completed_laps = 60.0, i + 1, laps
        d.lap_distance_fraction = 0.5 - i * 0.01
        d.time_delta_front = 0.4
    s.car_speed = 60.0
    drive(o, s, 5)
    age_intro(o)
    for tick in range(ticks):
        if tick % 12 == 0:
            a = _r.randint(1, N - 1)
            da = next(d for d in s.all_drivers_data_1[:N] if d.place == a)
            db = next(d for d in s.all_drivers_data_1[:N] if d.place == a + 1)
            da.place, db.place = a + 1, a
            da.lap_distance_fraction, db.lap_distance_fraction = (
                db.lap_distance_fraction, da.lap_distance_fraction)
        o.driver_radio_cd = {}
        drive(o, s, 1)
        age_place_hold(o)
    return [m for m in o.radio_msgs
            if not m.get("engineer") and not m.get("driver")]


print("\n1. THE CLOCK ITSELF")
o = headless_overlay(fake_tts=True)
o.RADIO_RIVAL_CD = 20.0
o._rival_card_t = 0.0
check(o._rival_card_ok(100.0), "a cold clock lets a card through")
o._rival_card_stamp(100.0)
check(not o._rival_card_ok(100.0), "the same instant is refused")
check(not o._rival_card_ok(119.9), "19.9s later is still refused")
check(o._rival_card_ok(120.0), "20.0s later is allowed")
o2 = headless_overlay(fake_tts=True)
# `now` is a unix timestamp, so the 0.0 an overlay starts with is forty-odd
# years in the past and can never block the first card.
check(o2._rival_card_ok(__import__("time").time()),
      "an overlay that has never shown a card is not blocked")

print("\n2. THE FLOOD IS GONE")
# The same racing, twice: once with the rule, once without it. Both runs take
# a fraction of a second of wall clock, so 20s of cooldown covers the whole
# stretch and the gate is the only difference between the two numbers.
paced = busy_race(20.0)
unpaced = busy_race(0.0)
print("     cards: paced=%d  unpaced=%d" % (len(paced), len(unpaced)))
check(len(unpaced) >= 4,
      "without the rule the cards pile up", "%d cards" % len(unpaced))
check(len(paced) <= 1,
      "with the rule at most one card airs in the window",
      "%d cards" % len(paced))
check(len(paced) < len(unpaced),
      "THE GATE IS LOAD-BEARING (delete it and this check fails)",
      "%d < %d" % (len(paced), len(unpaced)))

print("\n3. LAP ONE IS NO LONGER MUTED")
# Identical racing on the OPENING lap. The old code forced radio_open False
# for every driver with completed_laps < 1, so this was always zero.
lap_one = busy_race(0.0, laps=0)
check(len(lap_one) >= 1,
      "rival cards air before the first lap is complete",
      "%d cards on lap one" % len(lap_one))

print("\n4. THE ENGINEER IS STILL NOT PACED BY RIVAL CARDS")
# The point of the silent-rival work: his clock and theirs are separate.
o3 = headless_overlay(fake_tts=True)
o3.RADIO_RIVAL_CD = 20.0
o3._rival_card_t = 0.0
o3._rival_card_stamp(1000.0)
check(o3.last_radio_t != 1000.0,
      "showing a rival card does not stamp the engineer's clock")

print("\n%s" % ("ALL OK" if not fails else "FAILED: %s" % fails))
assert not fails
