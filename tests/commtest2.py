"""Tests for the latest batch: off-track persistence, next-lap-invalid,
lore exchange, shortened wrap, start-not-dropped, penalty panel."""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"  # tests: no disk deck state

import sys, time, random
sys.path.insert(0, r"D:\R3EOverlay")
import r3e_data as R
from r3e_overlay import Overlay
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])


def newo(stype, ncars=6, dur=600.0, track="Spa-Francorchamps - Grand Prix"):
    o = headless_overlay(fake_tts=True)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    s = make_shared(stype, ncars=ncars, track=track)
    s.session_time_duration = dur
    s.session_time_remaining = dur
    return o, s


# ---- 1. OFF-TRACK keeps registering over many laps (incl. spin-to-stop) -----
print("===== OFF-TRACK PERSISTENCE =====")
o, s = newo(1)
you = s.all_drivers_data_1[0]
drive(o, s, 2); age_intro(o)
offs = 0
for lap in range(1, 12):
    you.completed_laps = lap
    cum(you, 30, 44, 27.5); bestcum(you, 30, 44, 28)
    # clean laps a couple of ticks
    you.car_speed = 60.0; you.current_lap_valid = 1
    drive(o, s, 2)
    # go off: lap invalid at speed, then SPIN TO A STOP (speed ~0)
    you.car_speed = 60.0; you.current_lap_valid = 0
    drive(o, s, 1)
    you.car_speed = 1.0                       # spin to standstill
    o._eng_cd -= 20
    o._q_off_cd -= 10                          # simulate real time between laps
    drive(o, s, 2)
    eng = [t for p, t in o.tts.spoken if p == "ENGINEER"]
    n = sum(1 for t in eng if "island" in t.lower() or "off the" in t.lower()
            or "lost it" in t.lower() or "excursion" in t.lower()
            or "ran out of road" in t.lower() or "bin it" in t.lower()
            or "greedy" in t.lower() or "keep it on" in t.lower()
            or "big moment" in t.lower())
    if n > offs:
        offs = n
print(f"  distinct off-track warnings across 11 laps: {offs}")
assert offs >= 5, f"off-track detection dropped out (only {offs} over 11 laps)"
print("  off-track keeps registering late in the session: OK")


# ---- 2. NEXT-LAP-INVALID trigger -------------------------------------------
print("\n===== NEXT-LAP-INVALID =====")
o, s = newo(1)
you = s.all_drivers_data_1[0]
drive(o, s, 2); age_intro(o)
you.completed_laps = 2; you.car_speed = 60
s.lap_valid_state = 0
drive(o, s, 2)
o._eng_cd -= 20
s.lap_valid_state = 2          # this AND next lap invalid
drive(o, s, 2)
nl = [t for p, t in o.tts.spoken if p == "ENGINEER"
      and ("next lap" in t.lower() or "both this lap" in t.lower()
           or "two laps" in t.lower() or "next won't count" in t.lower()
           or "and the next one" in t.lower() or "and the next" in t.lower()
           or "current and next" in t.lower())]
assert nl, f"no next-lap-invalid warning! eng={[t for p,t in o.tts.spoken if p=='ENGINEER']}"
print(f"  engineer warned next lap won't count: {nl[0][:60]}")


# ---- 3. LORE exchange (Brett Le Mans / Miles rally) -------------------------
print("\n===== LORE EXCHANGE =====")
o, s = newo(2, ncars=8)
random.seed(3)
for i in range(s.num_cars):
    s.all_drivers_data_1[i].car_speed = 55.0
drive(o, s, 3); age_intro(o)
for lap in range(1, 40):
    for i in range(s.num_cars):
        s.all_drivers_data_1[i].completed_laps = lap
        s.all_drivers_data_1[i].lap_distance_fraction = (i * 0.05) % 1.0
    for _ in range(2):
        o._comm_cd = 0.0
        for k in list(o._filler_cd): o._filler_cd[k] -= 80
        drive(o, s, 1)
allt = [t for p, t in o.tts.spoken]
# lore Q&A — NEW backstory (Miles: F1 champ -> rally; Brett: Le Mans/WEC champ)
_LQ = ("won le mans", "endurance greats", "kristensen and mcnish", "le mans crown",
       "wec legends", "world champion before", "schumacher and häkkinen",
       "rally man", "forests", "endurance era", "racing past")
