"""A RADIO CARD MUST NEVER APPEAR WITHOUT ITS AUDIO.

Reported from a real race: "a commentator will talk and then I'll also see a
message from the race engineer, but no audio plays because the commentators
are still speaking."

Cause: on_drop aired the bubble anyway. When a line was discarded -- queue
full, TTL expired, interrupted -- the card still went up, reasoning that
something beat nothing. The result was a team-radio message on screen with no
voice behind it, ever, while the booth talked over the top of it.

A radio bubble IS the visual of a transmission. No transmission, no bubble.

Note the FakeTts used to swallow on_drop and always call on_play, so the drop
path was completely untested -- which is why this shipped.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import os
import sys

sys.path.insert(0, r"D:\R3EOverlay")
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "smoke.py")).read()
exec(_src.split('run_session("RACE"')[0])


def build():
    o = headless_overlay(fake_tts=True)
    s = make_shared(2)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    for i in range(s.num_cars):
        s.all_drivers_data_1[i].car_speed = 55.0
        s.all_drivers_data_1[i].completed_laps = 3
    drive(o, s, 3)
    age_intro(o)
    drive(o, s, 1)
    return o, s


# Damage is the most reliable engineer trigger: it bypasses the spacing, so
# the scenario produces radio on demand instead of depending on cooldown luck.
def radio_run(drop):
    o, s = build()
    o.tts.drop_all = drop
    o.radio_msgs = []
    for f in ("engine", "transmission", "aerodynamics", "suspension"):
        setattr(s.car_damage, f, 1.0)
    drive(o, s, 1)
    for i, val in enumerate((0.90, 0.70, 0.50)):
        s.car_damage.aerodynamics = val
        for _ in range(6):
            o._eng_cd -= 40.0
            o._eng_dmg_cd["aero"] = -1e9
            drive(o, s, 1)
    return o


# ---- 1. lines that PLAY still get their card ------------------------------
o = radio_run(drop=False)
played_cards = len(o.radio_msgs)
assert played_cards > 0, (
    "no radio cards at all when every line plays -- the harness isn't "
    "exercising the radio path, so the drop check below would prove nothing")
print("  lines that play still show a card: OK (%d)" % played_cards)

# ---- 2. lines that are DROPPED must show NO card --------------------------
o = radio_run(drop=True)
assert o.tts.dropped, (
    "the drop path never ran -- check FakeTts.drop_all is still wired")
assert not o.radio_msgs, (
    "%d radio card(s) went up for lines that will NEVER be heard: %s"
    % (len(o.radio_msgs),
       " | ".join(m["text"][:70] for m in o.radio_msgs)))
print("  %d dropped lines produced 0 cards: OK" % len(o.tts.dropped))

# ---- 3. the 20s safety net must not resurrect a dropped card --------------
# _pending_bubbles exists for a line that reports NEITHER play nor drop. A
# dropped line is already accounted for and must not come back later.
for _p in list(getattr(o, "_pending_bubbles", [])):
    _msg, _due, _st = _p
    assert _st.get("aired"), (
        "a dropped line was left un-consumed in _pending_bubbles -- the "
        "safety net will put its card up 20s later, with no audio")
print("  dropped lines are not resurrected by the safety net: OK")

print("\nMUTE-CARD CHECKS PASSED")
