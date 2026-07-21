"""OBJECTIVE DEPTH — the four things the driver asked for after a real race:

  1. HYSTERESIS: a pass/loss must STICK for a few seconds before it resolves, so
     a wheel-to-wheel fight that yo-yos for a place doesn't insta-score either way.
  2. ENGINEER-FIRST: the booth must not remark on a target until the driver's own
     pit-wall call for it has aired.
  3. STAKE-AWARE ENGINEER: mid-objective nudges name the prize ("you can get this
     podium"), not a bare gap/lap readout.
  4. STAKE-AWARE BOOTH: the set-brief names what it's worth ("to defend the podium").

Each assertion is written so it FAILS on the pre-change code (git stash the
sources, run, git stash pop) — that's the proof the behaviour is real.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import os
import sys

sys.path.insert(0, r"D:\R3EOverlay")
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "smoke.py")).read()
exec(_src.split('run_session("RACE"')[0])
from overlay_common import obj_stake, OBJ_BRIEF, _safe_format   # noqa: E402
from lines import ENGINEER_LINES                          # noqa: E402

NCARS = 8


def build(my_place=5, laps=20, done=5):
    # the player is ALWAYS index 0 (s.vehicle_info.slot_id); put them at my_place
    # and give the car that held that slot P1, exactly as objectivetest.race does.
    o = headless_overlay(fake_tts=True)
    s = make_shared(2, ncars=NCARS)
    s.number_of_laps = laps
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    o._obj_reset()
    o._obj_damaged = False
    you = s.all_drivers_data_1[0]
    for i, d in enumerate(s.all_drivers_data_1[:NCARS]):
        d.car_speed = 60.0
        d.place = i + 1
        d.completed_laps = done
    you.place = my_place
    s.all_drivers_data_1[my_place - 1].place = 1
    o._racing = True
    return o, s, you


def opm(s):
    order = sorted((d for d in s.all_drivers_data_1[:s.num_cars] if d.place > 0),
                   key=lambda d: d.place)
    return order, {d.place: d for d in order}


def chk(o, s, t):
    order, pm = opm(s)
    return o._obj_check(s, order, pm, t)


print("===== 1. HYSTERESIS: a yo-yo pass doesn't insta-resolve =====")
o, s, you = build(my_place=5)
vs = you.driver_info.slot_id
o.cplace[vs] = 5
o._obj = {"kind": "position", "target_slot": s.all_drivers_data_1[3].driver_info.slot_id,
          "target_name": "Rossi", "goal_pos": 4, "gap_target": 0.0, "laps": 8,
          "lap0": you.completed_laps, "gap0": 3.0, "hud": "P4 — pass Rossi"}
base = 1000.0
# you take P4...
you.place = 4
o.cplace[vs] = 4
r = chk(o, s, base)
assert r is None, f"a pass resolved INSTANTLY — no hold applied: {r}"
# ...but before the hold window elapses you get repassed back to P5
you.place = 5
o.cplace[vs] = 5
r = chk(o, s, base + 1.5)
assert r is None, f"a pass that swapped straight back still scored: {r}"
assert o._obj is not None, "the objective was resolved by a yo-yo — it must survive"
print("  a pass that yo-yos back within the window does NOT score: OK")
# now hold P4 continuously long enough
you.place = 4
o.cplace[vs] = 4
chk(o, s, base + 2.0)                      # re-arm at the new gain
r = chk(o, s, base + 2.0 + 6.0)           # held past OBJ_HOLD_GAIN
assert r and r[0] == "obj_met_pass", f"a pass HELD for the window didn't score: {r}"
print("  a pass held past the window DOES score: OK")


print("\n===== 1b. HYSTERESIS: a yo-yo loss doesn't insta-fail =====")
o, s, you = build(my_place=5)
vs = you.driver_info.slot_id
o.cplace[vs] = 5
o._obj = {"kind": "defend", "target_slot": s.all_drivers_data_1[5].driver_info.slot_id,
          "target_name": "Rossi", "goal_pos": 5, "gap_target": 3.0, "laps": 8,
          "lap0": you.completed_laps, "hud": "Hold P5 from Rossi"}
base = 2000.0
you.place = 6                             # lost the place...
o.cplace[vs] = 6
r = chk(o, s, base)
assert r is None, f"a lost place FAILED instantly — no hold applied: {r}"
you.place = 5                             # ...got it straight back
o.cplace[vs] = 5
r = chk(o, s, base + 2.0)
assert r is None and o._obj is not None, (
    f"a place lost-then-regained still failed the target: {r}")
print("  a place lost then regained within the window does NOT fail: OK")
you.place = 6                             # lost it and it stays lost
o.cplace[vs] = 6
chk(o, s, base + 3.0)                      # re-arm
r = chk(o, s, base + 3.0 + 6.0)           # held past OBJ_HOLD_LOSE
assert r and r[0] == "obj_miss_defend", f"a place lost for good didn't fail: {r}"
print("  a place lost past the window DOES fail: OK")


print("\n===== 2. ENGINEER-FIRST: booth waits for the pit-wall call =====")
o, s, you = build(my_place=5)
for _ in range(8):
    drive(o, s, 1)
o._green_at = time.time() - 60.0
before = len(o.tts.spoken)
_nt = time.time()
o._obj_booth = ("set", "defend", "Rossi", _nt, "the podium")
o._obj_eng_aired_t = _nt - 5.0            # engineer has NOT aired this notice yet
for _ in range(6):
    drive(o, s, 1)
assert not any("defend the podium" in t for _p, t in o.tts.spoken[before:]), (
    "the booth spoke the target BEFORE the engineer's call aired")
assert o._obj_booth is not None, "the held notice was dropped while waiting"
print("  booth stays silent until the engineer's call has aired: OK")
o._obj_eng_aired_t = _nt                   # now the pit-wall call has aired
for _ in range(6):
    drive(o, s, 1)
assert any("defend the podium" in t for _p, t in o.tts.spoken[before:]), (
    "the booth never picked up the target once the engineer had spoken")
print("  ...then picks it up once the engineer has spoken: OK")


print("\n===== 3. STAKE-AWARE ENGINEER NUDGE =====")
o, s, you = build(my_place=4)
o._obj = {"kind": "position", "target_name": "Rossi", "goal_pos": 3,
          "laps": 6, "lap0": you.completed_laps, "_trend": 0, "_laps_left": 4}
o._obj_nudge_t = 0.0
o._obj_nudge_i = 0                          # -> slot 1: the stakes branch
nud = o._obj_nudge(s, you, time.time())
assert nud and nud[0] == "obj_nudge_stakes_go", f"no stakes nudge for a podium chase: {nud}"
assert nud[1]["stake"] == "the podium", f"stake not the podium: {nud[1]}"
line = _safe_format(ENGINEER_LINES[nud[0]][0], nud[1])
assert "the podium" in line, f"the podium not named in the line: {line!r}"
print(f"  a podium chase names the prize: OK -> {line!r}")


print("\n===== 3b. RETARGET: the objective follows the POSITION, not the name =====")
o, s, you = build(my_place=6)
vs = you.driver_info.slot_id
for d in s.all_drivers_data_1[:NCARS]:
    o.cplace[d.driver_info.slot_id] = d.place
p5 = next(d for d in s.all_drivers_data_1[:NCARS] if d.place == 5)
p4 = next(d for d in s.all_drivers_data_1[:NCARS] if d.place == 4)
o._obj = {"kind": "position", "target_slot": p5.driver_info.slot_id,
          "target_name": o._dname(p5), "goal_pos": 5, "gap_target": 0.0,
          "laps": 8, "lap0": you.completed_laps, "gap0": 3.0,
          "hud": "P5 — pass " + o._dname(p5)}
# the car you were chasing for P5 climbs to P4; the old P4 car drops into P5
p5.place = 4
p4.place = 5
o.cplace[p5.driver_info.slot_id] = 4
o.cplace[p4.driver_info.slot_id] = 5
order, pm = opm(s)
o._obj_check(s, order, pm, 3000.0)
assert o._obj is not None, "the objective was wrongly withdrawn on a retarget"
assert o._obj["target_slot"] == p4.driver_info.slot_id, (
    f"objective did not retarget to the new car in P5: {o._obj['target_name']}")
assert o._dname(p4) in o._obj["hud"], f"HUD not updated to new target: {o._obj['hud']!r}"
print(f"  'P5 from X' retargets to whoever is now in P5: OK -> {o._obj['target_name']}")


print("\n===== 4. STAKE-AWARE BOOTH BRIEF + shared stake helper =====")
assert obj_stake("leadhome", 1) == "the win"
assert obj_stake("position", 3) == "the podium"
assert obj_stake("defend", 5) == "P5"
assert obj_stake("clean", None) == "a clean run"
_brief = _safe_format(OBJ_BRIEF["defend"], {"tgt": "Rossi", "stake": "the podium"})
assert "defend the podium" in _brief, f"defend brief not stake-aware: {_brief!r}"
_brief2 = _safe_format(OBJ_BRIEF["position"], {"tgt": "Rossi", "stake": "the win"})
assert "for the win" in _brief2, f"pass brief not stake-aware: {_brief2!r}"
print("  obj_stake + stake-aware briefs: OK")

print("\nOBJECTIVE DEPTH CHECKS PASSED")