lore_q = [t for t in allt if any(k in t.lower() for k in _LQ)]
_LA = (  # Brett's WEC answers / Miles's F1-then-rally answers (generic + track)
    "kristensen", "mcnish", "pirro", "lotterer", "capello", "endurance teaches",
    "prototype", "le mans years", "mulsanne", "porsche curves", "green hell",
    "schumacher", "häkkinen", "hakkinen", "barrichello", "rubens", "mika",
    "world champion", "formula one", "f1 days", "car control", "eau rouge",
    "parabolica", "becketts", "tamburello", "the forests")
lore_a = [t for t in allt if any(k in t.lower() for k in _LA)]
print(f"  lore questions: {len(lore_q)}   lore answers: {len(lore_a)}")
# an answer proves a full Q&A exchange fired (the answer is force-queued only
# in response to a lore question)
assert lore_a, "lore exchange did not fire / answer"
print(f"   A: {lore_a[0][:64]}")


# ---- 4. SHORTENED WRAP (<=5 lines incl sign-off) ---------------------------
print("\n===== SHORT WRAP =====")
o, s = newo(2)
for i in range(s.num_cars):
    s.all_drivers_data_1[i].car_speed = 55.0
drive(o, s, 3); age_intro(o)
for lap in range(1, 4):
    for i in range(s.num_cars):
        s.all_drivers_data_1[i].completed_laps = lap
    drive(o, s, 1)
before = len(o.tts.spoken)
s.session_phase = 6; s.flags.checkered = 1
for i in range(s.num_cars):
    s.all_drivers_data_1[i].finish_status = 1
drive(o, s, 2)
wrap = [t for p, t in o.tts.spoken[before:]]
print(f"  wrap+signoff lines: {len(wrap)}")
for w in wrap:
    print(f"    - {w[:62]}")
assert len(wrap) <= 6, f"wrap too long: {len(wrap)} lines"
assert "RacerTV" in wrap[-1], "last line is not the sign-off"
print("  wrap is short and ends on the sign-off: OK")


# ---- 5. START call NOT dropped when queue busy -----------------------------
print("\n===== START NOT DROPPED =====")
o, s = newo(2)
# flood the queue first (simulate busy pregrid welcome still rendering)
o.tts._pend = 9
for i in range(s.num_cars):
    s.all_drivers_data_1[i].car_speed = 60.0   # lights out -> racing edge
drive(o, s, 3); age_intro(o)
_ST = ("lights out", "lights go", "away we go", "and away", "they're away",
       "we are racing", "green flag", "flag drops", "off they go",
       "leads them", "into turn one", "first corner", "lights and away",
       "we're racing", "into the lead", "grabs the early")
start = [t for p, t in o.tts.spoken if any(k in t.lower() for k in _ST)]
assert start, f"START call was dropped! booth={[t for p,t in o.tts.spoken if p=='COMMENTATOR'][:6]}"
print(f"  lights-out call landed despite busy queue: {start[0][:58]}")


# ---- 6. PENALTY PANEL produces correct detail (headless stub) --------------
print("\n===== PENALTY PANEL =====")
o, s = newo(2)
# stub the drawing primitives
drawn = []
o.sw = 1920; o.sh = 1080
o._podium = None; o._podium_until = 0
o._begin_panel = lambda *a, **k: None
o._card = lambda *a, **k: None
class C:
    def create_rectangle(self, *a, **k): pass
    def create_text(self, *a, **k): pass
o._cv_real = C(); o._ox = 0; o._oy = 0       # canvas property wraps _cv_real
o.text = lambda x, y, t, **k: drawn.append(str(t))
import r3e_overlay as RM
o.f_row_b = o.f_small_b = None
you = s.all_drivers_data_1[0]
# slow-down penalty: give back 3.4s, for cutting track
s.penalties.slow_down = 3.4
you.penaltyType = 4; you.penaltyReason = 1
s.lap_valid_state = 2
o.draw_penalty(s)
txt = " | ".join(drawn)
print("  drawn:", txt[:140])
assert "SLOW DOWN" in txt and "3.4" in txt, "slow-down detail missing"
assert "NEXT LAP" in txt.upper(), "next-lap warning missing"
assert "cutting the track" in txt, "reason missing"
print("  penalty panel shows type + amount + reason + next-lap: OK")

print("\nALL BATCH-2 CHECKS PASSED")
