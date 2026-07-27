"""THE PUNDIT MUST ANSWER THE QUESTION HE WAS ACTUALLY ASKED.

Straight off a race transcript:

  Q: "Hand on heart, Brett — could peak-you beat this lot?"
  A: "Both, mate. It's better AND we're old..."          (answers a DIFFERENT
                                                          question in the pool)

  Q: "...was that famous overtake of yours skill or the other bloke's lunch
      break?"
  A: "Right here right now? Me, mate — my licence expired years ago..."

The topic pools were `{"q": [...], "a": [...]}` and the two lists were picked
independently. Many pairs had been WRITTEN positionally -- "how many world
championships did the analysis desk win this year?" has a reply, "Same number
as the commentary chair", that could only air together by luck. With seven
answers in the `booth` topic that is roughly a one-in-seven chance of the
exchange making sense.

crosstalk.json is now `{"qa": [{"q": ..., "a": [...]}, ...]}` -- each question
carries the answers written for it -- and the booth remembers WHICH question it
asked so it can reply from that entry.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import sys

sys.path.insert(0, r"D:\R3EOverlay")
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])
from lines import CROSSTALK, CROSSTALK_ANSWERS            # noqa: E402
from overlay_common import _safe_format                   # noqa: E402

FMT = {"drv": "Rossi", "pos": 4, "comm": "Miles", "pundit": "Brett",
       "comm_full": "Miles Crawford", "pundit_full": "Brett Calloway"}

# ---- 1. the data itself is well formed ----------------------------------
assert CROSSTALK, "no crosstalk topics loaded"
for topic, v in CROSSTALK.items():
    assert "qa" in v, "%s is still the old q/a shape" % topic
    assert v["qa"], "%s has no questions" % topic
    for i, e in enumerate(v["qa"]):
        assert e.get("q"), "%s[%d] has no question" % (topic, i)
        assert e.get("a"), (
            "%s[%d] (%r) has no answer written for it -- the pundit would "
            "fall back to an unrelated pool" % (topic, i, e["q"][:40]))
        _safe_format(e["q"], FMT)
        for a in e["a"]:
            _safe_format(a, FMT)
nq = sum(len(v["qa"]) for v in CROSSTALK.values())
na = sum(len(e["a"]) for v in CROSSTALK.values() for e in v["qa"])
print("  %d topics, %d questions, %d answer slots, all format cleanly: OK"
      % (len(CROSSTALK), nq, na))

# ---- 2. the specific transcript mismatches now pair up ------------------
def answers_for(topic, needle):
    e = next(x for x in CROSSTALK[topic]["qa"] if needle in x["q"])
    return e["a"]


checks = [
    ("era", "could peak-you beat this lot", "Peak me"),
    ("booth", "how many world championships", "Same number as the commentary"),
    ("booth", "skill or the other bloke's lunch break", "The lunch break was YOURS"),
    ("booth", "resting your eyes", "Resting my eyes was Thursday"),
]
for topic, q_needle, a_needle in checks:
    got = answers_for(topic, q_needle)
    assert any(a_needle in a for a in got), (
        "the answer written for %r (%r) is no longer reachable from it; "
        "available: %r" % (q_needle, a_needle, [a[:40] for a in got]))
    print("  %-9s %-38s -> %s: OK" % (topic, q_needle[:38], a_needle[:34]))

# ---- 3. the booth picks a question and answers THAT one -----------------
o = headless_overlay(fake_tts=True)
for topic in CROSSTALK:
    qa = CROSSTALK[topic]["qa"]
    for _ in range(len(qa) * 6):
        q = o._crosstalk_question(topic)
        qi = o._crosstalk_qi
        assert q, "no question drawn for %s" % topic
        assert qa[qi]["q"] == q, (
            "%s: recorded index %r does not match the question drawn" % (topic, qi))
        pool = o._crosstalk_answers(topic, qi)
        assert pool == qa[qi]["a"], (
            "%s question %d was answered from the wrong pool" % (topic, qi))
print("  every question is answered from its own pool (%d topics): OK"
      % len(CROSSTALK))

# ---- 4. a broken/unknown topic must not leave the pundit mute -----------
assert o._crosstalk_answers("no_such_topic", 0) == CROSSTALK_ANSWERS, (
    "an unknown topic no longer falls back to the generic answers")
some = next(iter(CROSSTALK))
pooled = o._crosstalk_answers(some, 999)          # index out of range
assert pooled and all(isinstance(x, str) for x in pooled), (
    "an out-of-range question index left the pundit with nothing to say")
assert o._crosstalk_question("no_such_topic") == ""
assert o._crosstalk_qi is None
print("  unknown topic / bad index fall back safely: OK")

# ---- 5. move_on questions must fit the moment it is OFFERED ------------
# The topic is offered when a car is CLOSING IN -- no pass has happened yet --
# so a question in the past tense ("Rate that overtake") describes a move the
# viewer never saw.
for e in CROSSTALK["move_on"]["qa"]:
    low = e["q"].lower()
    assert "that move," not in low and "rate that overtake" not in low, (
        "move_on asks about an overtake that has already happened, but the "
        "topic fires when someone is still chasing: %r" % e["q"])
print("  move_on only asks about a move still to come: OK")

# ---- 6. ungated filler must not assert checkable facts ------------------
import re                                                 # noqa: E402
from lines import COMMENTARY_LINES                        # noqa: E402
BAD = re.compile(r"\bP\d|covered by a second"
                 r"|seconds? (ahead|behind|clear|back)", re.I)
offenders = [x for x in COMMENTARY_LINES["analysis"] if BAD.search(x)]
assert not offenders, (
    "the analysis pool airs ungated, so it must not claim positions or gaps: "
    "%r" % offenders[:3])
print("  analysis pool (%d lines) claims no gaps or positions: OK"
      % len(COMMENTARY_LINES["analysis"]))

print("\nCROSSTALK-PAIRING CHECKS PASSED")
