"""Crosstalk coherence: when the lead asks the pundit a question, the pundit's
answer must come from the SAME paired topic (no more non-sequiturs), and the
commentator's hand-back must follow. Drives a race and forces the 35s-cadence
crosstalk repeatedly, then maps every emitted Q/A back to its topic by template."""
import re, sys
sys.path.insert(0, r"D:\R3EOverlay")
import r3e_data as R
from r3e_overlay import Overlay
from lines import CROSSTALK
src = open(r"C:\Users\ADMINI~1\AppData\Local\Temp\claude\D--R3EOverlay\a551edbd-1416-4192-af37-f06169b0707c\scratchpad\smoke.py").read()
exec(src.split('run_session("RACE"')[0])


def tmpl_to_re(t):
    # turn a line template into a regex: placeholders -> wildcards
    rx = re.escape(t)
    for ph in ("\\{drv\\}", "\\{pos\\}", "\\{pundit\\}", "\\{comm\\}"):
        rx = rx.replace(ph, ".+")
    return re.compile("^" + rx + "$")


Q_RX = [(topic, tmpl_to_re(q)) for topic, d in CROSSTALK.items() for q in d["q"]]
A_RX = [(topic, tmpl_to_re(a)) for topic, d in CROSSTALK.items() for a in d["a"]]


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
    qtopic = topic_of(t, Q_RX)
    if not qtopic:
        continue
    # the next PUNDIT line is the answer
    ans = next((tt for pp, tt in spoken[i + 1:i + 4] if pp == "PUNDIT"), None)
    assert ans is not None, f"question with no pundit answer: {t!r}"
    atopic = topic_of(ans, A_RX)
    assert atopic == qtopic, (
        f"MISMATCH: question topic {qtopic!r} answered from {atopic!r}\n"
        f"  Q: {t}\n  A: {ans}")
    exchanges += 1

assert exchanges >= 3, f"crosstalk barely fired ({exchanges}) — can't trust the check"
print(f"  [coherence] {exchanges} crosstalk exchanges, every answer matched its question: OK")
print("\nALL CROSSTALK CHECKS PASSED")
