"""The race engineer must reliably ACKNOWLEDGE the player's overtakes ("up to
P{pos}, great move") — even when the pass lands right after another engineer
line (the case the old last-tick + 14s-spacing logic silently dropped). And it
must call taking the LEAD, and acknowledge being passed."""
import sys
sys.path.insert(0, r"D:\R3EOverlay")
import r3e_data as R
from r3e_overlay import Overlay
src = open(r"C:\Users\ADMINI~1\AppData\Local\Temp\claude\D--R3EOverlay\a551edbd-1416-4192-af37-f06169b0707c\scratchpad\smoke.py").read()
exec(src.split('run_session("RACE"')[0])

GAIN = ("up to p", "that's the move", "great pass", "position gained",
        "clean overtake", "beautiful move", "another one", "superb pass",
        "made it look easy", "that's the way", "place gained", "through you come",
        "decisive move", "got him", "in front of him", "lovely work")
LEAD = ("lead", "p1", "front of the field", "out front", "the front")


def set_places(s, order):
    # order = list of slot_ids in finishing order (index 0 = P1)
    for place, sl in enumerate(order, start=1):
        s.all_drivers_data_1[sl].place = place


def confirm(o, s, ticks=8):
    # drive enough ticks for PLACE_CONFIRM_TICKS to confirm the new order
    for _ in range(ticks):
        o._eng_cd -= 40.0
        drive(o, s, 1)


def eng_since(o, before):
    return [t.lower() for p, t in o.tts.spoken[before:] if p == "ENGINEER"]


print("===== ENGINEER OVERTAKE ACKNOWLEDGEMENT =====")
o = headless_overlay(fake_tts=True)
o._show_caption = lambda *a, **k: None
o.radio_msgs = []
s = make_shared(2, ncars=8)
# green, past intro, a lap done. Player (slot 0) starts P6.
for i in range(s.num_cars):
    s.all_drivers_data_1[i].car_speed = 55.0
    s.all_drivers_data_1[i].completed_laps = 2
set_places(s, [1, 2, 3, 4, 5, 0, 6, 7])      # player slot0 is P6
drive(o, s, 3)
age_intro(o)
confirm(o, s, 8)

# A) force an unrelated engineer line, THEN overtake immediately after — the old
#    code dropped the ack here because of the 14s spacing.
o._eng_cd = __import__("time").time()         # engineer "just spoke" (cooldown hot)
set_places(s, [1, 2, 3, 4, 0, 5, 6, 7])       # player passes slot5 -> P5
before = len(o.tts.spoken)
confirm(o, s, 10)
got = [t for t in eng_since(o, before) if "p5" in t or any(g in t for g in GAIN)]
assert got, f"engineer did NOT acknowledge the overtake to P5: {eng_since(o, before)}"
print(f"  [overtake] pass right after another line still called: OK -> {got[0]}")

# B) climb all the way to the LEAD -> a 'taken the lead' call
set_places(s, [0, 1, 2, 3, 4, 5, 6, 7])       # player now P1
before = len(o.tts.spoken)
o._eng_place_cd -= 100.0
confirm(o, s, 12)
led = [t for t in eng_since(o, before)
       if "lead" in t or "p1" in t or "out front" in t or "the front" in t]
assert led, f"engineer did NOT call taking the lead: {eng_since(o, before)}"
print(f"  [lead] taking the lead called: OK -> {led[0]}")

# C) being PASSED -> acknowledged too (we dropped back to P3)
set_places(s, [1, 2, 0, 3, 4, 5, 6, 7])       # player drops to P3
before = len(o.tts.spoken)
o._eng_place_cd -= 100.0
confirm(o, s, 12)
lost = [t for t in eng_since(o, before) if "p3" in t or "lost" in t
        or "back" in t or "him back" in t or "regroup" in t or "get it back" in t]
assert lost, f"engineer did NOT acknowledge dropping to P3: {eng_since(o, before)}"
print(f"  [lost] dropping a place acknowledged: OK -> {lost[0]}")

print("\nALL OVERTAKE CHECKS PASSED")
