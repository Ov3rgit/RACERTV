"""Focused commentary smoke test for the booth changes:
sign-off + audio stop, time-aware quali order, solo/open sessions,
commentator>pundit balance, driver Q&A, snappier overtakes."""
import sys, time, random
sys.path.insert(0, r"D:\R3EOverlay")
import r3e_data as R
from r3e_overlay import Overlay
# reuse harness helpers (headless_overlay, make_shared, drive, cum, bestcum,
# age_intro, set_name) from the engineer smoke test
src = open(r"C:\Users\ADMINI~1\AppData\Local\Temp\claude\D--R3EOverlay\a551edbd-1416-4192-af37-f06169b0707c\scratchpad\smoke.py").read()
exec(src.split('run_session("RACE"')[0])


def new_overlay(session_type, ncars=6, track="Spa-Francorchamps - Grand Prix",
                duration=600.0):
    o = headless_overlay(fake_tts=True)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    s = make_shared(session_type, ncars=ncars, track=track)
    s.session_time_duration = duration
    s.session_time_remaining = duration
    return o, s


def booth(o):
    return [(p, t) for p, t in o.tts.spoken if p in ("COMMENTATOR", "PUNDIT")]


# ---- 1. SIGN-OFF + AUDIO STOPS AFTER RECAP ---------------------------------
print("===== SIGN-OFF + STOP =====")
o, s = new_overlay(2)
you = s.all_drivers_data_1[0]
for i in range(s.num_cars):
    s.all_drivers_data_1[i].car_speed = 55.0
drive(o, s, 3); age_intro(o)
for lap in range(1, 5):
    for i in range(s.num_cars):
        s.all_drivers_data_1[i].completed_laps = lap
    drive(o, s, 1)
# finish
s.session_phase = 6
s.flags.checkered = 1
for i in range(s.num_cars):
    s.all_drivers_data_1[i].finish_status = 1
drive(o, s, 2)
allspoken = list(o.tts.spoken)
signoff_idx = next((i for i, (p, t) in enumerate(allspoken)
                    if "next time on RacerTV" in t or "next time on RacerTV" in t
                    or "RacerTV" in t and ("Join" in t or "goodbye" in t.lower()
                                           or "so long" in t.lower())), None)
assert signoff_idx is not None, "no sign-off line aired!"
print(f"  sign-off aired: {allspoken[signoff_idx][1][:70]}")
n_before = len(o.tts.spoken)
# keep ticking AFTER finish — nothing new must be produced
for _ in range(20):
    o.last_radio_t = 0.0
    o._comm_cd = 0.0
    o._eng_cd = 0.0
    drive(o, s, 1)
assert len(o.tts.spoken) == n_before, \
    f"audio continued after sign-off: {o.tts.spoken[n_before:]}"
print(f"  no audio after sign-off (stayed at {n_before} lines): OK")
assert signoff_idx == len(allspoken) - 1, "sign-off was not the LAST line"
print("  sign-off was the final line: OK")


# ---- 2. QUALI: NO POLE/STANDINGS TALK BEFORE ANY TIME SET ------------------
print("\n===== QUALI: NO TIME SET =====")
o, s = new_overlay(1, ncars=6)
drive(o, s, 2); age_intro(o)
# everyone circulating, NOBODY completes a lap yet
for _ in range(40):
    o._comm_cd = 0.0
    for i in range(s.num_cars):
        s.all_drivers_data_1[i].car_speed = 60.0
        s.all_drivers_data_1[i].lap_distance_fraction = 0.4
    drive(o, s, 1)
bad = [t for p, t in booth(o)
       if "provisional pole" in t.lower() or "provisional grid" in t.lower()
       or "on pole" in t.lower() or "top three" in t.lower()
       or "heads the timesheets" in t.lower()]
assert not bad, f"talked about pole/standings with no times set: {bad}"
print(f"  {len(booth(o))} booth lines, none claimed pole/standings: OK")
nobody = [t for p, t in booth(o) if "no times" in t.lower()
          or "still on their out-laps" in t.lower() or "clean sheet" in t.lower()
          or "wide open" in t.lower() or "means nothing" in t.lower()
          or "first proper lap" in t.lower()]
print(f"  'nobody set a time' lines aired: {len(nobody)}")


