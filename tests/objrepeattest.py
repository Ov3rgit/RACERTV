"""THE ENGINEER MUST NOT ASK FOR THE SAME JOB OVER AND OVER.

From a real race transcript, the closing minutes:

  09:35:02  Protect P3. Pano Papas is the threat, 1 lap to withstand it.
  09:35:08  Pano Papas's fallen away, no more threat there. P3 is yours.
  09:35:33  Defensive job now: Pano Papas behind, P3 to protect, 1 lap.
  09:35:39  Held it! P3 is yours -- Pano Papas couldn't find a way past.

Set and "achieved" inside six seconds, twice, against the same driver -- and
that was the fourth and fifth time that same defend had been handed out. Two
separate faults:

  * The repeatable kinds (defend / position / chase) had no memory. `clean`,
    `tyres`, `recover` and friends are one-shot via _obj_seen, but the racing
    ones could be re-offered the instant they resolved -- and since the
    situation that produced the objective is still the situation the moment it
    ends, the very next offer was always identical.
  * In the closing laps `immediate` deliberately skips every hysteresis hold
    (there is no 'later' to wait for at the flag), which also meant a defend
    offered at 1.5s could bank itself the moment the gap touched 2.2s. The
    driver achieved nothing; the chaser simply wasn't there.

Fixes: OBJ_REPEAT_CD blocks the same (kind, driver) coming back, and
OBJ_MIN_LIFE stops a PASSIVE 'threat evaporated' verdict landing on an
objective that has barely existed. A genuine miss is deliberately exempt --
losing the place IS the answer, however fast it happens.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import sys

sys.path.insert(0, r"D:\R3EOverlay")
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])
from overlay_objective import (OBJ_MIN_LIFE, OBJ_REPEAT_CD,   # noqa: E402
                               OBJ_DEFEND_CLEAR_GAP)


def race(ncars=8, my_place=3, laps=20):
    """You run `my_place`, everyone else fills in around you in slot order, so
    the car directly BEHIND you is a known driver -- the defend logic retargets
    onto whoever actually occupies that place, so the field has to be real."""
    o = headless_overlay(fake_tts=True)
    s = make_shared(2, ncars=ncars)
    s.number_of_laps = laps
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    o._obj_reset()
    o._obj_damaged = False
    o._racing = True
    you = s.all_drivers_data_1[0]
    others = list(s.all_drivers_data_1[1:ncars])
    places = [p for p in range(1, ncars + 1) if p != my_place]
    for d in s.all_drivers_data_1[:ncars]:
        d.car_speed = 60.0
        d.completed_laps = 6
    you.place = my_place
    for d, p in zip(others, places):
        d.place = p
    o.cplace[you.driver_info.slot_id] = my_place
    for d in others:
        o.cplace[d.driver_info.slot_id] = d.place
    behind = next(d for d in others if d.place == my_place + 1)
    return o, s, you, behind


# ---- 1. a PASSIVE defend verdict needs the objective to have existed -----
o, s, you, chaser = race()
vslot = you.driver_info.slot_id
csl = chaser.driver_info.slot_id
now = time.time()
# a live defend, set RIGHT NOW, against a chaser who has just dropped away
o._obj = {"kind": "defend", "target_slot": csl, "target_name": "Chaser",
          "gap_target": 1.0, "goal_pos": you.place, "laps": 1,
          "lap0": you.completed_laps, "set_at": now, "gap0": 1.0}
o.interval[csl] = OBJ_DEFEND_CLEAR_GAP + 1.0      # plainly clear
assert o._obj_too_soon(now + 1.0), (
    "an objective one second old is not being treated as too young to bank")
assert not o._obj_too_soon(now + OBJ_MIN_LIFE + 1.0), (
    "an objective older than OBJ_MIN_LIFE is still considered too young")
print("  a brand-new objective is too young to resolve MET: OK (< %.0fs)"
      % OBJ_MIN_LIFE)

# drive the real resolver at the flag (immediate=True path -- the bug)
order = sorted((d for d in s.all_drivers_data_1[:8] if d.place > 0),
               key=lambda d: d.place)
pm = {d.place: d for d in order}
s.flags.white = 1                                  # closing: immediate holds
res = o._obj_check(s, order, pm, now + 2.0)
assert not (res and res[0] == "obj_met_defend_clear"), (
    "a defend set two seconds ago was already banked as MET because the "
    "chaser was never there -- the reported 'set and won in six seconds'")
print("  ...so the closing-lap defend is NOT banked after 2s: OK")

# once it has genuinely stood for a while, it resolves as before
res = o._obj_check(s, order, pm, now + OBJ_MIN_LIFE + 5.0)
assert res and res[0] == "obj_met_defend_clear", (
    "a defend that DID stand for a real stretch no longer resolves: %r" % (res,))
print("  ...and still resolves once it has actually stood: OK -> %s" % res[0])


# ---- 1b. THE ACTUAL TRANSCRIPT BUG: a TIMED race at the flag ------------
# This is the branch that produced the reported lines, and it is NOT the
# defend_clear path above. In a timed race _obj_race_ending goes true near the
# end, and the ending-bank branch then banks ANY live hold objective instantly
# -- so a defend handed out seconds earlier got "Held it! P3 is yours" for
# surviving a deadline it never had time to face. (Verified against the
# pre-fix code, which answered obj_met_defend for a two-second-old defend.)
def timed_closing(age):
    o, s, you, chaser = race()
    s.number_of_laps = 0                           # timed, like the transcript
    s.session_time_remaining = 40.0
    o.recent_laps[you.driver_info.slot_id] = [95.0, 95.0, 95.0]
    csl = chaser.driver_info.slot_id
    t0 = time.time()
    o._obj = {"kind": "defend", "target_slot": csl, "target_name": "Chaser",
              "gap_target": 1.0, "goal_pos": 3, "laps": 1,
              "lap0": you.completed_laps, "set_at": t0, "gap0": 1.0}
    o.interval[csl] = 0.9                          # still right behind
    order = sorted((d for d in s.all_drivers_data_1[:8] if d.place > 0),
                   key=lambda d: d.place)
    pm = {d.place: d for d in order}
    assert o._obj_race_ending(s, order), "test setup is not in the closing phase"
    return o, o._obj_check(s, order, pm, t0 + age)


o2, res = timed_closing(2.0)
assert not (res and res[0].startswith("obj_met")), (
    "a defend set two seconds before the flag was still congratulated as met "
    "-- this is the exact transcript line 'Held it! P3 is yours': %r" % (res,))
assert o2._obj is None, "the hollow objective was left live on the HUD"
print("  timed-race flag: a 2s-old defend is dropped silently: OK")

o3, res = timed_closing(OBJ_MIN_LIFE + 5.0)
assert res and res[0] == "obj_met_defend", (
    "a defend that stood for a real stretch to the flag lost its verdict: %r"
    % (res,))
print("  ...while one that actually stood still gets its verdict: OK -> %s"
      % res[0])

# SERVING THE LAPS COUNTS. The guard is about targets the flag cut short, not
# about the clock: a driver who actually ran the laps asked of them earned the
# verdict however compressed the timeline looks.
o4, s4, you4, ch4 = race()
s4.number_of_laps = 0
s4.session_time_remaining = 40.0
o4.recent_laps[you4.driver_info.slot_id] = [95.0, 95.0, 95.0]
t0 = time.time()
o4._obj = {"kind": "defend", "target_slot": ch4.driver_info.slot_id,
           "target_name": "Chaser", "gap_target": 1.0, "goal_pos": 3,
           "laps": 2, "lap0": you4.completed_laps, "set_at": t0, "gap0": 1.0}
o4.interval[ch4.driver_info.slot_id] = 0.9
you4.completed_laps += 2                       # the two laps were actually run
_order = sorted((d for d in s4.all_drivers_data_1[:8] if d.place > 0),
                key=lambda d: d.place)
res = o4._obj_check(s4, _order, {d.place: d for d in _order}, t0 + 1.0)
assert res and res[0] == "obj_met_defend", (
    "the driver ran the two laps the target asked for and still got no "
    "verdict, because the wall clock said it was young: %r" % (res,))
print("  serving the laps earns the verdict regardless of the clock: OK")

# ---- 2. a genuine MISS is exempt -- losing the place is the answer -------
o, s, you, chaser = race()
vslot = you.driver_info.slot_id
csl = chaser.driver_info.slot_id
now = time.time()
o._obj = {"kind": "defend", "target_slot": csl, "target_name": "Chaser",
          "gap_target": 1.0, "goal_pos": 3, "laps": 3,
          "lap0": you.completed_laps, "set_at": now, "gap0": 1.0}
o.interval[csl] = 0.4
you.place = 4                                      # passed immediately
o.cplace[vslot] = 4
order = sorted((d for d in s.all_drivers_data_1[:8] if d.place > 0),
               key=lambda d: d.place)
pm = {d.place: d for d in order}
res = None
for dt in (1.0, 3.0, 5.0, 7.0, 9.0):               # let the lose-hold elapse
    res = o._obj_check(s, order, pm, now + dt)
    if res:
        break
assert res and "miss" in res[0], (
    "losing the place you were told to defend did not fail the objective "
    "(min-life must not gag a genuine miss): %r" % (res,))
print("  a genuine miss still lands regardless of age: OK -> %s" % res[0])

# ---- 3. the SAME (kind, driver) can't come straight back ----------------
o, s, you, _b = race()
now = time.time()
o._obj_recent[("defend", 7)] = now
assert o._obj_repeat_blocked("defend", 7, now + 5.0), (
    "the same defend against the same driver was offerable 5s after it "
    "resolved -- this is the loop from the transcript")
assert o._obj_repeat_blocked("defend", 7, now + OBJ_REPEAT_CD - 5.0), (
    "the repeat block expired early")
assert not o._obj_repeat_blocked("defend", 7, now + OBJ_REPEAT_CD + 1.0), (
    "the repeat block never expires -- one defend would kill defends for the "
    "rest of the race")
print("  same kind+driver blocked for %.0fs, then allowed again: OK"
      % OBJ_REPEAT_CD)

# a DIFFERENT driver, or a different kind, is still fair game -- the point is
# variety, not silence
assert not o._obj_repeat_blocked("defend", 9, now + 5.0), (
    "defending against a DIFFERENT driver was blocked")
assert not o._obj_repeat_blocked("chase", 7, now + 5.0), (
    "a different KIND of objective against the same driver was blocked")
print("  a different driver or a different job is NOT blocked: OK")

# ---- 4. resolving an objective records it -------------------------------
o, s, you, _b = race()
now = time.time()
o._obj = {"kind": "defend", "target_slot": 11, "target_name": "X",
          "gap_target": 1.0, "goal_pos": 3, "laps": 2,
          "lap0": 6, "set_at": now - 60.0, "gap0": 1.0}
o._obj_done(now, "obj_met_defend", {"drv": "X", "pos": 3})
assert o._obj_repeat_blocked("defend", 11, now + 1.0), (
    "a resolved objective was not recorded, so it can be handed straight back")
print("  resolving an objective records it for the repeat block: OK")

# ---- 5. VARIETY: the chase target scales with the gap -------------------
# Pinned at 1.0s, "close to within a second" from four seconds back was
# rejected by the feasibility maths, so a strung-out race had defend as its
# only repeatable objective -- which is how the loop formed. The ask now
# scales, which is also what the driver requested ("get within 2 seconds").
o, s, you, _b = race()
assert o._obj_gap_text(2.0) == "2s", o._obj_gap_text(2.0)
assert o._obj_gap_text(2.5) == "2.5s", o._obj_gap_text(2.5)
print("  gap targets read cleanly as '2s' / '2.5s': OK")

# the HUD and the spoken line must quote the SAME number
o._obj = {"kind": "chase", "target_slot": 5, "target_name": "X",
          "gap_target": 2.5, "goal_pos": None, "laps": 3, "lap0": 6,
          "set_at": time.time(), "gap0": 4.5,
          "hud": "Within 2.5s of X"}
spoken = o._obj_gap_text(o._obj["gap_target"])
assert spoken in o._obj["hud"], (
    "the spoken gap (%r) does not match the HUD card (%r)"
    % (spoken, o._obj["hud"]))
print("  spoken target matches the card: OK -> %s" % spoken)

print("\nOBJECTIVE-REPEAT CHECKS PASSED")
