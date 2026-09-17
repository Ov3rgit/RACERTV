# -*- coding: utf-8 -*-
"""A TOP-FIVE PASS IS CALLED, ONCE, IN RANK ORDER -- AND ONLY IF IT STUCK.

Reported from a video a user shared: *"the person overtook the position for
P1 and the booth didnt call it, also some overtakes are extremely delayed, the
highest ranking overtake should get called, AND especially if its in the top
5"*. And then: *"the overtake must be held to count, so an additional line of
dialogue if the position is pass and repass would be 'And Overboy is still
holding onto P1 somehow!!'"*.

MEASURED BEFORE THE FIX, with the booth busy: a P2, P3 or P5 pass built its
candidate, was deferred into a one-call hold with a four-second expiry, and
aired ZERO lines. P4 and P5 carried priority 2 -- the same as a pass for P15.

DETERMINISTIC ON PURPOSE. This drives `_resolve_top_passes` with positions
set by hand and a clock passed in, rather than sleeping and hoping. Several of
this project's randomised, timing-based tests have gone flaky; a guarantee is
only a guarantee if its test cannot pass by luck.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import sys

sys.path.insert(0, r"D:\R3EOverlay")
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])

from lines import COMMENTARY_LINES                        # noqa: E402

fails = []


def check(ok, what, detail=""):
    print("  [%s] %s%s" % ("OK" if ok else "FAIL", what,
                           ("  " + str(detail)) if detail else ""))
    if not ok:
        fails.append(what)


def booth():
    """An overlay whose booth is BUSY, recording stings and lines."""
    o = headless_overlay(fake_tts=True)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    o._pass_pending, o._defended = {}, {}
    o._sess_gen = 0
    o._incident_until = 0.0
    o.cplace = {}
    o.aired, o.stung = [], []
    rs = o.tts.speak
    o.tts.speak = lambda t, p, **k: (o.aired.append(t), rs(t, p, **k))[1]
    o.cuts = []
    o.tts.sting = (lambda g="alert", p="PUNDIT", on_play=None, cut=True:
                   (o.stung.append(g), o.cuts.append(cut), True)[2])
    o.tts._pending = lambda: 5            # a commentary-dense moment
    return o


H = 1.5          # BoothMixin.PASS_HOLD, asserted below so this cannot drift


print("\n0. THE CONSTANTS THIS FILE ASSUMES")
check(headless_overlay().PASS_HOLD == H, "a pass must hold for 1.5s")
check(headless_overlay().TOP_PASS == 5, "the guarantee covers P1 to P5")


print("\n1. A HELD PASS IS CALLED, EVEN WITH THE BOOTH BUSY")
for pos in (2, 3, 4, 5):
    o = booth()
    o.cplace = {10: pos, 20: pos + 1}      # 10 passed 20 for P{pos}
    o._pass_hold(10, 20, pos, "overtake", "Attacker", "Defender", 100.0, {})
    o._resolve_top_passes(100.0 + H * 0.5)
    check(not o.aired, "P%d: nothing is called before the pass has held" % pos)
    o._resolve_top_passes(100.0 + H + 0.05)
    check(len(o.aired) == 1 and "overtake" in o.stung,
          "P%d: once it holds, it is called WITH a sting" % pos,
          o.aired[:1])


print("\n2. PASS, THEN STRAIGHT BACK: THE DEFENCE, NOT THE PASS")
for pos in (1, 3):
    o = booth()
    o.cplace = {10: pos, 20: pos + 1}
    o._pass_hold(10, 20, pos, "overtake", "Attacker", "Overboy", 100.0, {})
    # the defender takes it back inside the hold -- and detection registers
    # that retake as a pass of its own, exactly as it does in a live race
    o.cplace = {10: pos + 1, 20: pos}
    o._pass_hold(20, 10, pos, "overtake", "Overboy", "Attacker", 100.6, {})
    o._resolve_top_passes(100.6)
    o._resolve_top_passes(100.6 + H * 3)   # long after both would have held
    holding = [t for t in o.aired if "Overboy" in t]
    check(len(o.aired) == 1 and holding,
          "P%d: exactly one line, and it names the car that kept its place"
          % pos, o.aired)
    check("overtake" not in o.stung,
          "P%d: no pass sting for a pass that never stuck" % pos, o.stung)


print("\n3. HIGHEST PLACE FIRST")
# Two top-five moves resolving on the same tick. The pass for the lead must
# not be queued behind a pass for fifth.
o = booth()
o.cplace = {10: 5, 20: 6, 30: 1, 40: 2}
o._pass_hold(10, 20, 5, "overtake", "FifthMan", "SixthMan", 100.0, {})
o._pass_hold(30, 40, 1, "leadchange", "NewLeader", "OldLeader", 100.0, {},
             lead=True)
o._resolve_top_passes(100.0 + H + 0.05)
check(len(o.aired) == 2, "both passes are called", len(o.aired))
if len(o.aired) == 2:
    check("NewLeader" in o.aired[0],
          "the lead change is called BEFORE the pass for fifth", o.aired)


print("\n4. A STALE PASS IS DROPPED, NOT CALLED LATE")
# The order moved on underneath it -- the passer is no longer in the place it
# took. A call about a position that no longer describes the race is worse
# than no call at all.
o = booth()
o.cplace = {10: 3, 20: 4}
o._pass_hold(10, 20, 3, "overtake", "Attacker", "Defender", 100.0, {})
o.cplace = {10: 7, 20: 9}                  # both have since fallen away
o._resolve_top_passes(100.0 + H * 5)
check(not o.aired and not o._pass_pending,
      "a pass that no longer matches the order is quietly dropped", o.aired)


print("\n5. A NEW SESSION FORGETS THE OLD ONE'S PASSES")
o = booth()
o.cplace = {10: 2, 20: 3}
o._pass_hold(10, 20, 2, "overtake", "Attacker", "Defender", 100.0, {})
o._sess_gen = 1                            # restart, new race
o._resolve_top_passes(100.0 + H + 0.05)
check(not o.aired, "a held pass from the last race does not air on this grid")


print("\n6. THE WORDS")
_pool = COMMENTARY_LINES.get("still_holding") or []
check(any("still holding onto P{pos} somehow" in t for t in _pool),
      "the defence pool carries the user's own line")
check(all("{drv}" in t and "{pos}" in t for t in _pool),
      "every defence line names the car AND the place", len(_pool))
import tts as _tts                                        # noqa: E402
_st = _tts.STING_LINES.get("overtake") or []
check(bool(_st), "there is an 'overtake' sting group", len(_st))
check(not any("{" in t for t in _st),
      "the sting is name-free, so it can be rendered ahead of time")
check(not any("lead" in t.lower() for t in _st),
      "no sting says 'the lead' -- it has to read right for P5 too")

# THIS FILE'S NAME CHECKS ARE ONLY DETERMINISTIC IF EVERY PASS LINE NAMES
# THE DRIVER. The booth picks a line at random; if one of them ever lacked
# {drv}, the 'NewLeader is called first' check above would pass or fail on
# the luck of the draw -- the exact flake that bit joinedtest, where a
# keyword match missed one line in eight. Asserted here, so a future line
# without a name fails loudly instead of intermittently.
_named = [k for k in ('leadchange', 'overtake', 'overtake_long', 'pass_clean')
          if any('{drv}' not in t for t in COMMENTARY_LINES.get(k) or [])]
check(not _named, 'every pass line names the driver', _named)

print("\n7. A PASS STING NEVER CUTS ANYONE OFF")
# THE REGRESSION THIS SECTION EXISTS FOR. The pass sting first reused the
# incident alert, which clears the audio queue so it can go first. Passes
# near the front happen every few seconds, and in one race that cut three
# of Brett's six answers dead mid-render (render DROP-cut PUNDIT, logged)
# and stranded the engineer's track-limits warnings. A pass is not an
# emergency: it queues, it does not interrupt.
o = booth()
o.cplace = {10: 2, 20: 3}
o._pass_hold(10, 20, 2, 'overtake', 'Attacker', 'Defender', 100.0, {})
o._resolve_top_passes(100.0 + H + 0.05)
check(o.stung == ['overtake'], 'the pass sting played', o.stung)
check(o.cuts == [False], 'and it was asked NOT to cut in', o.cuts)

print("\n" + ("FAILED: %d" % len(fails) if fails else "ALL PASSED"))
sys.exit(1 if fails else 0)
