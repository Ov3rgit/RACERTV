# -*- coding: utf-8 -*-
"""JOINING A RACE ALREADY RUNNING IS NOT A START.

The booth fires its start call on the `_racing` edge, and until now that call
was always "lights out and away we go" — a pre-rendered shout, fired with an
interrupt so nothing can bury it. That is exactly right when the lights have
just gone out, and wrong in every other way of arriving at a green race:

  * a replay scrubbed into the middle
  * a session spectated from lap four
  * a mid-race join

In all three the booth announced a start that had happened minutes earlier.
Reported as race starts being "not accurate".

IT GOT MORE LIKELY, NOT LESS, WHEN THE GREEN LATCH WAS FIXED. The latch used
to read the PLAYER's car speed, so arriving mid-race it sat silent until a lap
completed (see rollingstarttest section 4). Widening it to the field's speed
means a mid-race join now goes green on the very first tick — and shouts. The
two changes belong together, which is why this file exists.

THE TEST IS `pregrid` AND A COMPLETED LAP, NOT EITHER ALONE. Both cases below
are asserted: a real standing start must still get the lights-out sting, and a
RESTART — where the field has laps but the booth did see the grid — must not
be mistaken for a join.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import sys

sys.path.insert(0, r"D:\R3EOverlay")
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])

from lines import COMMENTARY_LINES                        # noqa: E402

fails = []


def check(ok, what, detail=""):
    print("  [%s] %s%s" % ("OK" if ok else "FAIL", what,
                           ("  " + str(detail)) if detail else ""))
    if not ok:
        fails.append(what)


def _watch(o):
    """Record what the booth ASKS FOR, without replacing the project's fake.

    An earlier version of this file substituted a stub TTS and immediately hit
    `flush()`; the overlay uses more of that object than a test can guess at.
    Wrapping the real fake keeps every method it already has and only notes the
    two calls this file is about — a STING (pre-rendered, instant) versus a
    spoken LINE, which is exactly the distinction under test.
    """
    t = o.tts
    # DISTINCT NAMES: the project's own fake already keeps a
    # `.spoken` list of (text, persona) tuples, and sharing it
    # meant this file read its records back as tuples.
    t.seen_stings, t.seen_lines = [], []
    _sting, _speak = t.sting, t.speak

    def sting(group="alert", persona="PUNDIT", on_play=None):
        t.seen_stings.append(group)
        try:
            _sting(group, persona, on_play=on_play)
        except Exception:
            pass
        return True                   # pretend the clip is cached and ready

    def speak(text, persona, **kw):
        # NOT every caller passes a plain string here (the radio side hands
        # through richer payloads), so coerce rather than assume.
        t.seen_lines.append(text if isinstance(text, str) else str(text))
        try:
            return _speak(text, persona, **kw)
        except Exception:
            return None
    t.sting, t.speak = sting, speak
    return o


def session(laps, ncars=8, speed=60.0):
    o = headless_overlay(fake_tts=True)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    _watch(o)
    s = make_shared(2, ncars=ncars)
    s.session_phase = 5
    s.player.game_simulation_time = 30.0
    s.session_time_remaining = 600.0
    for i, d in enumerate(s.all_drivers_data_1[:ncars]):
        d.car_speed, d.place, d.completed_laps = speed, i + 1, laps
        d.lap_distance_fraction = 0.4
    s.car_speed = speed
    return o, s


print("\n1. THE POOL EXISTS")
check(bool(COMMENTARY_LINES.get("joined")),
      "there is a 'joined' line pool",
      "%d lines" % len(COMMENTARY_LINES.get("joined") or []))
# A JOIN LINE MUST NOT SOUND LIKE A START. The whole point is that it tells
# the viewer he missed the lights; a pool that shouted them would be worse
# than no pool, because it would look fixed while still being wrong.
import re as _re                                          # noqa: E402
_bad = [t for t in (COMMENTARY_LINES.get("joined") or [])
        if _re.search(r"lights|away we go|five red", t, _re.I)]
check(not _bad, "...and not one of them calls the lights", _bad)


print("\n2. JOINING MID-RACE DOES NOT CLAIM A START")
# The field is racing on lap 4 and the booth has never seen a grid: no
# `pregrid` was ever set, because the race was already green on the first tick.
o, s = session(laps=4)
s.game_in_replay = 1
drive(o, s, 3)
check(o._racing, "the race is green (the latch fix)")
check("lightsout" not in o.tts.seen_stings,
      "the lights-out sting did NOT fire on a race joined at lap 4",
      o.tts.seen_stings)
# MATCHED AGAINST THE POOL, NOT AGAINST KEYWORDS.
#
# This used to look for words like "already" or "in progress" in what was
# said. The booth picks one of eight lines at random, and "We come to you
# mid-race at Spa" contains none of them -- so the test failed roughly one run
# in eight on a line that was exactly right. A test that passes by luck of the
# draw is not testing anything. Each template becomes a pattern with its
# {slots} as wildcards, and the spoken line must be one of them.
import re as _re2                                         # noqa: E402
_JOINED = [_re2.compile("^" + _re2.sub(r"\\{\w+\\}", ".+?",
                                        _re2.escape(t)) + "$")
           for t in COMMENTARY_LINES["joined"]]
check(any(any(rx.match(t) for rx in _JOINED) for t in o.tts.seen_lines),
      "...and a join-in-progress line was said instead",
      o.tts.seen_lines[:2])


print("\n3. A REAL START STILL GETS THE LIGHTS")
# The regression that matters most. The grid is stationary, the booth says its
# welcome, the field launches — this must be untouched by the above.
o, s = session(laps=0, speed=0.0)
drive(o, s, 2)                       # on the grid: pregrid is said here
check(bool(o._comm_flags.get("pregrid")), "the booth welcomed us on the grid")
for d in s.all_drivers_data_1[:8]:   # lights out
    d.car_speed = 60.0
s.car_speed = 60.0
drive(o, s, 2)
check(o._racing, "the race goes green")
check("lightsout" in o.tts.seen_stings,
      "the lights-out sting DID fire on a real standing start", o.tts.seen_stings)


print("\n4. A RESTART IS NOT A JOIN")
# The field carries completed laps into a restart, so a laps-only test would
# call it a join and mumble "we join the action already underway" at a grid
# everybody is sitting on. `pregrid` is what tells the two apart.
o, s = session(laps=0, speed=0.0)
drive(o, s, 2)                            # grid seen, pregrid set
for d in s.all_drivers_data_1[:8]:        # ...now they have laps on the board
    d.completed_laps = 3
    d.car_speed = 60.0
s.car_speed = 60.0
drive(o, s, 2)
check("lightsout" in o.tts.seen_stings,
      "a green flag after the grid was seen is still a start, laps or not",
      o.tts.seen_stings)

print("\n" + ("FAILED: %d" % len(fails) if fails else "ALL PASSED"))
sys.exit(1 if fails else 0)
