"""START-OF-RACE OVERTAKE ACKS MUST NOT DRIP STALE.

Reported: start P14, overtake four cars, and the engineer calls them one after
another -- "P13 now", "P12 now", "P11 now" -- while you are already up in P10.

Two causes:
  * the acks used bypass=True, which set _ttl=None (never expire), so a "P13"
    queued behind the lights-out booth chatter played 15s late when long false.
  * every single-place step got its own call, a per-place roll-call.

Fixes: a short TTL so a stale ack drops, a longer early-race cooldown, and a
coalesced 'gained_multi' line for a fast multi-car climb.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import os
import sys

sys.path.insert(0, r"D:\R3EOverlay")
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "smoke.py")).read()
exec(_src.split('run_session("RACE"')[0])
from lines import ENGINEER_LINES                        # noqa: E402
from overlay_common import _safe_format                 # noqa: E402


def build(nc=16, my=14, lap=4):
    o = headless_overlay(fake_tts=True)
    s = make_shared(2, ncars=nc)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    for i in range(nc):
        s.all_drivers_data_1[i].car_speed = 60.0
        s.all_drivers_data_1[i].place = i + 1
        s.all_drivers_data_1[i].completed_laps = lap
    you = s.all_drivers_data_1[0]
    you.place = my
    drive(o, s, 3)
    age_intro(o)
    drive(o, s, 1)
    return o, s, you


def eng_events(o, s, you):
    """Call _engineer_events directly and return the raw event tuples."""
    evts = []
    placemap = {d.place: d for d in s.all_drivers_data_1[:s.num_cars]}
    o._engineer_events(s, you, placemap, evts, time.time())
    return evts


# ---- 1. a MULTI-CAR climb is ONE coalesced call, not a per-place drip ------
o, s, you = build(my=14)
you.place = 10                                # jumped four places at once
o.cplace[you.driver_info.slot_id] = 10       # confirmed at P10
o._eng_last_ann_place = 14
o._eng_place_cd = 0.0
evts = eng_events(o, s, you)
eng = [e for e in evts if e[5] == "ENGINEER"]
assert eng, "no engineer ack at all for a four-place climb"
txt = eng[0][3]
assert any(w in txt.lower() for w in
           ("places", "up to", "cars in a flash", "picked off", "positions")), (
    "a four-place climb did not coalesce into one multi line: %r" % txt)
assert "13" not in txt and "12" not in txt, (
    "the multi line named an intermediate position it skipped: %r" % txt)
print("  four-place climb -> one coalesced call: OK -> %s" % txt[:56])

# ---- 2. the ack carries a FINITE TTL (8th tuple element), not no-expiry ----
assert len(eng[0]) == 8 and isinstance(eng[0][7], (int, float)), (
    "the ack has no explicit TTL, so bypass makes it never expire and it can "
    "play stale: %r" % (eng[0],))
assert eng[0][7] <= 10.0, "the ack TTL is too long to prevent a stale call"
print("  ack carries a short finite TTL (%ss): OK" % eng[0][7])

# ---- 3. a SINGLE-place gain still acks normally, also with a TTL -----------
o, s, you = build(my=8)
you.place = 7
o.cplace[you.driver_info.slot_id] = 7
o._eng_last_ann_place = 8
o._eng_place_cd = 0.0
evts = eng_events(o, s, you)
eng = [e for e in evts if e[5] == "ENGINEER"]
assert eng and len(eng[0]) == 8 and eng[0][7] <= 10.0, (
    "a single-place ack lost its TTL: %r" % (eng[0] if eng else None))
print("  single-place ack still short-TTL'd: OK")

# ---- 4. the emit loop actually honours an explicit TTL over bypass --------
import inspect                                            # noqa: E402
src = inspect.getsource(type(o).update_radio)
assert 'ttl_override = _evt[7]' in src, (
    "the emit loop no longer reads a per-event TTL")
assert 'if ttl_override != "default":' in src, (
    "the emit loop no longer prefers an explicit TTL over bypass no-expiry")
print("  emit loop honours an explicit ack TTL over bypass: OK")

# ---- 5. gained_multi pool exists and formats ------------------------------
assert ENGINEER_LINES.get("gained_multi"), "no gained_multi pool"
for ln in ENGINEER_LINES["gained_multi"]:
    _safe_format(ln, {"pos": 10, "frm": 14, "gain": 4})
print("  gained_multi pool formats cleanly (%d lines): OK"
      % len(ENGINEER_LINES["gained_multi"]))

print("\nACK-TTL CHECKS PASSED")
