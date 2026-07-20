"""BOOTH FLOOD: don't hand lines to a queue that is already full.

From a real debug log: 200+ consecutive `speak DROP-busy urgent=True` with the
queue pegged at its cap for minutes on end. Urgent lines (prio<=2) skip
COMMENTARY_CD, and the tick loop runs at 20Hz, so the booth attempted a call
every 50ms and the cap discarded nearly all of it.

Returning early when the queue is full loses nothing (speak would have dropped
it anyway) and stops the churn.

NOT covered here, because it is NOT fixed: under saturation, WHICH line airs
is still arbitrary. A first attempt at fixing that added a minimum spacing
between urgent calls, which silently ate real overtake and crosstalk lines --
a booth line exists only at the moment it happens, so blocking it destroys it.
A real fix has to DEFER the best candidate and retry it, never discard.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, r"D:\R3EOverlay")
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "smoke.py")).read()
exec(_src.split('run_session("RACE"')[0])

NCARS = 8


def build():
    o = headless_overlay(fake_tts=True)
    s = make_shared(2, ncars=NCARS)
    s.number_of_laps = 20
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    for i, d in enumerate(s.all_drivers_data_1[:NCARS]):
        d.car_speed = 60.0
        d.place = i + 1
        d.completed_laps = 3
    return o, s


# ---- 1. a busy queue must not be hammered ---------------------------------
# Simulate the real condition: the audio queue is FULL and stays full, while
# the booth keeps finding urgent things to say. Count how many times it tries.
o, s = build()
for _ in range(8):
    drive(o, s, 1)
o._green_at = time.time() - 60.0

# Feed the booth one urgent candidate per tick with the queue FULL -- which
# is precisely the logged condition -- and count how many it hands to speak().
# (Driving real place swaps does NOT work here: places must hold
# PLACE_CONFIRM_TICKS to confirm, so swapping every tick generates no events
# at all and the test would pass vacuously against any code.)
attempts = []
_real_speak = o.tts.speak


def counting(text, persona="ENGINEER", **kw):
    if persona in ("COMMENTATOR", "PUNDIT"):
        attempts.append(text)
    return _real_speak(text, persona, **kw)


o.tts.speak = counting
o.tts._pend = 4                      # queue permanently at the cap
for i in range(200):                 # 200 ticks = 10s of racing at 20Hz
    c = SimpleNamespace(
        cands=[(2, f"URGENT SCRAP LINE {i}", "battle", 2, "COMMENTATOR")],
        cur={}, is_race=True, now=time.time(), trk="Spa")
    o._emit_commentary(c)
    time.sleep(0.001)

# Old behaviour: one attempt per tick, all discarded by the cap (200).
# Fixed: the full queue is not handed anything at all.
assert len(attempts) <= 25, (
    f"the booth handed {len(attempts)} urgent calls to a FULL queue over 200 "
    "ticks -- it is hammering the pipeline exactly as the debug log showed")
print(f"  urgent attempts into a full queue: {len(attempts)}/200 ticks: OK")

print("\nBOOTH FLOOD CHECKS PASSED")
