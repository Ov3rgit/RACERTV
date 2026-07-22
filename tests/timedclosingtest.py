"""TIMED-RACE CLOSING STAGES — the booth must know the race is winding down even
when the game is slow (or fails) to raise its white flag.

Reported: a timed race finished and the booth never said a word about the
closing stages — the phase computation and the 'final lap' announcement both
trusted ONLY s.flags.white after time-up, and R3E doesn't always raise it
promptly. The booth now ALSO estimates from the player's own pace once under
about a lap of time remains, purely for FRAMING (phase + the announcement);
the strict signal (white flag, or the clock having genuinely hit zero) is still
the only thing allowed to lock in _timed_flap, which the finish detector
(_leader_finished) depends on — a wrong early guess there would end the race a
lap too soon, so it must never come from the estimate alone.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import os
import sys

sys.path.insert(0, r"D:\R3EOverlay")
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "smoke.py")).read()
exec(_src.split('run_session("RACE"')[0])


def timed_race(rem, pace=90.0):
    o = headless_overlay(fake_tts=True)
    s = make_shared(2, ncars=8)
    s.number_of_laps = -1                 # TIMED
    s.session_time_duration = 1200.0
    s.session_time_remaining = rem
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    for i in range(8):
        d = s.all_drivers_data_1[i]
        d.car_speed = 55.0
        d.place = i + 1
        d.completed_laps = 8
    for _ in range(8):
        drive(o, s, 1)
    o._green_at = time.time() - 60.0
    you = s.all_drivers_data_1[0]
    o.recent_laps[you.driver_info.slot_id] = [pace, pace, pace]  # a real pace read
    return o, s


print("===== 1. clock genuinely expired, but the game's white flag never fired =====")
o, s = timed_race(rem=0.0)
s.flags.white = 0                         # the game did NOT raise it
o._comm_cd = 0.0
drive(o, s, 3)
assert o._comm_flags.get("final_lap"), (
    "the booth never announced the closing stages once the clock ran out, "
    "even though the game's white flag never fired")
print("  clock at zero without the game's flag -> closing announced anyway: OK")
assert o._timed_flap is not None, (
    "clock-expiry is a TRUE signal (RaceRoom always finishes the current lap "
    "once time is up) and should lock the final lap for finish detection")
print("  ...and the final lap IS locked in (clock-expiry is a reliable signal): OK")


print("\n===== 2. pace-based early warning frames it as closing WITHOUT locking "
      "the final lap early =====")
o, s = timed_race(rem=80.0, pace=90.0)    # rem <= pace*1.15 -> near_by_pace fires
s.flags.white = 0
o._comm_cd = 0.0
drive(o, s, 3)
assert o._comm_flags.get("final_lap"), (
    "no early closing-stage framing from the pace estimate")
assert o._timed_flap is None, (
    "the pace ESTIMATE locked the final lap early -- a wrong guess here would "
    "end the race narrative (and _leader_finished) a lap too soon")
print("  early pace-based framing fires WITHOUT prematurely locking the final lap: OK")


print("\n===== 3. a comfortable clock stays quiet (no false closing-stage call) =====")
o, s = timed_race(rem=600.0, pace=90.0)
s.flags.white = 0
o._comm_cd = 0.0
drive(o, s, 3)
assert not o._comm_flags.get("final_lap"), (
    "the closing-stage announcement fired far too early on a comfortable clock")
assert o._timed_flap is None
print("  plenty of time left -> no false closing-stage call: OK")

print("\nTIMED-RACE CLOSING-STAGE CHECKS PASSED")
