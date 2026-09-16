"""Render the WHOLE RacerTV overlay to a PNG, as it sits over the game.

    python tests/uishot.py [out.png]

Every panel is drawn by the method the overlay calls each frame, at its real
game-relative coordinates, in the REAL FONTS -- Michroma for the chyron and
Chakra Petch for the data, loaded privately from the .ttf files next to the
app exactly as the running overlay loads them.

THAT LAST PART IS THE POINT. Earlier preview tools substituted Segoe UI
because it was one line shorter, and every judgement made from those images
was a judgement about the wrong typeface. A preview that quietly swaps the
font is worse than no preview: it looks authoritative and it is wrong.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import ctypes
import os
import sys
import time

sys.path.insert(0, r"D:\R3EOverlay")

import tkinter as tk
import tkinter.font as tkfont

_DIR = r"D:\R3EOverlay"
_root = tk.Tk()
_src = open(os.path.join(_DIR, "tests", "smoke.py")).read()
exec(_src.split('run_session("RACE"')[0])          # noqa: E402

from overlay_common import PANEL_BG                # noqa: E402
import r3e_data as R                               # noqa: E402
import helmet as H                                 # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else r"D:\R3EOverlay\_previews\_ui_preview.png"
W, HGT = 1600, 900          # a 16:9 game window, scaled from 1920x1080


# ---- the fonts, loaded the way the app loads them -----------------------
def load_fonts():
    DISP = "Bahnschrift SemiBold SemiConden"
    BC = "Bahnschrift SemiCondensed"
    BCB = "Bahnschrift SemiBold SemiConden"
    try:
        n = 0
        for ttf in ("Michroma-Regular.ttf", "ChakraPetch-Regular.ttf",
                    "ChakraPetch-SemiBold.ttf", "ChakraPetch-Bold.ttf"):
            fp = os.path.join(_DIR, ttf)
            if os.path.exists(fp):
                n += bool(ctypes.windll.gdi32.AddFontResourceExW(fp, 0x10, 0))
        if n >= 4:
            return "Michroma", "Chakra Petch", "Chakra Petch SemiBold"
    except Exception:
        pass
    return DISP, BC, BCB


DISP, BC, BCB = load_fonts()
print("fonts: display=%s  body=%s" % (DISP, BC))

_root.geometry("%dx%d+0+0" % (W, HGT))
_root.overrideredirect(True)          # no title bar, so the grab is only the UI
_root.configure(bg=PANEL_BG)
CV = tk.Canvas(_root, width=W, height=HGT, bg=PANEL_BG, highlightthickness=0)
CV.pack()


def build():
    o = headless_overlay(fake_tts=True)
    o._cv_real = CV
    o._bg_real = None
    o._ox = o._oy = 0
    o.sw, o.sh = W, HGT
    o.game_x = o.game_y = 0
    o.visible = True
    o.compact = False
    o.speedo = "kmh"
    o.debug = False
    o._DISP, o._BC, o._BCB = DISP, BC, BCB
    o.f_row = tkfont.Font(family=BC, size=11)
    o.f_row_b = tkfont.Font(family=BCB, size=11)
    o.f_hdr = tkfont.Font(family=DISP, size=12 if DISP == "Michroma" else 14)
    o.f_sub = tkfont.Font(family=BC, size=10)
    o.f_small = tkfont.Font(family=BC, size=9)
    o.f_small_b = tkfont.Font(family=BCB, size=9)
    o.f_tow = tkfont.Font(family=BC, size=11)
    o.f_tow_b = tkfont.Font(family=BCB, size=11)
    o.f_tiny = tkfont.Font(family=BC, size=8)
    o.f_spd = tkfont.Font(family=DISP, size=20 if DISP == "Michroma" else 24)
    o.f_gear = tkfont.Font(family=DISP, size=14 if DISP == "Michroma" else 17)

    # EVERY PANEL ONTO ONE CANVAS, at its true game-relative position. The
    # real `_begin_panel` moves a small window per panel; here the origin is
    # simply never offset, so each stage draws exactly where it would appear
    # over the game.
    def begin(name, lx, ly, w, h):
        o._ox = o._oy = 0
        return o.canvas
    o._begin_panel = begin
    o.text = lambda x, y, t, fill="#fff", font=None, anchor="w": \
        CV.create_text(x, y, text=t, fill=fill, font=font, anchor=anchor)
    o._menu_hits = []
    o._my_name = "Dante_K"
    o._my_helmet = {"base": "#161616", "accent": "#d4ff00", "pattern": "blade",
                    "weight": "bold", "number": 4, "ink": "#f2f2f2"}
    return o


NAMES = ["Zolder_Zed", "vTec_Ryan", "Dante_K", "Ana_Ferreira", "apex_andy",
         "BrakeLate", "nurburgnerd", "MilaS", "T.Okafor", "Lap1Hero"]

o = build()
s = make_shared(2, ncars=len(NAMES))
s.session_phase = 5
s.player.game_simulation_time = 600.0
s.session_time_remaining = 900.0
s.number_of_laps = 14
s.completed_laps = 6
s.car_speed = 61.0          # m/s
s.engine_rps = 780.0
s.max_engine_rps = 900.0
s.gear = 5
for i, d in enumerate(s.all_drivers_data_1[:len(NAMES)]):
    # NULL-TERMINATED. Without the trailing 0 the leftover bytes of whatever
    # was in the buffer run on, and the tower came out reading "DANTE_KSSI"
    # and "LAP1HEROKE" -- a preview bug that looks exactly like a product bug.
    nb = NAMES[i].encode("utf-8")[:62] + bytes([0])
    for k in range(64):
        d.driver_info.name[k] = nb[k] if k < len(nb) else 0
    d.driver_info.slot_id = i
    d.place = i + 1
    d.completed_laps = 6
    d.car_speed = 61.0
    d.lap_distance_fraction = 0.42 - i * 0.012
    d.time_delta_front = 0.4 + i * 0.3
    d.sector_time_previous_self[0] = 30.1
    d.sector_time_previous_self[1] = 62.4
    d.sector_time_previous_self[2] = 102.881
s.vehicle_info.slot_id = 2               # we are watching Dante_K, P3

# Let the real pipeline populate its own state, then draw.
for _ in range(3):
    o.update_stats(s)

CV.delete("all")
STAGES = [("header", lambda: o.draw_header(s)),
          ("flags", lambda: o.draw_flags(s)),
          ("penalty", lambda: o.draw_penalty(s)),
          ("tower", lambda: o.draw_tower(s)),
          ("relative", lambda: o.draw_relative(s)),
          ("objective", lambda: o.draw_objective(s))]
for nm, fn in STAGES:
    try:
        fn()
    except Exception as ex:
        print("  %-10s %s: %s" % (nm, type(ex).__name__, ex))

# the speedo, which is its own stage in the real frame
try:
    o.draw_speedo(s)
except Exception as ex:
    print("  speedo %s: %s" % (type(ex).__name__, ex))

# radio cards: the engineer, and a rival keying the mic
try:
    o.radio_msgs = []
    for i, (who, txt, eng) in enumerate(
            [("ENGINEER", "Box this lap, box this lap.", True),
             ("vTec_Ryan", "That was never a racing line.", False)]):
        col = ("#ff8e72" if eng else
               H.readable(H.card_colour(H.generated(who)), "#16100f"))
        o._draw_bubble(W - 330, 250 + i * 62, 300,
                       {"name": who, "text": txt, "color": col,
                        "engineer": eng, "until": 9e9, "at": 0.0})
except Exception as ex:
    print("  radio %s: %s" % (type(ex).__name__, ex))

# the settings menu, open on the designer page
try:
    o._menu_page = "helmet"
    o._menu_hits = []
    o._draw_helmet_page(x=40, y=430)
except Exception as ex:
    print("  designer %s: %s" % (type(ex).__name__, ex))

# THE WINDOW MUST ACTUALLY BE IN FRONT BEFORE IT IS GRABBED.
#
# ImageGrab takes a rectangle of the SCREEN, not of a window. A borderless Tk
# window that has not been raised sits behind whatever was already there, and
# the grab silently returns that instead -- the first run of this tool
# captured the desktop underneath and wrote it out as though it were the
# overlay. A preview that can quietly photograph the wrong thing is worse than
# no preview, so it now raises itself, waits, and then CHECKS.
_root.attributes("-topmost", True)
_root.lift()
_root.focus_force()
for _ in range(6):
    _root.update()
    time.sleep(0.15)

try:
    from PIL import ImageGrab
    x0, y0 = _root.winfo_rootx(), _root.winfo_rooty()
    img = ImageGrab.grab(bbox=(x0, y0, x0 + W, y0 + HGT))

    # PROOF WE PHOTOGRAPHED OUR OWN WINDOW. A marker is painted in a known
    # corner and read back out of the grab; if it is not there, something else
    # was in front and the image is of that, so write nothing at all.
    MARK = (255, 0, 255)
    CV.create_rectangle(0, HGT - 6, 6, HGT, fill="#ff00ff", outline="")
    _root.update()
    time.sleep(0.25)
    img = ImageGrab.grab(bbox=(x0, y0, x0 + W, y0 + HGT))
    got = img.convert("RGB").getpixel((2, HGT - 3))
    if max(abs(a - b) for a, b in zip(got, MARK)) > 24:
        print("REFUSED: the grab is not our window (marker read %s, wanted %s)"
              % (got, MARK))
        print("         nothing written -- another window is in front.")
    else:
        # crop the marker back off and save
        img.crop((0, 0, W, HGT - 8)).save(OUT)
        print("wrote", OUT)
except Exception as ex:
    print("could not grab: %s: %s" % (type(ex).__name__, ex))
_root.destroy()
