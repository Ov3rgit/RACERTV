"""ARBITRATION BUFFER: a blocked booth call is DEFERRED, never discarded.

The problem this fixes: a booth line exists only on the tick the moment
happens. If the audio queue was full right then, it was thrown away -- so
under saturation WHICH call aired was decided by timing rather than
importance. A midfield scrap could take the slot a beat before a lead change,
and the lead change was simply lost. That is why the big moments felt like
they were not being called.

A blocked call is now held and re-entered as a candidate on later ticks.

The dangerous half is expiry, and it gets the most attention here: play-by-play
ROTS. "Takes P3" a few seconds late is wrong, not merely old, and airing a
stale call is worse than saying nothing. A buffer that never forgets would be
a downgrade on the bug it replaces.
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
    for _ in range(8):
        drive(o, s, 1)
    o._green_at = time.time() - 60.0
    o._comm_hold = None
    return o, s


def ctx(o, cands, now=None):
    return SimpleNamespace(cands=list(cands), cur={}, is_race=True,
                           now=now if now is not None else time.time(),
                           trk="Spa")


def said(o, lo):
    return [t for _p, t in o.tts.spoken[lo:]]


# ---- 1. a call blocked by a full queue AIRS once a slot frees --------------
o, s = build()
o.tts._pend = 4                              # queue full
before = len(o.tts.spoken)
o._emit_commentary(ctx(o, [(1, "LEAD CHANGE LINE", "leadchange", 2,
                            "COMMENTATOR")]))
assert not said(o, before), "it aired into a full queue"
assert o._comm_hold is not None, "the blocked call was DISCARDED, not held"
o.tts._pend = 0                              # a slot frees
o._emit_commentary(ctx(o, []))               # nothing new this tick
assert any("LEAD CHANGE" in t for t in said(o, before)), (
    "the held call never came back once the queue had room -- it was lost, "
    "which is the whole bug")
assert o._comm_hold is None, "the hold was not released after airing"
print("  a blocked call is held and airs when a slot frees: OK")

# ---- 2. it must not air TWICE ---------------------------------------------
before = len(o.tts.spoken)
o._emit_commentary(ctx(o, []))
assert not any("LEAD CHANGE" in t for t in said(o, before)), (
    "the held call aired a second time")
print("  a held call airs exactly once: OK")

# ---- 3. EXPIRY: a stale call is dropped, not aired late --------------------
# The important one. Past the TTL the call is wrong, not just old.
o, s = build()
o.tts._pend = 4
before = len(o.tts.spoken)
t0 = time.time()
o._emit_commentary(ctx(o, [(1, "STALE PASS LINE", "overtake", 2,
                            "COMMENTATOR")], now=t0))
assert o._comm_hold is not None
o.tts._pend = 0
# ...a long time later, well past COMMENTARY_HOLD_TTL
o._emit_commentary(ctx(o, [], now=t0 + o.COMMENTARY_HOLD_TTL + 1.0))
assert not any("STALE PASS" in t for t in said(o, before)), (
    "a call held past COMMENTARY_HOLD_TTL still aired -- play-by-play rots, "
    "and a late 'takes P3' is wrong rather than merely old")
assert o._comm_hold is None, "the expired hold was not cleared"
print("  a call held past its TTL is dropped, not aired late: OK")

# ---- 4. a MORE important call displaces a held one ------------------------
o, s = build()
o.tts._pend = 4
o._emit_commentary(ctx(o, [(2, "MIDFIELD SCRAP", "battle", 2, "COMMENTATOR")]))
assert o._comm_hold[0] == 2
o._emit_commentary(ctx(o, [(1, "LEAD CHANGE", "leadchange", 2, "COMMENTATOR")]))
assert o._comm_hold[0] == 1 and "LEAD CHANGE" in o._comm_hold[1], (
    f"a prio-1 call did not displace the held prio-2 scrap: {o._comm_hold[:2]}")
print("  a more important call displaces the held one: OK")

# ---- 5. ...and a LESS important one does not ------------------------------
o._emit_commentary(ctx(o, [(3, "FILLER LINE", "analysis", 0, "PUNDIT")]))
assert "LEAD CHANGE" in o._comm_hold[1], (
    f"a prio-3 filler evicted the held lead change: {o._comm_hold[:2]}")
print("  a less important call does not evict it: OK")

# ---- 6. the held call competes on PRIORITY, not on age --------------------
# The scenario from the report: a lead change is waiting, a midfield scrap
# arrives live. The lead change must win.
o, s = build()
o.tts._pend = 4
o._emit_commentary(ctx(o, [(1, "HELD LEAD CHANGE", "leadchange", 2,
                            "COMMENTATOR")]))
o.tts._pend = 0
before = len(o.tts.spoken)
o._emit_commentary(ctx(o, [(2, "LIVE MIDFIELD SCRAP", "battle", 2,
                            "COMMENTATOR")]))
out = said(o, before)
assert any("HELD LEAD CHANGE" in t for t in out), (
    f"the live midfield scrap beat the held lead change: {out}")
print("  a held big moment outranks a live lesser one: OK")

print("\nARBITRATION BUFFER CHECKS PASSED")
