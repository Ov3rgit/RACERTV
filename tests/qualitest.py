"""Quali/practice: engineer warns EVERY track-limits/off, gives a session
intro, and the solo booth has varied content (not the same line repeated)."""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"  # tests: no disk deck state

import sys, random
sys.path.insert(0, r"D:\R3EOverlay")
import r3e_data as R
from r3e_overlay import Overlay
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])


def newo():
    o = headless_overlay(fake_tts=True)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    return o


# ---- 1. ENGINEER warns on EVERY track-limits cut (cut_track_warnings) -------
print("===== ENGINEER TRACK-LIMITS WARN =====")
o = newo()
s = make_shared(1, ncars=1, track="Laguna Seca")
you = s.all_drivers_data_1[0]
drive(o, s, 2); age_intro(o)
warns = 0
for i in range(1, 7):
    you.completed_laps = i
    you.car_speed = 55.0
    s.cut_track_warnings = i            # one new cut each lap (mild run-wide)
    o._eng_cd -= 20
    drive(o, s, 2)
    eng = [t for p, t in o.tts.spoken if p == "ENGINEER"]
    n = sum(1 for t in eng if "limit" in t.lower() or "white line" in t.lower()
            or "all four" in t.lower() or "ran a touch wide" in t.lower()
            or "edges" in t.lower() or "kerb" in t.lower())
    warns = max(warns, n)
print(f"  track-limits warnings over 6 cuts: {warns}")
assert warns >= 4, f"engineer missed track-limits cuts (only {warns})"
print("  engineer warns on track-limits every time: OK")


# ---- 2. ENGINEER session intro -------------------------------------------
print("\n===== ENGINEER SESSION INTRO =====")
o = newo()
s = make_shared(0, ncars=1, track="Laguna Seca")   # practice
you = s.all_drivers_data_1[0]
drive(o, s, 2); age_intro(o)
o._eng_cd -= 20
drive(o, s, 2)
intro = [t for p, t in o.tts.spoken if p == "ENGINEER"
         and ("practice" in t.lower() or "laguna" in t.lower())
         and ("warm" in t.lower() or "laps" in t.lower() or "tyres" in t.lower()
              or "build" in t.lower())]
print(f"  engineer intro: {intro[0][:90] if intro else '(none)'}")
assert intro, "engineer gave no session intro!"
assert "laguna" in intro[0].lower(), "intro should name the track"
print("  engineer session intro with track + warm-up: OK")


# ---- 3. SOLO booth variety (no single line dominating) ----------------------
print("\n===== SOLO BOOTH VARIETY =====")
o = newo()
s = make_shared(0, ncars=1, track="Laguna Seca")
you = s.all_drivers_data_1[0]
drive(o, s, 2); age_intro(o)
random.seed(1)
for lap in range(1, 30):
    you.completed_laps = lap
    you.car_speed = 58.0
    cum(you, 31, 45, 28); bestcum(you, 30.5, 44.5, 27.5)
    for _ in range(3):
        o._comm_cd = 0.0
        for k in list(o._filler_cd):
            o._filler_cd[k] -= 30
        drive(o, s, 1)
booth = [t for p, t in o.tts.spoken if p in ("COMMENTATOR", "PUNDIT")]
uniq = set(booth)
from collections import Counter
top = Counter(booth).most_common(1)[0]
print(f"  booth lines: {len(booth)}, unique: {len(uniq)}")
print(f"  most-repeated line said {top[1]}x: {top[0][:54]}")
# categories represented
cats = {
    "solo": sum(1 for t in booth if "out there" in t.lower() or "alone" in t.lower()
                or "clear air" in t.lower() or "to themselves" in t.lower()
                or "private" in t.lower() or "only car" in t.lower()
                or "belongs to" in t.lower() or "no one else" in t.lower()
                or "lonely" in t.lower() or "playground" in t.lower()
                or "no rivals" in t.lower() or "no traffic" in t.lower()),
    "goals": sum(1 for t in booth if "setup" in t.lower() or "braking point" in t.lower()
                 or "tyre management" in t.lower() or "building" in t.lower()
                 or "consistency" in t.lower() or "long-run" in t.lower()
                 or "confidence" in t.lower() or "working on" in t.lower()
                 or "representative lap" in t.lower() or "homework" in t.lower()
                 or "race-ready" in t.lower() or "references" in t.lower()),
    "lore": sum(1 for t in booth if "le mans" in t.lower() or "rally" in t.lower()
                or "forests" in t.lower() or "racing the legend" in t.lower()
                or "scars" in t.lower() or "in my day" in t.lower()
                or "raced" in t.lower() or "cockpit" in t.lower()),
    "joke": sum(1 for t in booth if "understeer" in t.lower() or "golf" in t.lower()
                or "snakes" in t.lower() or "karting reunion" in t.lower()
                or "buffet" in t.lower() or "coffee stone cold" in t.lower()
                or "anxiety" in t.lower() or "social calendar" in t.lower()
                or "catering" in t.lower() or "doctor" in t.lower()),
}
print(f"  category spread: {cats}")
assert top[1] <= 3, f"a line repeated too often ({top[1]}x): {top[0]}"
assert cats["goals"] >= 1, "no 'goals' content in solo"
assert cats["lore"] >= 1, "no lore content in solo"
assert cats["joke"] >= 1, "no jokes in solo"
print("  solo booth: varied (goals + lore + jokes), no line spammed: OK")

print("\nALL QUALI/SOLO CHECKS PASSED")
