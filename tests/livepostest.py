# -*- coding: utf-8 -*-
"""THE ORDER ON SCREEN IS THE ORDER ON TRACK, THIS INSTANT.

Reported by a tester running the published build: "i notice that the position
order doesn't update immediately and takes a while to register".

RaceRoom's `place` field lags an on-track move -- the timing tower's own
comment has said so for a long time, which is why the tower sorts by lap plus
lap fraction instead. The RELATIVE panel was never given the same treatment:
it sorted by `place` and printed `place`, and that panel is the one a driver
actually watches. So an overtake reordered the tower at once and left the
panel under his eyes a beat behind.

Reproduced here by doing what the game does: move the cars past each other on
track while `place` still says the old order.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import sys

sys.path.insert(0, r"D:\R3EOverlay")
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])

import tkinter as tk                                      # noqa: E402
import tkinter.font as tkfont                             # noqa: E402

fails = []


def check(ok, what, detail=""):
    print("  [%s] %s%s" % ("OK" if ok else "FAIL", what,
                           ("  " + str(detail)) if detail else ""))
    if not ok:
        fails.append(what)


try:
    _root = tk.Tk()
    _root.withdraw()
except Exception as ex:
    print("  no display (%s) -- skipped" % type(ex).__name__)
    raise SystemExit(0)
CV = tk.Canvas(_root, width=1920, height=1080)

N = 6


def overlay():
    o = headless_overlay(fake_tts=True)
    o._cv_real = CV
    o._bg_real = None
    o._ox = o._oy = 0
    o.sw, o.sh = 1920, 1080
    o.game_x = o.game_y = 0
    o.compact = False
    o._racing = True
    f = tkfont.Font(family="Segoe UI", size=11)
    for a in ("f_row", "f_row_b", "f_hdr", "f_sub", "f_small", "f_small_b",
              "f_tow", "f_tow_b", "f_tiny", "f_spd", "f_gear"):
        setattr(o, a, f)
    o.rows_drawn = []
    o._begin_panel = lambda *a, **k: o.canvas
    o.text = lambda x, y, t, fill="#fff", font=None, anchor="w": (
        o.rows_drawn.append((y, str(t))), CV.create_text(x, y, text=t, fill=fill,
                                                         font=font, anchor=anchor))[1]
    return o


def session():
    s = make_shared(2, ncars=N)
    s.session_phase = 5
    s.vehicle_info.slot_id = 2                # we are watching the P3 car
    for i, d in enumerate(s.all_drivers_data_1[:N]):
        d.car_speed, d.place, d.completed_laps = 60.0, i + 1, 4
        d.driver_info.slot_id = i
        d.lap_distance_fraction = 0.80 - i * 0.05
        d.time_delta_front = 0.6
    return s


def names_in_panel(o, s):
    """Draw the tower then the relative panel, as a real frame does, and read
    back the driver names the relative panel put on screen, in order."""
    o.rows_drawn = []
    o.draw_tower(s)
    n_tower = len(o.rows_drawn)
    o.draw_relative(s)
    # every string the relative panel drew, in the order it drew them. Not
    # filtered by name: a filter that matches one row cannot detect a reorder,
    # which is how the first version of this check passed on one row.
    return [t for _y, t in o.rows_drawn[n_tower:]]


print("\n1. AN ON-TRACK PASS SHOWS AT ONCE, BEFORE `place` CATCHES UP")
o, s = overlay(), session()
before = names_in_panel(o, s)
check(bool(before), "the relative panel drew rows", len(before))

# The P4 car passes the P3 car on track. RaceRoom has not updated `place` yet:
# this is exactly the window the tester was seeing.
p3 = next(d for d in s.all_drivers_data_1[:N] if d.place == 3)
p4 = next(d for d in s.all_drivers_data_1[:N] if d.place == 4)
p3.lap_distance_fraction, p4.lap_distance_fraction = (
    p4.lap_distance_fraction, p3.lap_distance_fraction)
after = names_in_panel(o, s)
check(after != before,
      "the panel reorders the instant the cars swap on track", after[:4])

# ...and the NUMBER beside each name agrees with the tower's live rank.
o.rows_drawn = []
o.draw_tower(s)
ranks = dict(o._tow_rank)
check(ranks.get(p4.driver_info.slot_id) == 3
      and ranks.get(p3.driver_info.slot_id) == 4,
      "the live rank has the passing car ahead", ranks)
check(p4.place == 4 and p3.place == 3,
      "...while RaceRoom's own place field still says otherwise "
      "(this is the lag being covered)")

print("\n2. THE TWO PANELS CANNOT DISAGREE")
src_d = open(r"D:\R3EOverlay\overlay_draw.py", encoding="utf-8").read()
_rel = src_d[src_d.index("    def draw_relative"):]
_rel = _rel[:_rel.index("\n    def ", 10)]        # next TOP-LEVEL method
check("self._tow_rank.get(di.slot_id, d.place)" in _rel,
      "the relative panel prints the tower's live rank, not `place`")
check("key=lambda d: -_rprog(d)" in _rel,
      "and sorts by track position while racing")

print("\n" + ("FAILED: %d" % len(fails) if fails else "ALL PASSED"))
_root.destroy()
sys.exit(1 if fails else 0)
