"""Crosstalk coherence: when the lead asks the pundit a question, the pundit's
answer must come from the SAME paired topic (no more non-sequiturs), and the
commentator's hand-back must follow. Drives a race and forces the 35s-cadence
crosstalk repeatedly, then maps every emitted Q/A back to its topic by template."""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"  # tests: no disk deck state

import re, sys
sys.path.insert(0, r"D:\R3EOverlay")
import r3e_data as R
from r3e_overlay import Overlay
from lines import CROSSTALK
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])


def tmpl_to_re(t):
    # turn a line template into a regex: placeholders -> wildcards
    rx = re.escape(t)
    for ph in ("\\{drv\\}", "\\{pos\\}", "\\{pundit\\}", "\\{comm\\}"):
        rx = rx.replace(ph, ".+")
    return re.compile("^" + rx + "$")


# CROSSTALK is now {topic: {"qa": [{"q":..., "a":[...]}]}} -- each question
# carries the answers written for it, so a Q/A pair can be matched to the exact
# QUESTION rather than just to a shared topic (see crosstalkpairtest.py).
Q_RX = [((topic, i), tmpl_to_re(e["q"]))
        for topic, d in CROSSTALK.items() for i, e in enumerate(d["qa"])]
A_RX = [((topic, i), tmpl_to_re(a))
        for topic, d in CROSSTALK.items() for i, e in enumerate(d["qa"])
        for a in e["a"]]


def topic_of(text, table):
    for topic, rx in table:
        if rx.match(text):
            return topic
    return None


print("===== CROSSTALK Q/A COHERENCE =====")
o = headless_overlay(fake_tts=True)
o._show_caption = lambda *a, **k: None
o.radio_msgs = []
s = make_shared(2, ncars=8)
# go green and get the booth past its intro
for i in range(s.num_cars):
    s.all_drivers_data_1[i].car_speed = 50.0
    s.all_drivers_data_1[i].completed_laps = 4
drive(o, s, 3)
age_intro(o)
drive(o, s, 2)

# force the 35s-cadence crosstalk to fire many times by resetting its timer
for _ in range(60):
    o._crosstalk_t = 0.0          # release the cadence gate
    o._comm_cd = 0.0
    drive(o, s, 1)

spoken = o.tts.spoken
exchanges = 0
for i, (p, t) in enumerate(spoken):
    if p != "COMMENTATOR":
        continue
    asked = topic_of(t, Q_RX)
    if not asked:
        continue
    # the next PUNDIT line is the answer
    ans = next((tt for pp, tt in spoken[i + 1:i + 4] if pp == "PUNDIT"), None)
    assert ans is not None, f"question with no pundit answer: {t!r}"
    # Must come from the pool written for THIS question. Membership, not a
    # first-match lookup: the same answer is deliberately reachable from
    # several questions in a topic (all four "rate {drv} out of ten" phrasings
    # share their answers), so resolving an answer back to one index would
    # fail on perfectly correct pairs.
    topic, qi = asked
    own = [tmpl_to_re(a) for a in CROSSTALK[topic]["qa"][qi]["a"]]
    assert any(rx.match(ans) for rx in own), (
        f"MISMATCH: the pundit answered a question he was not asked.\n"
        f"  Q ({topic}[{qi}]): {t}\n  A: {ans}\n"
        f"  written for that question: "
        f"{[a[:48] for a in CROSSTALK[topic]['qa'][qi]['a']]}")
    exchanges += 1

assert exchanges >= 3, f"crosstalk barely fired ({exchanges}) — can't trust the check"
print(f"  [coherence] {exchanges} crosstalk exchanges, every answer matched its question: OK")
print("\nALL CROSSTALK CHECKS PASSED")
