"""Race objectives: the engineer setting a target, tracking it, resolving it.

The assertions that matter most are the NEGATIVE ones. An objective that was
never achievable is worse than no objective at all — it instantly exposes the
engineer as fake — so most of this file is about proving he stays quiet when a
target isn't realistically on.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import sys

sys.path.insert(0, r"D:\R3EOverlay")
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])
from lines import ENGINEER_LINES                        # noqa: E402
from poolmatch import from_pool                         # noqa: E402
from overlay_common import _safe_format                 # noqa: E402

SET_POOLS = (ENGINEER_LINES["obj_set_chase"] + ENGINEER_LINES["obj_set_position"]
             + ENGINEER_LINES["obj_set_defend"] + ENGINEER_LINES["obj_set_damage"])


def race(ncars=8, laps=20, my_place=5):
    o = headless_overlay(fake_tts=True)
    s = make_shared(2, ncars=ncars)
    s.number_of_laps = laps
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    o._obj_reset()
    o._obj_damaged = False
    you = s.all_drivers_data_1[0]
    for i, d in enumerate(s.all_drivers_data_1[:ncars]):
        d.car_speed = 60.0
        d.place = i + 1
        d.completed_laps = 4
    you.place = my_place
    s.all_drivers_data_1[my_place - 1].place = 1
    o._racing = True
    return o, s, you


def pace(o, slot, t):
    o.recent_laps[slot] = [t, t, t]


def offer(o, s):
    """Ask the objective system directly for its decision this tick."""
    order = sorted((d for d in s.all_drivers_data_1[:s.num_cars] if d.place > 0),
                   key=lambda d: d.place)
    pm = {d.place: d for d in order}
    o._obj_last_t = 0.0
    return o.objective_event(s, order, pm, time.time())


print("===== STAYS SILENT WHEN A TARGET ISN'T ON =====")

# 1. no pace edge — we are no quicker than the car ahead
o, s, you = race()
pace(o, you.driver_info.slot_id, 90.0)
pace(o, s.all_drivers_data_1[1].driver_info.slot_id, 90.0)
o.interval = {you.driver_info.slot_id: 3.0}
assert offer(o, s) is None, "offered a chase with NO pace advantage"
print("  no pace edge -> silent: OK")

# 2. plenty of pace, but the gap is absurd
o, s, you = race()
pace(o, you.driver_info.slot_id, 88.0)
pace(o, s.all_drivers_data_1[1].driver_info.slot_id, 90.0)
o.interval = {you.driver_info.slot_id: 45.0}
assert offer(o, s) is None, "offered a chase across a 45s gap"
print("  gap far too large -> silent: OK")

# 3. good pace, small gap, but the race is nearly over
o, s, you = race(laps=20)
for d in s.all_drivers_data_1[:s.num_cars]:
    d.completed_laps = 19            # 1 lap to go
pace(o, you.driver_info.slot_id, 89.0)
pace(o, s.all_drivers_data_1[1].driver_info.slot_id, 90.0)
o.interval = {you.driver_info.slot_id: 4.0}
assert offer(o, s) is None, "offered a target with a single lap left"
print("  not enough laps left -> silent: OK")

# 4. no pace data at all yet (opening laps)
o, s, you = race()
o.recent_laps = {}
o.interval = {you.driver_info.slot_id: 2.0}
assert offer(o, s) is None, "offered a target with no pace read"
print("  no pace data -> silent: OK")

# 5. marginal edge: 0.02s/lap is noise, not a catch
o, s, you = race()
pace(o, you.driver_info.slot_id, 89.98)
pace(o, s.all_drivers_data_1[1].driver_info.slot_id, 90.0)
o.interval = {you.driver_info.slot_id: 5.0}
assert offer(o, s) is None, "offered a chase on a 0.02s/lap edge"
print("  edge below noise floor -> silent: OK")


print("\n===== OFFERS WHEN IT GENUINELY IS ON =====")
o, s, you = race(my_place=5)
pace(o, you.driver_info.slot_id, 89.0)          # 1s/lap quicker
pace(o, s.all_drivers_data_1[3].driver_info.slot_id, 90.0)
o.interval = {you.driver_info.slot_id: 4.0}     # 4s back, 16 laps left
got = offer(o, s)
assert got, "did NOT offer a target that was clearly achievable"
cat, kw = got
assert cat.startswith("obj_set_"), cat
line = ENGINEER_LINES[cat][0]
print(f"  offered {cat}: {line[:66]}")
assert o._obj, "objective was not stored"
assert o._obj["laps"] >= 2, "deadline is too tight to be meaningful"
print(f"  deadline {o._obj['laps']} laps, hud={o._obj['hud']!r}: OK")


print("\n===== RESOLVES, AND ONLY ONCE =====")
# meet it: take the position
you.place = 4
s.all_drivers_data_1[3].place = 5
res = offer(o, s)
assert res and res[0] == "obj_met_pass", f"pass not detected as met: {res}"
assert o._obj is None, "objective still active after being met"
assert o._obj_result and o._obj_result["ok"], "HUD result not latched as met"
print(f"  target met -> {res[0]}, HUD latched: OK")
assert offer(o, s) is None or o._obj, "resolved objective fired twice"

# miss it: run out of laps
o, s, you = race(my_place=5)
pace(o, you.driver_info.slot_id, 89.0)
pace(o, s.all_drivers_data_1[3].driver_info.slot_id, 90.0)
o.interval = {you.driver_info.slot_id: 4.0}
assert offer(o, s), "setup: no objective offered"
lap0 = o._obj["lap0"]
dl = o._obj["laps"]
for d in s.all_drivers_data_1[:s.num_cars]:
    d.completed_laps = lap0 + dl                 # deadline reached, no progress
res = offer(o, s)
assert res and res[0].startswith("obj_miss"), f"deadline miss not resolved: {res}"
assert o._obj is None, "missed objective still active"
assert o._obj_result and not o._obj_result["ok"], "HUD result not latched as missed"
print(f"  target missed -> {res[0]}, HUD latched: OK")


print("\n===== WITHDRAWN WHEN THE RACE CHANGES =====")
o, s, you = race(my_place=5)
pace(o, you.driver_info.slot_id, 89.0)
pace(o, s.all_drivers_data_1[3].driver_info.slot_id, 90.0)
o.interval = {you.driver_info.slot_id: 4.0}
assert offer(o, s), "setup: no objective offered"
o._obj_damaged = True                            # car breaks mid-objective
res = offer(o, s)
assert res and res[0] == "obj_withdraw_damage", f"not withdrawn on damage: {res}"
assert o._obj is None, "withdrawn objective still active"
print(f"  damage withdraws the target -> {res[0]}: OK")

# a damaged car still gets a salvage objective
o.interval = {s.all_drivers_data_1[5].driver_info.slot_id: 3.0}
o._obj_last_t = 0.0
got = offer(o, s)
if got:
    print(f"  damaged car still gets a target: {got[0]}")
    assert got[0] == "obj_set_damage", got[0]


print("\n===== EVERY LINE FORMATS =====")
bad = []
for cat in [k for k in ENGINEER_LINES if k.startswith("obj_")]:
    for tpl in ENGINEER_LINES[cat]:
        out = _safe_format(tpl, {"drv": "Kowalski", "laps": 5, "pos": 3,
                                 "gap": "1s"})
        if "{" in out:
            bad.append((cat, out))
assert not bad, f"objective lines failed to format: {bad[:3]}"
n = sum(len(ENGINEER_LINES[k]) for k in ENGINEER_LINES if k.startswith("obj_"))
print(f"  all {n} objective lines format cleanly: OK")

print("\nALL OBJECTIVE CHECKS PASSED")


print("\n===== PHASE 2: SITUATION-BASED TARGETS =====")

# CLEAN RUNNING — triggered by the engineer's own limits tally
o, s, you = race(my_place=5)
pace(o, you.driver_info.slot_id, 90.0)
o._own_cuts = 3
got = offer(o, s)
assert got and got[0] == "obj_set_clean", f"no clean-running target at 3 cuts: {got}"
print(f"  3 limits warnings -> {got[0]}: {o._obj['hud']!r}")
# another warning fails it
o._own_cuts = 4
res = offer(o, s)
assert res and res[0] == "obj_miss_clean", f"another cut should fail it: {res}"
print(f"  a further warning fails it -> {res[0]}: OK")
# and it is one-shot: not re-offered immediately
o._own_cuts = 4
assert o._obj_seen("clean"), "clean objective not recorded as used"
print("  one-shot (won't nag): OK")

# RECOVERY — lost real ground vs the grid
o, s, you = race(my_place=9)
pace(o, you.driver_info.slot_id, 90.0)
o.grid_place = {you.driver_info.slot_id: 4}
o._race_story = {you.driver_info.slot_id: {"best": 4, "worst": 9, "now": 9}}
got = offer(o, s)
assert got and got[0] == "obj_set_recover", f"no recovery target after dropping: {got}"
print(f"  dropped P4->P9 -> {got[0]}: {o._obj['hud']!r}")
you.place = o._obj["goal_pos"]
res = offer(o, s)
assert res and res[0] == "obj_met_recover", f"recovery not detected: {res}"
print(f"  regaining the ground -> {res[0]}: OK")

# TYRES — worn rubber, stint to run
o, s, you = race(my_place=5)
pace(o, you.driver_info.slot_id, 90.0)
s.tire_wear_active = 1
o._eng_tyre_base = [1.0, 1.0, 1.0, 1.0]
for i in range(4):
    s.tire_wear[i] = 0.35                 # 0.65 worn
got = offer(o, s)
assert got and got[0] == "obj_set_tyres", f"no tyre target on worn rubber: {got}"
print(f"  tyres 65% worn -> {got[0]}: {o._obj['hud']!r}")

# tyre wear must be IGNORED when the game isn't publishing it
o2, s2, you2 = race(my_place=5)
pace(o2, you2.driver_info.slot_id, 90.0)
s2.tire_wear_active = 0
o2._eng_tyre_base = [1.0, 1.0, 1.0, 1.0]
assert o2._obj_tyre_worn(s2) is None, "read tyre wear while tire_wear_active was off"
print("  wear ignored when the game reports N/A: OK")


print("\n===== PHASE 3: CAREER FORM + WRAP =====")
o, s, you = race()
o._career_data = {"races": 5, "wins": 0, "podiums": 1, "tracks": {},
                  "obj_set": 12, "obj_met": 8,
                  "obj_races": [[2, 3], [1, 2], [3, 3], [2, 4]]}
form = o.objective_form()
assert form, "no form returned despite 4 races of history"
met, setn, races = form
assert (met, setn, races) == (8, 12, 4), form
print(f"  recent form: {met} of {setn} over {races} races: OK")

# too little history -> stays quiet rather than inventing a trend
o._career_data["obj_races"] = [[1, 2]]
assert o.objective_form() is None, "claimed form from a single race"
print("  <3 races -> no form claim: OK")

# end-of-race wrap
for n_set, n_met, want in ((3, 3, "obj_wrap_all"), (3, 1, "obj_wrap_some"),
                           (2, 0, "obj_wrap_none")):
    o._obj_count, o._obj_met = n_set, n_met
    cat, kw = o.objective_summary()
    assert cat == want, f"{n_met}/{n_set} -> {cat}, expected {want}"
    out = _safe_format(ENGINEER_LINES[cat][0], kw)
    assert "{" not in out, out
print("  wrap picks all/some/none correctly and formats: OK")

o._obj_count = 0
assert o.objective_summary() is None, "wrapped up a race with no targets set"
print("  no targets set -> no wrap: OK")

print("\nALL PHASE 2/3 OBJECTIVE CHECKS PASSED")

print("\n===== PHASE 4: ADAPTS TO THE RACE (the bugs from a real run) =====")


def order_pm(s):
    order = sorted((d for d in s.all_drivers_data_1[:s.num_cars] if d.place > 0),
                   key=lambda d: d.place)
    return order, {d.place: d for d in order}


# 1. a DEFEND objective tracks progress on the HUD (was a frozen empty bar)
o, s, you = race(my_place=4)
you.place = 4
o._obj = {"kind": "defend", "target_slot": s.all_drivers_data_1[4].driver_info.slot_id,
          "target_name": "Rossi", "goal_pos": 4, "gap_target": 3.0, "laps": 4,
          "lap0": you.completed_laps, "hud": "Hold P4 from Rossi"}
you.completed_laps += 2                       # halfway through the 4-lap hold
prog = o._obj_progress(s, [d for d in s.all_drivers_data_1[:s.num_cars]])
assert prog is not None and 0.4 < prog < 0.6, (
    f"a defend objective reported no/wrong progress: {prog}")
print(f"  defend objective tracks progress: OK ({prog:.2f})")

# 2. THE HEADLINE BUG: holding off P4, a crash climbs you to P2 -> the target
#    is superseded and banked, not left stuck forever
o, s, you = race(my_place=4)
you.place = 4
o._obj = {"kind": "defend", "target_slot": s.all_drivers_data_1[4].driver_info.slot_id,
          "target_name": "Rossi", "goal_pos": 4, "gap_target": 3.0, "laps": 4,
          "lap0": you.completed_laps, "hud": "Hold P4 from Rossi"}
you.place = 2                                 # a crash ahead put you up to P2
order, pm = order_pm(s)
res = o._obj_check(s, order, pm, time.time())
assert res and res[0] == "obj_supersede_gained", (
    f"climbing P4->P2 did not supersede the defend target: {res}")
assert o._obj is None, "the stale defend objective was not cleared"
print(f"  defend P4 -> climbed to P2 supersedes: OK -> {res[0]}")

# 3. supersede shortens the spacing so a fresh target can land promptly
assert o._obj_last_t < time.time() - 1, (
    "supersede did not shorten the next-objective spacing")
print("  supersede lets the next objective come sooner: OK")

# 4. the engineer NUDGES mid-objective (closing on a chase)
o, s, you = race(my_place=5)
you.place = 5
vs = you.driver_info.slot_id
o._obj = {"kind": "chase", "target_slot": s.all_drivers_data_1[3].driver_info.slot_id,
          "target_name": "Dubois", "goal_pos": None, "gap_target": 1.0, "laps": 6,
          "lap0": you.completed_laps, "gap0": 4.0, "hud": "Within 1s of Dubois",
          "_trend": -1, "_prog": 0.4, "_laps_left": 3}
o._obj_nudge_t = 0.0
nud = o._obj_nudge(s, you, time.time())
assert nud and nud[0] == "obj_nudge_closing", f"no closing nudge fired: {nud}"
# ...and it respects its cooldown (won't nag every tick)
again = o._obj_nudge(s, you, time.time() + 1.0)
assert again is None, f"nudge ignored its cooldown: {again}"
print(f"  engineer nudges mid-objective, on cooldown: OK -> {nud[0]}")

# 5. every new line pool formats cleanly
_newcats = ("obj_nudge_closing", "obj_nudge_slipping", "obj_nudge_threat",
            "obj_nudge_nearly", "obj_supersede_gained")
for _c in _newcats:
    assert ENGINEER_LINES.get(_c), f"missing line pool: {_c}"
    for _ln in ENGINEER_LINES[_c]:
        _safe_format(_ln, {"drv": "Rossi", "pos": 2})
print(f"  all {len(_newcats)} new engineer pools format cleanly: OK")

print("\nALL PHASE 4 OBJECTIVE CHECKS PASSED")

print("\n===== PHASE 5: WHOLE-RACE AWARENESS (from a real transcript) =====")


def order_pm2(s):
    order = sorted((d for d in s.all_drivers_data_1[:s.num_cars] if d.place > 0),
                   key=lambda d: d.place)
    return order, {d.place: d for d in order}


# 1. THREAT EVAPORATES: "hold P5 from Marco" resolves once Marco falls far back
o, s, you = race(my_place=5)
you.place = 5
mk = s.all_drivers_data_1[5]                  # the car behind (P6)
o._obj = {"kind": "defend", "target_slot": mk.driver_info.slot_id,
          "target_name": "Marco", "goal_pos": 5, "gap_target": 3.0, "laps": 6,
          "lap0": you.completed_laps, "hud": "Hold P5 from Marco"}
o.interval = {mk.driver_info.slot_id: 11.0}    # Marco is now 11s back
order, pm = order_pm2(s)
res = o._obj_check(s, order, pm, time.time())
assert res and res[0] == "obj_met_defend_clear", (
    f"a defend target whose threat vanished did not resolve: {res}")
assert o._obj is None
print(f"  defend resolves when the threat falls away: OK -> {res[0]}")

# 2. CLOSING-LAPS PODIUM PUSH: right behind a car in the last laps -> target,
#    even without a measured pace edge (the "behind P3, got nothing" bug)
o, s, you = race(my_place=4, laps=20)
you.place = 4
# only 2 laps to go, tight behind P3, and NO pace edge in the data
for d in s.all_drivers_data_1[:s.num_cars]:
    d.completed_laps = 18                       # 2 laps left of 20
    o.recent_laps[d.driver_info.slot_id] = [92.0, 92.0, 92.0]  # equal pace
you.completed_laps = 18
o.interval = {you.driver_info.slot_id: 0.4}     # 0.4s behind P3
o._obj = None
o._obj_last_t = 0.0
got = offer(o, s)
assert got and got[0] == "obj_set_position", (
    f"right behind P3 in the closing laps got no podium push: {got}")
assert "last chance" in o._obj["hud"].lower() or "pass" in o._obj["hud"].lower()
print(f"  closing-laps podium push fires without a pace edge: OK -> {o._obj['hud']!r}")

# 3. a STEADY hold gets a check-in nudge (not only on a trend change)
o, s, you = race(my_place=5)
you.place = 5
o._obj = {"kind": "defend", "target_slot": s.all_drivers_data_1[5].driver_info.slot_id,
          "target_name": "Marco", "goal_pos": 5, "gap_target": 3.0, "laps": 6,
          "lap0": you.completed_laps, "hud": "Hold P5", "_trend": 0,
          "_laps_left": 3}
o._obj_nudge_t = 0.0
nud = o._obj_nudge(s, you, time.time())
assert nud and nud[0] == "obj_nudge_holding", (
    f"a steady hold produced no check-in nudge: {nud}")
assert "more lap" in nud[1]["laps"]
print(f"  steady hold gets a check-in nudge with laps left: OK -> {nud[1]['laps']}")

print("\nALL PHASE 5 OBJECTIVE CHECKS PASSED")
