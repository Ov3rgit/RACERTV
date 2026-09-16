"""Render RacerTV's real panels to a PNG, to LOOK at the theme.

    python tests/themeshot.py [out.png]

A mockup can lie; this cannot. Every panel here is drawn by the same method
the overlay calls each frame, so the colours are the shipped ones.

WHY IT EXISTS. RacerTV wore FACTORtv's cyan-on-blue-black. RaceRoom's own
colour is red, and the two products reading as one thing served neither. A
palette is the one change that cannot be judged from a diff.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import os
import sys
import time

sys.path.insert(0, r"D:\R3EOverlay")

import tkinter as tk
import tkinter.font as tkfont

_root = tk.Tk()
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "smoke.py")).read()
exec(_src.split('run_session("RACE"')[0])          # noqa: E402
from overlay_common import (ACCENT, CARD_BG, CARD_BG2, DIM, GREEN,      # noqa
                            HEADER_ACCENT, LEADER, PANEL_BG, PURPLE,
                            TEXT, ENGINEER_COLOR)
import helmet as H                                  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else r"D:\R3EOverlay\_previews\_theme_preview.png"
W, HGT = 980, 600

_root.geometry("%dx%d+60+60" % (W, HGT))
_root.configure(bg=PANEL_BG)
_root.title("RacerTV theme")
CV = tk.Canvas(_root, width=W, height=HGT, bg=PANEL_BG, highlightthickness=0)
CV.pack()


def overlay():
    o = headless_overlay(fake_tts=True)
    o._cv_real = CV
    o._bg_real = None
    o._ox = o._oy = 0
    o.sw, o.sh = W, HGT
    o.f_row = tkfont.Font(family="Segoe UI", size=10)
    o.f_row_b = tkfont.Font(family="Segoe UI", size=10, weight="bold")
    o.f_small_b = tkfont.Font(family="Segoe UI", size=8, weight="bold")
    o.f_tiny = tkfont.Font(family="Segoe UI", size=8)
    o.f_sub = o.f_row
    o._begin_panel = lambda *a, **k: o.canvas
    o.text = lambda x, y, t, fill="#fff", font=None, anchor="w": \
        CV.create_text(x, y, text=t, fill=fill, font=font, anchor=anchor)
    o._menu_hits = []
    o._my_name = "Dante_K"
    o._my_helmet = {"base": "#161616", "accent": "#d4ff00", "pattern": "blade",
                    "weight": "bold", "number": 4, "ink": "#f2f2f2"}
    o._menu_page = "helmet"
    o.radio_msgs = []
    return o


o = overlay()
CV.delete("all")
f_t = tkfont.Font(family="Segoe UI", size=11, weight="bold")


def cap(x, y, t):
    CV.create_text(x, y, text=t, fill=DIM, font=f_t, anchor="w")


# ---- a timing tower, hand-laid so the SEMANTIC colours are all present ----
# purple = session best, green = personal best, amber = the car you watch,
# platinum = the leader. These are the four that had to survive the retheme.
cap(20, 16, "TIMING  \u2014  meaning kept, chrome changed")
o._card(20, 30, 300, 210, accent=HEADER_ACCENT, side="left")
ROWS = [("1", "Zolder_Zed", "1:42.881", LEADER),
        ("2", "vTec_Ryan", "+0.412", PURPLE),
        ("3", "Dante_K", "+1.008", ACCENT),
        ("4", "Ana_Ferreira", "+2.334", GREEN),
        ("5", "apex_andy", "+4.910", TEXT),
        ("6", "BrakeLate", "+6.002", TEXT)]
yy = 46
for pos, nm, gap, col in ROWS:
    CV.create_rectangle(28, yy, 32, yy + 22, fill=col, outline="")
    CV.create_text(44, yy + 11, text=pos, fill=DIM, font=o.f_row_b, anchor="w")
    CV.create_text(64, yy + 11, text=nm, fill=col, font=o.f_row, anchor="w")
    CV.create_text(310, yy + 11, text=gap, fill=col, font=o.f_row_b, anchor="e")
    yy += 31

# ---- radio cards: the engineer, and a driver in his generated helmet ----
cap(20, 262, "RADIO")
o.radio_msgs = []
for i, (who, txt, eng) in enumerate(
        [("ENGINEER", "Box this lap, box this lap.", True),
         ("vTec_Ryan", "That was never a racing line.", False)]):
    m = {"name": who, "text": txt, "color": (ENGINEER_COLOR if eng
                                             else H.readable(
                                                 H.card_colour(H.generated(who)),
                                                 CARD_BG)),
         "engineer": eng, "until": 9e9, "at": 0.0}
    try:
        o._draw_bubble(20, 276 + i * 58, 300, m)
    except Exception as ex:
        CV.create_text(24, 290 + i * 58, text="bubble: %s" % ex, fill="#f66",
                       anchor="w", font=o.f_row)

# ---- the speedo face, straight from its renderer ----
cap(20, 400, "SPEEDO")
try:
    import speedo
    from PIL import ImageTk
    _sp = speedo.render(150, 0.82, 0.82, 0.93)
    if _sp is not None:
        _ph = ImageTk.PhotoImage(_sp)
        CV.create_image(24, 416, image=_ph, anchor="nw")
        _keep = _ph
except Exception as ex:
    CV.create_text(24, 430, text="speedo: %s" % ex, fill="#f66", anchor="w",
                   font=o.f_row)

# ---- the helmet designer page ----
cap(360, 16, "HELMET DESIGNER")
o._menu_hits = []
o._draw_helmet_page(x=360, y=30)

# ---- the palette itself: what moved, and what deliberately did not ----
SW = 22
cap(360, 442, "CHROME  —  re-themed")
for i, (nm, c) in enumerate([("accent", HEADER_ACCENT), ("brand", "#e2001a"),
                             ("card", CARD_BG), ("panel", PANEL_BG),
                             ("control", "#2a1e20"), ("leader", LEADER),
                             ("engineer", ENGINEER_COLOR)]):
    bx = 362 + i * 86
    CV.create_rectangle(bx, 456, bx + SW * 2, 456 + SW, fill=c,
                        outline="#4a3a3c")
    CV.create_text(bx, 492, text=nm, fill=DIM, font=o.f_row, anchor="w")

cap(360, 516, "MEANING  —  untouched, and why")
for i, (nm, c) in enumerate([("session best", PURPLE), ("personal best", GREEN),
                             ("your car", ACCENT), ("live", "#ff3b3b"),
                             ("replay", "#ffb000")]):
    bx = 362 + i * 122
    CV.create_rectangle(bx, 530, bx + SW * 2, 530 + SW, fill=c,
                        outline="#4a3a3c")
    CV.create_text(bx, 566, text=nm, fill=DIM, font=o.f_row, anchor="w")

_root.update()
time.sleep(0.4)
try:
    from PIL import ImageGrab
    x0, y0 = _root.winfo_rootx(), _root.winfo_rooty()
    ImageGrab.grab(bbox=(x0, y0, x0 + W, y0 + HGT)).save(OUT)
    print("wrote", OUT)
except Exception as ex:
    print("could not grab: %s: %s" % (type(ex).__name__, ex))
_root.destroy()
