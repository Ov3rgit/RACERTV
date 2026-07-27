"""THE LAUNCH CALL MUST NOT QUOTE A POSITION IT CANNOT KEEP FRESH.

Reported: "the lap 1 position call from the race engineer can be inaccurate."
The pick side was already careful — confirmed place plus a stability window —
but the NUMBER is frozen at queue time, and the start call is a bypass
one-shot with no deadline (deliberately, after it used to TTL-drop and the
start aired silently). At the busiest queue moment of the whole race that
means it can sound 15-20 seconds after its number was read, by which point
lap one has reshuffled it.

Fix: if the pipeline is busy when the call fires, say a NUMBER-FREE launch
line instead. A claim we can't keep fresh is a claim we don't make; the
periodic position reads pick the number up seconds later, current.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import re
import sys

sys.path.insert(0, r"D:\R3EOverlay")
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])
from lines import ENGINEER_LINES                          # noqa: E402
from overlay_common import _safe_format                   # noqa: E402


def fire_start(pend, my_place=6):
    """Drive the start-call block directly with the queue at `pend`."""
    o = headless_overlay(fake_tts=True)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    s = make_shared(2, ncars=10)
    s.number_of_laps = 11
    you = s.all_drivers_data_1[0]
    others = list(s.all_drivers_data_1[1:10])
    places = [p for p in range(1, 11) if p != my_place]
    for d in s.all_drivers_data_1[:10]:
        d.car_speed, d.completed_laps = 60.0, 0
    you.place = my_place
    for d, p in zip(others, places):
        d.place = p
    drive(o, s, 3)
    age_intro(o)
    o._racing = True
    o._green_t = time.time() - 60.0          # long past every start window
    o._eng_flags.pop("start", None)
    o._eng_start_fp = my_place
    o._eng_start_since_g = 0.0
    o.cplace[you.driver_info.slot_id] = my_place
    o.grid_place[you.driver_info.slot_id] = my_place
    o.tts._pend = pend
    evts = []
    o._engineer_events(s, you, {d.place: d for d in s.all_drivers_data_1[:10]},
                       evts, time.time())
    o.tts._pend = 0
    return [e[3] for e in evts]


# ---- 1. QUIET queue: the numbered call, as ever -------------------------
lines = fire_start(pend=0)
assert lines, "no start call fired at all on a quiet queue"
assert any(re.search(r"P\d+", t) for t in lines), (
    "a quiet queue should still get the numbered launch call: %r" % (lines,))
print("  quiet queue -> numbered launch call: OK -> %s" % lines[0][:56])

# ---- 2. BUSY queue: number-free, so nothing can go stale ----------------
lines = fire_start(pend=3)
assert lines, (
    "a busy queue silenced the start call entirely — the whole point of "
    "bypass was that the launch is always acknowledged")
assert not any(re.search(r"P\d+|\b\d+ places?\b", t) for t in lines), (
    "the start call quotes a position into a busy queue, where it can air "
    "15-20s stale: %r" % (lines,))
print("  busy queue -> number-free launch call: OK -> %s" % lines[0][:56])

# ---- 3. the pool exists and formats -------------------------------------
assert ENGINEER_LINES.get("start_busy"), "no start_busy pool"
for ln in ENGINEER_LINES["start_busy"]:
    _safe_format(ln, {})
    assert not re.search(r"\{pos\}|\{gain\}", ln), (
        "a start_busy line asks for a position placeholder — the entire point "
        "is that it must not claim one: %r" % ln)
print("  start_busy pool is number-free and formats (%d lines): OK"
      % len(ENGINEER_LINES["start_busy"]))

print("\nSTART-CALL CHECKS PASSED")
