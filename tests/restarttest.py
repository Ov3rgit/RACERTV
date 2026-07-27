"""RESTARTING A SESSION MUST START THE OVERLAY FRESH.

Reported: restart a session and the overlay carries on with the previous one's
data — old best laps, old grid positions, an objective from a race that no
longer exists.

The session key is (track, layout, session_type, session_iteration, gen).
Restarting the SAME session at the same track changes none of the first four —
RaceRoom does not reliably advance session_iteration — so everything hung on
`gen`, which only bumps when the leader's lap count falls by TWO OR MORE.
Restart during the opening laps and the drop is 0 or 1, so it never fired.

Two more signals, both one-directional and therefore unambiguous: a session
clock only counts DOWN while you are in a session, and your own lap count only
goes UP. Either moving the wrong way means the session was replaced.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import sys

sys.path.insert(0, r"D:\R3EOverlay")
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])


def session(ncars=6, laps_done=1, rem=600.0):
    o = headless_overlay(fake_tts=True)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    s = make_shared(2, ncars=ncars)
    s.session_time_remaining = rem
    for i, d in enumerate(s.all_drivers_data_1[:ncars]):
        d.car_speed, d.place, d.completed_laps = 60.0, i + 1, laps_done
    return o, s


def key_of(o):
    return getattr(o, "_sess_key", None)


def dirty(o, s):
    """Leave obvious state behind so a missed reset is visible."""
    o.best_lap[s.all_drivers_data_1[0].driver_info.slot_id] = 91.234
    o.grid_place[s.all_drivers_data_1[0].driver_info.slot_id] = 4
    o.fastest = {"time": 90.0, "slot": 0, "car": 1, "name": "OLD", "at": 1.0}


# ---- 1. an EARLY restart is detected (the reported case) ----------------
# One lap in, restart. The leader's laps go 1 -> 0, a drop of one, which the
# old two-lap rule ignored completely.
o, s = session(laps_done=1, rem=600.0)
drive(o, s, 2)
k1 = key_of(o)
dirty(o, s)
assert o.best_lap, "test setup failed to leave state behind"

s.session_time_remaining = 900.0            # clock back to full = restart
for d in s.all_drivers_data_1[:6]:
    d.completed_laps = 0
drive(o, s, 2)
k2 = key_of(o)
assert k2 != k1, (
    "restarting one lap in did not start a new session — the leader's lap "
    "count only fell by one, which the old rule ignored")
assert not o.best_lap, "best laps carried over from the previous session"
assert o.fastest["time"] is None, "the fastest lap carried over"
# grid_place is legitimately re-seeded for the new session, so the check is
# that the STALE value is gone, not that the map is empty
_sl0 = s.all_drivers_data_1[0].driver_info.slot_id
assert o.grid_place.get(_sl0) != 4, (
    "the previous session's grid position survived the restart")
print("  early restart (1 lap in) resets the session: OK")

# ---- 2. the CLOCK jumping up alone is enough ----------------------------
o, s = session(laps_done=0, rem=300.0)
drive(o, s, 2)
k1 = key_of(o)
dirty(o, s)
s.session_time_remaining = 300.0 + 600.0    # clock jumped up; laps unchanged
drive(o, s, 2)
assert key_of(o) != k1, (
    "the session clock jumped UP by ten minutes and the overlay carried on — "
    "a clock only counts down inside a session")
assert not o.best_lap, "state survived a clock reset"
print("  a session clock jumping up is treated as a restart: OK")

# ---- 3. YOUR lap count falling alone is enough --------------------------
o, s = session(laps_done=3, rem=600.0)
drive(o, s, 2)
k1 = key_of(o)
dirty(o, s)
s.all_drivers_data_1[0].completed_laps = 0   # you are back on lap 1
drive(o, s, 2)
assert key_of(o) != k1, (
    "your own completed-lap count fell and the overlay kept the old session")
print("  your lap count falling is treated as a restart: OK")

# ---- 4. a NORMAL session must NOT keep resetting itself ----------------
# The clock ticking down and laps counting up is the ordinary case; if either
# signal is too eager the overlay would wipe itself mid-race.
o, s = session(laps_done=0, rem=600.0)
drive(o, s, 2)
k1 = key_of(o)
for lap in range(1, 6):
    s.session_time_remaining -= 90.0
    for d in s.all_drivers_data_1[:6]:
        d.completed_laps = lap
    drive(o, s, 3)
    assert key_of(o) == k1, (
        "the session reset itself mid-race on lap %d — clock %.0f, laps %d"
        % (lap, s.session_time_remaining, lap))
print("  a normal green-flag race never resets itself: OK (5 laps)")

# a tiny clock wobble (telemetry jitter) must not trip it either
o, s = session(laps_done=2, rem=500.0)
drive(o, s, 2)
k1 = key_of(o)
for wob in (500.5, 501.0, 500.2, 499.0):
    s.session_time_remaining = wob
    drive(o, s, 2)
assert key_of(o) == k1, (
    "a sub-second clock wobble was mistaken for a restart — real restarts "
    "put minutes back on the clock, so the threshold must absorb jitter")
print("  small clock jitter is not mistaken for a restart: OK")

print("\nSESSION-RESTART CHECKS PASSED")
