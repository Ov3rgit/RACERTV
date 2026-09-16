"""Render the helmet designer page to a PNG, straight from the real renderer.

A mockup can lie; this cannot. It drives `_draw_helmet_page` on a real tk
canvas -- the same method the overlay calls -- so what comes out is what goes
on screen.

    python tests/designershot.py [out.png]

WHY A SHOT TOOL AND NOT JUST TESTS. The helmet port passed every assertion it
had while four of twenty driver names were effectively invisible on the card,
because "is this a distinct colour" and "can you read this" are different
questions. Some things have to be looked at.
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
from overlay_common import CARD_BG                 # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else r"D:\R3EOverlay\_previews\_designer_preview.png"
W, H = 470, 560

_root.geometry("%dx%d+80+80" % (W, H))
_root.configure(bg=CARD_BG)
_root.title("RacerTV — helmet designer")
CV = tk.Canvas(_root, width=W, height=H, bg=CARD_BG, highlightthickness=0)
CV.pack()


def overlay(spec, name="Dante_K"):
    o = headless_overlay(fake_tts=True)
    o._cv_real = CV
    o._bg_real = None
    o._ox = o._oy = 0
    o.sw, o.sh = W, H
    o.f_row = tkfont.Font(family="Segoe UI", size=10)
    o.f_row_b = tkfont.Font(family="Segoe UI", size=10, weight="bold")
    o.f_small_b = tkfont.Font(family="Segoe UI", size=8, weight="bold")
    o.f_sub = o.f_row
    o._begin_panel = lambda *a, **k: o.canvas
    o.text = lambda x, y, t, fill="#fff", font=None, anchor="w": \
        CV.create_text(x, y, text=t, fill=fill, font=font, anchor=anchor)
    o._menu_hits = []
    o._my_name = name
    o._my_helmet = dict(spec or {})
    o._menu_page = "helmet"
    return o


# The state worth LOOKING at: a design with every optional row showing.
SPEC = {"base": "#161616", "accent": "#d4ff00", "pattern": "blade",
        "weight": "bold", "pattern2": "visorband", "accent2": "#ff3d7a",
        "weight2": "normal", "number": 4, "ink": "#f2f2f2", "flip": False}

o = overlay(SPEC)
CV.delete("all")
o._draw_helmet_page(x=8, y=8)
_root.update()
time.sleep(0.35)          # let the compositor settle before grabbing

try:
    from PIL import ImageGrab
    x0 = _root.winfo_rootx()
    y0 = _root.winfo_rooty()
    img = ImageGrab.grab(bbox=(x0, y0, x0 + W, y0 + H))
    img.save(OUT)
    print("wrote %s  %s" % (OUT, img.size))
except Exception as ex:
    print("could not grab: %s: %s" % (type(ex).__name__, ex))
_root.destroy()
