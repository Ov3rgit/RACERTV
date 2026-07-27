"""FALLING BACK MUST NOT CONFUSE THE WHOLE BROADCAST.

Reported twice. First fix did not work, and the debug log shows why.

  18:31:03  three "caught" lines queued INSIDE ONE SECOND as the player spun
  18:31:07  HOTHEAD  I'm giving it everything I've got, everything!
  18:31:10  HOTHEAD  I can see the bastard in my mirrors, do something!
  18:31:27  VILLAIN  It's hammer time — he's all over me!
  18:32:07  ROOKIE   Yes! Mirrors full of Over Boy. Here we go.

The chase block targets placemap[fp - 1] — the LIVE place, which moves the
instant you drop. The guard armed off cp(), the DEBOUNCED place, which needs
several ticks to agree. A spin outruns the debounce, so the block was already
seeing a new car ahead while the guard still believed nothing had happened.

Two independent defences now, because one clearly was not enough:
  1. the guard arms off the LIVE place as well (a false arm costs a few
     seconds of quiet; a missed arm costs the cascade)
  2. the car ahead must HOLD that slot for CHASE_TARGET_STABLE_S before its
     driver reacts — while your place churns it never does, whatever the cause

And the same race showed the engineer announcing a position that had moved on:
"Defend P7" was computed at 18:31:39 and aired at 18:32:12. A set line's
content is a live position, so it now carries a deadline, and a target whose
set line never got said is withdrawn rather than left on the HUD.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import sys

sys.path.insert(0, r"D:\R3EOverlay")
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])
from overlay_radio import (RADIO_FALL_QUIET, CHASE_TARGET_STABLE_S,  # noqa: E402
                           OBJ_SET_TTL)
from overlay_objective import OBJ_SET_STALE_S              # noqa: E402


def build(my_place=5, ncars=12):
    o = headless_overlay(fake_tts=True)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    s = make_shared(2, ncars=ncars)
    s.number_of_laps = 11
    you = s.all_drivers_data_1[0]
    others = list(s.all_drivers_data_1[1:ncars])
    places = [p for p in range(1, ncars + 1) if p != my_place]
    for d in s.all_drivers_data_1[:ncars]:
        d.car_speed, d.completed_laps = 60.0, 4
    you.place = my_place
    for d, p in zip(others, places):
        d.place = p
    for _ in range(8):
        drive(o, s, 1)
    o._green_at = o._green_t = time.time() - 60.0
    o._racing = True
    return o, s, you


# ---- 1. the guard arms off the LIVE place, before the debounce agrees ----
o, s, you = build(my_place=5)
o._radio_my_live = 5
o._radio_my_place = 5                 # confirmed still believes P5
o._fall_t = -1e9
you.place = 8                         # live place has already collapsed
drive(o, s, 1)
armed = time.time() - getattr(o, "_fall_t", -1e9)
assert armed < RADIO_FALL_QUIET, (
    "the live place fell from P5 to P8 and the fall guard did not arm — this "
    "is the exact hole the first fix left, since cp() had not caught up yet")
print("  guard arms off the LIVE place before the debounce agrees: OK")

# ---- 2. a churning place can never produce a chase call -----------------
# Independent of the guard: the target must hold its slot first.
o, s, you = build(my_place=5)
o._chase = {}
o._chase_ahead = None
o._fall_t = -1e9                       # guard deliberately DISARMED
vs = you.driver_info.slot_id


def radio_tick(o, s, you, place, itv):
    """Set the gap and run the radio directly.

    NOT via drive(): update_stats recomputes self.interval from telemetry every
    tick and would overwrite the gap, so the chase block would never run and
    'no cascade' would pass for the wrong reason — which is exactly how the
    first attempt at this test fooled me."""
    you.place = place
    o.interval[you.driver_info.slot_id] = itv
    o.update_radio(s)


for p in range(6, 12):                 # tumbling: a new car ahead every tick
    radio_tick(o, s, you, p, 0.4)      # genuinely right behind each one
assert not o._chase, (
    "a tumbling player still reached the chase logic (%d targets) even with "
    "the fall guard disarmed — the stability requirement is not holding"
    % len(o._chase))
print("  churning place never reaches the chase logic (2nd defence): OK")

# ---- 3. ...but sitting behind ONE car still does ------------------------
o, s, you = build(my_place=5)
o._chase = {}
o._chase_ahead = None
o._fall_t = -1e9
radio_tick(o, s, you, 5, 0.7)
assert o._chase_ahead is not None, (
    "the chase block never even ran — the harness is not reaching it, so the "
    "cascade check above would prove nothing")
o._chase_ahead = (o._chase_ahead[0], time.time() - CHASE_TARGET_STABLE_S - 1.0)
radio_tick(o, s, you, 5, 0.7)
assert o._chase, (
    "sitting behind the SAME car for longer than the stability window no "
    "longer reaches the chase logic — a genuine chase has gone silent")
print("  a stable chase target still fires: OK")

# ---- 4. an objective SET line carries a deadline ------------------------
o, s, you = build()
o._obj_say = ("obj_set_defend", {"drv": "Rival", "laps": 4, "pos": 7,
                                 "gap": "1s"})
o.last_radio_t = 0.0
o._eng_cd -= 40
evts = []
o._engineer_events(s, you, {d.place: d for d in s.all_drivers_data_1[:12]},
                   evts, time.time())
setev = [e for e in evts if len(e) > 7]
assert setev, "the objective set line no longer carries an explicit TTL"
assert setev[0][7] == OBJ_SET_TTL, (
    "set line TTL is %r, expected %r" % (setev[0][7], OBJ_SET_TTL))
print("  objective SET line carries a %.0fs deadline: OK" % OBJ_SET_TTL)

# a VERDICT must NOT — it describes something that already happened and stays
# true however late it lands
o, s, you = build()
o._obj_say = ("obj_met_defend", {"drv": "Rival", "pos": 7})
o.last_radio_t = 0.0
o._eng_cd -= 40
evts = []
o._engineer_events(s, you, {d.place: d for d in s.all_drivers_data_1[:12]},
                   evts, time.time())
if evts:
    assert len(evts[0]) <= 7 or evts[0][7] == "default", (
        "a verdict was given a deadline — it must never be dropped, that is "
        "the whole objective contract")
    print("  a verdict still carries no deadline: OK")

# ---- 5. a target whose set line was never said is withdrawn -------------
o, s, you = build()
o._obj_reset()
o._obj = {"kind": "defend", "target_slot": 3, "target_name": "Rival",
          "gap_target": 1.0, "goal_pos": 7, "laps": 4, "lap0": 4,
          "set_at": time.time() - (OBJ_SET_STALE_S + 3.0), "gap0": 1.0}
o._obj_say = ("obj_set_defend", {})        # still undrained -> never announced
order = sorted((d for d in s.all_drivers_data_1[:12] if d.place > 0),
               key=lambda d: d.place)
o.objective_event(s, order, {d.place: d for d in order}, time.time())
assert o._obj is None and o._obj_say is None, (
    "a target whose set line was never even queued is still on the HUD — the "
    "driver was never told about it, and announcing it now would quote a "
    "position from %.0fs ago" % OBJ_SET_STALE_S)
print("  an unannounced target is withdrawn, not left on the card: OK")

# ...while one that WAS drained survives untouched
o, s, you = build()
o._obj_reset()
o._obj = {"kind": "defend", "target_slot": 3, "target_name": "Rival",
          "gap_target": 1.0, "goal_pos": 7, "laps": 4, "lap0": 4,
          "set_at": time.time() - (OBJ_SET_STALE_S + 3.0), "gap0": 1.0}
o._obj_say = None                          # drained normally
o.objective_event(s, order, {d.place: d for d in order}, time.time())
assert o._obj is not None, (
    "an objective that WAS announced got withdrawn as stale — only an "
    "undrained set line means the driver never heard it")
print("  an announced target is left alone: OK")

print("\nFALL-RADIO CHECKS PASSED")
