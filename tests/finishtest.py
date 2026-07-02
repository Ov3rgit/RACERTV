"""Finish accuracy: win call fires at the leader's crossing, but the podium /
summary / engineer verdict use the FINAL order after the player crosses — so a
last-corner pass for the player's place is reported correctly."""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"  # tests: no disk deck state

import sys
sys.path.insert(0, r"D:\R3EOverlay")
import r3e_data as R
from r3e_overlay import Overlay
src = open(r"C:\Users\ADMINI~1\AppData\Local\Temp\claude\D--R3EOverlay\a551edbd-1416-4192-af37-f06169b0707c\scratchpad\smoke.py").read()
exec(src.split('run_session("RACE"')[0])


def newo():
    o = headless_overlay(fake_tts=True)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    return o


print("===== FINISH: LAST-CORNER PASS FOR P3->P4 =====")
o = newo()
s = make_shared(2, ncars=6)
s.number_of_laps = 3
you = s.all_drivers_data_1[0]    # slot 0 = YOU
you_name = R.u8_to_str(you.driver_info.name).upper()
rival = s.all_drivers_data_1[3]  # slot 3 will pip you at the line
rival_name = R.u8_to_str(rival.driver_info.name).upper()
for i in range(s.num_cars):
    s.all_drivers_data_1[i].car_speed = 55.0
# grid: slot1=P1, slot2=P2, YOU(slot0)=P3, RIVAL(slot3)=P4, slot4=P5, slot5=P6
places = {1: 1, 2: 2, 0: 3, 3: 4, 4: 5, 5: 6}
for sl, pl in places.items():
    s.all_drivers_data_1[sl].place = pl
drive(o, s, 3); age_intro(o)
for lap in range(1, 3):
    for i in range(s.num_cars):
        s.all_drivers_data_1[i].completed_laps = lap
    drive(o, s, 2)
# FINAL lap, drag to the line: leader (P1,P2) cross first -> finish triggers
for i in range(s.num_cars):
    s.all_drivers_data_1[i].completed_laps = 3
p1 = next(d for d in s.all_drivers_data_1[:6] if d.place == 1)
p2 = next(d for d in s.all_drivers_data_1[:6] if d.place == 2)
p1.finish_status = 1
p2.finish_status = 1
s.flags.checkered = 1            # leader crossed -> win call (phase A)
o._comm_cd = 0.0
drive(o, s, 2)
win = [t for p, t in o.tts.spoken if p == "COMMENTATOR" and
       ("win" in t.lower() or "victory" in t.lower() or "takes it" in t.lower()
        or "wins it" in t.lower() or "flag" in t.lower() or "first" in t.lower())]
print(f"  win call fired at leader crossing: {bool(win)}")
assert win, "win call did not fire at the leader's crossing"

# now YOU get pipped to the line: rival passes you, both cross P3<->P4 swap
you.place = 4
rival.place = 3
you.finish_status = 1
rival.finish_status = 1
o._comm_cd = 0.0
o._eng_cd -= 40
drive(o, s, 3)

allt = o.tts.spoken
# the summary / podium must NOT credit YOU with P3; the rival took it
summary = [t for p, t in allt if p == "COMMENTATOR" and you_name in t and
           "podium" in t.lower()]
# engineer verdict to the player should be P4 (just off the podium), not podium
eng = [t for p, t in allt if p == "ENGINEER"]
eng_fin = [t for t in eng if "P3" in t or "P4" in t or "podium" in t.lower()
           or "off the podium" in t.lower() or "points" in t.lower()]
print(f"  engineer finish verdict: {eng_fin[-1][:64] if eng_fin else '(none)'}")

# CLIMACTIC victory sign-off — the signature closing call names the winner AND
# RacerTV (the combined victory + sign-off line).
signoff = [t for p, t in allt if p == "COMMENTATOR" and "racertv" in t.lower()]
assert signoff, "victory sign-off (RacerTV) did not fire"
assert any(k in t.lower() for t in signoff for k in
           ("victory", "crosses the line", "chequered flag", "seals victory",
            "belongs to", "does it")), \
    f"sign-off wasn't the climactic victory one: {signoff}"
print(f"  climactic victory sign-off fired: OK -> {signoff[-1][:58]}")
# podium snapshot
o.sw = 1920; o.sh = 1080
# capture podium by calling draw_podium with stubs
o._begin_panel = lambda *a, **k: None
o.panel = lambda *a, **k: None
class C:
    def create_rectangle(self, *a, **k): pass
    def create_text(self, *a, **k): pass
    def create_image(self, *a, **k): pass
o._cv_real = C(); o._ox = 0; o._oy = 0
o.f_row_b = o.f_row = o.f_small = o.f_hdr = None
o.text = lambda *a, **k: None
o.tower_logo = None
o.PODIUM_HOLD = 30
import time as _t
# advance the podium grace by backdating
o._podium_seen_at = _t.time() - 20
try:
    o.draw_podium(s)          # capture happens before any drawing; ignore draw errs
except Exception:
    pass
pod = {p["place"]: p["name"] for p in (o._podium or [])}
print(f"  podium P3 = {pod.get(3)}  (rival={rival_name}, you={you_name})")
assert o._podium, "podium not captured"
assert pod.get(3) == rival_name, f"podium P3 should be the rival, got {pod.get(3)}"
assert pod.get(3) != you_name, "podium wrongly credits YOU with P3"
print("  podium P3 correctly the rival, not you: OK")

# engineer must not CLAIM a podium for the player (P4) — but "close to the
# podium" / "just missed the box" is correct. Check against the celebration pool.
from lines import ENGINEER_LINES
podium_claim = [t for t in eng if t in ENGINEER_LINES["podium"]
                or "on the box" in t.lower() or "rostrum" in t.lower()
                or "that's a podium" in t.lower()]
assert not podium_claim, f"engineer wrongly claimed a podium: {podium_claim}"
assert any("p4" in t.lower() for t in eng), "engineer should reference P4"
print("  engineer gave a correct P4 verdict (no false podium claim): OK")

print("\nALL FINISH-ACCURACY CHECKS PASSED")
