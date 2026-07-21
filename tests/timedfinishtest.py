"""TIMED-RACE FINISH + POST-FLAG SILENCE (two things a real Sepang timed race
exposed):

  * the booth called the chequered flag the instant the CLOCK hit zero, while
    the leader still had a full lap to run — a timed race ends when the leader
    TAKES the flag, not when time expires.
  * the moment the flag fell, the rival drivers all keyed the mic celebrating,
    and the pile-up buried the engineer's finish call and the commentators'
    wrap. No driver audio should play once the race is over.

Both are driven by _leader_finished, which this proves is timed-race aware, and
by the race_over gate on rival radio.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import os
import sys

sys.path.insert(0, r"D:\R3EOverlay")
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "smoke.py")).read()
exec(_src.split('run_session("RACE"')[0])

NON_DRIVER = ("COMMENTATOR", "PUNDIT", "ENGINEER")


def timed(ncars=8, rem=1200.0):
    o = headless_overlay(fake_tts=True)
    s = make_shared(2, ncars=ncars)
    s.number_of_laps = -1                 # TIMED
    s.session_time_duration = 1200.0
    s.session_time_remaining = rem
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    for i in range(ncars):
        d = s.all_drivers_data_1[i]
        d.car_speed = 55.0
        d.place = i + 1
        d.completed_laps = 8
    return o, s


print("===== 1. a timed race is NOT finished when the clock hits zero =====")
o, s = timed()
leader = s.all_drivers_data_1[0]
# clock has expired and the white flag is out — the leader is ON the final lap
s.session_time_remaining = 0.0
s.flags.white = 1
s.flags.checkered = 0
s.session_phase = 5
assert not o._leader_finished(s, leader), (
    "the race was called finished at time-zero, with the final lap still to run")
print("  time-up + white flag (final lap running) is NOT the finish: OK")

# even if the session phase / checkered flag flip at time-zero, a TIMED race is
# only over once the leader crosses — those flags can't be trusted here
s.session_phase = 6
s.flags.checkered = 1
assert not o._leader_finished(s, leader), (
    "session_phase/checkered at time-zero wrongly ended the timed race early")
print("  session_phase 6 / checkered at time-zero is still NOT the finish: OK")

# now the leader actually takes the flag
leader.finish_status = 1
assert o._leader_finished(s, leader), "the leader crossing did not register as the finish"
print("  ...only the leader crossing the line finishes it: OK")


print("\n===== 1b. the captured-final-lap fallback also finishes it =====")
o, s = timed()
leader = s.all_drivers_data_1[0]
o._timed_flap = leader.completed_laps          # final lap began on this lap
assert not o._leader_finished(s, leader), "finished before the final lap completed"
leader.completed_laps += 1                     # leader completes the final lap
assert o._leader_finished(s, leader), "completing the final lap did not finish it"
print("  leader completing the captured final lap finishes it: OK")


print("\n===== 1c. a LAP race still finishes on the flag/phase =====")
o2 = headless_overlay(fake_tts=True)
s2 = make_shared(2, ncars=8)
s2.number_of_laps = 10
ld = s2.all_drivers_data_1[0]
ld.place = 1
ld.completed_laps = 9
assert not o2._leader_finished(s2, ld), "lap race finished a lap early"
s2.flags.checkered = 1                          # flag shown in a lap race
assert o2._leader_finished(s2, ld), "lap race did not finish on the checkered flag"
print("  lap race: checkered flag finishes it (phase/flag trusted): OK")


print("\n===== 2. no rival driver audio once the race is over =====")
o, s = timed()
for _ in range(8):
    drive(o, s, 1)
o._green_t = time.time() - 60.0
o._green_at = time.time() - 60.0
# the leader takes the flag — race over
s.all_drivers_data_1[0].finish_status = 1
assert o._leader_finished(s, s.all_drivers_data_1[0])
before = len(o.tts.spoken)
# keep shuffling the midfield to give the rivals every reason to key the mic
for k in range(12):
    a = s.all_drivers_data_1[3]
    b = s.all_drivers_data_1[4]
    a.place, b.place = b.place, a.place
    drive(o, s, 1)
rival_after = [(p, t) for p, t in o.tts.spoken[before:] if p not in NON_DRIVER]
assert not rival_after, (
    "rival drivers spoke after the race finished — that space is for the "
    "engineer and commentators:\n  " + "\n  ".join(f"{p}: {t}" for p, t in rival_after))
print("  rival radio is silent after the flag: OK")

print("\nTIMED-FINISH + POST-FLAG SILENCE CHECKS PASSED")
