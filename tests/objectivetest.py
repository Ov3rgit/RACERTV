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

# 2. plenty of pace, but the gap is absurd — must NOT offer a chase (it may now
# offer a clean-air consistency target instead, which is fine; just never a
# doomed chase across 45s)
o, s, you = race()
pace(o, you.driver_info.slot_id, 88.0)
pace(o, s.all_drivers_data_1[1].driver_info.slot_id, 90.0)
o.interval = {you.driver_info.slot_id: 45.0}
g2 = offer(o, s)
assert g2 is None or g2[0] not in ("obj_set_chase", "obj_set_position"), (
    f"offered a chase across a 45s gap: {g2}")
print("  gap far too large -> no chase: OK")

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

# 2. THE HEADLINE BUG: holding P6, you overtake into P5 -> the target is
#    superseded THE MOMENT you climb above it, not two places later. (Reported:
#    "hold off P6" stuck live while I was already P5 chasing P4.)
o, s, you = race(my_place=6)
you.place = 6
o._obj = {"kind": "defend", "target_slot": s.all_drivers_data_1[6].driver_info.slot_id,
          "target_name": "Rossi", "goal_pos": 6, "gap_target": 3.0, "laps": 4,
          "lap0": you.completed_laps, "hud": "Hold P6 from Rossi"}
you.place = 5                                 # one overtake — now above the held spot
o.cplace[you.driver_info.slot_id] = 5        # confirmed at P5
order, pm = order_pm(s)
res = o._obj_check(s, order, pm, time.time())
assert res and res[0] == "obj_supersede_gained", (
    f"climbing P6->P5 did not immediately supersede the hold target: {res}")
assert o._obj is None, "the stale defend objective was not cleared"
print(f"  hold P6 -> climbed to P5 supersedes at once: OK -> {res[0]}")

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
o._obj_nudge_advice = True         # force the PROGRESS branch (advice alternates)
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
o._obj_nudge_advice = True         # force the PROGRESS branch (advice alternates)
nud = o._obj_nudge(s, you, time.time())
assert nud and nud[0] == "obj_nudge_holding", (
    f"a steady hold produced no check-in nudge: {nud}")
assert "more lap" in nud[1]["laps"]
print(f"  steady hold gets a check-in nudge with laps left: OK -> {nud[1]['laps']}")

print("\nALL PHASE 5 OBJECTIVE CHECKS PASSED")

print("\n===== PHASE 6: AWARENESS ACROSS ALL KINDS + ADVICE =====")


def opm(s):
    order = sorted((d for d in s.all_drivers_data_1[:s.num_cars] if d.place > 0),
                   key=lambda d: d.place)
    return order, {d.place: d for d in order}


# 1. DAMAGE threat evaporates (same awareness as defend, now generalised)
o, s, you = race(my_place=5)
you.place = 5
bh = s.all_drivers_data_1[5]
o._obj = {"kind": "damage", "target_slot": bh.driver_info.slot_id,
          "target_name": "Rossi", "goal_pos": 5, "gap_target": 5.0, "laps": 4,
          "lap0": you.completed_laps, "hud": "Stay ahead of Rossi"}
o.interval = {bh.driver_info.slot_id: 12.0}
order, pm = opm(s)
res = o._obj_check(s, order, pm, time.time())
assert res and res[0] == "obj_met_defend_clear", (
    f"a DAMAGE target whose threat vanished did not resolve: {res}")
print(f"  damage target: threat evaporates -> {res[0]}: OK")

# 2. CHASE goes stale when YOU DROP a place (racing a car that's behind now)
o, s, you = race(my_place=5)
o._obj = {"kind": "position", "target_slot": s.all_drivers_data_1[3].driver_info.slot_id,
          "target_name": "Dubois", "goal_pos": 4, "gap_target": 0.0, "laps": 6,
          "lap0": you.completed_laps, "gap0": 3.0, "hud": "P4 — pass Dubois"}
you.place = 6                                 # you got passed; P4 is now 2 back
order, pm = opm(s)
res = o._obj_check(s, order, pm, time.time())
assert res and res[0] == "obj_withdraw_gone", (
    f"a chase target did not withdraw after you dropped a place: {res}")
