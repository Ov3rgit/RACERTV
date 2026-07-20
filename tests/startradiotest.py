"""The engineer's race-start reaction, and booth-exchange protection.

Two behaviours that regressed in real racing and are easy to break again:

1. The engineer's start call must land AFTER the launch has played out, not on
   the green. Fired at lights-out it can only ever say a generic "good luck" —
   `gained` (delta vs the grid slot) is still 0 that instant — and it collides
   with the booth's lights-out call, which interrupts.

2. A booth exchange (question -> answer -> ack) must stay intact. Team radio is
   priority 0 and booth colour is 1, so an engineer line will otherwise beat a
   pundit reply into the queue and land in the middle of the conversation.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import sys

sys.path.insert(0, r"D:\R3EOverlay")
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])
from lines import ENGINEER_LINES                       # noqa: E402
from poolmatch import from_pool                        # noqa: E402

START_POOLS = (ENGINEER_LINES["start"] + ENGINEER_LINES.get("start_gain", [])
               + ENGINEER_LINES.get("start_loss", []))


GRID = 5                         # the player's starting slot


def race(gain=0):
    """Green-flag race with the player having gained `gain` places off the line.

    The player must START mid-grid: grid_place is latched on first sighting,
    so a driver seeded in P1 can never show a gain at all."""
    o = headless_overlay(fake_tts=True)
    s = make_shared(2, ncars=8)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    you = s.all_drivers_data_1[0]
    for i, d in enumerate(s.all_drivers_data_1[:s.num_cars]):
        d.car_speed = 60.0
        d.completed_laps = 0
        d.place = i + 1
    you.place = GRID             # player lines up P5
    s.all_drivers_data_1[GRID - 1].place = 1
    drive(o, s, 3)               # lights out -> _racing latches, _green_t set
    age_intro(o)
    assert o.grid_place.get(you.driver_info.slot_id) == GRID, \
        f"grid slot not latched as P{GRID}: {o.grid_place}"
    if gain:                     # now move them up the order off the line
        you.place = max(1, GRID - gain)
    return o, s, you


def eng(o, since):
    return [t for p, t in o.tts.spoken[since:] if p == "ENGINEER"]


print("===== START CALL WAITS FOR THE LAUNCH =====")
o, s, you = race()
n = len(o.tts.spoken)
o._eng_cd -= 40
drive(o, s, 3)                              # still within the 9s hold
early = [t for t in eng(o, n) if from_pool(t, START_POOLS)]
assert not early, f"start call fired ON the green (too early): {early}"
print("  silent through the lights-out moment: OK")

o._green_t -= 10.0                          # launch has now played out
o._eng_cd -= 40
n = len(o.tts.spoken)
drive(o, s, 3)
late = [t for t in eng(o, n) if from_pool(t, START_POOLS)]
assert late, "start call NEVER fired after the launch!"
print(f"  fired once the launch settled: {late[0][:64]}")
assert "{" not in late[0], f"unformatted placeholder: {late[0]}"

# and only once
n = len(o.tts.spoken)
o._eng_cd -= 40
drive(o, s, 4)
again = [t for t in eng(o, n) if from_pool(t, START_POOLS)]
assert not again, f"start call repeated: {again}"
print("  fires exactly once: OK")


print("\n===== START CALL REFLECTS THE LAUNCH =====")
o, s, you = race(gain=3)                     # gained places off the line
o._green_t -= 10.0
o._eng_cd -= 40
n = len(o.tts.spoken)
drive(o, s, 3)
got = [t for t in eng(o, n) if from_pool(t, START_POOLS)]
assert got, "no start call for a good launch"
gain_pool = ENGINEER_LINES.get("start_gain")
if gain_pool:
    assert from_pool(got[0], gain_pool), (
        f"a 3-place gain should use start_gain, got: {got[0]}")
    print(f"  good launch -> start_gain: {got[0][:64]}")


print("\n===== BOOTH EXCHANGE STAYS INTACT =====")
# every followup must be queued as an exchange (priority -1); otherwise the
# hold expect_answer() sets blocks the reply itself and the engineer wins
import inspect                                          # noqa: E402
import overlay_booth                                    # noqa: E402
srcb = inspect.getsource(overlay_booth)
i = srcb.index("for ftxt, fper, finten, ffor in _f:")
call = srcb[i:i + 700]
assert "exchange=True" in call, (
    "booth followups are not queued as exchanges — the pundit's reply will be "
    "blocked by its own question's hold and the engineer will cut in")
assert "exchange=ffor" not in call, "followups still use the old conditional exchange flag"
print("  all booth followups queued with exchange=True: OK")

print("\nALL START/EXCHANGE CHECKS PASSED")
