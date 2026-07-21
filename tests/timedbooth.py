"""Booth frames a TIMED race up front — it used to count down but never say
the race was timed or how long ('the commentators don't know how long a timed
race is')."""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"
import os, sys
sys.path.insert(0, r"D:\R3EOverlay")
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "smoke.py")).read()
exec(_src.split('run_session("RACE"')[0])

o = headless_overlay(fake_tts=True)
s = make_shared(2, ncars=8)
s.number_of_laps = -1                 # TIMED
s.session_time_duration = 1200.0      # 20 minutes
s.session_time_remaining = 1180.0
o._show_caption = lambda *a, **k: None
o.radio_msgs = []
for i in range(8):
    s.all_drivers_data_1[i].car_speed = 55.0
    s.all_drivers_data_1[i].completed_laps = 2
drive(o, s, 3)
age_intro(o)
o._green_t = time.time() - 30.0       # green flag well established
for _ in range(6):
    drive(o, s, 1)
said = " || ".join(t for p, t in o.tts.spoken if p == "COMMENTATOR")
assert "minute" in said.lower(), (
    "booth never framed the timed-race duration:\n" + said)
assert "20" in said or "twenty" in said.lower(), (
    "booth stated a duration but not the right length (20 min):\n" + said)
print("  booth frames the timed-race duration (20 min): OK")

# lap races must NOT get the timed framing
o2 = headless_overlay(fake_tts=True)
s2 = make_shared(2, ncars=8)
s2.number_of_laps = 12                # LAP race
o2._show_caption = lambda *a, **k: None
o2.radio_msgs = []
for i in range(8):
    s2.all_drivers_data_1[i].car_speed = 55.0
    s2.all_drivers_data_1[i].completed_laps = 2
drive(o2, s2, 3)
age_intro(o2)
o2._green_t = time.time() - 30.0
for _ in range(6):
    drive(o2, s2, 1)
lap_said = " || ".join(t for p, t in o2.tts.spoken if p == "COMMENTATOR")
assert "minute sprint" not in lap_said.lower() and "minutes on the clock" not in lap_said.lower(), (
    "a LAP race got the timed-duration framing:\n" + lap_said)
print("  lap race does NOT get the timed framing: OK")

print("\nTIMED-BOOTH CHECKS PASSED")