# ---- 3. SOLO SESSION ("only X out there today") ----------------------------
print("\n===== SOLO PRACTICE =====")
o, s = new_overlay(0, ncars=1, duration=600.0)
you = s.all_drivers_data_1[0]
drive(o, s, 2); age_intro(o)
for lap in range(1, 6):
    you.completed_laps = lap
    cum(you, 31.0, 45.0, 28.0); bestcum(you, 30.5, 44.5, 27.5)
    you.car_speed = 58.0
    for _ in range(6):
        o._comm_cd = 0.0
        drive(o, s, 1)
_SOLO = ("out there", "solo", "to themselves", "only car", "private session",
         "place to themselves", "out on track today", "the place to themselves",
         "alone", "no one else", "all the clear track", "clear air", "no traffic",
         "no rivals", "playground", "private playground", "lonely", "belongs to")
solo = [t for p, t in booth(o) if any(k in t.lower() for k in _SOLO)]
assert solo, f"no solo-session awareness lines! booth={booth(o)}"
print(f"  solo-awareness lines aired: {len(solo)}")
print(f"   e.g. {solo[0][:70]}")


# ---- 4. OPEN (no-clock) QUALI -> mileage angle ------------------------------
print("\n===== OPEN/NO-CLOCK QUALI =====")
o, s = new_overlay(1, ncars=1, duration=0.0)   # duration 0 = open/registered
you = s.all_drivers_data_1[0]
drive(o, s, 2); age_intro(o)
for lap in range(1, 9):
    you.completed_laps = lap
    cum(you, 30.0, 44.0, 27.5); bestcum(you, 30.5, 44.5, 28.0)
    you.car_speed = 60.0
    for _ in range(5):
        o._comm_cd = 0.0
        drive(o, s, 1)
mileage = [t for p, t in booth(o) if "mileage" in t.lower()
           or "completed" in t.lower() and "laps" in t.lower()
           or "no clock" in t.lower() or "no time limit" in t.lower()
           or "all the time in the world" in t.lower() or "reps" in t.lower()]
assert mileage, f"no open-session mileage lines! booth={booth(o)}"
print(f"  open-session mileage lines aired: {len(mileage)}")
print(f"   e.g. {mileage[0][:70]}")


# ---- 5. COMMENTATOR > PUNDIT airtime over a race ---------------------------
print("\n===== COMMENTATOR vs PUNDIT BALANCE =====")
o, s = new_overlay(2, ncars=8)
random.seed(7)
for i in range(s.num_cars):
    s.all_drivers_data_1[i].car_speed = 55.0
drive(o, s, 3); age_intro(o)
qa = 0
for lap in range(1, 30):
    for i in range(s.num_cars):
        s.all_drivers_data_1[i].completed_laps = lap
        s.all_drivers_data_1[i].lap_distance_fraction = (i * 0.05) % 1.0
    # induce some overtakes mid-pack by swapping a couple of places
    if lap % 4 == 0:
        a, b = s.all_drivers_data_1[3], s.all_drivers_data_1[4]
        a.place, b.place = b.place, a.place
    for _ in range(3):
        o._comm_cd = 0.0
        o._crosstalk_t -= 40.0
        drive(o, s, 1)
c = sum(1 for p, t in o.tts.spoken if p == "COMMENTATOR")
pnd = sum(1 for p, t in o.tts.spoken if p == "PUNDIT")
print(f"  commentator={c}  pundit={pnd}")
assert c > pnd, "commentator should speak more than the pundit"
print("  commentator speaks more than pundit: OK")


# ---- 6. DRIVER Q&A fires ----------------------------------------------------
print("\n===== DRIVER Q&A =====")
# look back over the balance-race transcript for a lead->pundit driver question
qline = [t for p, t in o.tts.spoken if p == "COMMENTATOR"
         and ("how's" in t.lower() or "how is" in t.lower() or "what do you make"
              in t.lower() or "tell me about" in t.lower() or "talk me through"
              in t.lower() or "what's the story" in t.lower()
              or "how would you" in t.lower() or "assess" in t.lower())]
print(f"  commentator->pundit driver questions aired: {len(qline)}")
assert qline, "no commentator->pundit driver Q&A aired across a 29-lap race!"
print(f"   e.g. {qline[0][:74]}")

print("\nALL COMMENTARY CHECKS PASSED")
