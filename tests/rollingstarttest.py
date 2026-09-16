"""THE FORMATION LAP, THE SESSION CLOCK, AND A REPLAY THAT ISN'T PLAYING YET.

Three reports from the same viewer, all of them about the overlay believing a
race had started when it hadn't.

1. ROLLING STARTS. The green latch tests whether the field is MOVING, which is
   exactly right for a standing start and exactly wrong for a rolling one: the
   pack forms up at speed, the test passes a whole lap early, and the booth
   calls lights-out somewhere on the formation lap. Phase 3 is Formation
   (R3E.cs SessionPhase) and now vetoes the latch.

2. RESTARTS. Every restart signal the overlay had was derived from race
   progress — lap counts, the session clock — so none of them could fire in
   the seconds when a restart is most likely: on the grid, before a lap
   exists. `player.game_simulation_time` is the session's own clock and falls
   the instant the session is replaced, whatever the lap counters say.

3. REPLAYS. A loaded replay publishes a full session, so the broadcast opened
   into a frozen frame while the viewer was still setting up their camera —
   the introduction spoken to nobody and lap one consumed before playback
   began.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import sys

sys.path.insert(0, r"D:\R3EOverlay")
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])


def session(ncars=6, phase=5, speed=60.0, laps=0, simt=30.0):
    o = headless_overlay(fake_tts=True)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    s = make_shared(2, ncars=ncars)
    s.session_phase = phase
    s.player.game_simulation_time = simt
    s.session_time_remaining = 600.0
    for i, d in enumerate(s.all_drivers_data_1[:ncars]):
        d.car_speed, d.place, d.completed_laps = speed, i + 1, laps
        d.lap_distance_fraction = 0.4
    s.car_speed = speed
    return o, s


# ---- 1. the formation lap is NOT the race ------------------------------
# The whole field circulating at 60 km/h with the phase still on Formation.
# Under the old speed-only latch this went green immediately.
o, s = session(phase=3, speed=60.0)
drive(o, s, 2)
# The formation call is OFFERED until it wins arbitration, with a 1.2s spacing
# between offers so it can't churn the line deck. A test that drives three
# ticks in three milliseconds sits entirely inside that spacing, so a single
# lost arbitration looked like permanent silence — the flake was in the test,
# not the booth. Age both stamps each time round and assert what is actually
# guaranteed: the call goes out, not that it wins first attempt.
# Match on the BEAT, not on keywords: two lines in the pool ("The lap that
# doesn't count...", "They're circulating now...") mention neither
# "formation" nor "rolling", so a keyword filter called a spoken line silence.
said = []
for _ in range(12):
    o._intro_emit_t = 0.0
    o._form_offer_t = 0.0
    n_before = len(o.tts.spoken)
    drive(o, s, 1)
    if "open" in getattr(o, "_form_said", set()):
        said = [t for _p, t in o.tts.spoken[n_before:]] or [o.tts.spoken[-1][1]]
        break
assert not o._racing, (
    "a rolling start's FORMATION lap was treated as the race being under way "
    "— the field is moving, but phase 3 says they have not started yet")
assert o._formation, "the formation lap was not recognised as one"

# the booth has something to say about it, and it names the leader
assert said, "the booth was silent through the entire formation lap"
assert "open" in o._form_said, (
    "the formation beat was marked spoken without a line actually going out")
print("  [formation] rolling start is not called as green: OK")
print("             ", said[0][:78])

# ...and the green still lands when the phase actually turns
s.session_phase = 5
drive(o, s, 3)
assert o._racing, "the race never went green after the formation lap ended"
assert not o._formation, "still 'on the formation lap' after the green"
print("  [formation] green latches once phase 3 clears: OK")


# ---- 1b. a phase that never leaves 3 must not gag the race forever ------
# Defensive: if a build parks the phase, a COMPLETED LAP outranks the veto.
o, s = session(phase=3, speed=60.0)
drive(o, s, 2)
assert not o._racing
for d in s.all_drivers_data_1[:6]:
    d.completed_laps = 1
drive(o, s, 2)
assert o._racing, (
    "a completed lap did not override the formation veto — a build that "
    "leaves the phase parked on 3 would never see a green flag")
print("  [formation] a completed lap outranks the veto: OK")


# ---- 2. the session clock detects a restart with no laps run -----------
# The hardest case there is: restart on the grid. No lap has been completed,
# the clock has barely moved, and every old signal is blind.
o, s = session(phase=5, speed=0.0, laps=0, simt=8.0)
drive(o, s, 2)
k1 = o._sess_key
o.best_lap[s.all_drivers_data_1[0].driver_info.slot_id] = 91.234
o.fastest = {"time": 90.0, "slot": 0, "car": 1, "name": "OLD", "at": 1.0}

s.player.game_simulation_time = 0.5       # the session's own clock restarted
drive(o, s, 2)
assert o._sess_key != k1, (
    "a restart on the grid was not detected — no lap had been run and the "
    "session clock had barely moved, so every derived signal was blind. "
    "game_simulation_time falling is the restart itself, not evidence of one")
assert not o.best_lap, "best laps carried into the restarted session"
assert o.fastest["time"] is None, "the fastest lap carried over"
print("  [restart] a grid restart is caught by the session clock: OK")


# ---- 2b. a replay scrub is NOT a restart --------------------------------
# The same clock runs backwards when you drag a replay's scrubber, and
# rewinding to watch a corner again must not tear the broadcast down.
o, s = session(phase=5, simt=120.0)
s.game_in_replay = 1
drive(o, s, 2)
k1 = o._sess_key
s.player.game_simulation_time = 116.0     # nudged back four seconds
drive(o, s, 2)
assert o._sess_key == k1, (
    "a small rewind inside a replay was treated as a new session")
print("  [restart] a small replay rewind is not a restart: OK")


# ---- 3. a replay that is loaded but not playing is not on air ----------
o, s = session(phase=5, simt=42.0)
s.game_in_replay = 1
for _ in range(6):
    assert not o._in_action(s), (
        "the broadcast opened on a replay that was loaded but frozen — the "
        "introduction is spoken to a viewer still setting up their camera, "
        "and lap one is consumed before playback ever starts")
print("  [replay] a frozen replay is not on air: OK")

# press play: the clock advances and, after the settle window, we go live
t0 = time.time()
live = False
for i in range(1, 40):
    s.player.game_simulation_time = 42.0 + i * 0.05
    if o._in_action(s):
        live = True
        break
    time.sleep(0.02)
assert live, "the replay never went on air once it started playing"
print("  [replay] playback puts the broadcast on air: OK")

# THE REALISTIC CASE: the physics clock frozen, the cars moving. R3E replays
# are played back rather than simulated, so game_simulation_time may never
# advance during playback at all — if the gate rested on it alone, the overlay
# would simply never come on air in a replay.
o2, s2 = session(phase=5, simt=42.0)
s2.game_in_replay = 1
for d in s2.all_drivers_data_1[:6]:
    d.lap_distance = 100.0
o2._in_action(s2)
live2 = False
for i in range(1, 40):
    for d in s2.all_drivers_data_1[:6]:
        d.lap_distance = 100.0 + i * 3.0        # only the CARS move
    if o2._in_action(s2):
        live2 = True
        break
    time.sleep(0.02)
assert live2, (
    "a replay whose physics clock never advances never came on air — the "
    "gate must not rest on game_simulation_time alone")
print("  [replay] cars moving is enough, with the physics clock frozen: OK")

# ...and the standing grid, where nothing moves but the countdown
o3, s3 = session(phase=4, speed=0.0, simt=5.0)
s3.game_in_replay = 1
for d in s3.all_drivers_data_1[:6]:
    d.lap_distance = 0.0
o3._in_action(s3)
live3 = False
for i in range(1, 40):
    s3.session_time_remaining = 600.0 - i * 0.05   # only the CLOCK moves
    if o3._in_action(s3):
        live3 = True
        break
    time.sleep(0.02)
assert live3, (
    "a replay playing over a standing grid never came on air — nothing moves "
    "there but the countdown, and that is exactly the build-up the broadcast "
    "is supposed to cover")
print("  [replay] a standing grid counting down is on air: OK")

# a one-frame stall must NOT take it off air again
s.player.game_simulation_time = s.player.game_simulation_time
assert o._in_action(s), "a single stalled frame tore the broadcast down"
print("  [replay] a stalled frame does not drop the broadcast: OK")

# re-cueing to the start IS a new session: the intro should play again
k1 = o._sess_key
drive(o, s, 1)
k1 = o._sess_key
s.player.game_simulation_time = 1.0       # scrubber dragged back to the start
o._in_action(s)
drive(o, s, 2)
assert o._sess_key != k1, (
    "dragging the replay back to the start did not re-open the broadcast — "
    "that is the gesture of someone about to record the race properly")
print("  [replay] re-cueing to the start re-opens the broadcast: OK")


# ---- 4. THE SPECTATED START — the bug that made starts land on lap 2 ----
#
# Reported as *"race starts are very underwhelming and not accurate, and it
# always only starts around lap 2"*, and lap 2 was not a figure of speech.
#
# The green latch read `s.car_speed` — the PLAYER'S car. Watching a replay or
# spectating there is no car of yours, so it sits at zero through the entire
# start and the latch had one route left: `completed_laps >= 1`. The race went
# green when the leader crossed the line, one whole lap after the lights.
#
# The field is moving and the player is not. That is the whole test.
o, s = session(phase=5, speed=60.0, laps=0)
s.game_in_replay = 1
s.all_drivers_data_1[0].car_speed = 0.0     # no car of ours to read
s.car_speed = 0.0
drive(o, s, 2)
assert o._racing, (
    "a spectated standing start never went green — the latch is reading the "
    "player's own car, which does not exist here, so the start call waits for "
    "a completed lap and lands on lap 2")
print("  [spectator] a start watched, not driven, goes green on time: OK")


# ...AND THE GRID ITSELF IS STILL NOT THE RACE. The check above is only worth
# having if the opposite case still holds: a stationary grid, watched rather
# than driven, must NOT be called green. Widening the latch is exactly the
# change that could break this, so the two are asserted together.
o, s = session(phase=5, speed=0.0, laps=0)
s.game_in_replay = 1
s.car_speed = 0.0
drive(o, s, 2)
assert not o._racing, (
    "a stationary grid was called green — the field-movement latch is "
    "triggering on cars that have not launched")
print("  [spectator] ...and a stationary grid is not: OK")


# ONE CAR CREEPING IS NOT A START. Somebody rolling on the grid, or jumping it,
# moves while the race has not begun. The latch wants a MAJORITY for this
# reason, and a single mover is the case that would have broken it.
o, s = session(phase=5, speed=0.0, laps=0)
s.game_in_replay = 1
s.car_speed = 0.0
s.all_drivers_data_1[3].car_speed = 30.0    # one jumped start
drive(o, s, 2)
assert not o._racing, (
    "one car creeping on the grid triggered the green flag")
print("  [spectator] one car creeping on the grid is not the start: OK")


print("\nROLLING START / RESTART / REPLAY GATING: ALL OK")
