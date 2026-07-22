"""RACE START — the engineer must not report a position that is still settling.

Reported: after a first-corner incident, the driver had already gained to P4,
but the engineer's start call still thought they were P10 well after the gain
had happened. Root cause: the call fired off a FIXED timer alone (9s past
green) using the LIVE place — so if the pack was still sorting itself out at
that exact instant, it reported whatever place happened to be showing that
tick. The call now ALSO requires the CONFIRMED place to have stopped changing
for ENG_START_STABLE_S, landing it a couple of corners in rather than at the
apex of turn one, and it reports the settled (confirmed) place, not the live one.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import sys

sys.path.insert(0, r"D:\R3EOverlay")
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])
from lines import ENGINEER_LINES                       # noqa: E402
from poolmatch import from_pool                        # noqa: E402
from overlay_radio import ENG_START_MIN_S, ENG_START_STABLE_S  # noqa: E402

START_POOLS = (ENGINEER_LINES["start"] + ENGINEER_LINES.get("start_gain", [])
               + ENGINEER_LINES.get("start_loss", []))

GRID = 10


def race():
    o = headless_overlay(fake_tts=True)
    s = make_shared(2, ncars=GRID)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    you = s.all_drivers_data_1[0]
    for i, d in enumerate(s.all_drivers_data_1[:s.num_cars]):
        d.car_speed = 60.0
        d.completed_laps = 0
        d.place = i + 1
    you.place = GRID              # lines up at the back
    s.all_drivers_data_1[GRID - 1].place = 1
    drive(o, s, 3)                # lights out -> _racing latches, _green_t set
    age_intro(o)
    assert o.grid_place.get(you.driver_info.slot_id) == GRID
    return o, s, you


def started(o, since):
    return [t for p, t in o.tts.spoken[since:]
            if p == "ENGINEER" and from_pool(t, START_POOLS)]


print("===== 1. silent while the CONFIRMED place is still settling, even well "
      "past the old fixed floor =====")
o, s, you = race()
vs = you.driver_info.slot_id
# Fast-forward (via the suite's usual RELATIVE _green_t -= convention) past the
# old fixed floor, landing as a first-corner incident is still resolving: the
# confirmed place changes several more times, a beat apart. Each change must
# reset the stability clock — under the OLD code (a fixed timer on the LIVE
# place) this would already have fired on the very first of these ticks.
o._green_t -= (ENG_START_MIN_S + 1.0)
for p in (6, 5, 4):
    o.cplace[vs] = p               # confirmed place transitions (incident sorting itself out)
    you.place = p
    o._eng_cd -= 40
    n = len(o.tts.spoken)
    drive(o, s, 1)
    fired = started(o, n)
    assert not fired, (
        f"start call fired while the confirmed place was still moving (P{p}): "
        f"{fired}")
    o._green_t -= 1.0              # a further beat passes before the next change
print("  no start call while the confirmed place keeps changing: OK")

print("\n===== 2. fires once it genuinely settles, reporting the SETTLED "
      "position =====")
# the confirmed place stops moving at P4. Let the stability window close (on
# top of the floor already cleared) without any further change.
o._green_t -= (ENG_START_STABLE_S + 1.0)
o._eng_cd -= 40
n = len(o.tts.spoken)
drive(o, s, 1)
fired = started(o, n)
assert fired, "start call never fired once the position genuinely settled"
assert "P4" in fired[0], f"start call reported the wrong (stale) position: {fired[0]}"
assert "P10" not in fired[0] and "P6" not in fired[0] and "P5" not in fired[0], (
    f"start call reported a stale mid-scramble position: {fired[0]}")
print(f"  fires with the correct, settled position: {fired[0][:64]}")

# and only once
n = len(o.tts.spoken)
o._eng_cd -= 40
drive(o, s, 3)
again = started(o, n)
assert not again, f"start call repeated: {again}"
print("  fires exactly once: OK")

print("\nSTART-CHAOS CHECKS PASSED")
