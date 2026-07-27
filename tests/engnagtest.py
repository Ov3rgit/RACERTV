"""THE ENGINEER STOPS NAGGING, AND THE BOOTH REMEMBERS THE VIEWER EXISTS.

Three things from one race transcript:

  * FOURTEEN incident-point calls. "1 of 30", "2 of 30", "4 of 30", "5 of 30",
    "9 of 30", "13 of 30", "17 of 30", "18", "19", "20", "21", "22"... The
    guarantee that matters (never be DQ'd by surprise) was implemented as
    "report every point on a 5s cooldown", which is a roll-call, and trains you
    to tune out the one voice that must never become background noise.

  * SIX gap reads to the same car in two and a half minutes -- 4.9s, 4.8s,
    4.3s, 4.1s, 4.6s, 6.1s -- none of which told the driver anything the
    previous one hadn't. The idle-filler block ran every FIFTEEN SECONDS and
    picked its category with a plain random.choice over four or five options.

  * The booth recapped four AI drivers' afternoons and never mentioned the
    viewer's own P4->P3 podium drive. That was correct by the old rules: the
    player was held to the same two-place swing bar as everyone else.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import sys

sys.path.insert(0, r"D:\R3EOverlay")
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])
from overlay_radio import ENC_CD                          # noqa: E402


# ---- 1. incident points: news, not a running tally ----------------------
def points_run(seq, maxpts=30):
    """Feed a rising point tally and collect the ticks he chose to speak on."""
    o = headless_overlay(fake_tts=True)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    s = make_shared(2, ncars=6)
    s.max_incident_points = maxpts
    for i, d in enumerate(s.all_drivers_data_1[:6]):
        d.car_speed, d.place, d.completed_laps = 60.0, i + 1, 5
    for _ in range(8):                         # green flag + intro out of the way
        drive(o, s, 1)
    o._green_at = o._green_t = time.time() - 60.0
    o._racing = True
    o._eng_ip = 0
    o._eng_ip_band = -1
    said = []
    for t, pts in seq:
        s.incident_points = pts
        evts = []
        o._eng_ip_cd = -1e9                    # never blocked by the 5s floor
        o._engineer_events(s, s.all_drivers_data_1[0],
                           {d.place: d for d in s.all_drivers_data_1[:6]},
                           evts, t)
        if any("of %d" % maxpts in e[3] for e in evts):
            said.append(pts)
    return said


# one point every 20s, all the way from 1 to the DQ limit — the transcript's
# shape, but run far enough to cross into the danger zone as well
MAXP = 30
seq = [(1000.0 + i * 20.0, i + 1) for i in range(MAXP)]
said = points_run(seq, maxpts=MAXP)
assert said, "the engineer never mentioned incident points at all"
assert said[0] == 1, "the FIRST point must always be reported: %r" % (said,)

CRIT_FROM = MAXP - max(2, int(MAXP * 0.15))      # left <= 4  ->  ip >= 26
quiet = [p for p in said if p < CRIT_FROM]
assert len(quiet) <= 8, (
    "still a roll-call below the danger zone: %d calls (%r). The transcript "
    "had fourteen." % (len(quiet), quiet))

# ...but EVERY point in the danger zone is still called. This is the whole
# reason the feature exists and must not be traded away for quiet.
crit_said = [p for p in said if p >= CRIT_FROM]
assert crit_said == list(range(CRIT_FROM, MAXP + 1)), (
    "points near the DQ limit are no longer reported one by one: got %r, "
    "expected every point from %d to %d" % (crit_said, CRIT_FROM, MAXP))
print("  incident points: %d calls below the danger zone (was ~22), first=%d, "
      "then every point from %d: OK" % (len(quiet), said[0], CRIT_FROM))

# ---- 2. idle filler is spaced, and a gap read has to be news ------------
assert ENC_CD >= 30.0, (
    "the engineer's idle filler still fires every %.0fs -- that is a line "
    "every half minute for the whole race" % ENC_CD)
print("  idle filler cadence is %.0fs (was 15s): OK" % ENC_CD)

o = headless_overlay(fake_tts=True)
# a gap that barely moves is not worth repeating
assert o._gap_is_news("ahead", 4.9), "the FIRST read must always be news"
o._gap_said["ahead"] = 4.9
for g in (4.8, 4.6, 5.1, 4.1):
    assert not o._gap_is_news("ahead", g), (
        "a %.1fs gap was called news after saying 4.9s -- this is the "
        "'4.9, 4.8, 4.3, 4.1, 4.6' sequence from the transcript" % g)
assert o._gap_is_news("ahead", 6.5), "a gap that really moved was suppressed"
assert o._gap_is_news("ahead", 2.0), "a gap that closed right up was suppressed"
print("  a gap read must actually have moved to be repeated: OK")

# close-quarters gaps are held to a TIGHTER bar -- a tenth matters at 0.8s
o2 = headless_overlay(fake_tts=True)
o2._gap_is_news("behind", 0.8)
o2._gap_said["behind"] = 0.8
assert o2._gap_is_news("behind", 1.4), (
    "at close quarters a 0.6s change is a real change and must be sayable")
print("  ...and the threshold scales with the size of the gap: OK")

# ---- 3. the booth tells the VIEWER's story ------------------------------
def story(net_places, mine_slot=0, rivals_move=True):
    """Player moved `net_places` (positive = climbed).

    `rivals_move` gives the AI drivers real races too. Without competition the
    player is the ONLY eligible candidate and any "is he picked often enough?"
    check passes trivially at 100% — which is exactly what a first version of
    this test did.
    """
    o = headless_overlay(fake_tts=True)
    o._race_story = {}
    o.grid_place = {}
    s = make_shared(2, ncars=8)
    order = []
    for i, d in enumerate(s.all_drivers_data_1[:8]):
        d.place = i + 1
        d.completed_laps = 8
        order.append(d)
    for i, d in enumerate(order):
        sl = d.driver_info.slot_id
        swing = (3 if rivals_move else 0)
        o.grid_place[sl] = d.place + swing
        o._race_story[sl] = {"best": d.place, "worst": d.place + swing,
                             "now": d.place}
    me = order[mine_slot]
    msl = me.driver_info.slot_id
    o.grid_place[msl] = me.place + net_places
    o._race_story[msl] = {"best": me.place, "worst": me.place + net_places,
                          "now": me.place}
    o._story_told = set()
    return o, order, msl


# a ONE-place gain: below the old two-place bar, so the player was invisible
o, order, msl = story(1)
picks = [o._story_pick(order, msl) for _ in range(200)]
mine = [p for p in picks if p is not None and p.driver_info.slot_id == msl]
assert mine, (
    "a one-place move by the player still produces no story -- the booth "
    "would recap AI drivers and skip the viewer's own race")
print("  a modest one-place player move is now a story: OK (%d/200 picks)"
      % len(mine))

# with the player eligible they should usually, but NOT always, be the subject
o, order, msl = story(3)
picks = [o._story_pick(order, msl) for _ in range(400)]
mine = sum(1 for p in picks if p is not None and p.driver_info.slot_id == msl)
assert mine > len(picks) * 0.4, (
    "the player is eligible but only picked %d/400 times -- still buried "
    "among the AI drivers" % mine)
assert mine < len(picks) * 0.95, (
    "the booth now talks about the player %d/400 times and has stopped "
    "noticing the rest of the grid" % mine)
print("  player usually but not always the subject: OK (%d/400)" % mine)

# an ENTIRELY static player must still not manufacture a story
o, order, msl = story(0)
picks = [o._story_pick(order, msl) for _ in range(80)]
mine = [p for p in picks if p is not None and p.driver_info.slot_id == msl]
assert not mine, (
    "a player who has not moved a single place got a race-story recap -- "
    "there is nothing to tell")
print("  a player who never moved gets no invented story: OK")

print("\nENGINEER-NAG CHECKS PASSED")
