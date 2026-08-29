"""THE RACE CLOCK — a timed race needs to say how much racing is left.

Reported by a viewer running 25-minute races: there is a lap counter in the
chyron and nothing else, so a timed race shows a lap number that tells you
nothing about how far through it you are.

Two things were wrong. The header only reached for the remaining time when
the lap count was absent AND the session was live — so a timed REPLAY, the
case that got reported, never showed a clock at all. And when it did show
one it formatted it with fmt_time(), which is the LAP-TIME format: a race
clock reading "12:38.417", counting milliseconds down from twenty-five
minutes.

The suspicion of replays was not unfounded, so the value is now VERIFIED
rather than either trusted or refused: it has to be in range and it has to
have been seen counting down before it reaches the screen.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import sys

sys.path.insert(0, r"D:\R3EOverlay")
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])

from overlay_draw import DrawMixin


class Head(DrawMixin):
    """Just enough object to exercise the clock helpers."""
    def __init__(self):
        self._clock_prev = None
        self._clock_seen = False


def timed_session(rem=1500.0, dur=1500.0):
    s = make_shared(2, ncars=6)
    s.number_of_laps = 0
    s.session_length_format = 0          # TimeBased
    s.session_time_duration = dur
    s.session_time_remaining = rem
    for i, d in enumerate(s.all_drivers_data_1[:6]):
        d.place, d.completed_laps = i + 1, 3
    return s


# ---- 1. it reads as a clock, not as a lap time -------------------------
assert DrawMixin._fmt_clock(1500.0) == "25:00", DrawMixin._fmt_clock(1500.0)
assert DrawMixin._fmt_clock(758.4) == "12:38"
assert DrawMixin._fmt_clock(59.9) == "0:59"
assert DrawMixin._fmt_clock(0.0) == "0:00"
assert DrawMixin._fmt_clock(-5.0) == "0:00", "a negative clock must not render"
assert DrawMixin._fmt_clock(3725.0) == "1:02:05", "endurance lengths need hours"
# the old behaviour, for contrast: this is what was on screen
assert R.fmt_time(758.4).startswith("12:38."), "fmt_time is a lap-time format"
print("  [clock] renders as M:SS / H:MM:SS, not as a lap time: OK")


# ---- 2. a lap race is untouched ----------------------------------------
h = Head()
s = timed_session()
s.number_of_laps = 10
s.session_length_format = 1              # LapBased
assert not h._is_timed(s), "a lap race was treated as timed"
assert not h._race_clock_ok(s), "a lap race tried to show a race clock"
print("  [clock] a lap race still shows only its lap counter: OK")


# ---- 3. the clock must be SEEN counting down before it is shown --------
h = Head()
s = timed_session(rem=1500.0)
assert not h._race_clock_ok(s), (
    "the very first reading went straight on screen — nothing had yet shown "
    "that this field was a working countdown")
s.session_time_remaining = 1499.5
assert h._race_clock_ok(s), "a clock observed counting down was still refused"
print("  [clock] one observed tick down is enough to trust it: OK")


# ---- 4. a field that never moves never reaches the screen --------------
# This is what the old code was afraid of in replays, and the reason it
# refused to show a clock there at all.
h = Head()
s = timed_session(rem=900.0)
for _ in range(20):
    h._race_clock_ok(s)                  # frozen value, tick after tick
assert not h._race_clock_ok(s), (
    "a frozen time-remaining field was put on screen as a live race clock")
print("  [clock] a frozen field is never shown: OK")


# ---- 4b. ...and an out-of-range one is rejected outright ---------------
h = Head()
s = timed_session(rem=99999.0, dur=1500.0)
assert not h._race_clock_ok(s), "a nonsense remaining time was shown"
s = timed_session(rem=-3.0, dur=1500.0)
assert not h._race_clock_ok(s), "a negative remaining time was shown"
print("  [clock] out-of-range values are rejected: OK")


# ---- 5. a REPLAY gets a clock too, which is the reported case ----------
h = Head()
s = timed_session(rem=1500.0)
s.game_in_replay = 1
h._race_clock_ok(s)
s.session_time_remaining = 1498.0
assert h._race_clock_ok(s), (
    "a timed REPLAY still showed no clock — refusing replays outright is "
    "what left 25-minute races with nothing but a lap number on screen")
print("  [clock] a timed replay shows a verified clock: OK")


# ---- 6. scrubbing/restarting drops it until it proves itself again -----
s.session_time_remaining = 1500.0        # jumped back up
assert not h._race_clock_ok(s), (
    "the clock jumped upward — a scrub or a new session — and was still "
    "trusted, so a stale number sat there looking authoritative")
s.session_time_remaining = 1499.0
assert h._race_clock_ok(s), "the clock never recovered after a scrub"
print("  [clock] a scrub drops it, and it re-earns its place: OK")


# ---- 7. time up is not the end of the race -----------------------------
# RaceRoom runs a timed race to the end of the leader's current lap, so 0:00
# on the clock is a lap and a half before the flag.
h = Head()
s = timed_session(rem=20.0)
h._race_clock_ok(s)
s.session_time_remaining = 19.0
h._race_clock_ok(s)
s.session_time_remaining = 0.0
assert not h._race_clock_ok(s), "a zeroed clock is not a clock to display"
assert h._timed_over(s), (
    "the clock ran out and the header had nothing to show — 0:00 for a lap "
    "and a half would be a lie and a blank panel would be worse")
print("  [clock] time-up becomes FINAL LAP, not 0:00: OK")


# ---- 8. the header actually uses all of it -----------------------------
src_hdr = open(r"D:\R3EOverlay\overlay_draw.py", encoding="utf-8").read()
hdr = src_hdr.split("def draw_header(")[1].split("\n    def ")[0]
assert "_race_clock_ok" in hdr and "_fmt_clock" in hdr, (
    "draw_header does not use the verified clock")
assert "R.fmt_time(s.session_time_remaining)" not in hdr, (
    "the header still formats the race clock as a lap time")
assert 'sub_prog = f"LAP {lead_laps + 1}"' in hdr, (
    "the lap number was dropped from timed races — the clock is the headline "
    "but which lap the leader is on still belongs on screen")
assert "_timed_over" in hdr, "the header has no time-up state"
print("  [clock] the header is wired to all of it: OK")


print("\nRACE CLOCK: ALL OK")
