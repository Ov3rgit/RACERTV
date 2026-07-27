"""THE BOOTH MUST NOT SAY THE SAME THING TWICE IN QUICK SUCCESSION.

Reported off a race transcript: seven exact-duplicate lines in one race, plus
fifteen name-free "someone's gone off!" alerts, two of them four seconds apart.

Instrumenting a race found three separate ways a line could come back:

  * The `analysis` filler pool supplies almost all booth colour (516 of 538
    lines in an instrumented run). Its 77-line deck therefore reshuffles every
    few minutes and begins dealing the same lines again.
  * The COMMENTATOR and the PUNDIT keep SEPARATE shuffle-bags for the same
    pool, so each could deal the same line independently of the other.
  * 31 lines exist in more than one pool, each pool with its own bag.

All three sound identical to a listener. _pick now keeps a global recency map
over the line TEXT, shared by every pool, key and persona, with a window at
least as long as the pool being dealt -- a shorter window let a line become
legal again before its own deck had finished cycling, which is how a 77-line
pool still repeated itself.

Measured on the pre-fix code, the closest repeat in a 533-line race was FOUR
lines apart, with 14 repeats inside 30 lines. After: 62 apart and none inside
30.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import collections
import sys

sys.path.insert(0, r"D:\R3EOverlay")
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])
import r3e_overlay as RO                                  # noqa: E402
from r3e_overlay import RECENT_LINE_WINDOW                # noqa: E402


def run_race(ticks=400, ncars=10):
    """A long green-flag race. Nothing dramatic happens, which is deliberate:
    it is the FILLER layer that repeats, and this maximises it."""
    o = headless_overlay(fake_tts=True)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    s = make_shared(2, ncars=ncars)
    s.number_of_laps = 0
    s.session_time_remaining = 600.0
    for i, d in enumerate(s.all_drivers_data_1[:ncars]):
        d.car_speed = 60.0
        d.place = i + 1
        d.completed_laps = 3
    for _ in range(ticks):
        drive(o, s, 1)
        s.session_time_remaining -= 1.0
    return o, [t for _p, t in o.tts.spoken]


o, aired = run_race()
assert len(aired) > 200, "not enough commentary to judge repetition (%d)" % len(aired)

pos = collections.defaultdict(list)
for i, t in enumerate(aired):
    pos[t].append(i)
gaps = sorted(b - a for ix in pos.values() for a, b in zip(ix, ix[1:]))

# ---- 1. nothing repeats CLOSE together ----------------------------------
assert gaps, "no line aired twice at all -- suspiciously clean, check the test"
assert gaps[0] >= 30, (
    "a line was repeated only %d lines after the last time it aired (pre-fix "
    "this was 4). Closest offenders: %r"
    % (gaps[0], [t[:50] for t, ix in pos.items()
                 if any(b - a == gaps[0] for a, b in zip(ix, ix[1:]))][:2]))
print("  closest repeat is %d lines apart (was 4 pre-fix): OK" % gaps[0])

tight = sum(1 for g in gaps if g < 30)
assert tight == 0, "%d repeats landed within 30 lines of each other" % tight
print("  zero repeats inside 30 lines (was 14 pre-fix): OK")

# ---- 2. back-to-back is impossible whatever the pool --------------------
for a, b in zip(aired, aired[1:]):
    assert a != b, "the booth said the same line twice in a row: %r" % a[:60]
print("  never the same line twice in a row: OK")

# ---- 3. the guard spans PERSONAS, not just pools ------------------------
# The COMMENTATOR and PUNDIT bags are separate; the recency map is not. Any
# line aired by one voice must not come straight back from the other.
by_line = collections.defaultdict(set)
for p, t in o.tts.spoken:
    by_line[t].add(p)
shared = {t for t, ps in by_line.items() if len(ps) > 1}
for t in shared:
    ix = pos[t]
    close = [b - a for a, b in zip(ix, ix[1:]) if b - a < 30]
    assert not close, (
        "a line aired by both voices repeated %d lines apart -- the recency "
        "map is not shared across personas: %r" % (close[0], t[:50]))
print("  lines shared by both voices still respect the window: OK (%d shared)"
      % len(shared))

# ---- 4. a SMALL pool must not deadlock into silence ---------------------
# When every candidate is recent the least recently used one is dealt, rather
# than returning nothing. A 2-line pool exercises that immediately.
o2 = headless_overlay(fake_tts=True)
small = ["Only line A.", "Only line B."]
got = [o2._pick(small, ("TEST", "small")) for _ in range(12)]
assert all(g in small for g in got), "small pool returned something unexpected"
assert len(set(got)) == 2, "a 2-line pool stopped alternating: %r" % (set(got),)
for a, b in zip(got, got[1:]):
    assert a != b, "a 2-line pool repeated back-to-back instead of alternating"
print("  a 2-line pool alternates rather than starving: OK")

# a 1-line pool is always that line, no crash
assert o2._pick(["Solo."], ("TEST", "one")) == "Solo."
assert o2._pick([], ("TEST", "none")) == ""
print("  1-line and empty pools handled: OK")

# ---- 5. the window is at least a full trip through the pool -------------
# A window shorter than the pool lets a line come back before its own deck has
# cycled -- the specific reason a 77-line pool still repeated itself.
big = ["line %02d" % i for i in range(RECENT_LINE_WINDOW + 25)]
o3 = headless_overlay(fake_tts=True)
seq = [o3._pick(big, ("TEST", "big")) for _ in range(len(big))]
assert len(set(seq)) == len(big), (
    "dealing a %d-line pool %d times produced only %d distinct lines -- the "
    "window is shorter than the pool"
    % (len(big), len(big), len(set(seq))))
print("  a pool longer than the window still cycles fully first: OK (%d lines)"
      % len(big))

# ---- 6. the name-free incident sting is rate limited --------------------
# It fires from two independent paths (an off-track report and a yellow flag)
# that had no shared cooldown, so a busy race stacked them -- the transcript
# had two four seconds apart and fifteen in one race.
import tts as _t                                          # noqa: E402
assert _t.Tts._STING_MIN_GAP.get("alert"), (
    "the generic incident alert has no minimum spacing")
for one_shot in ("lightsout", "victory"):
    assert one_shot not in _t.Tts._STING_MIN_GAP, (
        "%r is a one-shot signature moment and must never be rate limited"
        % one_shot)
print("  alert stings are spaced %.0fs; lightsout/victory never gated: OK"
      % _t.Tts._STING_MIN_GAP["alert"])

print("\nREPETITION CHECKS PASSED")