print(f"  chase withdraws when you drop a place: OK -> {res[0]}")

# 3. TYRES objective withdrawn when you PIT (fresh rubber)
o, s, you = race(my_place=5)
o._obj = {"kind": "tyres", "target_slot": you.driver_info.slot_id,
          "target_name": "", "goal_pos": 5, "gap_target": None, "laps": 5,
          "lap0": you.completed_laps, "hud": "Nurse the tyres"}
you.in_pitlane = 1
order, pm = opm(s)
res = o._obj_check(s, order, pm, time.time())
assert res and res[0] == "obj_withdraw_pit", (
    f"a tyre-management target survived a pit stop: {res}")
print(f"  tyres target withdrawn on a pit stop: OK -> {res[0]}")

# 4. the engineer gives KIND-SPECIFIC ADVICE, not only "keep it up"
o, s, you = race(my_place=5)
o._obj = {"kind": "tyres", "target_name": "", "_trend": 0, "_laps_left": 4,
          "goal_pos": 5, "laps": 5, "lap0": you.completed_laps}
o._obj_nudge_t = 0.0
o._obj_nudge_advice = False        # force the advice branch this call
nud = o._obj_nudge(s, you, time.time())
assert nud and nud[0] == "obj_advice_tyres", (
    f"a tyre objective gave no tyre-saving advice: {nud}")
print(f"  kind-specific advice fires: OK -> {ENGINEER_LINES[nud[0]][0][:52]}")

# 5. advice ALTERNATES with progress (both get an airing)
o._obj_nudge_t = 0.0
nud2 = o._obj_nudge(s, you, time.time())
assert nud2 and nud2[0] != "obj_advice_tyres", (
    f"nudge did not alternate away from advice: {nud2}")
print(f"  advice alternates with a progress read: OK -> {nud2[0]}")

# 6. every new advice/withdraw pool formats
for _c in ("obj_advice_chase", "obj_advice_defend", "obj_advice_tyres",
           "obj_advice_clean", "obj_advice_leadhome", "obj_withdraw_pit"):
    assert ENGINEER_LINES.get(_c), f"missing {_c}"
    for _l in ENGINEER_LINES[_c]:
        _safe_format(_l, {"drv": "Rossi", "pos": 4, "laps": "2 more laps"})
print("  all advice/withdraw pools format cleanly: OK")

print("\nALL PHASE 6 OBJECTIVE CHECKS PASSED")

print("\n===== PHASE 7: CONSISTENCY OBJECTIVE =====")


def opm3(s):
    order = sorted((d for d in s.all_drivers_data_1[:s.num_cars] if d.place > 0),
                   key=lambda d: d.place)
    return order, {d.place: d for d in order}


# 1. offered in CLEAN AIR (nothing to chase or defend)
o, s, you = race(my_place=6)
vs = you.driver_info.slot_id
pace(o, vs, 92.0)                              # steady pace, some data
o.recent_laps[vs] = [92.0, 92.1, 92.0]
o.interval = {vs: 30.0}                        # nobody near ahead
# nobody near behind either (all cars spread out)
for d in s.all_drivers_data_1[:s.num_cars]:
    if d.driver_info.slot_id != vs:
        o.interval[d.driver_info.slot_id] = 30.0
got = offer(o, s)
assert got and got[0] == "obj_set_consistency", (
    f"clean air did not produce a consistency target: {got}")
assert o._obj["kind"] == "consistency" and o._obj["_ref"] == 92.0
print(f"  clean air -> consistency target: OK -> {o._obj['hud']!r}")

# 2. a lap INSIDE the band counts; a full run is MET
o._obj["laps"] = 2
o._obj["_ok_laps"] = 0
o._obj["_last_lap_n"] = you.completed_laps
you.completed_laps += 1
o.recent_laps[vs].append(92.2)                # within +-0.6s of 92.0 ref
order, pm = opm3(s)
r1 = o._obj_check(s, order, pm, time.time())
assert r1 is None and o._obj["_ok_laps"] == 1, f"good lap not counted: {o._obj.get('_ok_laps')}"
you.completed_laps += 1
o.recent_laps[vs].append(91.9)
r2 = o._obj_check(s, order, pm, time.time())
assert r2 and r2[0] == "obj_met_consistency", f"consistent run not met: {r2}"
print("  two laps in the band -> met: OK")

