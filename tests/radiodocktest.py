"""THE RADIO BUBBLE STACK MUST NOT CLIMB INTO THE OBJECTIVE / RELATIVE COLUMN.

Reported: "the relative tower overlaps with the objective cards when there are
a lot of cars fighting in the same proximity".

The relative tower vs the objective card were already handled -- draw_objective
docks itself to the tower's live _rel_box every frame. The pairing with NO
collision avoidance at all was the RADIO BUBBLE STACK vs that whole right-hand
column: bubbles are anchored to the BOTTOM of the screen and grow UPWARD, sized
only by how many messages are queued, with no knowledge of how far down the
tower + objective card currently reach. They share the same x range
(sw-364..sw-24 vs sw-330..sw-30), so on a shorter window height, or with four
multi-line messages queued at once, the stack's top edge rose straight through
the objective card.

Fix: draw_objective stashes its footprint in _obj_box (nulled when not drawn,
exactly like _rel_box), and draw_radio clamps its ceiling to that box, dropping
its OLDEST bubbles first when the remaining room is too tight.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import os
import sys

sys.path.insert(0, r"D:\R3EOverlay")

try:
    import tkinter as tk
    import tkinter.font as tkfont
    _root = tk.Tk()
    _root.withdraw()
except Exception as ex:                       # headless box — nothing to test
    print(f"  no display available ({type(ex).__name__}) — skipped")
    raise SystemExit(0)

_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "smoke.py")).read()
exec(_src.split('run_session("RACE"')[0])          # noqa: E402

CV = tk.Canvas(_root, width=1920, height=1080)


def make_overlay(sh=700):
    """A real Overlay that RECORDS every panel box instead of guessing at one.

    sh defaults to a short window: that is the case the report describes, and
    it is where a bottom-anchored stack and a top-anchored column collide
    soonest. The bug is not resolution-specific -- four long messages collide
    at 1080 too -- but a short window makes it deterministic.
    """
    o = headless_overlay(fake_tts=True)
    o._cv_real = CV
    o._bg_real = None
    o._ox = o._oy = 0
    o.sw, o.sh = 1920, sh
    o.f_row = tkfont.Font(family="Segoe UI", size=10)
    o.f_row_b = tkfont.Font(family="Segoe UI", size=10, weight="bold")
    o.f_small_b = tkfont.Font(family="Segoe UI", size=8, weight="bold")
    o.f_hdr = o.f_row
    o.f_sub = o.f_row
    o._obj = None
    o._obj_result = None
    o._rel_box = None
    o._obj_box = None
    o.radio_msgs = []
    o.boxes = {}

    def _bp(name, x, y, w, h, *a, **k):
        o.boxes[name] = (x, y, w, h)
        return o.canvas
    o._begin_panel = _bp
    o.text = lambda x, y, t, fill="#fff", font=None, anchor="w": \
        CV.create_text(x, y, text=t, fill=fill, font=font, anchor=anchor)
    return o


def bubbles(n=4, text="He pushed me wide there, that was never his corner "
                      "and he knows it, absolutely furious about that one."):
    """n queued messages, each long enough to wrap to several lines -- what a
    busy multi-car scrap actually produces."""
    now = time.time()
    return [{"name": "M. Hill", "text": text, "color": "#e23b3b",
             "emotion": "angry", "engineer": False,
             "until": now + 30.0, "at": now - 5.0} for _ in range(n)]


def draw_column(o, rows=7):
    """Draw a FULL relative tower + the objective card docked under it, the
    'lots of cars fighting in the same proximity' state from the report."""
    rh = 24
    o._rel_box = (o.sw - 300 - 30, 110, 300, 22 + rh * rows)
    o._obj = {"hud": "Pass Pierre Dubois", "_prog": 0.5, "_badge": "P4",
              "_laps_left": 3, "_gap": 1.8, "_trend": -1, "kind": "position",
              "goal_pos": 4, "laps": 4, "lap0": 2}
    o.draw_objective(None)


def overlap(a, b):
    """Do two (x, y, w, h) boxes intersect on BOTH axes?"""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (ax < bx + bw and bx < ax + aw
            and ay < by + bh and by < ay + ah)


# ---- 1. the objective card publishes its footprint ------------------------
o = make_overlay()
draw_column(o)
assert o._obj_box is not None, (
    "draw_objective drew a card but published no _obj_box, so draw_radio has "
    "nothing to dock away from")
assert o._obj_box == o.boxes["objective"], (
    "_obj_box disagrees with the box actually drawn: %r vs %r"
    % (o._obj_box, o.boxes["objective"]))
print("  objective card publishes its footprint: OK -> %r" % (o._obj_box,))

# ---- 2. and NULLS it when no card is on screen (no stale docking) ---------
o2 = make_overlay()
o2._obj_box = (1, 2, 3, 4)                    # stale box from an earlier frame
o2._obj = None
o2._obj_result = None
o2.draw_objective(None)
assert o2._obj_box is None, (
    "_obj_box survived a frame with no objective card, so the radio stack "
    "would dock away from a card that is not there")
print("  _obj_box nulled when no card is drawn: OK")

# ---- 3. THE BUG: bubbles must not overlap the objective card --------------
o = make_overlay()
draw_column(o)
o.radio_msgs = bubbles(4)
o.draw_radio(None)
obj, rad = o.boxes["objective"], o.boxes["radio"]
assert not overlap(obj, rad), (
    "the radio bubble stack overlaps the objective card: objective=%r "
    "radio=%r" % (obj, rad))
assert rad[1] >= obj[1] + obj[3], (
    "the radio stack's top edge (%s) is above the objective card's bottom "
    "edge (%s)" % (rad[1], obj[1] + obj[3]))
print("  4 long bubbles + full tower -> no overlap: OK (obj ends %s, radio "
      "starts %s)" % (obj[1] + obj[3], rad[1]))

# ---- 4. it yields by DROPPING OLDEST, not by squashing into itself --------
# The clamp must not just shove `top` down and let the bubbles render past the
# bottom of their own panel -- the stack has to actually shed messages.
o = make_overlay()
draw_column(o)
o.radio_msgs = bubbles(4)
o.draw_radio(None)
rad = o.boxes["radio"]
assert rad[3] <= (o.sh - 150) - rad[1] + 1, (
    "the radio panel is taller than the space it was clamped into (h=%s, "
    "room=%s) -- bubbles will spill past the panel"
    % (rad[3], (o.sh - 150) - rad[1]))
print("  stack sheds bubbles to fit rather than spilling: OK (h=%s)" % rad[3])

# ---- 5. with NO objective card it still respects the relative tower -------
o = make_overlay()
rh = 24
o._rel_box = (o.sw - 300 - 30, 110, 300, 22 + rh * 7)
o._obj = None
o._obj_result = None
o.draw_objective(None)                        # publishes _obj_box = None
o.radio_msgs = bubbles(4)
o.draw_radio(None)
rel, rad = o._rel_box, o.boxes["radio"]
assert not overlap(rel, rad), (
    "with no objective card the radio stack climbed into the relative tower "
    "itself: relative=%r radio=%r" % (rel, rad))
print("  no objective card -> still clears the relative tower: OK")

# ---- 6. a FREE screen is left alone (the clamp must not always bite) ------
# Nothing in the right-hand column and a tall window: the stack should sit
# exactly where it always did, bottom-anchored. A fix that permanently pinned
# the bubbles lower would pass every check above and still be wrong.
o = make_overlay(sh=1080)
o._rel_box = None
o._obj = None
o._obj_result = None
o.draw_objective(None)
o.radio_msgs = bubbles(2, text="Box this lap.")
o.draw_radio(None)
rad = o.boxes["radio"]
assert abs((rad[1] + rad[3]) - (o.sh - 150)) <= 1, (
    "with an empty column the stack no longer sits on its bottom anchor: "
    "bottom=%s expected=%s" % (rad[1] + rad[3], o.sh - 150))
print("  empty column -> stack keeps its normal bottom anchor: OK")

print("\nRADIO-DOCK CHECKS PASSED")
