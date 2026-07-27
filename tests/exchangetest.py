"""AN AIRED QUESTION MUST GET ITS ANSWER, AND FILLER MUST NOT CLAIM THE CLOCK.

From a race transcript, measuring every commentator question to the pundit's
next line:

    15:26:50  +9s   "Put a number on Timo Glock's drive..."   -> incident call
    15:28:33  +5s   "How would you rate Over Boy's afternoon" -> incident call
    15:30:22  +72s  "Score this field for me, Brett..."       -> answered a
                                                                 LATER question
Median 7s, but two answers replaced by incident calls and one gap of 72
seconds. The cause is in _purge: an incident sting purges the booth queue with
keep_engineer=True, which keeps team radio and drops everything in a booth
persona -- including the pundit's pending reply. By the time that reply exists
its question has ALREADY been heard out loud (it is queued from the question's
on_play), so dropping it leaves the question hanging.

Separately, the ungated `analysis` filler pool contained lines claiming how
much race was left. "A long, long way to go, and plenty of twists left in this
tale" aired with FOUR LAPS remaining, seconds before the engineer said "4 more
laps left". That pool airs in both the mid and late phases, so any such claim
is true only by luck.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import re
import sys

sys.path.insert(0, r"D:\R3EOverlay")
import tts as T                                           # noqa: E402
from lines import COMMENTARY_LINES                        # noqa: E402


def engine():
    """A Tts with just enough state to exercise _purge."""
    t = object.__new__(T.Tts)
    t.enabled = True
    t.gen_q = T.queue.PriorityQueue()
    t.play_q = T.queue.PriorityQueue(maxsize=64)
    t._seq = T.itertools.count()
    t._epoch = t._eng_epoch = 0
    t._topics = {}
    t._answer_due = 0.0
    return t


def gen_job(text, persona, prio):
    # gen jobs are 9-tuples: text, persona, voice, intensity, cue, epoch,
    # deadline, topic, prio
    return (text, persona, "v", 0, None, 0, None, None, prio)


def drain(q):
    out = []
    while True:
        try:
            _p, _s, payload = q.get_nowait()
        except Exception:
            return out
        if payload is not None:
            out.append(payload)


# ---- 1. an exchange reply SURVIVES an incident interrupt ----------------
t = engine()
t._qput(t.gen_q, "PUNDIT", gen_job("the answer", "PUNDIT", -1), prio=-1)
t._qput(t.gen_q, "COMMENTATOR", gen_job("loose colour", "COMMENTATOR", 1), prio=1)
t._qput(t.gen_q, "ENGINEER", gen_job("box this lap", "ENGINEER", 0), prio=0)
t._purge(keep_engineer=True)              # what sting() does on an incident
left = [p[0] for p in drain(t.gen_q)]
assert "the answer" in left, (
    "an incident sting dropped the pundit's pending reply -- its question has "
    "already been heard, so this leaves the booth mid-conversation. Survivors: "
    "%r" % (left,))
assert "box this lap" in left, "team radio no longer survives an interrupt"
assert "loose colour" not in left, (
    "ordinary booth commentary now survives an interrupt too -- an incident is "
    "supposed to CUT the play-by-play, that is the whole point of the sting")
print("  exchange reply survives an incident interrupt: OK -> %r" % (left,))

# ---- 2. ...and keeps its PRIORITY, or it arrives far too late -----------
t = engine()
t._qput(t.gen_q, "PUNDIT", gen_job("the answer", "PUNDIT", -1), prio=-1)
for i in range(4):
    t._qput(t.gen_q, "COMMENTATOR", gen_job("filler %d" % i, "COMMENTATOR", 1),
            prio=1)
t._purge(keep_engineer=True)
first = t.gen_q.get_nowait()
assert first[0] < 0, (
    "the surviving reply was requeued at priority %r instead of -1 -- _qput "
    "recomputes priority from the persona when it is not given one, which "
    "buries the answer behind the commentary it is meant to pre-empt"
    % (first[0],))
assert first[2][0] == "the answer", "wrong job came out first: %r" % (first[2][0],)
print("  ...and keeps priority -1 so it still comes out first: OK")

# ---- 3. a FULL purge still takes everything ----------------------------
t = engine()
t._qput(t.gen_q, "PUNDIT", gen_job("the answer", "PUNDIT", -1), prio=-1)
t._qput(t.gen_q, "ENGINEER", gen_job("box", "ENGINEER", 0), prio=0)
t._purge(keep_engineer=False)             # stop / flush / session end
assert not drain(t.gen_q), (
    "a FULL purge left jobs behind -- stopping the engine must stop everything")
print("  a full purge (stop/flush) still clears the exchange too: OK")

# the hold must be released by a full purge, and kept by an interrupt
t = engine()
t._answer_due = 1e18
t._purge(keep_engineer=True)
assert t._answer_due > 0, (
    "an interrupt cleared the answer hold while the answer itself survived, "
    "so other lines can wedge into the gap the hold exists to protect")
t._purge(keep_engineer=False)
assert t._answer_due == 0.0, "a full purge must release the answer hold"
print("  answer hold kept on interrupt, released on a full purge: OK")

# ---- 4. ungated filler must not claim where we are in the race ---------
PHASE = re.compile(
    r"long way to go|still long|early (days|stages)|plenty of (time|laps)"
    r"|closing stages|final (laps|stages)|late in the race|last few laps"
    r"|to the flag now|just getting started|whole race ahead", re.I)
bad = [x for x in COMMENTARY_LINES["analysis"] if PHASE.search(x)]
assert not bad, (
    "the `analysis` pool airs as ungated filler in BOTH the mid and late "
    "phases, so a claim about how much race is left is true only by luck: %r"
    % bad)
print("  analysis pool (%d lines) makes no claim about race position: OK"
      % len(COMMENTARY_LINES["analysis"]))

# the phase-gated pool is where such lines belong, and it still has them
assert any("flag now" in x or "closing stages" in x
           for x in COMMENTARY_LINES["late"]), (
    "the late-phase lines were removed rather than moved -- the booth should "
    "still talk about the closing stages WHEN IT IS the closing stages")
print("  ...and they live in the phase-gated `late` pool instead: OK (%d)"
      % len(COMMENTARY_LINES["late"]))

# a missed objective can happen on the last lap, so its booth reaction must
# not assert there is time left
bad = [x for x in COMMENTARY_LINES["obj_booth_miss"] if PHASE.search(x)]
assert not bad, (
    "the booth's missed-objective reaction claims race time remains, but an "
    "objective can be missed on the final lap: %r" % bad)
print("  missed-objective reaction makes no time claim: OK")

print("\nEXCHANGE / PHASE-CLAIM CHECKS PASSED")