# 3. a lap OUTSIDE the band fails it
o, s, you = race(my_place=6)
vs = you.driver_info.slot_id
o._obj = {"kind": "consistency", "target_slot": vs, "target_name": "",
          "goal_pos": 6, "gap_target": None, "laps": 4, "_ref": 92.0,
          "_band": 0.6, "_last_lap_n": you.completed_laps, "_ok_laps": 0,
          "lap0": you.completed_laps, "hud": "Consistent laps"}
you.completed_laps += 1
o.recent_laps[vs] = [92.0, 94.5]              # 2.5s off — way outside
order, pm = opm3(s)
res = o._obj_check(s, order, pm, time.time())
assert res and res[0] == "obj_miss_consistency", f"off-band lap not failed: {res}"
print("  a lap outside the band -> missed: OK")

# 4. progress fills with laps kept in the band
o._obj = {"kind": "consistency", "laps": 5, "_ok_laps": 3, "lap0": 0}
prog = o._obj_progress(s, [d for d in s.all_drivers_data_1[:s.num_cars]])
assert prog is not None and abs(prog - 0.6) < 0.01, f"progress wrong: {prog}"
print(f"  progress tracks laps-in-band: OK ({prog:.1f})")

# 5. consistency LOSES CLEAN AIR: a car closes into racing range -> withdraw,
#    because "do consistent laps" is the wrong call once you're racing someone.
o, s, you = race(my_place=6)
vs = you.driver_info.slot_id
o._obj = {"kind": "consistency", "target_slot": vs, "target_name": "",
          "goal_pos": 6, "gap_target": None, "laps": 5, "_ref": 92.0,
          "_band": 0.8, "_last_lap_n": you.completed_laps, "_ok_laps": 1,
          "lap0": you.completed_laps, "hud": "Consistent laps"}
# a car 3s behind is NOT a fight yet — consistency stands
o.interval = {d.driver_info.slot_id: 30.0 for d in s.all_drivers_data_1[:s.num_cars]}
bslot = s.all_drivers_data_1[6].driver_info.slot_id
o.interval[bslot] = 3.0
order, pm = opm3(s)
assert o._obj_check(s, order, pm, time.time()) is None, (
    "consistency withdrew at 3s behind — that's not a fight yet")
# ...but 1.5s behind IS — withdraw and hand over to a race
o.interval[bslot] = 1.5
res = o._obj_check(s, order, pm, time.time())
assert res and res[0] == "obj_withdraw_race", (
    f"consistency did not withdraw with a car 1.5s behind: {res}")
assert o._obj is None
print(f"  consistency: stands at 3s, withdraws at 1.5s (2s gate): OK -> {res[0]}")

print("\nALL PHASE 7 CONSISTENCY CHECKS PASSED")

# PHASE 7 addendum: the clean-air gate is 5s ahead / 4s behind (RaceRoom 5s is
# a big gap; a car behind matters more, so it's tighter).
def _consistency_offered(ahead_gap, behind_gap):
    o, s, you = race(my_place=6)
    vs = you.driver_info.slot_id
    o.recent_laps[vs] = [92.0, 92.0, 92.0]
    for d in s.all_drivers_data_1[:s.num_cars]:
        o.interval[d.driver_info.slot_id] = 30.0
    o.interval[vs] = ahead_gap                        # gap to car ahead
    o.interval[s.all_drivers_data_1[6].driver_info.slot_id] = behind_gap  # P7
    g = offer(o, s)
    return bool(g and g[0] == "obj_set_consistency")

assert not _consistency_offered(4.5, 30.0), "fired with a car 4.5s ahead (<5s)"
assert not _consistency_offered(30.0, 3.5), "fired with a car 3.5s behind (<4s)"
assert _consistency_offered(6.0, 5.0), "did NOT fire in genuine clean air"
print("  clean-air gate holds at 5s ahead / 4s behind: OK")
