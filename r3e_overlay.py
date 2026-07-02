"""
RaceRoom replay/broadcast overlay.

A transparent, always-on-top, click-through window that reads RaceRoom's
"$R3E" shared memory and draws:
  - a timing tower (position, car #, name, laps, gap-to-leader / interval)
  - a session header (track, session type, lap counter / time remaining)
  - a live track map built from car world positions

Works in replays (the driver array populates during replay playback).

RUN:   python r3e_overlay.py
QUIT:  Ctrl+Shift+Q  (works even though the window is click-through)

IMPORTANT: RaceRoom must run in *Borderless* or *Windowed* mode for the
overlay to be visible on top. Exclusive fullscreen will hide it.
"""
import ctypes
import json
import os
import random
import re
import time
from ctypes import wintypes
from types import SimpleNamespace
import tkinter as tk
import tkinter.font as tkfont

import r3e_data as R
import avatars
from lines import (   # dialogue pools (moved out of this file for size)
    COMMENTATOR_NAME, PUNDIT_NAME, COMMENTATOR_FULL, PUNDIT_FULL,
    COMMENTARY_LINES, CROSSTALK, CROSSTALK_ACK, CROSSTALK_ANSWERS,
    DRIVER_FINISH, EASTER_EGGS, ENGINEER_LINES, ENGINEER_PRACTICE, ENGINEER_QUALI,
    EXTRA_LINES, LEAD, LORE_COMM_BY_TRACK, LORE_PUNDIT_BY_TRACK,
    MOOD_FRUSTRATED, MOOD_PUMPED, NATIVE_RADIO,
    NATIVE_RADIO_QUALI,
    PERSONAS, PERSONA_KEYS,
    PUNDIT_LINES, PUNDIT_PICK, REVENGE, RIVAL_QUALI,
    SECTOR_COACH,
    SHORT_TRACK, TRACK_COACH, TRACK_FACTS, TRACK_PUNDIT, TRACK_PUNDIT_BY_TRACK,
    TRACK_TIPS, CORNER_NAMES)

import sys as _sys
if getattr(_sys, "frozen", False):       # PyInstaller: assets sit next to the exe
    _DIR = os.path.dirname(_sys.executable)
else:
    _DIR = os.path.dirname(os.path.abspath(__file__))

# ----- team-radio personalities ----------------------------------------------
# Each driver is assigned ONE persona (consistently, by name) and speaks from
# its pools. {pos} is replaced with the driver's current position.
# Categories:  overtaken = you passed them | caught = you're closing on them |
#              crash = they spun/crashed   | taunt = they just passed YOU
# Language: explicit (full send), as requested.

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
gdi32 = ctypes.windll.gdi32

# Type SetWindowPos so HWND_TOPMOST (-1) marshals as a real handle on 64-bit
# (otherwise it can be passed as a bad 32-bit value and topmost silently fails).
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                wintypes.UINT]
user32.SetWindowPos.restype = wintypes.BOOL
HWND_TOPMOST = wintypes.HWND(-1)
SWP_NOMOVE_NOSIZE_NOACT = 0x1 | 0x2 | 0x10

# GDI region calls — type them so 64-bit HRGN handles aren't truncated
gdi32.CreateRectRgn.restype = ctypes.c_void_p
gdi32.CreateRectRgn.argtypes = [ctypes.c_int] * 4
gdi32.CombineRgn.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                             ctypes.c_void_p, ctypes.c_int]
gdi32.DeleteObject.argtypes = [ctypes.c_void_p]
user32.SetWindowRgn.argtypes = [wintypes.HWND, ctypes.c_void_p, wintypes.BOOL]


def _proc_image(pid):
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(512)
        size = wintypes.DWORD(512)
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return buf.value
        return ""
    finally:
        kernel32.CloseHandle(h)


_WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def find_game_rect():
    """Return (x, y, w, h) of the RaceRoom (RRRE64.exe) main window, or None."""
    best = {"area": 0, "rect": None}

    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        img = _proc_image(pid.value).lower()
        if not img.endswith("rrre64.exe"):
            return True
        r = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(r)):
            return True
        w, h = r.right - r.left, r.bottom - r.top
        area = w * h
        if w > 200 and h > 200 and area > best["area"]:
            best["area"] = area
            best["rect"] = (r.left, r.top, w, h)
        return True

    user32.EnumWindows(_WNDENUMPROC(cb), 0)
    return best["rect"]

# ----- look & feel -----------------------------------------------------------
CHROMA = "#010102"      # fully transparent key color (must be unused elsewhere)
WIN_ALPHA = 0.86        # whole-window opacity: solid SOLID dark panels (no dotty
                        # stipple behind text) but slightly see-through over the game
PANEL_STIPPLE = ""        # solid panel backgrounds (stipple looked pixelated behind
                          # the data); transparency now comes from WIN_ALPHA + CHROMA
PANEL_ALPHA = 0.55        # (legacy whole-window alpha; superseded by stipple+CHROMA)
PANEL_BG = "#0c1014"
PANEL_OUTLINE = "#2b313b"
# broadcast "card" styling — dark fill, thin subtle border, rounded corners,
# coloured accent strip (shared by the header, radio bubbles and commentary)
CARD_BG = "#0d1320"
CARD_BG2 = "#0a0d12"
CARD_BORDER = "#2a3440"
HEADER_ACCENT = "#39d0e0"
TEXT = "#f2f4f7"
DIM = "#9aa3ad"
ACCENT = "#ffd23f"      # viewed/focused car
LEADER = "#5cc8ff"
PURPLE = "#c77dff"      # session best (fastest)
GREEN = "#69db7c"       # personal best
ENGINEER_COLOR = "#39d0e0"   # your engineer's radio colour (not a driver)
COMMENTATOR_COLOR = "#ffcf33"  # broadcast booth caption colour


_LEET = {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "8": "b", "9": "g"}


def pronounce(name):
    """Turn a gamer-tag into something a TTS voice says cleanly, WITHOUT
    changing what's shown on screen. De-leets (OV3R BOY -> Over Boy), splits on
    separators, drops repeated tokens, and title-cases so ALL-CAPS tags aren't
    spelled out letter by letter."""
    toks, last = [], None
    for tok in re.split(r"[\s\-_/.|]+", name):
        if not tok:
            continue
        if any(c.isalpha() for c in tok):            # a word, not a pure number
            tok = "".join(_LEET.get(c, c) for c in tok)
        low = tok.lower()
        if low != last:                              # drop immediate duplicates
            toks.append(tok)
            last = low
    return " ".join(toks).title() if toks else name


def _safe_format(tmpl, kw):
    """str.format that never raises on a missing/extra key (blanks missing)."""
    class _D(dict):
        def __missing__(self, k):
            return ""
    try:
        return tmpl.format_map(_D(kw))
    except Exception:
        return tmpl



# how hyped the booth voice gets per event (0 calm .. 2 max)
CAT_INTENSITY = {
    "start": 1, "overtake": 2, "overtake_long": 2, "leadchange": 2, "fastlap": 1,
    "spin": 2, "battle": 2, "battle_mid": 1, "battle_sustained": 2,
    "pit": 0, "lastlap": 2, "win": 2,
    "second": 1, "third": 1, "summary": 1, "closing": 1, "pulling_away": 0,
    "recovery": 1, "podium_lock": 0, "penalty": 1, "yellow": 1, "analysis": 0,
    "lap_milestone": 0, "standings": 0, "praise": 0, "criticism": 0,
    "time_remaining": 1,
    "track_generic": 0, "track_fact": 0, "crosstalk_q": 0, "stat": 0,
    "car": 0, "pass_clean": 1, "midpack": 0,
    "late": 2, "final_lap": 2,
    "pregrid": 1,
    "quali_start": 1, "practice_start": 0, "quali_fastlap": 1, "quali_pole": 2,
    "quali_improve": 0, "quali_standings": 0, "quali_final": 1, "practice_note": 0,
    "session_colour": 0, "lap_report": 1, "lap_report_slow": 0,
    "insight_lead_slim": 1, "insight_lead_big": 0, "insight_podium_fight": 1,
    "insight_field_spread": 0, "insight_laps_left": 1, "insight_time_left": 1,
    "offtrack": 2, "offtrack_ack": 0, "offtrack_more": 2, "offtrack_chaos": 2,
    "ranwide": 1,
    "offtrack_cut": 2, "offtrack_late": 2, "broadcast": 0, "retake": 2,
    "arc_cost": 1, "arc_recovered": 1, "shuffle": 2, "driverstory_q": 0,
    "lore_q": 0, "lore_a": 0, "lore_q_rally": 0, "lore_a_rally": 0,
    "signoff": 1, "quali_goals": 0, "booth_joke": 0,
}
# spoken penalty names by penaltyType (RaceRoom PenaltyType enum)
PENALTY_SPOKEN = {0: "drive-through penalty", 1: "stop-and-go penalty",
                  2: "pit-stop penalty", 3: "time penalty", 4: "slow-down penalty",
                  5: "disqualification"}
# which events earn a co-commentator follow-up (and how often) — keep the booth
# chatting back and forth on the big moments
PUNDIT_AFTER = {"overtake": 0.7, "overtake_long": 0.8, "spin": 0.75,
                "leadchange": 0.7, "win": 0.0, "battle": 0.5, "battle_mid": 0.4,
                "battle_sustained": 0.6,
                "penalty": 0.7, "yellow": 0.6, "closing": 0.3, "recovery": 0.5,
                "fastlap": 0.4, "analysis": 0.45, "standings": 0.3,
                "lap_milestone": 0.3}

# radio category -> driver-avatar emotion (the face drawn in the bubble)
ENG_EMOTION = {
    "start": "fired", "win": "happy", "podium": "happy", "recovery": "fired",
    "slip": "sad", "finish_strong": "happy", "finish_points": "neutral",
    "finish_low": "sad", "fastest": "smug", "lastlap": "fired", "pit": "neutral",
    "lead": "smug", "gained": "happy", "lost": "sad", "catching": "fired",
    "dropping": "worried", "defending": "worried", "clear": "smug",
    "encourage": "neutral", "enc_top": "smug", "enc_mid": "neutral",
    "enc_back": "worried", "info_ahead": "neutral", "info_behind": "neutral",
    "nextlap": "worried", "tyres_gone": "worried",
    "tyre_cold": "neutral", "tyre_hot": "worried",
    "tyre_hot_traffic": "worried", "brake_hot": "worried",
    "engine_hot": "worried", "engine_hot_dmg": "worried",
    "gained_where": "happy", "section_ahead": "neutral",
}
# vivid, broadcast-style per-driver colours (assigned consistently by name)
# 20 distinct, well-spaced colours (assigned sequentially per driver, so the
# first 20 cars on track each get a unique one before any repeat)
DRIVER_COLORS = [
    "#ff3b3b", "#ff7a1a", "#ffb000", "#ffe24d", "#b6e02e",
    "#4fd13a", "#16c98a", "#00c2c7", "#29a8ff", "#4f7bff",
    "#8a6dff", "#b964ff", "#e85aff", "#ff5db4", "#ff6f61",
    "#c98a3c", "#88c057", "#5ad1b0", "#c3a6ff", "#9fd8ff",
]
YELLOWT = "#e6c84a"     # slower than best
CYAN = "#4dd6e0"        # push-to-pass
# tyre compound dot colors, keyed by tire_subtype (2=soft,3=med,4=hard,
# 0=primary,1=alternate)
TYRE_COLORS = {2: "#e03131", 3: "#f1c40f", 4: "#e9ecef",
               0: "#4dabf7", 1: "#69db7c"}
ROW_H = 22
MAX_ROWS = 24
CORNER_NBINS = 180      # lap-fraction bins for learning corner positions (2°)
UPDATE_MS = 50          # 20 Hz — snappier event detection + tower updates
PLACE_CONFIRM_TICKS = 6  # a position must hold this many ticks (~300ms) before
                         # the booth/radio treat it as a REAL change. This kills
                         # the side-by-side flicker that made the booth call a
                         # pass when two cars were merely running level. The TIMING
                         # TOWER is unaffected — it sorts by live track position —
                         # so the display stays instant; only the spoken overtake
                         # CALLS wait for the new order to actually stick.

VK_CONTROL, VK_SHIFT, VK_Q, VK_O, VK_E, VK_M = 0x11, 0x10, 0x51, 0x4F, 0x45, 0x4D
VK_D = 0x44
VK_C = 0x43


def key_down(vk):
    return ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000


def _BUBBLE_H(n_lines):
    """Radio bubble height for n message lines (shared by draw_radio + _draw_bubble
    so the stacking maths and the drawn box always agree)."""
    return 40 + 18 * n_lines


class _TC:
    """Canvas wrapper that subtracts a panel's origin, so existing draw code
    written in game-relative coords lands correctly inside a small panel window."""
    def __init__(self, cv, ox, oy):
        self.cv, self.ox, self.oy = cv, ox, oy

    def create_rectangle(self, x1, y1, x2, y2, **kw):
        return self.cv.create_rectangle(x1 - self.ox, y1 - self.oy,
                                        x2 - self.ox, y2 - self.oy, **kw)

    def create_oval(self, x1, y1, x2, y2, **kw):
        return self.cv.create_oval(x1 - self.ox, y1 - self.oy,
                                   x2 - self.ox, y2 - self.oy, **kw)

    def create_text(self, x, y, **kw):
        return self.cv.create_text(x - self.ox, y - self.oy, **kw)

    def create_line(self, *a, **kw):
        pts = [a[i] - (self.ox if i % 2 == 0 else self.oy) for i in range(len(a))]
        return self.cv.create_line(*pts, **kw)

    def create_polygon(self, *a, **kw):
        pts = [a[i] - (self.ox if i % 2 == 0 else self.oy) for i in range(len(a))]
        return self.cv.create_polygon(*pts, **kw)


class _Panel:
    """One small always-on-top window (like the toggle, which composites
    reliably over the borderless game — a single big window does not)."""
    def __init__(self, root):
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        try:
            # near-opaque window so TEXT stays crisp; the see-through look comes
            # from CHROMA-keyed empty areas + stippled panel BACKGROUNDS, so the
            # background drops out to the game while numbers/text stay solid.
            self.win.attributes("-alpha", WIN_ALPHA)
            self.win.attributes("-transparentcolor", CHROMA)
        except Exception:
            pass
        self.win.configure(bg=CHROMA)
        self.cv = tk.Canvas(self.win, highlightthickness=0, bd=0, bg=CHROMA)
        self.cv.pack(fill="both", expand=True)
        self.win.withdraw()
        self.shown = False
        self._geo = None
        self.hwnd = None
        try:
            self.win.update_idletasks()
            h = user32.GetAncestor(self.win.winfo_id(), 2)
            ex = user32.GetWindowLongW(h, -20)
            user32.SetWindowLongW(h, -20, ex | 0x80 | 0x8000000)  # TOOLWINDOW|NOACTIVATE
            self.hwnd = h
        except Exception:
            pass

    def place(self, x, y, w, h):
        w, h = max(1, int(w)), max(1, int(h))
        x, y = int(x), int(y)
        geo = (x, y, w, h)
        if geo != self._geo:
            self.win.geometry(f"{w}x{h}+{x}+{y}")
            self.cv.config(width=w, height=h)
            self._geo = geo
        self.cv.delete("all")
        if not self.shown:
            self.win.deiconify()
            self.shown = True
        if self.hwnd:
            user32.SetWindowPos(self.hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                                SWP_NOMOVE_NOSIZE_NOACT)
        return self.cv

    def hide(self):
        if self.shown:
            self.win.withdraw()
            self.shown = False


class Overlay:
    def __init__(self):
        self.reader = R.R3EReader()
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        # Root stays hidden; every panel is its own small always-on-top window
        # (a single big window gets shoved behind the borderless game by the
        # GPU's multiplane-overlay path — small windows composite reliably).
        self.root.withdraw()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.sw, self.sh = sw, sh        # game width/height (updated per frame)
        self.game_x, self.game_y = 0, 0  # game window origin (updated per frame)
        self.cur_rect = None
        self.panels = {}                 # name -> _Panel
        self._used = set()               # panels drawn this frame
        self._cv_real = None             # current panel's raw canvas
        self._ox = self._oy = 0          # current panel origin (game-relative)
        self._car_names = self._load_car_names()   # model_id -> car name

        # Broadcast-TV look: Bahnschrift (ships with Win11) — condensed, with
        # TABULAR (fixed-width) digits so the timing tower columns stay aligned.
        # SemiBold SemiCondensed on headers reads like an F1 graphics package.
        _BC = "Bahnschrift SemiCondensed"
        _BCB = "Bahnschrift SemiBold SemiConden"
        self.f_row = tkfont.Font(family=_BC, size=12)
        self.f_row_b = tkfont.Font(family=_BCB, size=12)
        self.f_hdr = tkfont.Font(family=_BCB, size=15)
        self.f_sub = tkfont.Font(family=_BC, size=11)

        # track-map: accumulating bounds + sampled track outline (quantized
        # car positions over time trace the circuit shape)
        self.minx = self.minz = 1e9
        self.maxx = self.maxz = -1e9
        self.track_cells = {}     # {(qx,qz): lap_fraction}
        self.sf_xy = None         # start/finish world position
        self.MAP_CELL = 4.0       # meters per sample cell

        self.visible = True
        self._o_prev = False
        self.compact = False     # compact tower (racing) vs full (replay watching)
        self._e_prev = False
        self.last_live = None    # last good snapshot, kept when focus is lost
        self._was_in_action = False
        self._pending_handshakes = []  # timestamps to hide/show the window at
        self.f_small = tkfont.Font(family="Bahnschrift SemiCondensed", size=10)
        self.f_small_b = tkfont.Font(family="Bahnschrift SemiBold SemiConden",
                                     size=10)
        # slightly larger fonts dedicated to the timing tower (so it can grow
        # without enlarging the other panels)
        self.f_tow = tkfont.Font(family="Bahnschrift SemiCondensed", size=12)
        self.f_tow_b = tkfont.Font(family="Bahnschrift SemiBold SemiConden", size=12)

        # broadcast stats (reset per session). Initialised here too — not just in
        # update_stats' per-session reset — so the radio/commentary stages can
        # never hit an AttributeError if the stats stage ever throws first.
        self._sess_key = None
        self.grid_place = {}     # slot -> first-seen place (for ▲▼ arrows)
        self.last_laps = {}      # slot -> completed_laps (detect lap done)
        self.best_lap = {}       # slot -> best lap time (quali/practice tower)
        self.fastest = {"time": None, "slot": None, "car": 0, "name": "", "at": 0.0}
        self.cum_gap = {}        # slot -> seconds to leader (track-position based)
        self.interval = {}       # slot -> seconds to car directly ahead
        self.ref_lap = None      # representative lap time for gap conversion
        self.cplace = {}         # slot -> debounced 'confirmed' place
        self._cpend = {}         # slot -> (candidate place, ticks held)
        self._racing = False     # has the race actually gone green yet?
        self._green_at = -1e9    # time the race went green (grid-sort window)
        self._gone = set()       # slots out of the race (DNF / frozen / left)
        self._move_sig = {}      # slot -> (movement signature, last-change time)
        self._tow_rank = {}      # slot -> live track-position rank (race tower)
        self._q_off_lv = 1       # prev player lap-valid (non-race off-track edge)
        self._q_off_watch = None # (deadline, ref_speed) confirming a genuine off
        self._q_off_cd = -1e9    # last confirmed off (re-arm cooldown)
        self._q_ref_spd = 0.0    # rolling recent-peak speed reference
        self._q_lvs = -1         # prev lap_valid_state (next-lap-invalid edge)
        self._q_cuts = 0         # prev cut_track_warnings (track-limits edge)
        self._sess_gen = 0       # bumped on a detected race restart
        self._prev_lead_laps = None  # leader lap count last tick (restart detect)
        self._last_found_t = 0.0     # last time the RaceRoom window was seen
        self._tts_silenced = False   # audio stopped because the game is gone

        # team-radio engine state
        self.prev_places = {}    # slot -> place last tick
        self.prev_int_focus = None
        self.radio_msgs = []     # active bubbles [{name,text,color,until}]
        self.last_radio_t = 0.0
        self.driver_radio_cd = {}  # slot -> last time we aired their radio
        self._last_line = {}       # (persona,cat) -> last line index (no repeats)
        self._chase = {}           # target slot -> set of chase tiers already aired
        self._eng_cd = 0.0         # last time your engineer spoke
        self._eng_flags = {}       # once-per-session engineer triggers
        self._rivals = {}          # slot -> time you last overtook them (revenge)
        self._mood = {}            # slot -> momentum (-=tumbling, +=charging)
        self._prev_gap = None      # last interval to car ahead (for direction)
        self._prev_gapb = None     # last interval to car behind
        self._enc_cd = 0.0         # last gentle-encouragement time
        self._sec_laps = {}        # slot -> completed_laps (sector-coach lap edge)
        self._eng_sec_cd = 0.0     # sector-coaching cooldown (race)
        self._intro_emit_t = None  # when the booth aired its session opener
        self._intro_aired = False  # engineer gate: has the intro finished?
        self._eng_ip = 0           # last incident-point count (every-pickup warn)
        self._eng_ip_cd = -1e9     # incident-point report cooldown
        self._sess_start_t = 0.0   # session start (intro-gate safety release)
        self._signed_off = False   # broadcast over after the closing sign-off
        self._filler_until = 0.0   # est. time a colour/filler line finishes
        self.RADIO_ENG_CD = 14.0   # min seconds between engineer messages

        # team-radio voice (TTS) — optional; never breaks the overlay
        self.tts = None
        try:
            import tts as _tts
            self.tts = _tts.Tts()
        except Exception:
            self.tts = None
        self._m_prev = False
        self.RADIO_GLOBAL_CD = 5.5   # min seconds between any two bubbles
        self.RADIO_DRIVER_CD = 25.0  # min seconds between same driver's bubbles
        self.RADIO_HOLD = 6.0        # how long a bubble stays on screen
        self.RADIO_NEAR = 4          # crashes within N places of you = high priority
        self.RADIO_FAR_CHANCE = 0.6  # chance a far-away crash gets a reaction
        self.RADIO_MAX_BUBBLES = 3   # max bubbles on screen at once (no flooding)
        self.RADIO_MAX_BURST = 3     # max new messages from one big incident

        # post-race podium screen
        self._podium_seen_at = 0.0    # when the race-end was first seen (podium)
        self._podium = None          # captured top-3 snapshot (list of dicts)
        self._podium_at = 0.0        # time the podium was captured (drop anim)
        self._podium_until = 0.0     # show until this time
        self._podium_key = None      # session key the podium was captured for
        self._wrap_until = 0.0       # protect post-race wrap from the leave flush
        self.PODIUM_HOLD = 12.0      # seconds the podium stays up

        # play-by-play commentary (Ctrl+Shift+C toggles it)
        self.commentary_on = True
        self._c_prev = False
        self.COMMENTARY_CD = 5.0     # min seconds between commentary lines (the
                                     # "breather" — keeps the booth lively but not
                                     # a wall of noise; incidents bypass this)
        self._comm_prev = {}         # slot -> place (own change tracker)
        self._comm_cd = 0.0
        self._comm_flags = {}
        self._comm_lead = None
        self._comm_fastest_at = 0.0
        self._comm_pit = {}
        self._comm_key = None
        self._comm_caption = None    # {text, until} lower-third caption
        self._pron = {}              # display name -> TTS pronunciation
        self._dcolor = {}            # driver name -> assigned colour (unique-ish)
        self._dcolor_n = 0           # next colour index to hand out

        # diagnostics (Ctrl+Shift+D toggles an on-screen HUD)
        self.debug = False
        self._d_prev = False
        self._tick_ms = 0.0
        self._stage_err = {}         # stage name -> last exception text
        self._radio_recent = []      # last few emitted radio lines (for the HUD)
        self._dbg_moves = 0          # position changes seen this session

        self.logo_h = 0
        self.logo_win = None
        self.logo_hwnd = None
        self.logo_img = None
        self.tower_logo = None        # smaller logo drawn atop the timing tower
        self.root.bind("<Escape>", lambda e: self.quit())
        self._build_logo()
        self._build_toggle_button()
        self._build_clock()
        self.tick()

    def _build_logo(self):
        """Show a broadcast logo (any .png/.gif in the folder) top-left."""
        import glob
        cands = [os.path.join(_DIR, n) for n in ("logo.png", "logo.gif", "logo.ppm")]
        cands += sorted(glob.glob(os.path.join(_DIR, "*.png")))
        cands += sorted(glob.glob(os.path.join(_DIR, "*.gif")))
        for p in cands:
            if not os.path.exists(p):
                continue
            try:
                orig = tk.PhotoImage(file=p)
                img = orig
                while img.width() > 230:          # integer downscale to fit
                    img = img.subsample(2)
                self.logo_img = img
                # a SMALLER copy to sit at the top of the timing tower
                tl = orig
                while tl.width() > 150:
                    tl = tl.subsample(2)
                self.tower_logo = tl
                w = tk.Toplevel(self.root)
                w.overrideredirect(True)
                w.attributes("-topmost", True)
                w.configure(bg="#010102")
                try:
                    w.attributes("-transparentcolor", "#010102")   # see-through bg
                except Exception:
                    pass
                tk.Label(w, image=img, bg="#010102", bd=0).pack()
                hwnd = user32.GetAncestor(w.winfo_id(), 2)
                ex = user32.GetWindowLongW(hwnd, -20)
                user32.SetWindowLongW(hwnd, -20, ex | 0x80 | 0x8000000)
                self.logo_win, self.logo_hwnd = w, hwnd
                self.logo_h = img.height()
                return
            except Exception:
                pass

    # ---- per-panel window plumbing ----
    @property
    def canvas(self):
        return _TC(self._cv_real, self._ox, self._oy)

    def _begin_panel(self, name, lx, ly, w, h):
        """Start drawing a panel whose top-left is at game-relative (lx, ly).
        Positions its small window over the game and returns a translating
        canvas, so the existing game-relative draw code lands correctly."""
        p = self.panels.get(name)
        if p is None:
            p = _Panel(self.root)
            self.panels[name] = p
        p.place(self.game_x + lx, self.game_y + ly, w, h)
        self._used.add(name)
        self._cv_real = p.cv
        self._ox, self._oy = lx, ly
        return self.canvas

    def _hide_unused_panels(self):
        for name, p in self.panels.items():
            if name not in self._used:
                p.hide()

    def _build_toggle_button(self):
        """Small always-on-top CLICKABLE window (the main overlay is
        click-through, so the toggle lives in its own window)."""
        self.btn_win = tk.Toplevel(self.root)
        self.btn_win.overrideredirect(True)
        self.btn_win.attributes("-topmost", True)
        self.btn_win.configure(bg="#0a0d12")
        self.btn_lbl = tk.Label(self.btn_win, text="● OVERLAY", fg=GREEN,
                                bg="#0a0d12", font=("Segoe UI", 10, "bold"),
                                padx=12, pady=5, cursor="hand2")
        self.btn_lbl.pack()
        self.btn_lbl.bind("<Button-1>", lambda e: self.toggle_visible())
        self.btn_win.bind("<Button-1>", lambda e: self.toggle_visible())
        # toolwindow so it doesn't show in alt-tab
        try:
            h = ctypes.windll.user32.GetAncestor(self.btn_win.winfo_id(), 2)
            ex = ctypes.windll.user32.GetWindowLongW(h, -20)
            ctypes.windll.user32.SetWindowLongW(h, -20, ex | 0x80)
            self._btn_hwnd = h
        except Exception:
            self._btn_hwnd = None

    def _build_clock(self):
        """A small always-on REAL-WORLD clock (the local laptop time) so you can
        time online sessions that start at a set hour. Its own topmost window,
        shown whenever the overlay is running — even in menus."""
        self.clock_win = tk.Toplevel(self.root)
        self.clock_win.overrideredirect(True)
        self.clock_win.attributes("-topmost", True)
        self.clock_win.configure(bg="#0a0d12")
        self.clock_lbl = tk.Label(self.clock_win, text="--:--:--", fg=HEADER_ACCENT,
                                  bg="#0a0d12", font=("Consolas", 11, "bold"),
                                  padx=12, pady=4)
        self.clock_lbl.pack()
        try:
            h = ctypes.windll.user32.GetAncestor(self.clock_win.winfo_id(), 2)
            ex = ctypes.windll.user32.GetWindowLongW(h, -20)
            ctypes.windll.user32.SetWindowLongW(h, -20, ex | 0x80)   # toolwindow
            self._clock_hwnd = h
        except Exception:
            self._clock_hwnd = None

    def _place_button(self, found):
        """Pin the toggle to the game's top-LEFT and the logo to the top-RIGHT."""
        gx = self.cur_rect[0] if (found and self.cur_rect) else 0
        gy = self.cur_rect[1] if (found and self.cur_rect) else 0
        gw = self.cur_rect[2] if (found and self.cur_rect) else self.sw
        lx, ly = gx + 12, gy + 8
        # logo bug (top-RIGHT)
        if self.logo_win is not None:
            try:
                logo_w = self.logo_img.width() if self.logo_img else 200
                rx = gx + gw - logo_w - 12
                self.logo_win.geometry(f"+{rx}+{ly}")
                self.logo_win.attributes("-topmost", True)
                if self.logo_hwnd:
                    user32.SetWindowPos(self.logo_hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                                        SWP_NOMOVE_NOSIZE_NOACT)
            except Exception:
                pass
        by = ly   # toggle now sits in the top-left (logo moved to the right)
        try:
            self.btn_win.geometry(f"+{lx}+{by}")
            self.btn_win.attributes("-topmost", True)
            hwnd = (user32.GetAncestor(self.btn_win.winfo_id(), 2)
                    or self._btn_hwnd)
            if hwnd:
                self._btn_hwnd = hwnd
                user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                                    SWP_NOMOVE_NOSIZE_NOACT)
        except Exception:
            pass
        # real-world clock sits just below the toggle, top-left
        try:
            self.clock_win.geometry(f"+{lx}+{by + 32}")
            self.clock_win.attributes("-topmost", True)
            chwnd = (user32.GetAncestor(self.clock_win.winfo_id(), 2)
                     or self._clock_hwnd)
            if chwnd:
                self._clock_hwnd = chwnd
                user32.SetWindowPos(chwnd, HWND_TOPMOST, 0, 0, 0, 0,
                                    SWP_NOMOVE_NOSIZE_NOACT)
        except Exception:
            pass

    def _region(self, *a, **k):
        pass  # no longer used (each panel is its own window)

    def _lock_to_game(self):
        """Find the RaceRoom window and record its rect so panels position
        themselves over it. Returns True if found."""
        rect = find_game_rect()
        if rect is None:
            return False
        x, y, w, h = rect
        self.cur_rect = rect
        self.game_x, self.game_y = x, y
        self.sw, self.sh = w, h
        return True

    def quit(self):
        try:
            self.reader.close()
            if self.tts:
                self.tts.close()
        finally:
            self.root.destroy()

    # ---- drawing helpers (draw into the current panel via translating canvas) -
    def panel(self, x, y, w, h, fill=PANEL_BG, stipple=PANEL_STIPPLE):
        # stippled fill (screen-door transparency to the game) + a crisp solid
        # outline drawn separately so the border stays sharp
        self.canvas.create_rectangle(x, y, x + w, y + h, fill=fill,
                                     outline="", stipple=stipple or "")
        self.canvas.create_rectangle(x, y, x + w, y + h, fill="",
                                     outline=PANEL_OUTLINE, width=1)

    def _card(self, x, y, w, h, fill=CARD_BG, accent=None, side="top", r=7):
        """A broadcast 'card': rounded dark box + thin border + optional coloured
        accent (a top strip or a left bar). Rounded corners are see-through to
        the game via the panel's transparent-colour key — looks clean."""
        r = int(min(r, w / 2, h / 2))
        pts = [x + r, y, x + w - r, y, x + w, y, x + w, y + r,
               x + w, y + h - r, x + w, y + h, x + w - r, y + h, x + r, y + h,
               x, y + h, x, y + h - r, x, y + r, x, y]
        self.canvas.create_polygon(*pts, smooth=True, splinesteps=14,
                                   fill=fill, outline=CARD_BORDER, width=1)
        if accent:
            if side == "left":
                self.canvas.create_rectangle(x + 1, y + r, x + 4, y + h - r,
                                             fill=accent, outline="")
            else:                                   # top strip
                self.canvas.create_rectangle(x + r, y + 1, x + w - r, y + 4,
                                             fill=accent, outline="")

    def text(self, x, y, s, fill=TEXT, font=None, anchor="nw"):
        self.canvas.create_text(x, y, text=s, fill=fill,
                                font=font or self.f_row, anchor=anchor)

    # ---- main loop ----
    def tick(self):
        t0 = time.perf_counter()
        if key_down(VK_CONTROL) and key_down(VK_SHIFT) and key_down(VK_Q):
            return self.quit()
        o = bool(key_down(VK_CONTROL) and key_down(VK_SHIFT) and key_down(VK_O))
        if o and not self._o_prev:
            self.toggle_visible()
        self._o_prev = o
        e = bool(key_down(VK_CONTROL) and key_down(VK_SHIFT) and key_down(VK_E))
        if e and not self._e_prev:
            self.compact = not self.compact
        self._e_prev = e
        m = bool(key_down(VK_CONTROL) and key_down(VK_SHIFT) and key_down(VK_M))
        if m and not self._m_prev and self.tts:
            self.tts.toggle()
        self._m_prev = m
        dk = bool(key_down(VK_CONTROL) and key_down(VK_SHIFT) and key_down(VK_D))
        if dk and not self._d_prev:
            self.debug = not self.debug
        self._d_prev = dk
        ck = bool(key_down(VK_CONTROL) and key_down(VK_SHIFT) and key_down(VK_C))
        if ck and not self._c_prev:
            self.commentary_on = not self.commentary_on
        self._c_prev = ck

        found = self._lock_to_game()
        s = self.reader.read()
        live = (s is not None and s.version_major == 3 and
                (R.u8_to_str(s.track_name) != "" or s.num_cars > 0))
        # When RaceRoom CLOSES its shared-memory block can linger with the last
        # frame, so `live` stays true and the booth would commentate forever over
        # a dead session. Gate on the RaceRoom WINDOW actually being present
        # (debounced ~2.5s); if it's gone, silence the audio.
        if found:
            self._last_found_t = time.time()
        game_present = (time.time() - getattr(self, "_last_found_t", 0.0)) < 2.5
        if not game_present:
            if self.tts and not self._tts_silenced:
                self.tts.stop()
                self._tts_silenced = True
        elif self._tts_silenced and self.tts:
            self.tts.resume()
            self._tts_silenced = False
        game_running = bool(found or live)
        in_action = bool(game_present and live and self._in_action(s))

        # flush queued audio whenever we leave an active session — covers pause,
        # returning to menus/garage, and session restarts. The post-race wrap-up
        # is allowed to finish as the player drops to the results screen, BUT an
        # explicit PAUSE always stops audio immediately (it must never be held off
        # by the wrap protection).
        paused = bool(s is not None and s.game_paused == 1)
        if self._was_in_action and not in_action and self.tts:
            if paused or time.time() >= getattr(self, "_wrap_until", 0.0):
                self.tts.flush()
        self._was_in_action = in_action

        self._update_button(game_running, in_action)
        try:
            self.clock_lbl.config(text=time.strftime("%H:%M:%S"))
        except Exception:
            pass
        self._place_button(found)

        # draw the panels (each into its own small window). Each stage is
        # isolated: a failure in one (e.g. update_radio) must NOT abort the
        # rest of the frame, or panels drawn after it would appear frozen.
        self._used = set()
        if self.visible and in_action and self._drivers(s):
            stages = (("stats", self.update_stats), ("radio", self.update_radio),
                      ("comm", self.update_commentary),
                      ("header", self.draw_header), ("flags", self.draw_flags),
                      ("penalty", self.draw_penalty),
                      ("tower", self.draw_tower), ("relative", self.draw_relative),
                      ("fastest", self.draw_fastest_banner),
                      ("sectors", self.draw_sectors), ("map", self.draw_map),
                      ("bubbles", self.draw_radio), ("caption", self.draw_commentary),
                      ("podium", self.draw_podium))
            for nm, fn in stages:
                try:
                    fn(s)
                except Exception as ex:
                    self._stage_err[nm] = f"{type(ex).__name__}: {ex}"
        elif self.visible and in_action:
            try:
                self.draw_header(s)
                self._no_data_notice()
            except Exception:
                pass
        if self.debug and self.visible:
            try:
                self.draw_debug(s, game_running, in_action)
            except Exception:
                pass
        self._hide_unused_panels()   # hide whatever wasn't drawn this frame
        self._tick_ms = (time.perf_counter() - t0) * 1000.0
        self.root.after(UPDATE_MS, self.tick)

    def _drivers(self, s):
        # scan the whole array; some replay modes populate it without ever
        # setting the num_cars field, so don't trust num_cars as the gate.
        # EXCLUDE cars that are out: finish_status 2/3/4/5 = DNF/DNQ/DNS/DQ, plus
        # any slot flagged 'gone' (frozen on track = retired/disconnected). The
        # game leaves these in the array; without this the booth and team radio
        # keep talking about drivers who've left the race.
        gone = getattr(self, "_gone", ())
        return [d for d in s.all_drivers_data_1
                if d.place > 0 and d.finish_status not in (2, 3, 4, 5)
                and d.driver_info.slot_id not in gone]

    def _in_action(self, s):
        """True during a race/practice/qualy on track, or any replay."""
        if s.game_paused == 1:
            return False
        if s.game_in_replay == 1:
            return True
        if not self._drivers(s):
            return False
        return (s.game_in_menus != 1 and s.game_player_in_garage != 1
                and s.session_phase in (3, 4, 5, 6))

    def _no_data_notice(self):
        w = 470
        x = (self.sw - w) // 2
        y = 96
        self._begin_panel("notice", x, y, w, 50)
        self.panel(x, y, w, 50)
        self.text(x + 16, y + 14, "Waiting for replay data…",
                  fill=ACCENT, font=self.f_hdr, anchor="w")
        self.text(x + 16, y + 36,
                  "Press PLAY — RaceRoom only streams the field while the "
                  "replay is actually playing.",
                  fill=DIM, font=self.f_sub, anchor="w")

    def _update_button(self, game_running, in_action):
        if not self.visible:
            txt, col = "● OVERLAY: OFF — click to show", "#ffa94d"
        elif not game_running:
            txt, col = "● OVERLAY: waiting for RaceRoom", YELLOWT
        elif in_action:
            txt, col = "● OVERLAY: LIVE", GREEN
        else:
            txt, col = "● OVERLAY: standby (menus)", YELLOWT
        try:
            self.btn_lbl.config(text=txt, fg=col)
        except Exception:
            pass

    def toggle_visible(self):
        self.visible = not self.visible
        if self.visible:
            # turning back on -> force a fresh window + compositing handshake
            self._main_shown = False
            self._last_reassert = 0.0

    def draw_waiting(self, s):
        running = s is not None and s.version_major == 3
        x, y, w, h = 24, 24, 430, 70
        self.panel(x, y, w, h)
        self.canvas.create_oval(x + 14, y + 16, x + 26, y + 28,
                                fill=(GREEN if running else ACCENT), outline="")
        self.text(x + 38, y + 14, "RaceRoom Overlay – running", fill=TEXT,
                  font=self.f_hdr)
        msg = ("Connected. Load a session or replay to see timing."
               if running else
               "Waiting for RaceRoom… start the game in Borderless mode.")
        self.text(x + 38, y + 42, msg, fill=DIM, font=self.f_sub)
        self.text(x + w - 14, y + h - 6, "Ctrl+Shift+Q to close",
                  fill=DIM, font=self.f_sub, anchor="se")

    def draw_hint(self):
        self.text(self.sw - 12, self.sh - 8,
                  "Ctrl+Shift+O hide  ·  Ctrl+Shift+Q close",
                  fill=DIM, font=self.f_sub, anchor="se")

    def draw_flags(self, s):
        """Broadcast-style flag & penalty chips, centered under the header."""
        # while the end-of-race RESULT panel is dropped down (same top-centre
        # slot), suppress the flag row — otherwise the CHEQUERED chip sits right
        # on top of the podium strip.
        if self._podium and time.time() < self._podium_until:
            return
        chips = []  # (text, fg, bg)
        f = s.flags
        sectors = [i + 1 for i in range(3) if f.sector_yellow[i] == 1]
        if f.yellow == 1 or sectors:
            txt = "YELLOW FLAG" + (" S" + "".join(map(str, sectors)) if sectors else "")
            chips.append((txt, "#000000", "#ffd23f"))
        if f.blue == 1:
            chips.append(("BLUE FLAG", "#ffffff", "#2b6cff"))
        if f.black == 1:
            chips.append(("BLACK FLAG", "#ffffff", "#101010"))
        if f.black_and_white == 1:
            chips.append(("WARNING", "#101010", "#ffffff"))
        if f.white == 1:
            chips.append(("WHITE FLAG", "#101010", "#ffffff"))
        if f.checkered == 1:
            chips.append(("CHEQUERED", "#101010", "#ffffff"))

        # penalty for the currently-viewed car
        vslot = s.vehicle_info.slot_id
        pen_names = {0: "DRIVE-THROUGH", 1: "STOP & GO", 2: "PITSTOP",
                     3: "TIME PENALTY", 4: "SLOW DOWN", 5: "DISQUALIFIED"}
        for d in self._drivers(s):
            if d.driver_info.slot_id == vslot and d.penaltyType >= 0:
                chips.append((pen_names.get(d.penaltyType, "PENALTY"),
                              "#ffffff", "#e03131"))
                break

        if not chips:
            return
        # measure & center the row of chips
        pad_in, gap, h = 12, 8, 26
        widths = [self.f_row_b.measure(t) + pad_in * 2 for t, _, _ in chips]
        total = sum(widths) + gap * (len(chips) - 1)
        x = (self.sw - total) // 2
        y = 74
        self._begin_panel("flags", x, y, total, h)
        for (txt, fg, bg), w in zip(chips, widths, strict=False):
            self.canvas.create_rectangle(x, y, x + w, y + h, fill=bg, outline="")
            self.text(x + w / 2, y + h / 2, txt, fill=fg,
                      font=self.f_row_b, anchor="center")
            x += w + gap

    # spoken/short reasons for a penalty, keyed by (penaltyType, penaltyReason)
    # — the common ones RaceRoom hands out (see r3e.h penaltyType comments).
    _PEN_REASON = {
        (0, 1): "cutting the track", (0, 2): "pit-lane speeding",
        (0, 3): "a false start", (0, 4): "ignoring blue flags",
        (0, 5): "driving too slowly", (0, 9): "ignoring a slow-down",
        (1, 1): "cutting the track", (1, 2): "repeatedly cutting the track",
        (1, 3): "overtaking under yellow", (4, 1): "cutting the track",
        (4, 2): "repeatedly cutting the track",
    }

    def draw_penalty(self, s):
        """RaceRoom-style penalty detail: the EXACT pending penalty and how to
        serve it — drive-through, stop-and-go duration, how much time to give
        back on a slow-down, a time penalty, plus the 'next lap won't count'
        warning. Reads the authoritative penalty amounts from s.penalties."""
        if self._podium and time.time() < self._podium_until:
            return
        p = s.penalties
        vslot = s.vehicle_info.slot_id
        pdrv = next((d for d in self._drivers(s)
                     if d.driver_info.slot_id == vslot), None)
        ptype = pdrv.penaltyType if pdrv is not None else -1
        preason = getattr(pdrv, "penaltyReason", -1) if pdrv is not None else -1
        reason = self._PEN_REASON.get((ptype, preason))

        lines = []   # (big_text, sub_text)
        # the five pending-penalty amounts (-1 = none). See r3e.h:
        # drive-through active = 0.0; stop-and-go = seconds to stay; slow-down =
        # seconds still to give back; time_deduction = seconds added.
        if p.drive_through >= 0:                       # 0.0 = active, -1 = none
            lines.append(("DRIVE-THROUGH PENALTY", "Enter the pit lane to serve it"))
        if p.stop_and_go > 0.05:                       # seconds to stay in the box
            lines.append((f"STOP & GO PENALTY — STOP {int(round(p.stop_and_go))}s",
                          "Pit and stop in your box"))
        if p.pit_stop >= 0:
            lines.append(("PIT-STOP PENALTY", "Serve a pit stop"))
        if p.slow_down > 0.05:                         # seconds still to give back
            lines.append((f"SLOW DOWN — GIVE BACK {p.slow_down:.1f}s",
                          "Lift until the time is repaid"))
        if p.time_deduction > 0.05:                    # seconds added to race time
            lines.append((f"TIME PENALTY +{p.time_deduction:.1f}s",
                          "Added to your race time"))
        # generic fallback if penaltyType is set but no amount surfaced
        if not lines and ptype >= 0:
            nm = {0: "DRIVE-THROUGH PENALTY", 1: "STOP & GO PENALTY",
                  2: "PIT-STOP PENALTY", 3: "TIME PENALTY",
                  4: "SLOW-DOWN PENALTY", 5: "DISQUALIFIED"}.get(ptype, "PENALTY")
            lines.append((nm, "Penalty pending"))
        if reason and lines:
            big, sub = lines[0]
            lines[0] = (big, sub + f"  ·  for {reason}")

        # 'lap won't count' warning — TRANSIENT: it flashes up for a few seconds
        # on the rising edge, then clears (it shouldn't sit on screen all lap).
        # Real pending PENALTIES above persist (you must serve them).
        now = time.time()
        lvs = getattr(s, "lap_valid_state", -1)
        prev = getattr(self, "_pen_lvs", -1)
        if lvs in (1, 2) and lvs != prev:     # entered/escalated -> start the flash
            self._pen_lvs_at = now
        elif lvs not in (1, 2):
            self._pen_lvs_at = 0.0
        self._pen_lvs = lvs
        warn = None
        if lvs in (1, 2) and now - getattr(self, "_pen_lvs_at", 0.0) < 5.0:
            warn = ("THIS & NEXT LAP WILL NOT COUNT" if lvs == 2
                    else "LAP INVALIDATED — TRACK LIMITS")

        if not lines and not warn:
            return
        w = 460
        rh = 44
        warn_h = 24 if warn else 0
        h = rh * len(lines) + warn_h
        x = (self.sw - w) // 2
        y = 104
        self._begin_panel("penalty", x, y, w, h)
        cy = y
        for big, sub in lines:
            self._card(x, cy, w, rh, fill="#2a0d0d", accent="#ff3b3b", side="left")
            self.text(x + 16, cy + 14, big, fill="#ff5a5a",
                      font=self.f_row_b, anchor="w")
            self.text(x + 16, cy + 31, sub, fill="#ffb3b3",
                      font=self.f_small_b, anchor="w")
            cy += rh
        if warn:
            self.canvas.create_rectangle(x, cy, x + w, cy + warn_h,
                                         fill="#5a3b00", outline="")
            self.text(x + w / 2, cy + warn_h / 2, warn, fill="#ffd23f",
                      font=self.f_small_b, anchor="center")

    def draw_header(self, s):
        track = R.u8_to_str(s.track_name)
        if not track:
            return
        stype = {0: "PRACTICE", 1: "QUALIFY", 2: "RACE", 3: "WARMUP"}.get(
            s.session_type, "")
        replay = "▶ REPLAY" if s.game_in_replay == 1 else ""
        sub = "   ".join(t for t in (stype, replay) if t)

        # progress: prefer lap counter; in replays/time sessions fall back to
        # the leader's actual lap (RaceRoom's time-remaining is unreliable here)
        lead_laps = max((d.completed_laps for d in self._drivers(s)), default=0)
        total = s.number_of_laps
        if total and total > 0:
            prog = f"LAP {min(lead_laps + 1, total)}/{total}"
        elif (s.game_in_replay != 1 and s.session_time_remaining
                and s.session_time_remaining > 0):
            prog = R.fmt_time(s.session_time_remaining)
        else:
            prog = f"LAP {lead_laps + 1}"

        # size the panel to fit the (truncated) title + progress, never overlap
        title = track[:30]
        tw = self.f_hdr.measure(title)
        pw = self.f_hdr.measure(prog)
        w = max(420, 16 + tw + 40 + pw + 16)
        x = (self.sw - w) // 2
        self._begin_panel("header", x, 14, w, 50)
        self._card(x, 14, w, 50, fill=CARD_BG2, accent=HEADER_ACCENT, side="top")
        self.text(x + 16, 29, title, fill=TEXT, font=self.f_hdr, anchor="w")
        self.text(x + 16, 49, sub, fill=DIM, font=self.f_sub, anchor="w")
        self.text(x + w - 16, 31, prog, fill=HEADER_ACCENT, font=self.f_hdr, anchor="e")

    # ---------- stats engine ----------
    def update_stats(self, s):
        # GONE detection (runs before _drivers is used downstream): a car frozen
        # on track during a green race — same lap + track position for 20s+, not
        # in the pits, not the player — is treated as retired/disconnected so the
        # booth/radio stop talking about it. DNF/DQ are handled in _drivers. Scans
        # the RAW array so a car that recovers can un-freeze and return.
        now = time.time()
        green = (s.session_type == 2 and self._racing)
        vslot = s.vehicle_info.slot_id
        # learn the track's corner positions from the player's speed trace (all
        # sessions, so practice/quali laps feed the race) — used to place overtakes
        try:
            self._corner_tick(s)
        except Exception:
            pass
        gone = set()
        for d in s.all_drivers_data_1:
            if d.place <= 0:
                continue
            sl = d.driver_info.slot_id
            if d.finish_status in (2, 3, 4, 5):
                gone.add(sl)
                continue
            frac = max(0.0, min(1.0, d.lap_distance_fraction))
            sig = (d.completed_laps, int(frac * 200))
            rec = self._move_sig.get(sl)
            if rec is None or rec[0] != sig:
                self._move_sig[sl] = (sig, now)
            elif (green and now - rec[1] > 20.0 and d.in_pitlane != 1
                    and sl != vslot):
                gone.add(sl)
        self._gone = gone

        order = sorted(self._drivers(s), key=lambda d: d.place)
        # keep a display-name -> spoken-name map fresh for clean TTS pronunciation
        for d in order:
            nm = self._dname(d)
            if nm not in self._pron:
                self._pron[nm] = pronounce(nm)
        # RESTART DETECTION: a race restart may keep the same session_iteration,
        # so also watch for the leader's lap count jumping BACKWARDS (e.g. lap 8
        # -> lap 0). Bump a generation counter so the key changes and everything
        # (incl. the TTS queue) resets back to lap one.
        lead_laps = max((d.completed_laps for d in order), default=0)
        if self._prev_lead_laps is not None and lead_laps + 2 < self._prev_lead_laps:
            self._sess_gen += 1
        self._prev_lead_laps = lead_laps

        # reset everything on a new session/track/restart
        key = (s.track_id, s.layout_id, s.session_type, s.session_iteration,
               self._sess_gen)
        if key != self._sess_key:
            self._sess_key = key
            self.grid_place = {}
            self.last_laps = {}
            self.best_lap = {}       # slot -> best lap time (for quali/practice tower)
            self.fastest = {"time": None, "slot": None, "car": 0, "name": "", "at": 0.0}
            self.cplace = {}         # slot -> DEBOUNCED ('confirmed') place
            self._cpend = {}         # slot -> (candidate place, ticks held)
            self._racing = False     # has the race actually gone GREEN yet?
            self._move_sig = {}      # reset gone/freeze tracking for the new session
            self._gone = set()
            self._q_valid = {}       # slot -> prev current_lap_valid (lap-delete edge)
            self._q_set = set()      # slots that have set ANY lap time this session
            self._q_off_lv = 1       # prev player lap-valid (non-race off-track edge)
            self._q_off_watch = None # (deadline, ref_speed) confirming a genuine off
            self._q_off_cd = -1e9    # last confirmed off (re-arm cooldown)
            self._q_ref_spd = 0.0    # rolling recent-peak speed reference
            self._q_lvs = -1         # prev lap_valid_state (next-lap-invalid edge)
            self._q_cuts = 0         # prev cut_track_warnings (track-limits edge)
            self._sec_laps = {}      # slot -> completed_laps (sector-coach lap edge)
            # dump any audio still queued from the previous session/race so it
            # never carries over into the new one (everything resets to lap 1)
            if self.tts:
                self.tts.flush()

        # CONFIRMED POSITIONS: RaceRoom's `place` flickers during side-by-side
        # moments, so a 1-tick swap is NOT a real overtake. A place only becomes
        # 'confirmed' once it has held for a few ticks (~200ms) — the commentary
        # and radio engines key off THIS, so the booth never calls a pass that
        # didn't actually stick (which the live tower would then contradict).
        for d in order:
            sl = d.driver_info.slot_id
            raw = d.place
            cand = self._cpend.get(sl)
            held = cand[1] + 1 if (cand and cand[0] == raw) else 1
            self._cpend[sl] = (raw, held)
            if sl not in self.cplace or held >= PLACE_CONFIRM_TICKS:
                self.cplace[sl] = raw          # seed immediately, else confirm

        # HAS THE RACE GONE GREEN? On the standing grid the cars are stationary
        # and nose-to-tail, which otherwise triggers bogus "he's catching you /
        # in my mirrors" radio. We latch on the one signal that's reliable in
        # every mode: the field is actually MOVING (lights out), or a lap has
        # been completed. (session_phase / start_lights proved unreliable — they
        # were flipping this true ON the grid, flooding the radio AND breaking
        # the start call.) The START announcement fires on this same transition.
        # Non-races have no grid start, so they're always 'racing'.
        if not self._racing:
            if s.session_type != 2:
                self._racing = True
            elif (abs(s.car_speed) > 4.0
                  or any(d.completed_laps >= 1 for d in order)):
                # trigger as soon as the field launches (lower threshold) so the
                # 'lights out' call lands closer to the actual moment
                self._racing = True

        # RaceRoom's time_delta_front/behind are garbage in replays (huge
        # numbers / NaN), so derive gaps from track position instead. Convert a
        # track-distance gap to seconds using a representative lap time:
        # gap_seconds = (laps + lap_fraction difference) * lap_time.
        lts = []
        for d in order:
            st = d.sector_time_previous_self
            # RaceRoom sector times are CUMULATIVE ([s1, s1+s2, s1+s2+s3]) so
            # the 3rd value IS the full lap time. (Summing them ~tripled it ->
            # a 1:30 lap read as ~3:30 and made every gap wrong.)
            if st[0] > 0 and st[1] > 0 and st[2] > 0:
                t = st[2]
                if 20.0 < t < 600.0:
                    lts.append(t)
        if lts:
            lts.sort()
            self.ref_lap = lts[len(lts) // 2]      # median valid lap time
        elif not getattr(self, "ref_lap", None):
            self.ref_lap = 100.0                   # fallback until we have data
        ref = self.ref_lap

        def prog(d):
            f = d.lap_distance_fraction
            f = 0.0 if f < 0 else (1.0 if f > 1 else f)
            return d.completed_laps + f

        lead_prog = prog(order[0]) if order else 0.0
        self.cum_gap = {}
        self.interval = {}
        # QUALI/PRACTICE event stream — populated this tick, consumed by the
        # engineer, booth and driver radio so their reactions are tied to what
        # ACTUALLY happens (a lap set, a PB, provisional pole, a deleted lap)
        # instead of random filler. (slot, kind, value)
        self._q_events = []
        is_lap_sess = (s.session_type != 2)
        prev_car = None
        for d in order:
            slot = d.driver_info.slot_id
            self.grid_place.setdefault(slot, d.place)
            # lap DELETED — flying lap invalidated (track limits) out of the pits
            if is_lap_sess:
                cv = d.current_lap_valid
                pv = self._q_valid.get(slot, 1)
                self._q_valid[slot] = cv
                if pv == 1 and cv == 0 and d.in_pitlane != 1 and slot in self._q_set:
                    self._q_events.append((slot, "deleted", None))
            p = prog(d)
            g = (lead_prog - p) * ref
            self.cum_gap[slot] = g if g >= 0 else 0.0
            self.interval[slot] = ((prog(prev_car) - p) * ref
                                   if prev_car is not None else 0.0)
            prev_car = d

            # fastest lap: when a car completes a lap, its last lap = sum of
            # previous-lap sectors (driver array has no direct best-lap field)
            pl = self.last_laps.get(slot)
            if pl is not None and d.completed_laps > pl:
                st = d.sector_time_previous_self
                if st[0] > 0 and st[1] > 0 and st[2] > 0:
                    lap = st[2]                    # cumulative -> last = full lap
                    pb = self.best_lap.get(slot)
                    improved = (pb is None or lap < pb)
                    if improved:                   # per-driver best (quali tower)
                        self.best_lap[slot] = lap
                    was_fastest = (self.fastest["time"] is None
                                   or lap < self.fastest["time"])
                    if was_fastest:
                        self.fastest = {
                            "time": lap, "slot": slot,
                            "car": d.driver_info.car_number,
                            "name": (R.u8_to_str(d.driver_info.name) or "").upper(),
                            "at": time.time()}
                    # quali/practice lap-completion events (only count valid laps)
                    if is_lap_sess and d.current_lap_valid != 0:
                        first = slot not in self._q_set
                        self._q_set.add(slot)
                        if was_fastest:
                            self._q_events.append((slot, "pole", lap))
                        elif improved:
                            self._q_events.append((slot, "pb", lap))
                        else:
                            self._q_events.append((slot, "lap_slow", lap))
                        if first:
                            self._q_events.append((slot, "first", lap))
            self.last_laps[slot] = d.completed_laps

        # PLAYER off-track in PRACTICE / QUALIFYING — the race off-track call is
        # handled by the incident system in update_commentary, but in non-race
        # sessions the engineer still needs to know you've had a moment so he can
        # warn you. Same confirm logic as the race path: a lap going invalid is
        # only a CANDIDATE (it includes a harmless kerb clip); we confirm a real
        # excursion by a genuine COLLAPSE in speed (grass / gravel / a spin).
        if is_lap_sess:
            now = time.time()
            vslot = s.vehicle_info.slot_id
            pdrv = next((d for d in order
                         if d.driver_info.slot_id == vslot), None)
            in_pit = ((pdrv is not None and pdrv.in_pitlane == 1)
                      or s.in_pitlane == 1)
            plv = s.current_lap_valid
            spd = abs(s.car_speed)
            moving = (pdrv is not None and not in_pit)
            # rolling recent-PEAK speed (decays slowly) = the 'before the off'
            # reference, so we can spot a collapse even when the lap was already
            # invalid (a spin on an out-lap, repeated offs, etc.)
            ref = getattr(self, "_q_ref_spd", 0.0)
            self._q_ref_spd = max(spd, ref * 0.95) if moving else spd
            # ARM the watch on the lap-invalidation EDGE (you crossed a limit), at
            # any speed, on its own cooldown so repeated offs each register
            if (moving and self._q_off_lv == 1 and plv == 0
                    and self._q_off_watch is None
                    and now - getattr(self, "_q_off_cd", -1e9) > 5.0):
                self._q_off_watch = (now + 3.0, max(self._q_ref_spd, spd))
            # CONFIRM a genuine off — speed COLLAPSED (grass/gravel/spin, right
            # down to a standstill) within the window. Crucially we DON'T cancel
            # the watch just because the car slowed: that collapse IS the signal
            # (the old code cleared it on a spin-to-stop, so big spins went
            # unreported). Only a pit entry or the window expiring cancels it.
            if self._q_off_watch is not None:
                deadline, refspd = self._q_off_watch
                if in_pit:
                    self._q_off_watch = None
                elif refspd > 10.0 and spd < refspd * 0.55:
                    self._q_off_watch = None
                    self._q_off_cd = now
                    self._q_events.append((vslot, "offtrack", None))
                elif now >= deadline:
                    self._q_off_watch = None               # just a clip — no news
            self._q_off_lv = plv
            # TRACK LIMITS — cut_track_warnings is RaceRoom's authoritative "you
            # ran off the limits" counter; its rising edge catches EVERY excursion
            # (even a mild wheel-over-the-line that the speed-collapse test misses)
            # so the engineer warns you every single time in practice/quali.
            cuts = s.cut_track_warnings
            if cuts > getattr(self, "_q_cuts", 0):
                self._q_events.append((vslot, "limits", None))
            self._q_cuts = cuts
            # NEXT LAP WON'T COUNT — lap_valid_state == 2 means THIS and the next
            # lap are both invalid. Fire on each rising edge so the engineer warns
            # you every time it happens.
            lvs = getattr(s, "lap_valid_state", -1)
            if lvs == 2 and getattr(self, "_q_lvs", -1) != 2:
                self._q_events.append((vslot, "nextlap_invalid", None))
            self._q_lvs = lvs

    def _sector_color(self, val, pbest, sbest):
        if val is None or val <= 0:
            return DIM
        if sbest and sbest > 0 and val <= sbest + 0.05:
            return PURPLE
        if pbest and pbest > 0 and val <= pbest + 0.05:
            return GREEN
        return YELLOWT

    def _tyre_color(self, d):
        sub = d.tire_subtype_front
        if sub in TYRE_COLORS:
            return TYRE_COLORS[sub]
        # fall back to option/prime
        return "#f1c40f" if d.tire_type_front == 0 else "#e9ecef"

    # ---------- timing tower ----------
    def draw_tower(self, s):
        drivers = self._drivers(s)
        if not drivers:
            return
        is_race = (s.session_type == 2)
        # RACE: order by LIVE track position (laps + lap fraction) so an on-track
        # overtake reorders the tower the instant it happens, instead of waiting
        # for RaceRoom's `place` field to catch up (which lags the move). The row
        # NUMBER is the live rank, so order and number always agree. QUALI/
        # PRACTICE keeps RaceRoom's place (already sorted by best time).
        if is_race and self._racing:
            def _prog(d):
                f = d.lap_distance_fraction
                f = 0.0 if f < 0 else (1.0 if f > 1 else f)
                return d.completed_laps + f
            drivers.sort(key=lambda d: -_prog(d))
            for i, d in enumerate(drivers):
                self._tow_rank[d.driver_info.slot_id] = i + 1
        else:
            drivers.sort(key=lambda d: d.place)
            self._tow_rank = {}
        viewed_slot = s.vehicle_info.slot_id

        if self.compact:
            # racing mode: just the cars around you — minimal screen footprint
            vidx = next((i for i, d in enumerate(drivers)
                         if d.driver_info.slot_id == viewed_slot), None)
            rows = drivers[max(0, vidx - 4):vidx + 5] if vidx is not None else drivers[:9]
            w, rh, pos_w, name_len = 284, 22, 28, 12
            font, fontb = self.f_tow, self.f_tow_b
        else:
            rows = drivers[:MAX_ROWS]
            # slim + tall like a broadcast timing tower (was 320 wide = too square)
            w, rh, pos_w, name_len = 274, 21, 26, 12
            font, fontb = self.f_tow, self.f_tow_b

        x, y = 30, 110
        hdr_h = 16
        c2_x = x + w - 8                 # far value column (right edge)
        c1_x = x + w - 58                # near value column
        # the two columns mean different things by session: a RACE shows the gap
        # to the car ahead + the gap to the leader; QUALI/PRACTICE shows each
        # driver's best lap time + the gap to provisional pole (just like F1 TV)
        lbl1, lbl2 = ("INT", "LEAD") if is_race else ("TIME", "GAP")
        pole = None                      # provisional pole time (quali/practice)
        if not is_race:
            bts = [self.best_lap.get(d.driver_info.slot_id) for d in rows]
            bts = [t for t in bts if t]
            pole = min(bts) if bts else None
        # broadcast logo strip sitting on TOP of the tower (like F1 TV)
        strip_h = (self.tower_logo.height() + 10) if self.tower_logo else 0
        self._begin_panel("tower", x, y, w, strip_h + hdr_h + rh * len(rows))
        c = self.canvas

        if strip_h:
            c.create_rectangle(x, y, x + w, y + strip_h, fill="#0a0d12",
                               outline=PANEL_OUTLINE, stipple=PANEL_STIPPLE)
            # image isn't proxied by the translating canvas — draw on the real
            # panel canvas at panel-local coords (like the avatars do)
            self._cv_real.create_image((x + w / 2) - self._ox,
                                       (y + strip_h / 2) - self._oy,
                                       image=self.tower_logo, anchor="center")
        hy = y + strip_h                 # header row sits below the logo strip
        c.create_rectangle(x, hy, x + w, hy + hdr_h, fill="#0a0d12",
                           outline=PANEL_OUTLINE, stipple=PANEL_STIPPLE)
        self.text(x + pos_w + 18, hy + hdr_h / 2, "DRIVER", fill=DIM, font=fontb, anchor="w")
        self.text(c1_x, hy + hdr_h / 2, lbl1, fill=DIM, font=fontb, anchor="e")
        self.text(c2_x, hy + hdr_h / 2, lbl2, fill=DIM, font=fontb, anchor="e")
        ry = hy + hdr_h

        for d in rows:
            di = d.driver_info
            slot = di.slot_id
            pos = self._tow_rank.get(slot, d.place)   # live rank in a race
            is_viewed = (viewed_slot >= 0 and slot == viewed_slot)
            is_leader = (pos == 1)
            holds_fl = (self.fastest["slot"] is not None and slot == self.fastest["slot"])

            c.create_rectangle(x, ry, x + w, ry + rh,
                               fill=("#1b222b" if is_viewed else "#0e1217"),
                               outline=PANEL_OUTLINE, stipple=PANEL_STIPPLE)
            if holds_fl:
                c.create_rectangle(x, ry, x + 5, ry + rh, fill=PURPLE, outline="")

            box = ACCENT if is_viewed else (LEADER if is_leader else "#212a30")
            c.create_rectangle(x, ry, x + pos_w, ry + rh, fill=box, outline="")
            self.text(x + pos_w / 2, ry + rh / 2, str(pos),
                      fill=("#000000" if (is_viewed or is_leader) else TEXT),
                      font=fontb, anchor="center")

            # grid-delta arrow only matters in a race; reclaim the space otherwise
            if is_race:
                delta = self.grid_place.get(slot, d.place) - d.place
                arr, acol = (("▲", GREEN) if delta > 0
                             else ("▼", "#ff6b6b") if delta < 0 else ("–", DIM))
                self.text(x + pos_w + 7, ry + rh / 2, arr, fill=acol,
                          font=self.f_tow, anchor="center")
                tx = x + pos_w + 17
            else:
                tx = x + pos_w + 9
            c.create_oval(tx - 4, ry + rh / 2 - 4, tx + 4, ry + rh / 2 + 4,
                          fill=self._tyre_color(d), outline="#000000")

            name = (R.u8_to_str(di.name) or "---").upper()
            self.text(tx + 9, ry + rh / 2,
                      f"{di.car_number:>2} {name[:name_len]}",
                      fill=(ACCENT if is_viewed else self._color_for(d)),
                      font=(fontb if is_viewed else font), anchor="w")

            if d.ptp_state == 1:
                self.text(c1_x - 46, ry + rh / 2, "P2P", fill=CYAN,
                          font=fontb, anchor="e")
            elif d.drs_state == 1:
                self.text(c1_x - 46, ry + rh / 2, "DRS", fill=GREEN,
                          font=fontb, anchor="e")

            if is_race:
                if d.in_pitlane == 1:
                    self.text(c2_x, ry + rh / 2, "PIT", fill="#ffa94d",
                              font=fontb, anchor="e")
                elif is_leader:
                    self.text(c2_x, ry + rh / 2, "LDR" if self.compact else "LEADER",
                              fill=LEADER, font=font, anchor="e")
                else:
                    itv = self.interval.get(slot)
                    if holds_fl:
                        # FL sits in the INT column — no name-column overlap
                        self.text(c1_x, ry + rh / 2, "FL",
                                  fill=PURPLE, font=fontb, anchor="e")
                    elif itv is not None and itv > 0.05:
                        close = itv < 1.0
                        self.text(c1_x, ry + rh / 2, f"{itv:.1f}",
                                  fill=("#ffffff" if close else DIM),
                                  font=(fontb if close else font), anchor="e")
                    cg = self.cum_gap.get(slot)
                    if cg is not None and cg > 0.05:
                        self.text(c2_x, ry + rh / 2, f"+{cg:.1f}",
                                  fill=(GREEN if is_viewed else DIM), font=font, anchor="e")
            else:
                # QUALI / PRACTICE: best lap time + gap to provisional pole
                bt = self.best_lap.get(slot)
                if bt:
                    self.text(c1_x, ry + rh / 2, R.fmt_time(bt),
                              fill=("#ffffff" if is_leader else TEXT),
                              font=(fontb if (is_leader or is_viewed) else font),
                              anchor="e")
                    if pole and bt > pole + 0.001:
                        self.text(c2_x, ry + rh / 2, f"+{bt - pole:.3f}",
                                  fill=(GREEN if is_viewed else DIM), font=font,
                                  anchor="e")
                    elif is_leader:
                        self.text(c2_x, ry + rh / 2, "POLE", fill=PURPLE,
                                  font=font, anchor="e")
                else:
                    tag = "PIT" if d.in_pitlane == 1 else "RUN"
                    self.text(c1_x, ry + rh / 2, tag, fill=DIM, font=font, anchor="e")
            ry += rh

    # ---------- relative panel (cars around the focused car) ----------
    def draw_relative(self, s):
        vslot = s.vehicle_info.slot_id
        if vslot < 0:
            return
        order = sorted(self._drivers(s), key=lambda d: d.place)
        idx = next((i for i, d in enumerate(order)
                    if d.driver_info.slot_id == vslot), None)
        if idx is None or len(order) < 2:
            return
        lo = max(0, idx - 3)
        hi = min(len(order), idx + 4)
        window = order[lo:hi]
        focus_cg = self.cum_gap.get(vslot)

        w, rh = 300, 24
        x = self.sw - w - 30
        y = 110
        self._begin_panel("relative", x, y, w, 22 + rh * len(window))
        c = self.canvas
        c.create_rectangle(x, y, x + w, y + 22, fill="#0a0d12",
                           outline=PANEL_OUTLINE)
        self.text(x + 10, y + 11, "RELATIVE", fill=DIM, font=self.f_row_b, anchor="w")
        self.text(x + w - 10, y + 11, "GAP", fill=DIM, font=self.f_row_b, anchor="e")
        ry = y + 22
        for d in window:
            di = d.driver_info
            is_focus = (di.slot_id == vslot)
            c.create_rectangle(x, ry, x + w, ry + rh,
                               fill=("#1b222b" if is_focus else "#0e1217"),
                               outline=PANEL_OUTLINE, stipple=PANEL_STIPPLE)
            self.text(x + 10, ry + rh / 2, f"{d.place:>2}", fill=DIM,
                      font=self.f_row, anchor="w")
            c.create_oval(x + 34, ry + rh / 2 - 5, x + 44, ry + rh / 2 + 5,
                          fill=self._tyre_color(d), outline="#000000")
            name = (R.u8_to_str(di.name) or "---").upper()
            self.text(x + 52, ry + rh / 2, f"{di.car_number:>3} {name[:13]}",
                      fill=(ACCENT if is_focus else self._color_for(d)),
                      font=(self.f_row_b if is_focus else self.f_row), anchor="w")
            cg = self.cum_gap.get(di.slot_id)
            if is_focus:
                rel = "◀"  # marker for the followed car
                col = ACCENT
            elif cg is not None and focus_cg is not None:
                diff = cg - focus_cg
                rel = f"{diff:+.1f}"
                col = "#ff8787" if diff < 0 else GREEN
            else:
                rel, col = "", DIM
            self.text(x + w - 10, ry + rh / 2, rel, fill=col,
                      font=self.f_row, anchor="e")
            ry += rh

    # ---------- fastest lap banner + focused-car sectors (lower third) ----------
    def draw_fastest_banner(self, s):
        fl = self.fastest
        if fl["time"] is None:
            return
        age = time.time() - fl["at"]
        if age > 10.0:               # don't leave it on screen forever
            return
        fresh = age < 6.0
        w, h = 360, 28
        x = (self.sw - w) // 2
        y = self.sh - 104
        self._begin_panel("fastest", x, y, w, h)
        self.canvas.create_rectangle(x, y, x + w, y + h,
                                     fill=(PURPLE if fresh else "#1a1326"),
                                     outline=PURPLE)
        fg = "#000000" if fresh else PURPLE
        self.text(x + 12, y + h / 2, "● FASTEST LAP", fill=fg,
                  font=self.f_row_b, anchor="w")
        self.text(x + w - 12, y + h / 2,
                  f"#{fl['car']} {fl['name'][:12]}  {R.fmt_time(fl['time'])}",
                  fill=fg, font=self.f_row_b, anchor="e")

    # ---------- team-radio engine ----------
    def _dname(self, d):
        return (R.u8_to_str(d.driver_info.name) or "DRIVER").upper()

    _LAP_WORDS = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
                  7: "seven", 8: "eight", 9: "nine", 10: "ten"}

    def _spell_laps(self, n):
        """'three laps', 'ten laps', else 'N laps' — reads better than digits."""
        return f"{self._LAP_WORDS.get(n, n)} laps"

    def _spoken(self, text):
        """Swap each driver's on-screen name for its TTS-friendly pronunciation
        in the SPOKEN string only (bubbles/captions still show the real tag)."""
        for disp, say in sorted(self._pron.items(), key=lambda kv: -len(kv[0])):
            if disp and disp != say and disp in text:
                text = text.replace(disp, say)
        # expand a bare "1.9s" / "2s" gap into "1.9 seconds" so the booth reads
        # it as a word, not the letter "S" (display bubbles keep the short form)
        text = re.sub(r'(\d+(?:\.\d+)?)\s*s\b', r'\1 seconds', text)
        return text

    def _color_for_name(self, name):
        if not name:
            return "#c9ced6"
        # assign sequentially on first sighting so each driver gets a UNIQUE
        # colour until all 20 are used, then it wraps (name-hashing collided
        # well before 20 on a typical ~15-car grid)
        c = self._dcolor.get(name)
        if c is None:
            c = DRIVER_COLORS[self._dcolor_n % len(DRIVER_COLORS)]
            self._dcolor[name] = c
            self._dcolor_n += 1
        return c

    def _color_for(self, d):
        return self._color_for_name(R.u8_to_str(d.driver_info.name))

    def _persona_for(self, d):
        # stable assignment by name (same driver = same personality)
        nm = R.u8_to_str(d.driver_info.name) or str(d.driver_info.slot_id)
        idx = sum(nm.encode("utf-8", "ignore")) % len(PERSONA_KEYS)
        return PERSONA_KEYS[idx]

    def _pick(self, pool, key):
        """Random line from pool, avoiding the last several used for this key so
        you don't hear the same phrase again and again."""
        if not pool:
            return ""
        if len(pool) == 1:
            return pool[0]
        recent = self._last_line.get(key) or []
        choices = [i for i in range(len(pool)) if i not in recent]
        if not choices:
            choices = list(range(len(pool)))
        idx = random.choice(choices)
        # avoid-window scales with pool size: ~1/3 of pool, minimum 5, max pool-1
        # so a 90-line pool avoids the last 30 = no repeat until you've heard 30 unique
        avoid = min(len(pool) - 1, max(5, len(pool) // 3))
        self._last_line[key] = (recent + [idx])[-avoid:]
        return pool[idx]

    def _moodify(self, slot, line):
        """Prepend a frustrated/pumped interjection when a driver is on a
        losing/winning streak — makes them feel human over a stint."""
        m = self._mood.get(slot, 0.0)
        if m <= -2.5 and random.random() < 0.5:
            return self._pick(MOOD_FRUSTRATED, ("moodf",)) + " " + line
        if m >= 2.5 and random.random() < 0.5:
            return self._pick(MOOD_PUMPED, ("moodp",)) + " " + line
        return line

    def _radio_line(self, d, category, who=""):
        persona = self._persona_for(d)
        # ~10% of the time, drop in a famous real motorsport quote as an easter
        # egg (kept rare so it stays a treat, not a gimmick).
        eggs = EASTER_EGGS.get(category)
        if eggs and random.random() < 0.10:
            line = self._pick(eggs, ("EGG", category))
            line = line.format(pos=d.place, who=who or "the guy behind")
            return self._moodify(d.driver_info.slot_id, line)
        pools = PERSONAS[persona]
        pool = pools.get(category) or pools.get("taunt") or next(iter(pools.values()))
        pool = pool + EXTRA_LINES.get(category, [])   # +generic lines for variety
        line = self._pick(pool, (persona, category))
        line = line.format(pos=d.place, who=who or "the guy behind")
        return self._moodify(d.driver_info.slot_id, line)

    def _sector_advice(self, s, focused):
        """On a completed-lap edge, read your last lap's three sector splits
        against your OWN best (and the session best) and return (category, fmt)
        for a specific coaching line — or None. Consumes the lap edge per call.

        RaceRoom sector times are CUMULATIVE ([s1, s1+s2, s1+s2+s3]), so each
        sector is the difference between consecutive entries."""
        sl = focused.driver_info.slot_id
        cl = focused.completed_laps
        prevc = self._sec_laps.get(sl)
        self._sec_laps[sl] = cl
        if prevc is None or cl <= prevc or cl < 2:
            return None                      # need a prior lap to compare against
        prev = list(focused.sector_time_previous_self)
        best = list(focused.sector_time_best_self)
        if not (prev[0] > 0 and prev[1] > 0 and prev[2] > 0):
            return None
        if not (best[0] > 0 and best[1] > 0 and best[2] > 0):
            return None
        lap = [prev[0], prev[1] - prev[0], prev[2] - prev[1]]
        bst = [best[0], best[1] - best[0], best[2] - best[1]]
        if min(lap) <= 0 or min(bst) <= 0:
            return None                      # garbage split — skip
        deltas = [lap[i] - bst[i] for i in range(3)]      # +ve = slower than best
        worst = max(range(3), key=lambda i: deltas[i])
        bests = min(range(3), key=lambda i: deltas[i])
        # was a sector right on the SESSION best (purple)?
        sess = list(getattr(s, "session_best_lap_sector_times", [0, 0, 0]))
        purple = None
        if len(sess) == 3 and sess[0] > 0 and sess[1] > 0 and sess[2] > 0:
            ss = [sess[0], sess[1] - sess[0], sess[2] - sess[1]]
            for i in range(3):
                if ss[i] > 0 and lap[i] <= ss[i] + 0.03:
                    purple = i
        d_txt = f"{deltas[worst]:.2f}s"
        # all three near your best -> a clean, consistent lap
        if deltas[worst] < 0.12:
            if deltas[bests] < -0.03 or purple is not None:
                return ("strong", {"sec": (purple if purple is not None
                                           else bests) + 1})
            return ("solid", {})
        # one strong AND one weak -> the classic "great here, costing there"
        if deltas[bests] < -0.04 and deltas[worst] > 0.15:
            return ("mixed", {"one": bests + 1, "two": worst + 1, "d": d_txt})
        # otherwise: name the weakest sector and how much it's costing
        return ("slow", {"sec": worst + 1, "d": d_txt})

    def _emit_sector(self, adv, events, prio):
        """Append a sector-coaching engineer line for a (category, fmt) advice."""
        cat, fmt = adv
        line = _safe_format(self._pick(SECTOR_COACH[cat], ("SEC", cat)), fmt)
        emo = {"strong": "smug", "solid": "smug"}.get(cat, "neutral")
        events.append((prio, -1, "RACE ENGINEER", line, False, "ENGINEER", emo))

    def _intro_done(self, now):
        """True once the booth's session intro has AIRED, so the engineer can
        start talking. Latches True for the session. If there's no booth to wait
        for (commentary off / TTS muted or absent) it's immediately True; the
        booth records _intro_emit_t when it emits the opener (set in
        update_commentary), and we release once the audio queue has drained or a
        safety timeout passes so the engineer can never be starved into silence."""
        if getattr(self, "_intro_aired", False):
            return True
        if (not self.commentary_on or self.tts is None
                or not getattr(self.tts, "enabled", False)):
            self._intro_aired = True
            return True
        et = getattr(self, "_intro_emit_t", None)
        if et is None:
            # SAFETY: if the booth never sets a scene (mid-session join, or a
            # replay where the opener doesn't trigger), don't gag the engineer
            # forever — release a few seconds into the session.
            if now - getattr(self, "_sess_start_t", now) > 8.0:
                self._intro_aired = True
                return True
            return False                       # booth hasn't set the scene yet
        drained = (not self.tts.speaking() and self.tts._pending() == 0)
        if (now - et > 12.0) or (now - et > 1.0 and drained):
            self._intro_aired = True
            return True
        return False

    def _engineer_events(self, s, focused, placemap, events, now):
        """Your engineer reacts to YOUR race. At most one candidate per tick;
        the emit loop throttles them with RADIO_ENG_CD."""
        vslot = focused.driver_info.slot_id
        # LIVE place for 'who is around me' (neighbours/gaps must match reality);
        # CONFIRMED place only for detecting a CHANGE (gained/lost/took the lead)
        fp = focused.place
        fpc = self.cplace.get(vslot, fp)
        ahead = placemap.get(fp - 1)
        behind = placemap.get(fp + 1)
        gap = self.interval.get(vslot)
        gapb = self.interval.get(behind.driver_info.slot_id) if behind else None
        pgap, pgapb = self._prev_gap, self._prev_gapb
        self._prev_gap, self._prev_gapb = gap, gapb
        grid = self.grid_place.get(vslot, fp)
        gained = grid - fp                       # +climbed / -dropped vs start

        def add(cat, prio, bypass=False, **extra):
            fmt = dict(
                pos=fp,
                ahead=self._dname(ahead) if ahead else "the car ahead",
                behind=self._dname(behind) if behind else "the car behind",
                gap=f"{gap:.1f}s" if gap else "a bit",
                gapb=f"{gapb:.1f}s" if gapb else "a bit",
                grid=grid, gain=abs(gained))
            fmt.update(extra)
            line = _safe_format(self._pick(ENGINEER_LINES[cat], ("ENGINEER", cat)),
                                fmt)
            events.append((prio, -1, "RACE ENGINEER", line, bypass, "ENGINEER",
                           ENG_EMOTION.get(cat, "neutral")))

        # GATE: stay silent until the booth has finished its session intro
        # (pregrid / lights-out, or the quali / practice opener). The engineer
        # must never talk over the commentators setting the scene.
        if not self._intro_done(now):
            return

        # PRACTICE / QUALIFY / WARMUP: EVENT-DRIVEN. The engineer reacts to YOUR
        # actual laps — a lap completed (with gap to pole), a personal best,
        # provisional pole, a slow lap, a deleted lap — plus a real track tip to
        # help you find time. No more random filler.
        if s.session_type != 2:
            is_quali = (s.session_type == 1)
            trk = self._short_track(R.u8_to_str(s.track_name))
            pb = self.best_lap.get(vslot)
            pole_d = placemap.get(1)
            pole_t = (self.best_lap.get(pole_d.driver_info.slot_id)
                      if pole_d else None)
            gtp = (pb - pole_t) if (pb and pole_t and pole_t < pb) else None
            gtp_s = f"{gtp:.3f}s" if gtp else "a couple of tenths"

            def qadd(cat, prio):
                pool = ENGINEER_QUALI.get(cat)
                if not pool:
                    return
                line = _safe_format(self._pick(pool, ("ENGQ", cat)),
                                    dict(pos=fp, gap=gtp_s))
                emo = {"pole": "happy", "pb": "smug", "improve": "happy",
                       "hold": "neutral", "push": "fired", "traffic": "worried",
                       "deleted": "worried", "offbest": "neutral",
                       "offtrack": "shock", "nextlap": "worried",
                       "limits": "worried"}.get(cat, "neutral")
                events.append((prio, -1, "RACE ENGINEER", line, False,
                               "ENGINEER", emo))

            # ENGINEER SESSION INTRO — once, after the booth opener: greet you,
            # drop a bit of track knowledge and a warm-up plan, like a real race
            # engineer would on the way out of the garage.
            if not self._eng_flags.get("qintro"):
                self._eng_flags["qintro"] = True
                greet = _safe_format(self._pick(
                    ENGINEER_PRACTICE["intro_quali" if is_quali
                                      else "intro_practice"], ("ENGINEER", "qintro")),
                    {"trk": trk})
                # a real PACE tip (where to find time), not a history fun-fact
                know = self._track_tip(trk) or ""
                tail = self._pick(ENGINEER_PRACTICE["intro_tail"], ("ENGINEER", "qtail"))
                line = " ".join(p for p in (greet, know, tail) if p).strip()
                # bypass=True so the intro is never dropped if the booth queue is
                # busy at session start (that's why it wasn't firing)
                events.append((1, -1, "RACE ENGINEER", line, True,
                               "ENGINEER", "neutral"))
                return

            # react to MY lap events THIS tick (highest priority, immediate).
            # A completed lap (pole/pb/lap_slow) is also a chance for SPECIFIC
            # sector coaching rather than a generic verdict.
            for sl, kind, val in getattr(self, "_q_events", []):
                if sl != vslot:
                    continue
                if kind == "offtrack":
                    return qadd("offtrack", 0)  # genuine off — warn immediately
                if kind == "limits":
                    return qadd("limits", 0)    # ran off the track limits
                if kind == "nextlap_invalid":
                    return qadd("nextlap", 0)   # this AND next lap won't count
                if kind == "deleted":
                    return qadd("deleted", 1)
                if kind == "pole":
                    return qadd("pole", 0)
                if kind == "pb":
                    adv = self._sector_advice(s, focused)
                    if adv and random.random() < 0.45:
                        return self._emit_sector(adv, events, 1)
                    return qadd("improve", 1)   # PB: reports position + gap to pole
                if kind == "lap_slow":
                    adv = self._sector_advice(s, focused)
                    if adv:                      # name the weak sector, not just "slow"
                        return self._emit_sector(adv, events, 2)
                    return qadd("offbest", 2)
            # otherwise, periodic help — but keep it LIGHT. The real coaching is
            # the SECTOR advice above (only when you're actually slow somewhere);
            # a generic full-corner TRACK TIP is now a rare extra, and never in
            # your opening laps (you're still finding your feet). Mostly the
            # engineer just gives a push/hold nudge or a practice run note.
            if now - getattr(self, "_prac_cd", 0.0) > 50.0:
                self._prac_cd = now
                laps_done = focused.completed_laps
                tip = self._track_tip(trk) if laps_done >= 4 else None
                if tip and random.random() < 0.12:
                    events.append((3, -1, "RACE ENGINEER", tip, False,
                                   "ENGINEER", "neutral"))
                    return
                if is_quali:
                    return qadd("push" if fp == 1 or not gtp else "hold", 3)
                line = self._pick(ENGINEER_PRACTICE["practice"], ("ENGINEER", "prac"))
                events.append((3, -1, "RACE ENGINEER", line, False, "ENGINEER",
                               "neutral"))
            return

        # Seed the car-damage HEALTH baseline as early as possible — from the
        # green flag, at full health — so it's captured BEFORE any contact. The
        # report ladder further down sits behind higher-priority returns, so if
        # it owned the baseline it would only snapshot AFTER damage was already
        # taken (baselining at the damaged value) and never see the drop.
        if self._racing:
            cd0 = s.car_damage
            for _p, _v in (("engine", cd0.engine),
                           ("transmission", cd0.transmission),
                           ("aero", cd0.aerodynamics),
                           ("suspension", cd0.suspension)):
                if _v >= 0 and _p not in self._eng_dmg:
                    self._eng_dmg[_p] = _v
            # Engine-temp baseline: capture at the first WARMED-UP tick (lap >= 2),
            # unconditionally here rather than down in the return-heavy ladder —
            # otherwise it would only snapshot after a rise had already begun
            # (baselining the hot value as "normal"), and seeding at the green
            # flag would baseline a COLD engine so the normal warm-up looks like
            # an overheat. Player-only field; -1/0 = N/A.
            if (self._eng_engtemp_base is None and focused.completed_laps >= 2):
                _et = max(s.engine_temp, s.engine_oil_temp)
                if _et > 0:
                    self._eng_engtemp_base = _et

        # race start (once) — fire the instant the race goes green (_racing edge)
        if not self._eng_flags.get("start") and self._racing:
            self._eng_flags["start"] = True
            return add("start", 0)
        # race finish (once) -> win / podium / finish. Wait until the PLAYER has
        # actually CROSSED the line (finish_status == 1) so their position is FINAL
        # — otherwise a last-corner pass for your place gets the verdict wrong
        # ("P3, podium!" when you were pipped to P4 at the flag). A grace timeout
        # covers a DNF where you never take the flag.
        if not self._eng_flags.get("finish"):
            ldr = placemap.get(1)
            race_over = (s.session_phase == 6 or s.flags.checkered == 1
                         or (ldr is not None and ldr.finish_status == 1)
                         or (s.number_of_laps > 0 and ldr is not None
                             and ldr.completed_laps >= s.number_of_laps))
            if race_over and not self._eng_flags.get("finseen"):
                self._eng_flags["finseen"] = True
                self._eng_flags["finat"] = now
            player_done = (focused.finish_status == 1)
            done = (self._eng_flags.get("finseen")
                    and (player_done
                         or now - self._eng_flags.get("finat", now) > 8.0))
            if done:
                self._eng_flags["finish"] = True
                if fp == 1:
                    cat = "win"
                elif fp <= 3:
                    cat = "podium"
                elif gained >= 6:
                    cat = "recovery"          # big climb from the grid
                elif gained <= -6:
                    cat = "slip"              # big drop from the grid
                elif fp <= 6:
                    cat = "finish_strong"     # just off the podium
                elif fp <= 10:
                    cat = "finish_points"     # decent points
                else:
                    cat = "finish_low"        # tough day
                return add(cat, 0)

        # INCIDENT POINTS — report EVERY point you pick up and escalate hard as
        # you near the disqualification limit. Checked from the GREEN flag (they
        # count from lap one) and BYPASSES the chatter-drop so you never miss one
        # — the whole point is you should never get DQ'd by surprise.
        ip, mip = s.incident_points, s.max_incident_points
        if (self._racing and mip > 0 and ip > getattr(self, "_eng_ip", 0)
                and now - getattr(self, "_eng_ip_cd", -1e9) > 5.0):
            self._eng_ip = ip
            self._eng_ip_cd = now
            left = mip - ip
            cat = ("points_critical" if left <= max(2, int(mip * 0.15))
                   else "points_high" if ip >= mip * 0.5
                   else "warn_points")
            line = _safe_format(self._pick(ENGINEER_LINES[cat], ("ENGINEER", cat)),
                                dict(pos=fp, pts=ip, maxpts=mip, left=left))
            events.append((0, -1, "RACE ENGINEER", line, True,  # bypass: never drop
                           "ENGINEER", "worried"))
            return

        # only the START call until the race is green AND the opening lap is done
        # — no "he's catching you" on the grid or during the lap-one scramble
        if not self._racing or focused.completed_laps < 1:
            return
        if (self.fastest.get("slot") == vslot and self.fastest.get("time")
                and not self._eng_flags.get("fastest")):
            self._eng_flags["fastest"] = True
            return add("fastest", 0)
        if (s.number_of_laps > 0 and focused.completed_laps == s.number_of_laps - 1
                and not self._eng_flags.get("lastlap")):
            self._eng_flags["lastlap"] = True
            return add("lastlap", 0)
        # closing-laps COUNTDOWN — once each at 5 / 3 / 2 to go (lap races)
        if s.number_of_laps > 0 and self._racing:
            cd_togo = s.number_of_laps - focused.completed_laps
            if cd_togo in (5, 3, 2) and self._eng_flags.get("cd") != cd_togo:
                self._eng_flags["cd"] = cd_togo
                return add("laps_countdown", 1, togo=cd_togo)
        # closing-MINUTES countdown — once each at 10 / 5 / 2 / 1 min (TIMED races)
        if s.number_of_laps <= 0 and self._racing and s.session_time_remaining > 0:
            secs = s.session_time_remaining
            mmk = (1 if secs <= 60 else 2 if secs <= 120 else 5 if secs <= 300
                   else 10 if secs <= 600 else 0)
            if mmk and self._eng_flags.get("mcd", 99) > mmk:
                self._eng_flags["mcd"] = mmk
                return add("mins_countdown", 1,
                           mins=("1 minute" if mmk == 1 else f"{mmk} minutes"))
        if focused.in_pitlane == 1:
            if not self._eng_flags.get("inpit"):
                self._eng_flags["inpit"] = True
                return add("pit", 0)
            return
        self._eng_flags["inpit"] = False

        # ---- TELEMETRY WARNINGS (your car's real data) — high priority ----
        # a penalty was just issued (rising edge on penaltyType)
        pen = getattr(focused, "penaltyType", -1)
        if pen >= 0 and self._eng_pen != pen:
            self._eng_pen = pen
            return add("warn_penalty", 0,
                       pen=PENALTY_SPOKEN.get(pen, "penalty"))
        if pen < 0:
            self._eng_pen = -1
        # (incident-point reporting moved above the lap-1 gate so it fires from
        # the green flag — every point, escalating toward the DQ limit)
        # NEXT LAP WON'T COUNT — lap_valid_state == 2 (this AND next lap invalid).
        # Rising edge -> warn every time it happens.
        lvs = getattr(s, "lap_valid_state", -1)
        if lvs == 2 and getattr(self, "_eng_lvs", -1) != 2:
            self._eng_lvs = lvs
            return add("nextlap", 1)
        self._eng_lvs = lvs
        # OFF-TRACK / TRACK LIMITS — warn EVERY time you leave the track, from
        # TWO signals: cut_track_warnings (RaceRoom's official limits counter) AND
        # the lap going invalid (current_lap_valid 1->0), which also catches the
        # grass/gravel excursions that DON'T trip the limits counter (the offs the
        # engineer used to miss). One shared cooldown so a single off that fires
        # both signals doesn't double-call; the emit loop's RADIO_ENG_CD throttles
        # it further so it never becomes chatter.
        plv = s.current_lap_valid
        cut_edge = s.cut_track_warnings > self._eng_cuts
        lap_edge = (getattr(self, "_eng_plv", 1) == 1 and plv == 0
                    and self._racing and focused.in_pitlane != 1)
        self._eng_cuts = s.cut_track_warnings
        self._eng_plv = plv
        if (cut_edge or lap_edge) and now - getattr(self, "_eng_off_cd", -1e9) > 5.0:
            self._eng_off_cd = now
            return add("warn_offtrack", 1)
        # a serveable penalty (drive-through / stop-go) sitting unserved — remind
        if pen in (0, 1) and now - getattr(self, "_eng_pen_remind", 0.0) > 22.0:
            self._eng_pen_remind = now
            return add("penalty_serve", 1)
        # MANDATORY pit stop only. RaceRoom's pitstop_status is the authoritative
        # signal: -1 = no mandatory stop this session, 0/1 = a mandatory stop is
        # required and NOT yet served (two/four tyres), 2 = already served. Only
        # nag when a stop is genuinely required, unserved, AND the window's open
        # (pit_window_status 2 = OPEN) — never on a no-stop race.
        pstat = getattr(focused, "pitstop_status", -1)
        mandatory_unserved = pstat in (0, 1)
        window_open = getattr(s, "pit_window_status", 0) == 2
        if (mandatory_unserved and window_open
                and now - getattr(self, "_eng_pit_remind", 0.0) > 30.0):
            self._eng_pit_remind = now
            return add("pit_needed", 1)

        # OVERTAKE / position-change acknowledgement. Compare CONFIRMED place to
        # the place we LAST ANNOUNCED — not just last tick — so the call survives
        # even if the exact overtaking tick is busy with another message; it then
        # lands at the next opening instead of being lost forever (the old
        # last-tick compare gave a one-tick window that the 14s spacing routinely
        # swallowed, which is why overtakes went unacknowledged). bypass=True so
        # it skips that spacing; its own short cooldown stops a multi-place
        # shuffle from machine-gunning.
        if self._eng_last_ann_place is None:
            self._eng_last_ann_place = fpc
        elif fpc != self._eng_last_ann_place and now - self._eng_place_cd > 8.0:
            gained_now = fpc < self._eng_last_ann_place
            led = (fpc == 1 and self._eng_last_ann_place > 1)
            self._eng_last_ann_place = fpc
            self._eng_place_cd = now
            if led:
                return add("lead", 0, bypass=True)
            if not gained_now:
                return add("lost", 1, bypass=True)
            # name WHERE the pass happened when we can place it at a corner
            # (named or 'Turn N'); a vague sector phrase isn't worth it for an
            # overtake, so only upgrade on a real corner, else the plain pool.
            where = self._where_on_track(s, focused.lap_distance_fraction)
            if where.startswith("into ") and random.random() < 0.7:
                return add("gained_where", 1, bypass=True, where=where)
            return add("gained", 1, bypass=True)
        # directional gap calls (only when the gap is actually moving)
        if ahead and gap and pgap is not None:
            if gap < 2.0 and gap < pgap - 0.05:        # you're closing on car ahead
                return add("catching", 2)
            if gap < 4.0 and gap > pgap + 0.10:        # car ahead pulling away
                return add("dropping", 2)
        if behind and gapb and pgapb is not None:
            if gapb < 1.5 and gapb < pgapb - 0.05:      # car behind closing on you
                return add("defending", 2)
            if gapb < 3.0 and gapb > pgapb + 0.10:      # you're pulling clear
                return add("clear", 2)
        # ---- TELEMETRY STATUS (fuel / tyres / damage) — lower priority, on
        # their own long cooldowns so they're useful, not naggy ----
        if s.fuel_use_active and s.fuel_per_lap > 0 and now - self._eng_fuel_cd > 40.0:
            laps_fuel = s.fuel_left / s.fuel_per_lap
            laps_left = (s.number_of_laps - focused.completed_laps
                         if s.number_of_laps > 0 else None)
            if laps_left is not None and 0 < laps_fuel < laps_left - 0.5:
                self._eng_fuel_cd = now
                return add("fuel_save", 2, laps=max(1, int(laps_fuel)))
            if laps_fuel < 3.0:
                self._eng_fuel_cd = now
                return add("fuel_low", 2)
        if s.tire_wear_active and now - self._eng_tyre_cd > 45.0:
            tw = list(s.tire_wear)
            if len(tw) == 4:
                if self._eng_tyre_base is None:
                    self._eng_tyre_base = tw          # fresh-tyre reference
                else:
                    worn = max(abs(self._eng_tyre_base[i] - tw[i]) for i in range(4))
                    if worn > 0.75 and not self._eng_flags.get("tyrecrit"):
                        self._eng_flags["tyrecrit"] = True
                        self._eng_tyre_cd = now
                        # only tell him to BOX if a mandatory stop is still coming
                        # (pstat 0/1 unserved); otherwise it's a no-stop race —
                        # manage the worn tyres to the flag, don't nag to pit.
                        return add("pit_tyres" if pstat in (0, 1)
                                   else "tyres_gone", 1)
                    if worn > 0.45:                   # well into the wear range
                        self._eng_tyre_cd = now
                        return add("tyres_worn", 2)
        # CAR DAMAGE — car_damage fields are a HEALTH fraction (1.0 = pristine,
        # 0.0 = hurt; -1.0 = N/A when the damage model is off). RaceRoom's note:
        # aero damage is "a bit arbitrary", so real contact often moves health
        # only a few percent — the old >0.12 gate meant most damage was never
        # called. Report meaningful drops sensitively, re-baseline so a SEPARATE
        # later contact reports again, and escalate to a box call when a part is
        # badly hurt (big single hit OR low absolute health).
        dmg = s.car_damage
        for part, val in (("engine", dmg.engine), ("transmission", dmg.transmission),
                          ("aero", dmg.aerodynamics), ("suspension", dmg.suspension)):
            if val < 0:                       # -1 = N/A (damage model disabled)
                continue
            base = self._eng_dmg.get(part)
            if base is None:
                self._eng_dmg[part] = val
                continue
            if val > base:                    # part repaired (pit) -> track recovery
                self._eng_dmg[part] = val
                continue
            drop = base - val                 # health lost since the reference
            if drop < 0.03:                   # noise / nothing meaningful
                continue
            # SEVERE -> box to repair. Latched per part, but re-arms if it gets
            # materially worse so a second big hit still gets a fresh call.
            sev = self._eng_dmg_sev.get(part)
            if (drop > 0.22 or val < 0.55) and (sev is None or sev - val > 0.10):
                self._eng_dmg_sev[part] = val
                self._eng_dmg[part] = val
                self._eng_dmg_cd[part] = now
                self._eng_flags[f"dmg_{part}"] = True
                # bypass the engineer throttle: a box-to-repair call is one-shot
                # (the baseline resets after it, so it never regenerates) and must
                # never be swallowed by the 14s spacing — like the DQ warnings.
                return add("pit_damage", 1, bypass=True, part=part)
            # LIGHT/MODERATE -> report it, re-baseline, and cool down so a single
            # scrape doesn't chatter but a fresh contact later still gets called.
            if now - self._eng_dmg_cd.get(part, -1e9) > 25.0:
                self._eng_dmg[part] = val
                self._eng_dmg_cd[part] = now
                self._eng_flags[f"dmg_{part}"] = True
                return add("damage", 1, part=part)

        # ---- TYRE & BRAKE TEMPERATURES — read the live tread/brake telemetry
        # against the car's OWN optimal/cold/hot references. Centre-tread (index
        # 1) is the core temperature; -1 / non-positive refs mean N/A (no temp
        # model) and are skipped. Not for the pit-lane or the opening crawl.
        if (self._racing and focused.in_pitlane != 1
                and focused.completed_laps >= 1):
            def _axle_temp(i0, i1):
                cs, opt, cold, hot = [], [], [], []
                for i in (i0, i1):
                    t = s.tire_temp[i]
                    c = t.current_temp[1]               # CENTER tread = core
                    if c > 0 and t.hot_temp > 0 and t.optimal_temp > 0:
                        cs.append(c)
                        opt.append(t.optimal_temp)
                        cold.append(t.cold_temp)
                        hot.append(t.hot_temp)
                if not cs:
                    return None
                n = len(cs)
                return (sum(cs) / n, sum(cold) / n, sum(hot) / n)
            front = _axle_temp(0, 1)
            rear = _axle_temp(2, 3)
            # OVERHEAT / COLD — a centre temp past the hot or cold reference.
            if (front or rear) and now - getattr(self, "_eng_temp_cd", -1e9) > 50.0:
                hot_ax = [nm for nm, ax in (("fronts", front), ("rears", rear))
                          if ax and ax[0] > ax[2]]
                cold_ax = [nm for nm, ax in (("fronts", front), ("rears", rear))
                           if ax and ax[0] < ax[1]]
                if hot_ax:
                    self._eng_temp_cd = now
                    ax = "tyres" if len(hot_ax) == 2 else hot_ax[0]
                    # sitting in another car's wake is a classic overheat cause
                    if ahead and gap and gap < 1.5:
                        return add("tyre_hot_traffic", 2, ax=ax)
                    return add("tyre_hot", 2, ax=ax)
                if cold_ax:
                    self._eng_temp_cd = now
                    ax = "tyres" if len(cold_ax) == 2 else cold_ax[0]
                    return add("tyre_cold", 2, ax=ax)
            # BRAKES — a brake over its hot reference risks fade.
            if now - getattr(self, "_eng_brake_cd", -1e9) > 60.0:
                def _brake_hot(i0, i1):
                    cs, hot = [], []
                    for i in (i0, i1):
                        b = s.brake_temp[i]
                        if b.current_temp > 0 and b.hot_temp > 0:
                            cs.append(b.current_temp)
                            hot.append(b.hot_temp)
                    return bool(cs) and (sum(cs) / len(cs) > sum(hot) / len(hot))
                fb, rb = _brake_hot(0, 1), _brake_hot(2, 3)
                if fb or rb:
                    self._eng_brake_cd = now
                    ax = ("front and rear" if fb and rb
                          else "front" if fb else "rear")
                    return add("brake_hot", 2, ax=ax)

        # ---- ENGINE TEMPERATURE (mechanical sympathy). The API gives a bare
        # Celsius value with NO optimal/max reference (and it's player-only), so
        # an absolute threshold would be wrong from car to car. Instead learn
        # THIS car's warmed-up running temp (after a couple of green laps) and
        # warn only on a large, SUSTAINED rise above it — a genuine cooling
        # problem (damage, or a blocked radiator sat in traffic), not the normal
        # rise-and-fall of a stint.
        if (self._racing and focused.in_pitlane != 1
                and focused.completed_laps >= 2):
            et = max(s.engine_temp, s.engine_oil_temp)   # whichever runs hotter
            base = self._eng_engtemp_base                # seeded early (lap >= 2)
            if et > 0 and base is not None:
                if et < base:                            # track the steady-state
                    self._eng_engtemp_base = base + (et - base) * 0.05
                if et - self._eng_engtemp_base > 20.0:
                    if self._eng_engtemp_hot_since is None:
                        self._eng_engtemp_hot_since = now
                    elif (now - self._eng_engtemp_hot_since > 4.0
                          and now - self._eng_engtemp_cd > 60.0):
                        self._eng_engtemp_cd = now
                        dmg_now = any(
                            self._eng_flags.get(f"dmg_{p}") for p in
                            ("engine", "aero", "suspension", "transmission"))
                        return add("engine_hot_dmg" if dmg_now
                                   else "engine_hot", 2)
                else:
                    self._eng_engtemp_hot_since = None

        # SECTOR COACHING (race) — occasional, specific feedback on where your
        # last lap gained or lost time. Own slow cooldown so it stays useful, not
        # constant; the in-race battle/telemetry calls above always take priority.
        if (self._racing and focused.in_pitlane != 1
                and now - getattr(self, "_eng_sec_cd", 0.0) > 55.0):
            adv = self._sector_advice(s, focused)
            if adv and adv[0] != "solid":     # don't interrupt with "nothing to fix"
                self._eng_sec_cd = now
                return self._emit_sector(adv, events, 3)

        # periodic "where are we in the race" update so you always know how far is
        # left (laps or, in a timed race, minutes) — on its own slow cooldown
        if self._racing and now - getattr(self, "_eng_laps_cd", 0.0) > 70.0:
            if s.number_of_laps > 0:
                done = focused.completed_laps
                lt = s.number_of_laps - done
                if lt >= 4:                       # last few handled by the countdown
                    self._eng_laps_cd = now
                    return add("laps_update", 2, togo=lt, done=done,
                               total=s.number_of_laps)
            elif s.session_time_remaining > 90:
                self._eng_laps_cd = now
                return add("time_update", 2,
                           mins=int(s.session_time_remaining // 60))

        # PROACTIVE per-section coaching — as you cross into a new sector, an
        # occasional track-aware heads-up for the part of the lap coming up. Rare
        # in the race (long cooldown + low chance) so it's the engineer being
        # alive to where you are on the lap, never nagging you about a track you
        # already know. track_sector is 1/2/3 (0 = N/A); fire on the rising edge.
        cur_sec = getattr(focused, "track_sector", 0)
        prev_sec = self._eng_sector_prev
        self._eng_sector_prev = cur_sec
        if (self._racing and prev_sec in (1, 2, 3) and cur_sec in (1, 2, 3)
                and cur_sec != prev_sec and focused.in_pitlane != 1
                and now - self._eng_section_cd > 80.0
                and random.random() < 0.2):
            tip = self._track_tip(self._short_track(R.u8_to_str(s.track_name)))
            if tip:
                self._eng_section_cd = now
                return add("section_ahead", 3, sec=cur_sec, tip=tip)

        # nothing dynamic happening -> stay INVOLVED with a proactive report:
        # a gap to the car ahead/behind, or POSITION-AWARE encouragement (never
        # "you're perfect" when you're dead last). When the car's healthy, an
        # occasional "gap's good, no damage, keep pushing" status.
        if now - self._enc_cd > 15.0:
            self._enc_cd = now
            # occasionally drop a real track tip to help find pace (across all
            # sessions) instead of generic encouragement
            if now - getattr(self, "_eng_tip_cd", 0.0) > 150.0:
                tip = self._track_tip(self._short_track(R.u8_to_str(s.track_name)))
                if tip and random.random() < 0.25:
                    self._eng_tip_cd = now
                    events.append((3, -1, "RACE ENGINEER", tip, False,
                                   "ENGINEER", "neutral"))
                    return
            opts = []
            if ahead and gap:
                opts.append("info_ahead")
            if behind and gapb:
                opts.append("info_behind")
            healthy = not any(self._eng_flags.get(f"dmg_{p}") for p in
                              ("engine", "transmission", "aero", "suspension"))
            if healthy and fp <= 12:
                opts.append("status_good")
            opts.append("enc_top" if fp <= 3 else "enc_mid" if fp <= 10
                        else "enc_back")
            return add(random.choice(opts), 3)

    def update_radio(self, s):
        now = time.time()
        # reset radio state on a new session
        if getattr(self, "_radio_key", None) != self._sess_key:
            self._radio_key = self._sess_key
            self.prev_places = {}
            self.prev_int_focus = None
            self.radio_msgs = []
            self.driver_radio_cd = {}
            self._last_line = {}
            self._chase = {}
            self._eng_cd = 0.0
            self._eng_flags = {}
            self._rivals = {}
            self._mood = {}
            self._prev_gap = None
            self._prev_gapb = None
            self._enc_cd = 0.0
            self._prac_cd = 0.0
            self._finish_q = []          # queued driver finish-position reactions
            self._finish_built = False
            # engineer telemetry trackers (your car's real data)
            self._eng_pen = -1           # last penaltyType seen (rising-edge warn)
            self._eng_cuts = 0           # last cut_track_warnings count
            self._eng_plv = 1            # last player current_lap_valid (off edge)
            self._eng_off_cd = -1e9      # shared off-track warn cooldown
            self._eng_lvs = -1           # last lap_valid_state (next-lap warning)
            self._eng_ip = 0             # last incident-point count (every-pickup)
            self._eng_ip_cd = -1e9       # incident-point report cooldown
            self._eng_fuel_cd = 0.0      # fuel-warning cooldown
            self._eng_tyre_cd = 0.0      # tyre-warning cooldown
            self._eng_tyre_base = None   # fresh tyre_wear baseline (4 values)
            self._eng_temp_cd = -1e9     # tyre-temperature warning cooldown
            self._eng_brake_cd = -1e9    # brake-temperature warning cooldown
            self._eng_engtemp_base = None    # warmed-up engine-temp reference
            self._eng_engtemp_hot_since = None  # when the sustained rise began
            self._eng_engtemp_cd = -1e9  # engine-overheat warning cooldown
            self._eng_last_ann_place = None  # last place the engineer announced
            self._eng_place_cd = -1e9    # overtake/position-ack cooldown
            self._eng_sector_prev = 0    # last track_sector (proactive coaching)
            self._eng_section_cd = -1e9  # proactive section-coaching cooldown
            self._eng_dmg = {}           # part -> health reference (re-baselined)
            self._eng_dmg_cd = {}        # part -> last "light damage" report time
            self._eng_dmg_sev = {}       # part -> health at last severe (box) call
            self._eng_laps_cd = 0.0      # periodic laps/time-left update cooldown
            self._eng_sec_cd = 0.0       # sector-coaching cooldown (race)
            self._intro_emit_t = None    # when the booth aired its session opener
            self._intro_aired = False    # engineer gate: intro has finished?
            self._sess_start_t = now     # session start (intro-gate safety release)
            self._signed_off = False     # broadcast over (no more radio either)

        order = sorted(self._drivers(s), key=lambda d: d.place)
        if not order:
            return
        # after the booth's closing sign-off the broadcast is over — no more
        # engineer or driver radio either (the queued wrap still plays out)
        if getattr(self, "_signed_off", False):
            return
        placemap = {d.place: d for d in order}
        # radio reacts to CONFIRMED (debounced) places too, so a flicker never
        # produces a phantom "he passed you / you passed him" call
        cp = lambda d: self.cplace.get(d.driver_info.slot_id, d.place)
        cur = {d.driver_info.slot_id: cp(d) for d in order}
        vslot = s.vehicle_info.slot_id
        focused = next((d for d in order if d.driver_info.slot_id == vslot), None)

        who = self._dname(focused) if focused is not None else ""

        # OPENING LAP: mute rival driver radio so the start is clean — the
        # commentator sets the scene ("lights out, P1 defending into turn 1") and
        # the engineer reacts to the launch. Rivals chime in from lap two.
        lap1 = (s.session_type == 2 and focused is not None
                and focused.completed_laps < 1)
        radio_open = self._racing and not lap1

        # update each driver's momentum (decays; +gain / -loss) BEFORE building
        # lines, so _radio_line can flavour them frustrated/pumped
        for d in order:
            sl = d.driver_info.slot_id
            m = self._mood.get(sl, 0.0) * 0.97
            pv = self.prev_places.get(sl)
            if pv is not None:
                if d.place < pv:
                    m += 1.0
                elif d.place > pv:
                    m -= 1.0
            self._mood[sl] = max(-5.0, min(5.0, m))

        events = []  # (priority, slot, name, text, bypass, persona, emotion)
        is_race = (s.session_type == 2)

        # ---- post-race FINISH reactions on the radio (#2) ----------------
        # When the race ends, drivers key the mic reacting to their finishing
        # position. The WINNER's celebration is ALWAYS queued first, then the
        # rest of the podium, the player (if outside the top 3), and a couple of
        # others for colour. Aired one-per-global-cooldown so they don't flood.
        def _fin_tier(place):
            return "podium" if place <= 3 else "points" if place <= 10 else "low"

        if is_race and not self._finish_built:
            leader = order[0]
            done = (s.session_phase == 6 or s.flags.checkered == 1
                    or leader.finish_status == 1
                    or (s.number_of_laps > 0
                        and leader.completed_laps >= s.number_of_laps))
            if done:
                self._finish_built = True
                picks = []
                winner = placemap.get(1)
                if winner is not None:
                    picks.append((winner, "win"))          # ALWAYS first
                for pl in (2, 3):
                    d = placemap.get(pl)
                    if d is not None:
                        picks.append((d, "podium"))
                if focused is not None and focused.place > 3:
                    picks.append((focused, _fin_tier(focused.place)))
                others = [d for d in order if d.place > 3 and d is not focused]
                random.shuffle(others)
                for d in others[:2]:
                    picks.append((d, _fin_tier(d.place)))
                self._finish_q = [(d.driver_info.slot_id, self._dname(d),
                                   d.place, tier) for d, tier in picks]

        # emit one queued finish reaction per global-cooldown window (front =
        # winner), forced past the per-driver cooldown so the order is preserved
        if self._finish_q and (now - self.last_radio_t) >= self.RADIO_GLOBAL_CD:
            sl, nm, place, tier = self._finish_q.pop(0)
            d = placemap.get(place)
            line = self._pick(DRIVER_FINISH[tier], ("FIN", tier)).format(pos=place)
            emo = ("happy" if tier in ("win", "podium")
                   else "neutral" if tier == "points" else "sad")
            persona = self._persona_for(d) if d is not None else "VETERAN"
            events.append((-9, sl, nm, line, True, persona, emo))

        # a rival takes the lead (you taking it is handled by your engineer).
        # Position-battle radio only makes sense in a RACE that's actually GREEN
        # — in practice/qualy or on the grid, cars aren't racing for position.
        if is_race and radio_open:
            for d in order:
                sl = d.driver_info.slot_id
                pv = self.prev_places.get(sl)
                if cp(d) == 1 and sl != vslot and pv is not None and pv > 1:
                    events.append((0, sl, self._dname(d),
                                   self._pick(LEAD, ("LEAD",)), False,
                                   self._persona_for(d), "smug"))

        if focused is not None and is_race and radio_open:
            fp = focused.place          # LIVE place for neighbours / the chase
            fpc = cp(focused)           # CONFIRMED place for detecting a pass
            pvf = self.prev_places.get(vslot)
            if pvf is not None and fpc == pvf - 1:              # you overtook 1 car
                passed = placemap.get(fpc + 1)
                if (passed is not None
                        and self.prev_places.get(passed.driver_info.slot_id) == fpc):
                    psl = passed.driver_info.slot_id
                    self._rivals[psl] = now              # remember for revenge
                    events.append((1, psl, self._dname(passed),
                                   self._radio_line(passed, "overtaken", who), False,
                                   self._persona_for(passed), "angry"))
            elif pvf is not None and fpc == pvf + 1:            # someone passed YOU
                over = placemap.get(fpc - 1)
                if (over is not None
                        and self.prev_places.get(over.driver_info.slot_id) == fpc):
                    osl = over.driver_info.slot_id
                    # if you passed THEM in the last 90s, this is a revenge re-pass
                    # (bypass cooldown so the grudge actually lands)
                    if now - self._rivals.get(osl, -1e9) < 90:
                        line = self._pick(REVENGE, ("REVENGE",)).format(who=who or "you")
                        revenge = True
                    else:
                        line = self._radio_line(over, "taunt", who)
                        revenge = False
                    events.append((1, osl, self._dname(over), line, revenge,
                                   self._persona_for(over), "smug"))
            elif pvf is not None and fpc >= pvf + 2:            # you spun / lost places
                events.append((0, vslot, self._dname(focused),
                               self._radio_line(focused, "crash"), False,
                               self._persona_for(focused), "shock"))

            # closing on the car ahead -> ESCALATING chase radio: distinct lines
            # at each tier (1.5s / 0.8s / 0.3s), each aired once per chase, so a
            # long chase tells a story instead of repeating one line. Resets when
            # the gap opens back up (a new chase later sounds fresh).
            if fp > 1:
                ahead = placemap.get(fp - 1)
                itv = self.interval.get(vslot)
                if ahead is not None and itv is not None and itv > 0:
                    tslot = ahead.driver_info.slot_id
                    fired = self._chase.get(tslot, set())
                    if itv > 2.5:
                        fired = set()
                    tier = ("attack" if itv < 0.3 and "attack" not in fired else
                            "near" if itv < 0.8 and "near" not in fired else
                            "far" if itv < 1.5 and "far" not in fired else None)
                    if tier is not None:
                        fired = set(fired) | {tier}
                        events.append((2, tslot, self._dname(ahead),
                                       self._radio_line(ahead, "caught", who), True,
                                       self._persona_for(ahead), "worried"))
                    self._chase[tslot] = fired

        # your race engineer talking to YOU
        if focused is not None:
            self._engineer_events(s, focused, placemap, events, now)

        # any driver losing 2+ places at once = spin/crash. RACE only — in
        # quali/practice a place change is just the timesheet reshuffling as
        # others set times, NOT an on-track incident.
        for d in (order if (is_race and radio_open) else []):
            sl = d.driver_info.slot_id
            if sl == vslot:
                continue
            pv = self.prev_places.get(sl)
            if pv is None or cp(d) < pv + 2:            # confirmed place drop = real
                continue
            txt = self._radio_line(d, "crash")
            if focused is not None and (abs(pv - cp(focused)) <= self.RADIO_NEAR
                                        or abs(cp(d) - cp(focused)) <= self.RADIO_NEAR):
                events.append((0, sl, self._dname(d), txt, False,
                               self._persona_for(d), "shock"))
            elif random.random() < self.RADIO_FAR_CHANCE:
                events.append((3, sl, self._dname(d), txt, False,
                               self._persona_for(d), "shock"))

        # FIELD radio: occasionally a driver scrapping elsewhere on track keys the
        # mic, so you still hear the odd bit of team radio even when leading in
        # clean air. RARE — its own ~18s cooldown so it's flavour, not a flood.
        if is_race and radio_open and now - getattr(self, "_field_cd", 0.0) > 18.0:
            fighters = [d for d in order
                        if d.driver_info.slot_id != vslot and d.place > 1
                        and 0.1 < (self.interval.get(d.driver_info.slot_id) or 9) < 0.8]
            if fighters and random.random() < 0.5:
                # a 'fighter' is within 0.8s of the car AHEAD of it, i.e. it's the
                # CHASER. The natural radio is the car being HUNTED keying the mic
                # about the chaser right behind — get the perspective right so we
                # never say "X is on my tail" about a car that's actually ahead.
                chaser = random.choice(fighters)
                chased = placemap.get(chaser.place - 1)     # the car in front
                if chased is not None and chased.driver_info.slot_id != vslot:
                    self._field_cd = now
                    events.append((3, chased.driver_info.slot_id,
                                   self._dname(chased),
                                   self._radio_line(chased, "caught",
                                                    self._dname(chaser)),
                                   False, self._persona_for(chased), "worried"))

        # QUALI / PRACTICE rival radio: EVENT-DRIVEN. Drivers react to their OWN
        # actual laps this tick — provisional pole, a good lap (PB), a deleted lap
        # — and occasionally one reacts to SOMEONE ELSE going fastest. No random
        # filler; every line is tied to a real event.
        if not is_race:
            is_quali_sess = (s.session_type == 1)
            by_slot = {d.driver_info.slot_id: d for d in order}
            for sl, kind, val in getattr(self, "_q_events", []):
                if sl == vslot or sl not in by_slot:
                    continue
                d = by_slot[sl]
                if kind == "pole":
                    # only QUALIFYING has a 'pole'; in practice it's just a good
                    # (fastest) lap, so the rival doesn't shout 'pole!' in practice
                    if is_quali_sess:
                        cat, emo, pr = "pole", "happy", 1
                    else:
                        cat, emo, pr = "good", "smug", 3
                elif kind == "pb":
                    cat, emo, pr = "good", "smug", 3
                elif kind == "deleted":
                    cat, emo, pr = "scrappy", "worried", 3
                else:
                    continue                         # lap_slow / first: no radio
                events.append((pr, sl, self._dname(d),
                               self._pick(RIVAL_QUALI[cat], ("RQ", cat)),
                               False, self._persona_for(d), emo))
            # a rival reacting to SOMEONE ELSE setting the fastest lap
            pole_evt = next((e for e in getattr(self, "_q_events", [])
                             if e[1] == "pole" and e[0] != vslot), None)
            if (pole_evt and now - getattr(self, "_qreact_cd", 0.0) > 20.0
                    and random.random() < 0.4):
                others = [d for d in order
                          if d.driver_info.slot_id not in (vslot, pole_evt[0])]
                if others:
                    self._qreact_cd = now
                    d = random.choice(others)
                    events.append((3, d.driver_info.slot_id, self._dname(d),
                                   self._pick(RIVAL_QUALI["chasing"], ("RQ", "chasing")),
                                   False, self._persona_for(d), "fired"))

        if self.prev_places:
            self._dbg_moves += sum(1 for sl, p in cur.items()
                                   if self.prev_places.get(sl) not in (None, p))
        self.prev_places = cur

        if not events or (now - self.last_radio_t) < self.RADIO_GLOBAL_CD:
            return
        events.sort(key=lambda e: e[0])
        emitted = 0
        for _prio, sl, nm, txt, bypass, persona, emotion in events:
            if emitted >= self.RADIO_MAX_BURST:
                break
            # BALANCE: radio shares one serial audio queue with the booth and is
            # normally never dropped — but if a backlog is building, yield so the
            # commentary isn't buried under a flood of driver radio. Critical
            # lines (bypass: revenge / finish reactions) still always get through.
            if (not bypass and self.tts is not None
                    and self.tts._pending() >= 3):
                continue
            if persona == "ENGINEER":
                # bypass lines (overtake acks, severe damage, incident points,
                # session intro) skip the 14s spacing — they're one-shot, must
                # land while they still mean something, and carry their OWN
                # cooldowns so they can't machine-gun.
                if not bypass and now - self._eng_cd < self.RADIO_ENG_CD:
                    continue
            elif not bypass and (now - self.driver_radio_cd.get(sl, 0)
                                 < self.RADIO_DRIVER_CD):
                continue
            # TIER-C rival drivers radio in their NATIVE language; the bubble then
            # shows the English translation. Use SESSION-APPROPRIATE chatter — the
            # race set is full of battle lines ("he's right behind me!"), which is
            # nonsense in practice/qualifying, so non-race sessions use the
            # lap/pace-flavoured set instead.
            spoken_text, disp_text = None, txt
            if persona != "ENGINEER" and self.tts:
                lang = self.tts.native_lang(persona, nm)
                pool = NATIVE_RADIO if is_race else NATIVE_RADIO_QUALI
                if lang and pool.get(lang):
                    spoken_text, disp_text = random.choice(pool[lang])
            color = (ENGINEER_COLOR if persona == "ENGINEER"
                     else self._color_for_name(nm))
            msg = {"name": nm, "text": disp_text, "color": color,
                   "emotion": emotion, "engineer": persona == "ENGINEER"}
            if persona == "ENGINEER":
                self._eng_cd = now
            else:
                self.driver_radio_cd[sl] = now
            spoke = "no-tts"
            if self.tts and self.tts.enabled:
                # show the BUBBLE when the audio actually starts (on_play), so the
                # message on screen matches what you hear instead of racing ahead.
                # native lines are spoken as-is (no English name/gap substitution).
                say_text = (spoken_text if spoken_text is not None
                            else self._spoken(txt))
                self.tts.speak(say_text, persona, seed=nm,
                               on_play=lambda t, p, _m=msg: self._air_bubble(_m))
                spoke = "spoke"
            else:
                self._air_bubble(msg)                 # muted / no TTS -> show now
                spoke = "muted" if self.tts else "no-tts"
            self._radio_recent.append(f"{time.strftime('%H:%M:%S')} {persona[:4]}"
                                      f"/{emotion[:4]} [{spoke}] {txt[:40]}")
            self._radio_recent = self._radio_recent[-7:]
            emitted += 1
        if emitted:
            self.last_radio_t = now

    def _wrap(self, text, width=34, maxlines=2):
        words, lines, cur = text.split(), [], ""
        for wd in words:
            if len(cur) + len(wd) + 1 > width:
                lines.append(cur); cur = wd
            else:
                cur = (cur + " " + wd).strip()
        if cur:
            lines.append(cur)
        return lines[:maxlines]

    def _draw_bubble(self, x, y, w, m):
        col = m.get("color", ACCENT)
        is_eng = bool(m.get("engineer"))
        accent = HEADER_ACCENT if is_eng else col
        emotion = m.get("emotion", "neutral")
        lines = self._wrap(m["text"], width=30)
        h = _BUBBLE_H(len(lines))
        # broadcast card: dark rounded box, thin border, accent strip in the
        # driver's colour (cyan for the engineer)
        self._card(x, y, w, h, fill=CARD_BG, accent=accent, side="top")
        # avatar in a SQUARE region (so it's never stretched), vertically centred.
        # Drawn on the panel's real canvas — avatars use polygon/arc, which the
        # translating canvas wrapper doesn't proxy — at panel-local coords.
        av = h - 18
        ax = x + 11
        ay = y + (h - av) // 2
        if is_eng:
            avatars.draw_engineer(self._cv_real, ax - self._ox, ay - self._oy,
                                  av, emotion)
        else:
            avatars.draw_avatar(self._cv_real, ax - self._ox, ay - self._oy,
                                av, emotion, col)
        tx = ax + av + 12                     # text zone starts after the avatar
        name = m["name"][:14]
        self.text(tx, y + 17, name, fill=accent, font=self.f_row_b, anchor="w")
        if not is_eng:                        # small "RADIO" tag pill (drivers)
            px = tx + self.f_row_b.measure(name) + 8
            self.canvas.create_rectangle(px, y + 10, px + 42, y + 23,
                                         fill="#1c2530", outline="")
            self.text(px + 21, y + 16, "RADIO", fill=DIM,
                      font=self.f_small_b, anchor="center")
        ly = y + 36
        for ln in lines:
            self.text(tx, ly, ln, fill=TEXT, font=self.f_row, anchor="w")
            ly += 18
        return h

    def update_commentary(self, s):
        """Third-person play-by-play over the WHOLE field. Reuses the per-tick
        stats (places, intervals, fastest lap) the overlay already computes."""
        if not self.commentary_on:
            return
        now = time.time()
        if self._comm_key != self._sess_key:           # reset on new session
            self._comm_key = self._sess_key
            self._comm_prev = {}
            self._comm_cd = 0.0
            self._comm_flags = {}
            self._comm_lead = None
            self._comm_fastest_at = 0.0
            self._comm_pit = {}
            self._pit_t = {}          # slot -> last time seen in pitlane
            self._comm_prev_int = {}
            self._comm_pen = {}
            self._battle = {}
            self._battle_called = {}  # (chaser,target) -> last sustained-battle call
            self._battle_cd = 0.0     # global cooldown for sustained-battle calls
            self._last_pass = None    # (winner_slot, loser_slot, pos, t) re-pass detect
            self._race_story = {}     # slot -> {best,worst,now}: each driver's arc
            self._story_told = set()  # slots whose race-story recap has been aired
            self._wrap_until = 0.0    # clear stale post-race wrap protection
            self._last_off = None     # (name, t) most recent off — for naming yellows
            self._filler_cd = {}
            self._story = {}          # slot -> list of notable tags ("spun","led","recovered")
            self._comm_best = {}      # slot -> best lap seen (quali/practice reports)
            self._comm_lap_cd = 0.0   # throttle for lap-report events
            self._crosstalk_t = 0.0   # last commentator->pundit question
            self._crosstalk_topic = None  # paired Q/A topic for the current crosstalk
            self._crosstalk_pos = 0   # the questioned driver's place
            self._comm_close_t = 0.0  # last closing-phase 'win fight' emphasis
            self._offtrack_cd = {}    # slot -> last off-track call (anti-double)
            self._player_lap_valid = 1  # player's prev current_lap_valid (edge)
            self._off_watch = None     # (deadline, ref_speed) while confirming an off
            self._incident_until = 0.0  # an incident is being reported until this
            self._incident_extra = 0    # extra cars off during the current window
            self._signed_off = False    # booth has aired its closing sign-off?
            self._filler_until = 0.0    # est. time a colour/filler line finishes
            self._comm_qpole = None     # slot on provisional pole (time-true)

        # once the booth has signed off (after the post-race wrap), the broadcast
        # is OVER — produce no further commentary. The queued wrap still plays out.
        if getattr(self, "_signed_off", False):
            return

        order = sorted(self._drivers(s), key=lambda d: d.place)
        if len(order) < 1:
            return
        placemap = {d.place: d for d in order}
        # change detection runs on CONFIRMED (debounced) places so the booth
        # never reacts to a flicker; display/naming still uses the live placemap
        cp = lambda d: self.cplace.get(d.driver_info.slot_id, d.place)
        cur = {d.driver_info.slot_id: cp(d) for d in order}
        # RACE STORY: keep every driver's arc (best/worst/current place) so the
        # booth can talk about anyone's race with real context ("started P3,
        # dropped to P12, recovered to P7"). Cheap per-tick bookkeeping.
        if s.session_type == 2 and self._racing:
            for d in order:
                sl, p = d.driver_info.slot_id, d.place
                st = self._race_story.get(sl)
                if st is None:
                    self._race_story[sl] = {"best": p, "worst": p, "now": p}
                else:
                    st["now"] = p
                    st["best"] = min(st["best"], p)
                    st["worst"] = max(st["worst"], p)
        trk = self._short_track(R.u8_to_str(s.track_name))
        is_race = (s.session_type == 2)
        n1 = self._dname(placemap[1]) if 1 in placemap else ""
        n2 = self._dname(placemap[2]) if 2 in placemap else ""
        n3 = self._dname(placemap[3]) if 3 in placemap else ""
        # QUALI/PRACTICE: the timing-tower 'place' is just registration order
        # until laps are actually set, so a name being 'P1' does NOT mean they're
        # on provisional pole. Build the REAL provisional order from drivers who
        # have banked a lap (best_lap among _q_set), sorted by time. n1/n2/n3 stay
        # place-based for race use; q_n1/q_n2/q_n3 are the time-true quali order.
        field_n = len(order)
        # an OPEN/registered qualifying or practice has NO clock (you can stay out
        # as long as you like with just your ghost); a pre-race quali is timed.
        open_sess = (getattr(s, "session_time_duration", 0.0) or 0.0) <= 0.0
        # SOLO = effectively on your own: one car, OR an open/registered session
        # with just you and your ghost (which can show as two entries). A timed
        # session with 2+ real cars is NOT solo.
        solo = (not is_race) and (field_n <= 1 or (open_sess and field_n <= 2))
        q_n1 = q_n2 = q_n3 = ""
        q_set_t = []
        if not is_race:
            q_set_t = [d for d in order
                       if d.driver_info.slot_id in getattr(self, "_q_set", set())
                       and self.best_lap.get(d.driver_info.slot_id)]
            q_set_t.sort(key=lambda d: self.best_lap[d.driver_info.slot_id])
            q_n1 = self._dname(q_set_t[0]) if len(q_set_t) > 0 else ""
            q_n2 = self._dname(q_set_t[1]) if len(q_set_t) > 1 else ""
            q_n3 = self._dname(q_set_t[2]) if len(q_set_t) > 2 else ""
        cands = []   # (priority, text, cat, intensity, persona)

        def L(cat, prio, persona="COMMENTATOR", line=None, **kw):
            pool = COMMENTARY_LINES.get(cat)
            if pool or line is not None:
                kw.setdefault("trk", trk)
                kw.setdefault("comm", COMMENTATOR_NAME)
                kw.setdefault("pundit", PUNDIT_NAME)
                kw.setdefault("comm_full", COMMENTATOR_FULL)
                kw.setdefault("pundit_full", PUNDIT_FULL)
                # `line` lets the caller supply the exact text (e.g. a crosstalk
                # question drawn from a PAIRED topic) while still flowing through
                # the normal formatting / intensity / queueing path.
                text = line if line is not None else self._pick(pool, ("COMM", cat))
                cands.append((prio, _safe_format(text, kw),
                              cat, CAT_INTENSITY.get(cat, 1), persona))

        total = s.number_of_laps
        # CONFIRMED leader (debounced) so a flicker at the front never triggers a
        # false "new race leader" call
        leader = next((d for d in order if cp(d) == 1), placemap.get(1))
        is_quali = (s.session_type == 1)

        # ---- RACE PHASE: a real broadcast follows the STORY of the race, not the
        # whole field equally. Opening laps -> lock onto the leaders/front; the
        # mid race -> open it up to battles, track facts, the wider field; the
        # closing laps -> swing back to the fight for the win. `_focus(place)`
        # gates the chatter so we don't narrate a P12 scrap while the front is
        # the story (and so big stuff lands on time, not buried under midfield).
        ll = leader.completed_laps if leader is not None else 0
        # RaceRoom's white flag means SLOW CAR ON TRACK (European rules), NOT
        # final lap — a lap-3 tow-in was making the booth scream "LAST LAP".
        # So: in LAP races, "final lap" comes from counting laps only; in TIMED
        # races the white flag is only trusted once the clock has expired
        # (that's the one case where it does accompany the last lap).
        wf = (s.flags.white == 1)
        timed = not (total and total > 0)       # RaceRoom online sprints are timed
        self._timed = timed
        if not timed:                           # LAP race: phase by laps to go
            togo = total - ll
            white = (ll >= 1 and togo == 1)     # leader has started the last lap
            if ll < 1:
                phase = "opening"
            elif white or togo <= 1:
                phase = "closing"
            elif togo <= 4:
                phase = "late"
            else:
                phase = "mid"
        else:                                   # TIMED race: phase by the clock
            togo = 999
            dur, rem = s.session_time_duration, s.session_time_remaining
            white = (wf and not (rem and rem > 0))   # white only after time-up
            if ll < 1:
                phase = "opening"
            elif white:
                phase = "closing"               # on the final lap after time-up
            elif dur and dur > 0 and rem > 0 and rem / dur < 0.18:
                phase = "late"                  # final ~fifth of the clock
            else:
                phase = "mid"
        flimit = {"opening": 5, "late": 8, "closing": 5, "mid": 99}[phase]

        def _focus(place):
            """Is this place worth commentating in the current phase?"""
            return place <= flimit

        def _INC(cat, persona="PUNDIT", intensity=2, cutoff=False, **kw):
            """Incident line (yellow / penalty) — bypasses cands + COMMENTARY_CD,
            always force-queued. cutoff=True interrupts current audio, BUT never
            while an off-track report is mid-flight (it queues behind instead) so
            incidents don't sever one another — e.g. a yellow caused by a spin
            now FOLLOWS the spin call rather than cutting it off."""
            pool = COMMENTARY_LINES.get(cat)
            if not pool:
                return
            kw.setdefault("trk", trk)
            kw.setdefault("comm", COMMENTATOR_NAME)
            kw.setdefault("pundit", PUNDIT_NAME)
            kw.setdefault("comm_full", COMMENTATOR_FULL)
            kw.setdefault("pundit_full", PUNDIT_FULL)
            text = _safe_format(self._pick(pool, ("COMM", cat)), kw)
            spoken = self._spoken(text)
            seed = "PUNDIT" if persona == "PUNDIT" else "COMM"
            if self.tts:
                if cutoff and now >= getattr(self, "_incident_until", 0.0):
                    self.tts.interrupt()   # cut current dialogue, drain queue
                    self._incident_until = now + 5.0
                self.tts.speak(spoken, persona, seed=seed, intensity=intensity,
                               on_play=self._show_caption, force=True)
        # race START — works in REPLAYS too: don't rely on start_lights/phase
        # (often unset in replay), just catch the leader still on the opening lap
        # grid build-up (once, while still on the standing grid) so the booth is
        # AWARE of the start instead of dead silent, then the punchy lights-out
        # call lands at green
        if (is_race and not self._racing and leader is not None
                and not self._comm_flags.get("pregrid")):
            self._comm_flags["pregrid"] = True
            self._intro_emit_t = now            # engineer gate: scene being set
            L("pregrid", 2, drv=self._dname(leader))
        # START call fires the instant the race goes green (the _racing edge),
        # naming the leader — "Lights out and {leader} leads them away!" Fired
        # DIRECTLY with force (like the finish wrap) so this signature moment can
        # NEVER be dropped or buried behind the pregrid welcome — it interrupts
        # whatever's playing and lands right on the lights going out.
        if (is_race and self._racing and not self._comm_flags.get("start")
                and leader is not None):
            self._comm_flags["start"] = True
            self._intro_emit_t = now            # latest opener -> hold engineer
            self._green_at = now                # start of the grid-sort window
            if self.tts:
                # INSTANT pre-rendered lights-out sting fires on the green edge
                # with zero render latency; the named "…and {leader} leads them
                # away!" line is queued straight after WITHOUT its own interrupt
                # (the sting already purged), so it lands as the bridge finishes.
                # If no sting is ready yet, fall back to the old interrupt+render.
                stung = self.tts.sting("lightsout", "COMMENTATOR",
                                       on_play=self._show_caption)
                if not stung:
                    self.tts.interrupt()        # cut the welcome, land on the moment
                # the sting already SAID "lights out and away we go" — the named
                # follow-up must not repeat it, so filter the pool to the lines
                # that don't open with a lights/getaway call
                pool = COMMENTARY_LINES["start"]
                if stung:
                    _lo = re.compile(r"lights|five red|away we go", re.I)
                    pool = [t for t in pool if not _lo.search(t)] or pool
                stxt = _safe_format(self._pick(pool, ("COMM", "start")),
                                    {"drv": self._dname(leader), "trk": trk})
                self.tts.speak(self._spoken(stxt), "COMMENTATOR", seed="COMM",
                               intensity=2, on_play=self._show_caption, force=True)
                self._incident_until = now + 3.0  # protect it from being cut
            else:
                self._show_caption(_safe_format(
                    self._pick(COMMENTARY_LINES["start"], ("COMM", "start")),
                    {"drv": self._dname(leader), "trk": trk}), "COMMENTATOR")
        # QUALI/PRACTICE session intro (once) — so the booth names the session
        # correctly instead of calling everything "the race"
        if not is_race and not self._comm_flags.get("qstart"):
            self._comm_flags["qstart"] = True
            self._intro_emit_t = now            # engineer gate: opener airing
            L("quali_start" if is_quali else "practice_start", 1)
        # race FINISH — TWO PHASES so the result is accurate even in a drag race
        # to the line. PHASE A: the instant the LEADER crosses, call the win (the
        # winner is final the moment they take the flag). PHASE B: once the PLAYER
        # has also crossed (finish_status == 1) or a short grace window, fire the
        # rest of the wrap with FINAL positions — otherwise a last-corner pass for
        # the player's place gets mis-reported (the bug: "you finished P3" when
        # you were actually pipped to the line for P4).
        if (is_race and leader is not None
                and not self._comm_flags.get("winannounced")):
            done_race = (s.session_phase == 6 or s.flags.checkered == 1
                         or order[0].finish_status == 1
                         or leader.finish_status == 1
                         or (total and total > 0 and leader.completed_laps >= total))
            if done_race:
                self._comm_flags["winannounced"] = True
                self._finish_at = now
                wtxt = _safe_format(
                    self._pick(COMMENTARY_LINES["win"], ("FIN", "win")),
                    {"drv": self._dname(leader), "trk": trk,
                     "comm": COMMENTATOR_NAME, "pundit": PUNDIT_NAME,
                     "comm_full": COMMENTATOR_FULL, "pundit_full": PUNDIT_FULL})
                if self.tts:
                    # INSTANT pre-rendered VICTORY sting on the flag (zero render
                    # latency on the signature moment); the named win call is
                    # queued straight after WITHOUT its own interrupt (the sting
                    # already purged), so it lands as the bridge finishes.
                    stung = self.tts.sting("victory", "COMMENTATOR",
                                           on_play=self._show_caption)
                    if not stung:
                        self.tts.interrupt()
                    self.tts.speak(self._spoken(wtxt), "COMMENTATOR", seed="COMM",
                                   intensity=2, on_play=self._show_caption,
                                   force=True)
                    self._incident_until = now + 3.0   # protect it from being cut
                else:
                    self._show_caption(wtxt, "COMMENTATOR")
        if (is_race and self._comm_flags.get("winannounced")
                and not self._comm_flags.get("finish")):
            pfin = next((d for d in order if d.driver_info.slot_id
                         == s.vehicle_info.slot_id), None)
            if ((pfin is not None and pfin.finish_status == 1)
                    or now - getattr(self, "_finish_at", now) > 8.0):
                self._comm_flags["finish"] = True
                # FINAL order now (cars have crossed) -> accurate podium/player pos
                fn1 = self._dname(order[0]) if order else n1
                fn2 = self._dname(order[1]) if len(order) > 1 else ""
                fn3 = self._dname(order[2]) if len(order) > 2 else ""
                chasers = [self._dname(d) for d in order[1:5]]
                self._finish_sequence(fn1, fn2, fn3, trk, chasers, include_win=False)
                self._signed_off = True
                self._comm_prev = cur
                return

        if leader is not None:
            lslot = leader.driver_info.slot_id
            if is_race and self._comm_lead is not None and lslot != self._comm_lead:
                L("leadchange", 0, drv=self._dname(leader))
                self._story.setdefault(lslot, [])
                if "led" not in self._story[lslot]:
                    self._story[lslot].append("led")
            # QUALI: provisional pole is the fastest TIME set — NOT the
            # timing-tower position (which is just registration order until laps
            # go in). Only announce a change of pole among drivers who've banked a
            # lap; the very first time set is announced by the fastlap event.
            elif not is_race and q_set_t:
                pole_slot = q_set_t[0].driver_info.slot_id
                prev_pole = getattr(self, "_comm_qpole", None)
                if prev_pole is not None and pole_slot != prev_pole:
                    L("quali_pole", 1, drv=self._dname(q_set_t[0]))
                self._comm_qpole = pole_slot
            self._comm_lead = lslot
            # lap milestones (half distance, closing laps) — keep the story going
            if is_race and total and total > 0:
                done = leader.completed_laps
                togo = max(0, total - done)
                lap = min(total, done + 1)
                for key, cond in (("half", done >= total * 0.5),
                                  ("final5", 0 < togo <= 5),
                                  ("final3", 0 < togo <= 3)):
                    if cond and not self._comm_flags.get(key):
                        self._comm_flags[key] = True
                        L("lap_milestone", 4, lap=lap, total=total, togo=togo)
                        break
            # TIMED race: announce the CLOCK winding down — once each as it drops
            # below 10 / 5 / 2 / 1 minute(s) to go, so the booth is aware the race
            # is nearing its end just like a lap race.
            elif is_race and self._racing and s.session_time_remaining > 0:
                secs = s.session_time_remaining
                mk = (1 if secs <= 60 else 2 if secs <= 120 else 5 if secs <= 300
                      else 10 if secs <= 600 else 0)
                if mk and self._comm_flags.get("mins", 99) > mk:
                    self._comm_flags["mins"] = mk
                    L("time_remaining", 3,
                      mins=("1 minute" if mk == 1 else f"{mk} minutes"))
            if (is_race and s.number_of_laps > 0 and not self._comm_flags.get("lastlap")
                    and leader.completed_laps >= s.number_of_laps - 1):
                self._comm_flags["lastlap"] = True
                L("lastlap", 1, drv=self._dname(leader))

        ft = self.fastest.get("at", 0.0)
        if self.fastest.get("time") and ft > self._comm_fastest_at:
            self._comm_fastest_at = ft
            if self.fastest.get("name"):
                # in quali/practice the fastest lap is the session benchmark, not
                # "the fastest lap of the race" — use the right wording
                L("fastlap" if is_race else "quali_fastlap", 1,
                  drv=self.fastest["name"], gap=R.fmt_time(self.fastest["time"]))

        # periodic CONVERSATION: every ~35s the lead asks the pundit about a
        # specific driver and the pundit answers (the exchange is force-queued in
        # the emit so it always completes). This is the back-and-forth the user
        # wants, so it fires RELIABLY on a fixed cadence — when a driver's had an
        # eventful race we ask for the full story recap, otherwise a general
        # 'how's their race going'. Gated only on a little queue headroom.
        if (is_race and self._racing and order
                and now - self._crosstalk_t > 35.0
                and (self.tts is None or self.tts._pending() < 2)):
            self._crosstalk_t = now
            story_d = self._story_pick(order)
            if story_d is not None and random.random() < 0.6:
                # data-driven recap of THIS driver's race so far (grid -> now)
                self._storyq_d = story_d
                self._crosstalk_drv = self._dname(story_d)
                L("driverstory_q", 1, persona="COMMENTATOR",
                  drv=self._crosstalk_drv)
            else:
                d = random.choice(order[:min(6, len(order))])
                topic = random.choice(list(CROSSTALK))
                self._crosstalk_topic = topic
                self._crosstalk_drv = self._dname(d)
                self._crosstalk_pos = d.place
                L("crosstalk_q", 1, persona="COMMENTATOR",
                  line=self._pick(CROSSTALK[topic]["q"], ("XQ", topic)),
                  drv=self._crosstalk_drv, pos=d.place)

        # GRID-SORT window: for the first ~8s after lights-out the field is still
        # sorting from the standing grid, so big position swaps are NOT incidents.
        # Suppress incident/yellow calls so they can't preempt the lights-out call
        # with a bogus "someone's gone off".
        grid_sort = (is_race and now - getattr(self, "_green_at", -1e9) < 8.0)

        # yellow flag on track (rising edge) — incident, always immediate
        yellow = (s.flags.yellow == 1
                  or any(s.flags.sector_yellow[i] == 1 for i in range(3)))
        if yellow and not self._comm_flags.get("yellow") and not grid_sort:
            self._comm_flags["yellow"] = True
            # Only act if NO incident is already being reported (a player off that
            # caused this yellow already named the culprit). If it IS fresh: instant
            # sting, then NAME whoever most recently went off (past tense, so a
            # slightly late report still fits) — that's the missing follow-up. If
            # we don't know who, fall back to the generic yellow call.
            if now >= getattr(self, "_incident_until", 0.0):
                lo = self._last_off
                name = lo[0] if (lo and now - lo[1] < 8.0) else None
                stung = (self.tts.sting("alert", "PUNDIT",
                                        on_play=self._show_caption)
                         if self.tts else False)
                if name:
                    _INC("offtrack_late", persona="PUNDIT", intensity=2,
                         cutoff=not stung, drv=name)
                    _INC("offtrack_ack", persona="COMMENTATOR", intensity=0)
                else:
                    _INC("yellow", persona="PUNDIT", intensity=2, cutoff=not stung)
                self._incident_until = now + 6.0
        elif not yellow:
            self._comm_flags["yellow"] = False

        # BIG SHUFFLE — many positions changing within ~2s (a pile-up / multi-car
        # melee, common online). Compare to a snapshot taken ~2s ago; if 5+ cars
        # have changed place, the pundit flags the chaos. Skipped in the opening
        # phase (lap one always shuffles) and rate-limited.
        if not hasattr(self, "_shuf_snap") or now - self._shuf_snap_t > 2.0:
            prev_snap = getattr(self, "_shuf_snap", None)
            if (prev_snap and is_race and self._racing and phase != "opening"
                    and now - getattr(self, "_shuffle_cd", 0.0) > 25.0):
                changed = sum(1 for sl, p in cur.items()
                              if prev_snap.get(sl) not in (None, p))
                if changed >= 5:
                    self._shuffle_cd = now
                    L("shuffle", 2, persona="PUNDIT")
            self._shuf_snap = dict(cur)
            self._shuf_snap_t = now

        # PLAYER off-track — report only a GENUINE off, never a harmless run-wide.
        # A lap going invalid (current_lap_valid 1->0) only means you crossed a
        # track limit — which INCLUDES clipping a painted kerb/runoff at full
        # speed (the photo case): not news. So the invalidation is just a
        # CANDIDATE; we confirm it by what actually matters — did you lose real
        # speed? Grass, gravel and spins scrub a big chunk of pace; a clean clip
        # over the line does not. Only when the speed COLLAPSES during the off do
        # we call it — exactly the worth-reporting cases (and the ones that tend to
        # bring out a yellow). Gated to GREEN-flag, on-circuit, moving.
        vslot = s.vehicle_info.slot_id
        pdrv = next((d for d in order if d.driver_info.slot_id == vslot), None)
        in_pits = (pdrv is not None and pdrv.in_pitlane == 1) or s.in_pitlane == 1
        plv = s.current_lap_valid
        spd = abs(s.car_speed)
        racing_clean = (is_race and self._racing and not in_pits and spd > 3.0
                        and not grid_sort)

        if racing_clean:
            lap_edge = (getattr(self, "_player_lap_valid", 1) == 1 and plv == 0)
            if lap_edge and self._off_watch is None:
                # [deadline, ref_speed, min_speed] — min_speed tracks the dip so we
                # can grade the off at the end of the window (collapse / run-wide /
                # clean clip).
                self._off_watch = [now + 1.8, spd, spd]
                if pdrv is not None:                       # candidate culprit for a
                    self._last_off = (self._dname(pdrv), now)  # yellow to name
        else:
            self._off_watch = None
        if self._off_watch is not None and pdrv is not None:
            deadline, ref, mins = self._off_watch
            if spd < mins:
                self._off_watch[2] = mins = spd            # track the lowest dip
            if spd < ref * 0.58 and now - self._offtrack_cd.get(vslot, -1e9) > 5.0:
                # confirmed: lost 40%+ of pace mid-excursion -> a real off (spin)
                self._offtrack_cd[vslot] = now
                self._off_watch = None
                self._last_off = (self._dname(pdrv), now)
                self._report_offtrack(self._dname(pdrv), now, primary=True)
                self._story.setdefault(vslot, [])
                if "spun" not in self._story[vslot]:
                    self._story[vslot].append("spun")
            elif now >= deadline:
                self._off_watch = None
                # window elapsed with no collapse. A MODERATE loss of pace means
                # you ran wide / had a moment off the track -> a lighter booth note
                # (longer cooldown). A clean flat-out kerb clip (no real loss) stays
                # silent so the booth never spams painted-kerb touches.
                if (mins < ref * 0.85
                        and now - self._offtrack_cd.get(vslot, -1e9) > 12.0):
                    self._offtrack_cd[vslot] = now
                    self._report_wide(self._dname(pdrv), now)
        # keep the lap-valid tracker current (even while gated off) so a 1->0 that
        # happened on the grid / in the pits can't 'save up' and fire later
        self._player_lap_valid = plv

        # leader stretching clear out front (milestones at 3/6/10s)
        second = placemap.get(2)
        if is_race and leader is not None and second is not None:
            g2 = self.interval.get(second.driver_info.slot_id)
            if g2:
                mile = 10 if g2 >= 10 else 6 if g2 >= 6 else 3 if g2 >= 3 else 0
                if mile and self._comm_flags.get("pull") != mile:
                    self._comm_flags["pull"] = mile
                    L("pulling_away", 3, drv=self._dname(leader),
                      gap=f"{g2:.1f} seconds")

        prev_int = getattr(self, "_comm_prev_int", {})
        for d in order:
            sl = d.driver_info.slot_id
            if is_race and d.in_pitlane == 1:
                self._pit_t[sl] = now            # mark recently-in-pits (for the
                if not self._comm_pit.get(sl):   # off-track false-positive guard)
                    self._comm_pit[sl] = True
                    L("pit", 3, drv=self._dname(d))
            elif d.in_pitlane != 1:
                self._comm_pit[sl] = False
            # penalty handed out (rising edge per driver)
            pen = getattr(d, "penaltyType", -1)
            if is_race and pen >= 0 and self._comm_pen.get(sl) != pen:
                self._comm_pen[sl] = pen
                _INC("penalty", persona="PUNDIT", intensity=2, drv=self._dname(d))
            elif pen < 0:
                self._comm_pen[sl] = -1
            # a strong recovery drive (climbing well clear of the grid slot)
            gain = self.grid_place.get(sl, d.place) - d.place
            if is_race and gain >= 4:
                mk = gain // 3
                if self._comm_flags.get(f"rec{sl}") != mk:
                    self._comm_flags[f"rec{sl}"] = mk
                    L("recovery", 3, drv=self._dname(d), pos=d.place)
                    self._story.setdefault(sl, [])
                    if "recovered" not in self._story[sl]:
                        self._story[sl].append("recovered")
            pv = self._comm_prev.get(sl)
            cpd = cp(d)                                 # this driver's CONFIRMED place
            if pv is None:
                continue
            if (is_race and self._racing and cpd >= pv + 2   # off-track / big loss
                    and not grid_sort                        # not the grid sorting out
                    and d.in_pitlane != 1                    # not a car in the pits
                    and now - self._pit_t.get(sl, -1e9) > 12.0   # nor a pit rejoin
                    and now - self._offtrack_cd.get(sl, -1e9) > 6.0):
                # Routed through _report_offtrack so it can't cut off another
                # incident mid-call and multi-car pile-ups are coalesced. _focus()
                # intentionally NOT applied — an incident matters regardless of
                # position. Gated on the race being GREEN and the car not pitting,
                # so a standing-start shuffle or a pit stop isn't called an "off".
                # The per-slot cooldown also stops a double-call when the player's
                # instant lap-invalid path already fired above.
                self._offtrack_cd[sl] = now
                self._last_off = (self._dname(d), now)    # culprit for a yellow
                self._report_offtrack(self._dname(d), now)
                self._story.setdefault(sl, [])
                if "spun" not in self._story[sl]:
                    self._story[sl].append("spun")
            elif is_race and cpd == pv - 1 and _focus(cpd):  # gained a place
                victim = placemap.get(cpd + 1)
                if (victim is not None
                        and self._comm_prev.get(victim.driver_info.slot_id) == cpd):
                    # how close were they? the victim is now directly behind, so
                    # its interval IS the gap to our overtaker. Only call it a
                    # dramatic "dive up the inside" pass when they're genuinely
                    # wheel-to-wheel (<0.45s); a wider gap gets a neutral line,
                    # and a big gap (>1.6s) is almost always a pit cycle or an
                    # off, not real on-track combat, so don't commentate a duel.
                    vgap = self.interval.get(victim.driver_info.slot_id)
                    b = self._battle.get(sl)
                    longfight = (b and b[0] == victim.driver_info.slot_id
                                 and now - b[1] > 8.0)
                    if longfight:
                        cat = "overtake_long"
                    elif vgap is not None and vgap < 0.45:
                        cat = "overtake"            # close, on-track pass
                    elif vgap is None or vgap < 1.6:
                        cat = "pass_clean"          # a pass, but not a knife-fight
                    else:
                        cat = None                  # likely pit/off, stay quiet
                    # a routine (non-wheel-to-wheel) pass deep in the field is the
                    # "X passes Y for P12" spam the tester flagged — mostly skip it
                    if cat == "pass_clean" and cpd > 8 and random.random() > 0.35:
                        cat = None
                    # RE-PASS / REVERSAL: if this exact pair just swapped this
                    # position the other way moments ago, it's a fight-back. Say so
                    # AND interrupt the now-stale "X takes P{pos}" that's likely
                    # still rendering/playing, so the booth isn't a swap behind the
                    # live action (the P3-then-not confusion).
                    vsl = victim.driver_info.slot_id
                    lp = self._last_pass
                    if (cat and lp and lp[0] == vsl and lp[1] == sl
                            and lp[2] == cpd and now - lp[3] < 6.0):
                        cat = "retake"
                        if self.tts:
                            self.tts.interrupt()
                    if cat:
                        L(cat, 1 if cat == "retake" else 2,
                          drv=self._dname(d), oth=self._dname(victim), pos=cpd)
                        self._last_pass = (sl, vsl, cpd, now)
                    self._battle.pop(sl, None)

        if is_race and self._racing:
            for d in order[:8]:                         # close fight near the front
                sl = d.driver_info.slot_id
                itv = self.interval.get(sl)
                if itv is None or d.place <= 1:
                    continue
                ahead = placemap.get(d.place - 1)
                if ahead is None or not _focus(ahead.place):
                    continue
                if 0.05 < itv < 0.6 and random.random() < 0.12:
                    L("battle", 3, drv=self._dname(d),
                      oth=self._dname(ahead), pos=ahead.place)   # contested place
                    break
                pvi = prev_int.get(sl)                  # closing the gap down quickly
                if (pvi is not None and 0.6 < itv < 2.0 and pvi - itv > 0.2
                        and random.random() < 0.18):
                    L("closing", 3, drv=self._dname(d),
                      oth=self._dname(ahead), pos=ahead.place)
                    break
            # midfield scraps ONLY in the mid race (the opening + closing belong
            # to the leaders) and at a lower rate so it's not "X passes Y for P12"
            # every few seconds — the tester's main complaint
            if phase == "mid":
                for d in order[8:18]:
                    sl = d.driver_info.slot_id
                    itv = self.interval.get(sl)
                    if (itv is not None and 0.05 < itv < 0.5 and d.place > 1
                            and random.random() < 0.035):
                        ahead = placemap.get(d.place - 1)
                        if ahead is not None:
                            L("battle_mid", 4, drv=self._dname(d),
                              oth=self._dname(ahead), pos=ahead.place)
                            break
        self._comm_prev_int = {d.driver_info.slot_id:
                               self.interval.get(d.driver_info.slot_id) for d in order}

        # battle memory: track how long each car has been hounding the one ahead.
        # Tuple is (target_slot, start_time, start_lap) — start_lap lets the
        # sustained-battle callout report the fight's length in laps.
        for d in order:
            sl = d.driver_info.slot_id
            itv = self.interval.get(sl)
            ahead = placemap.get(d.place - 1)
            if ahead is not None and itv is not None and itv < 0.9 and d.place > 1:
                tslot = ahead.driver_info.slot_id
                b = self._battle.get(sl)
                if not b or b[0] != tslot:
                    self._battle[sl] = (tslot, now, d.completed_laps)  # new fight
            elif itv is None or itv > 1.4:
                self._battle.pop(sl, None)                 # gap opened, fight over

        # SUSTAINED BATTLE — a fight that's gone the distance WITHOUT resolving
        # into a pass yet ("nose-to-tail for three laps now"). The staple of real
        # colour commentary. Front-focused, gated on `not cands` so live events
        # always win, and rate-limited globally + per pair so it never nags. Picks
        # the longest-running, most forward unresolved fight on track.
        if (is_race and self._racing and not cands
                and now - getattr(self, "_battle_cd", 0.0) > 18.0):
            best = None
            for d in order:
                sl = d.driver_info.slot_id
                b = self._battle.get(sl)
                if not b:
                    continue
                tslot, t0, lap0 = b
                ahead = placemap.get(d.place - 1)
                if (ahead is None
                        or ahead.driver_info.slot_id != tslot
                        or not _focus(ahead.place)):
                    continue
                itv = self.interval.get(sl)
                if itv is None or itv > 1.0 or now - t0 < 14.0:
                    continue
                if now - self._battle_called.get((sl, tslot), -1e9) < 30.0:
                    continue
                score = (now - t0) - ahead.place      # longer + more forward wins
                if best is None or score > best[0]:
                    best = (score, d, ahead, sl, tslot, now - t0, lap0)
            if best is not None:
                _, d, ahead, sl, tslot, dur, lap0 = best
                laps = max(0, d.completed_laps - lap0)
                if laps >= 2:
                    dur_txt = self._spell_laps(laps)
                elif dur >= 45.0:
                    dur_txt = "the best part of a minute"
                else:
                    dur_txt = "several corners now"
                self._battle_cd = now
                self._battle_called[(sl, tslot)] = now
                L("battle_sustained", 3, drv=self._dname(d),
                  oth=self._dname(ahead), pos=ahead.place, dur=dur_txt)

        # OPENING, LATE & CLOSING keep FOCUS ON THE FRONT — the start/early
        # leaders and the fight for the win down the stretch. Mid race gets the
        # wider-field colour below.
        if (phase in ("opening", "late", "closing") and is_race and self._racing
                and leader is not None and not cands
                and now - self._comm_close_t > 15.0):
            self._comm_close_t = now
            sec = placemap.get(2)
            g2 = self.interval.get(sec.driver_info.slot_id) if sec is not None else None
            if sec is not None and g2 is not None and 0.05 < g2 < 1.5:
                L("battle", 2, drv=self._dname(sec), oth=self._dname(leader), pos=1)
            elif n3:
                L("standings", 3, p1=n1, p2=n2, p3=n3)

        # LATE phase — one-time urgency call (LAP races only; the {togo} wording
        # needs a lap count). Timed races get their late nudge via the time-aware
        # insight layer instead.
        if (is_race and phase == "late" and self._racing and not timed
                and not self._comm_flags.get("late_entry") and leader is not None):
            self._comm_flags["late_entry"] = True
            L("late", 2, persona="COMMENTATOR", togo=togo)

        # FINAL LAP — fire on the WHITE FLAG (works for BOTH lap and timed races;
        # in a timed race the last lap only begins once the clock hits zero).
        if (is_race and self._racing and leader is not None
                and (white or (total and total > 0 and togo <= 0))
                and not self._comm_flags.get("final_lap")):
            self._comm_flags["final_lap"] = True
            L("final_lap", 0, persona="COMMENTATOR")

        # a circuit-trivia drop early on (once, around lap 2) — name & history.
        # Hold it back until the MID race — the opening belongs to the leaders.
        if (is_race and phase != "opening" and not self._comm_flags.get("trackintro")
                and leader is not None and leader.completed_laps >= 1):
            self._comm_flags["trackintro"] = True
            fact = self._track_fact(trk)
            cands.append((4, _safe_format(fact or self._pick(
                COMMENTARY_LINES["track_generic"], ("COMM", "trk")), {"trk": trk}),
                "track_fact", 0, "COMMENTATOR"))

        ctx = SimpleNamespace(
            s=s, now=now, order=order, placemap=placemap, cur=cur, leader=leader,
            phase=phase, total=total, togo=togo, timed=timed, is_race=is_race,
            is_quali=is_quali, solo=solo, open_sess=open_sess, field_n=field_n,
            trk=trk, n1=n1, n2=n2, n3=n3, q_n1=q_n1, q_n2=q_n2, q_n3=q_n3,
            q_set_t=q_set_t, cands=cands, L=L)
        self._colour_race(ctx)        # MID-RACE colour rotation
        self._quali_events(ctx)       # quali/practice event-driven booth
        self._colour_quali(ctx)       # quali/practice filler
        self._emit_commentary(ctx)    # arbitrate cands -> speak

    def _colour_race(self, c):
        """MID-RACE colour rotation (extracted verbatim from update_commentary)."""
        # once the win is announced the race is OVER for the booth: no more
        # "X minutes remaining" / stakes / analysis colour — those lines queue
        # behind the finish wrap and air stale after the flag, which is the
        # single most immersion-breaking thing the booth can do
        if self._comm_flags.get("winannounced"):
            return
        is_race, phase, cands, now = c.is_race, c.phase, c.cands, c.now
        order, placemap, leader = c.order, c.placemap, c.leader
        total, togo, timed = c.total, c.togo, c.timed
        n1, n2, n3, s, trk, L = c.n1, c.n2, c.n3, c.s, c.trk, c.L
        # MID-RACE colour (no dead air): driver assessments, track trivia,
        # standings, analysis. Mid + late phases — opening belongs to leaders,
        # closing to the win fight. Late phase gets a narrower subset (no random
        # criticism/midpack — keep urgency, not colour).
        if is_race and phase in ("mid", "late") and not cands:
            # the LEAD commentator is the primary voice — weight filler toward him
            # (~65%) so the pundit complements rather than dominates the booth
            who2 = lambda: "COMMENTATOR" if random.random() < 0.65 else "PUNDIT"
            fcd = self._filler_cd
            rdy = lambda t, g: now - fcd.get(t, -1e9) >= g
            pcar = self._player_car(s)
            types = ["analysis"]
            # INSIGHT — the pundit framing the live race state (gaps, laps,
            # stakes). The core "help the viewer understand the race" layer, so
            # it's offered often (short gate) in BOTH mid and late phases.
            mins_left = (int(s.session_time_remaining // 60)
                         if timed and s.session_time_remaining > 0 else None)
            ins = self._insight(placemap, n1, n2, n3, total, togo, mins_left)
            if ins and rdy("insight", 9):
                types.append("insight")
            if rdy("stat", 12):
                types.append("stat")
            if n3 and rdy("standings", 12):
                types.append("standings")
            if rdy("crosstalk", 14):
                types.append("crosstalk")
            if rdy("lore", 70):                 # the booth's racing-past banter
                types.append("lore")
            # RACE ARC — call back to a driver's earlier incident (did it cost
            # them, or did they recover?). Available mid AND late, since the
            # closing-stages payoff ("that earlier incident cost them") is the
            # whole point.
            arc = self._story_arc(order)
            if arc and rdy("storyarc", 18):
                types.append("storyarc")
            # RACE STORY conversation — the lead asks the pundit to recap an
            # eventful driver's whole race (grid -> now), pundit answers from the
            # recorded data. Rare-ish; it's a proper bit of analysis.
            story_d = self._story_pick(order)
            if story_d is not None and rdy("driverstory", 30):
                types.append("driverstory")
            # colour-padding types only in mid (not late — urgency wins)
            if phase == "mid":
                if rdy("praise", 14):
                    types.append("praise")
                if len(order) >= 5 and rdy("midpack", 16):
                    types.append("midpack")
                if len(order) > 10 and rdy("criticism", 18):
                    types.append("criticism")
                if rdy("track", 22):
                    types.append("track")
                if rdy("broadcast", 40):      # RacerTV channel ID — a rare treat
                    types.append("broadcast")
                if total and total > 0 and leader is not None and rdy("lap", 24):
                    types.append("lap")
                if pcar and rdy("car", 45):
                    types.append("car")
            # ROTATION (#3): bias toward the category used LONGEST ago so every
            # type cycles in and no two races sound the same — round-robin-ish,
            # with a little random jitter so the order still varies. (Plain
            # random.choice clustered the same few fillers.)
            pick = min(types, key=lambda t: fcd.get(t, -1e9) + random.uniform(0, 5))
            fcd[pick] = now
            if pick == "insight":
                cat, ikw = ins
                # the lead frames the race state too (not just the pundit), so the
                # play-by-play voice stays prominent
                L(cat, 6, persona=who2(), **ikw)
            elif pick == "storyarc":
                acat, adrv = arc
                L(acat, 6, persona="PUNDIT", drv=adrv)
            elif pick == "driverstory":
                # lead asks; pundit answers dynamically at emission (below)
                self._storyq_d = story_d
                self._crosstalk_drv = self._dname(story_d)
                L("driverstory_q", 6, persona="COMMENTATOR",
                  drv=self._crosstalk_drv)
            elif pick == "lap":
                done = leader.completed_laps
                L("lap_milestone", 6, lap=min(total, done + 1), total=total,
                  togo=max(0, total - done))
            elif pick == "standings":
                L("standings", 6, p1=n1, p2=n2, p3=n3)
            elif pick == "car":                          # name the player's car
                pdrv = next((d for d in order
                             if d.driver_info.slot_id == s.vehicle_info.slot_id),
                            None)
                L("car", 6, persona=who2(),
                  drv=self._dname(pdrv) if pdrv else "our driver", car=pcar)
            elif pick == "praise":                       # TOP 3 — driving brilliantly
                dd = random.choice(order[:3])
                dsl = dd.driver_info.slot_id
                tags = self._story.get(dsl, [])
                cat = ("praise_recovery" if "recovered" in tags and
                       COMMENTARY_LINES.get("praise_recovery")
                       else "praise_led" if "led" in tags and
                       COMMENTARY_LINES.get("praise_led")
                       else "praise")
                L(cat, 6, persona=who2(), drv=self._dname(dd))
            elif pick == "midpack":                      # P4-P10 — solid/average race
                cand = order[3:10]
                if cand:
                    dd = random.choice(cand)
                    dsl = dd.driver_info.slot_id
                    tags = self._story.get(dsl, [])
                    cat = ("midpack_recovery" if "recovered" in tags and
                           COMMENTARY_LINES.get("midpack_recovery")
                           else "midpack_spun" if "spun" in tags and
                           COMMENTARY_LINES.get("midpack_spun")
                           else "midpack")
                    L(cat, 6, persona=who2(), drv=self._dname(dd), pos=dd.place)
            elif pick == "criticism":                    # P11+ — having a rough one
                cand = order[10:]
                if cand:
                    dd = random.choice(cand)
                    dsl = dd.driver_info.slot_id
                    tags = self._story.get(dsl, [])
                    cat = ("criticism_spun" if "spun" in tags and
                           COMMENTARY_LINES.get("criticism_spun")
                           else "criticism")
                    L(cat, 6, persona=who2(), drv=self._dname(dd))
            elif pick == "crosstalk":                    # lead asks the pundit
                d = random.choice(order[:5])
                topic = random.choice(list(CROSSTALK))
                self._crosstalk_topic = topic
                self._crosstalk_drv = self._dname(d)
                self._crosstalk_pos = d.place
                L("crosstalk_q", 6, persona="COMMENTATOR",
                  line=self._pick(CROSSTALK[topic]["q"], ("XQ", topic)),
                  drv=self._crosstalk_drv, pos=d.place)
            elif pick == "lore":                         # racing-past banter
                if random.random() < 0.6:
                    L("lore_q", 6, persona="COMMENTATOR")     # Miles asks Brett
                else:
                    L("lore_q_rally", 6, persona="PUNDIT")    # Brett asks Miles
            elif pick == "stat":                         # fill space with real numbers
                txt = self._stat_line(placemap, n1, n2)
                if txt:
                    cands.append((6, txt, "stat", 0, who2()))
                else:
                    L("analysis", 6, persona=who2())
            elif pick == "track":
                # the PUNDIT owns circuit knowledge (history + where-to-find-time
                # coaching) — it's his analytical role, and what the player loved
                fact = self._track_fact(trk)
                if fact:
                    cands.append((6, _safe_format(fact, {"trk": trk}),
                                  "track_fact", 0, "PUNDIT"))
                else:
                    L("track_generic", 6, persona="PUNDIT")
            else:
                L("analysis", 6, persona=who2())


    def _quali_events(self, c):
        """Quali/practice event-driven booth (extracted from update_commentary)."""
        is_race, cands, now = c.is_race, c.cands, c.now
        order, q_set_t, L = c.order, c.q_set_t, c.L
        # QUALI / PRACTICE: EVENT-DRIVEN booth — react to the actual laps THIS
        # tick (provisional pole / a notable improvement / a deleted lap) with the
        # real time and provisional position. Tied to events, not a timer.
        if not is_race and not cands and now - self._comm_lap_cd > 4.0:
            by_slot = {d.driver_info.slot_id: d for d in order}
            for sl, kind, val in getattr(self, "_q_events", []):
                d = by_slot.get(sl)
                if d is None:
                    continue
                if kind == "pole":
                    self._comm_lap_cd = now
                    L("quali_fastlap", 2, drv=self._dname(d), gap=R.fmt_time(val))
                    break
                if kind == "deleted":
                    self._comm_lap_cd = now
                    L("quali_deleted", 3, persona="PUNDIT", drv=self._dname(d))
                    break
                if kind == "pb":                      # notable improvements only
                    # rank by TIME among drivers who've actually set a lap, not the
                    # raw timing-tower place (which lags / is registration order)
                    rank = next((i + 1 for i, dd in enumerate(q_set_t)
                                 if dd.driver_info.slot_id == sl), None)
                    if rank is not None and rank <= 8:
                        self._comm_lap_cd = now
                        L("lap_report", 3, drv=self._dname(d),
                          time=R.fmt_time(val), pos=rank)
                        break


    def _colour_quali(self, c):
        """Quali/practice filler (extracted verbatim from update_commentary)."""
        is_race, cands, now, order = c.is_race, c.cands, c.now, c.order
        q_n1, q_n2, q_n3, q_set_t = c.q_n1, c.q_n2, c.q_n3, c.q_set_t
        field_n, solo, open_sess, is_quali = c.field_n, c.solo, c.open_sess, c.is_quali
        s, trk, L, n1 = c.s, c.trk, c.L, c.n1
        # QUALI / PRACTICE filler — keep the booth talking but ONLY with
        # session-safe pools (no race wording). The provisional grid, the venue,
        # the player's car, and in practice a run note.
        if not is_race and not cands:
            # in the calmer practice/qualifying booth keep a genuine 50/50 between
            # the two voices — they're chatting, not calling a race — so it always
            # sounds like TWO people, not one voice droning on
            who2 = lambda: "COMMENTATOR" if random.random() < 0.5 else "PUNDIT"
            fcd = self._filler_cd
            rdy = lambda t, g: now - fcd.get(t, -1e9) >= g
            pcar = self._player_car(s)
            # bread-and-butter "colour" is the default; track facts are an
            # occasional TREAT on a long cooldown (there are only ~4-6 per
            # circuit, so firing them often = an obvious repeating loop)
            nset = len(q_set_t)                          # how many have a TIME
            npits = sum(1 for d in order if d.in_pitlane == 1)
            pdrv = next((d for d in order
                         if d.driver_info.slot_id == s.vehicle_info.slot_id), None)
            pname = self._dname(pdrv) if pdrv is not None else (q_n1 or n1)
            types = []
            if solo:
                # PRIVATE session (just you, maybe a ghost) — talk about YOUR
                # running and GOALS, the venue, the booth's racing past and the
                # odd joke; never a 'field' or 'provisional grid'. Spread across
                # many types on long cooldowns so it never loops the same line.
                if (open_sess and pdrv is not None and pdrv.completed_laps >= 2
                        and rdy("qopen", 28)):
                    types.append("qopen")
                if rdy("qsolo", 45):              # 'only you out there' — sparingly
                    types.append("qsolo")
                if rdy("qgoals", 26):             # what you're working on
                    types.append("qgoals")
                if pcar and rdy("qcar", 40):
                    types.append("qcar")
                if not is_quali and rdy("pnote", 22):
                    types.append("pnote")
                if rdy("scolour", 24):
                    types.append("scolour")
                if rdy("joke", 70):               # a light joke now and then
                    types.append("joke")
                if rdy("qtrack", 50):
                    types.append("qtrack")
            else:
                if rdy("scolour", 9):
                    types.append("scolour")
                # nobody's set a lap yet -> DON'T read the registration order as a
                # grid; say so plainly instead
                if nset == 0 and rdy("qnobody", 16):
                    types.append("qnobody")
                # SESSION STATE — who's set a time, who's still in the pits
                if 0 < nset < field_n and rdy("qcount", 18):
                    types.append("qcount")
                if npits >= max(3, field_n // 2) and rdy("qpits", 22):
                    types.append("qpits")
                # only a 'provisional grid' once THREE have actually set times
                if nset >= 3 and rdy("qstand", 14):
                    types.append("qstand")
                if pcar and rdy("qcar", 34):
                    types.append("qcar")
                if not is_quali and rdy("pnote", 12):
                    types.append("pnote")
                if nset >= 4 and rdy("sslow", 24):
                    types.append("sslow")
                if (open_sess and pdrv is not None and pdrv.completed_laps >= 3
                        and rdy("qopen", 34)):
                    types.append("qopen")
                if pcar and rdy("qgoals", 26):      # what the player's working on
                    types.append("qgoals")
                if rdy("joke", 80):
                    types.append("joke")
                if rdy("qtrack", 40):               # track facts: rare, a treat
                    types.append("qtrack")
            if rdy("lore", 55):                     # racing-past banter (any session)
                types.append("lore")
            # if EVERYTHING is on cooldown, just stay quiet — a practice/quali
            # booth doesn't need to fill every gap, and forcing a repeat was
            # exactly what made the track facts loop.
            if types:
                pick = min(types,
                           key=lambda t: fcd.get(t, -1e9) + random.uniform(0, 4))
                fcd[pick] = now
                if pick == "scolour":
                    L("session_colour", 6, persona=who2())
                elif pick == "qgoals":
                    L("quali_goals", 6, persona=who2(), drv=pname)
                elif pick == "joke":
                    L("booth_joke", 6, persona=who2())
                elif pick == "lore":
                    if random.random() < 0.6:
                        L("lore_q", 6, persona="COMMENTATOR")
                    else:
                        L("lore_q_rally", 6, persona="PUNDIT")
                elif pick == "qsolo":
                    L("quali_solo", 6, persona=who2(), drv=pname)
                elif pick == "qopen":
                    L("quali_open_laps", 6, persona=who2(), drv=pname,
                      laps=pdrv.completed_laps if pdrv is not None else 0)
                elif pick == "qnobody":
                    L("quali_nobody", 6, persona=who2())
                elif pick == "qstand":
                    L("quali_standings", 6, p1=q_n1, p2=q_n2, p3=q_n3)
                elif pick == "qcount":
                    if nset == 1:                    # only one driver has a time
                        L("quali_onlyone", 6, persona=who2(),
                          drv=q_n1 or pname)
                    else:
                        L("quali_count", 6, persona=who2(),
                          set=nset, total=field_n)
                elif pick == "qpits":
                    L("quali_pits", 6, persona=who2())
                elif pick == "qcar":
                    L("car", 6, persona=who2(),
                      drv=pname if pdrv is not None else "our driver", car=pcar)
                elif pick == "pnote":
                    L("practice_note", 6, persona=who2(),
                      drv=self._dname(random.choice(order[:10] or order)))
                elif pick == "sslow":
                    dd = q_set_t[-1]                 # the slowest car WITH a time
                    L("lap_report_slow", 6, persona=who2(),
                      drv=self._dname(dd), pos=len(q_set_t))
                else:
                    # quali/practice booth: pull the RICH track-knowledge pool
                    # (history + analysis + deep per-corner tips) so a solo
                    # session is genuinely track-focused and never loops.
                    fact = self._track_knowledge(trk)
                    cands.append((6, _safe_format(
                        fact or self._pick(COMMENTARY_LINES["track_generic"],
                                           ("COMM", "trk")), {"trk": trk}),
                        "track_fact", 0, "COMMENTATOR"))


    def _emit_commentary(self, c):
        """Arbitrate the candidate lines and speak the winner (from update_commentary)."""
        cands, cur, is_race, now = c.cands, c.cur, c.is_race, c.now
        trk = c.trk
        self._comm_prev = cur
        if not cands:
            return
        cands.sort(key=lambda c: c[0])
        _prio, text, cat, inten, persona = cands[0]
        # big live moments (overtakes/spins/lead changes/start/finish = prio <=2)
        # jump the cooldown so the booth reacts right away. Everything else only
        # starts when the audio queue has ROOM, so the booth never lags the race
        # by a long backlog. Urgent events are NOT force-queued — they're capped
        # too (just with a touch more headroom), so a busy race can't bury the
        # booth seconds behind the action with stale "takes the lead" calls.
        urgent = _prio <= 2
        busy = self.tts is not None and self.tts._pending() >= 2
        # the booth is RELAXED in practice/qualifying — a much longer gap between
        # colour lines, so it isn't chattering away over a quiet session
        cd = self.COMMENTARY_CD if is_race else self.COMMENTARY_CD * 4.0
        if not urgent and (busy or (now - self._comm_cd) < cd):
            return
        self._comm_cd = now
        spoken = self._spoken(text)
        seed = "PUNDIT" if persona == "PUNDIT" else "COMM"
        nmkw = {"comm": COMMENTATOR_NAME, "pundit": PUNDIT_NAME,
                "comm_full": COMMENTATOR_FULL, "pundit_full": PUNDIT_FULL,
                "trk": trk}
        if self.tts:
            # BOOTH PRIORITY over team radio: if a big live call (overtake / lead
            # change / incident, prio<=2) needs to land and a driver's radio
            # message is mid-playback, cut the radio off — the broadcast booth
            # talks over the radio, never the other way round. (Only urgent calls
            # do this; routine colour still waits its turn politely.)
            # SIGNATURE moments that must NEVER be dropped or buried, even if the
            # queue is busy — the lights-out start and the final-lap call. These
            # interrupt whatever's playing (e.g. the long pregrid welcome) so the
            # call lands ON the moment, and force=True so they can't be dropped.
            signature = cat in ("start", "final_lap")
            if urgent:
                sp = self.tts.speaking_persona()
                if signature:
                    self.tts.interrupt()                  # land it on the moment
                elif sp is not None and sp not in ("COMMENTATOR", "PUNDIT"):
                    self.tts.interrupt()                  # cut team radio
                elif (sp in ("COMMENTATOR", "PUNDIT")
                      and now < getattr(self, "_filler_until", 0.0)):
                    # a LIVE moment (overtake / lead change / spin) trumps the
                    # low-value colour the booth is mid-way through — cut it so
                    # the call lands NOW instead of queuing behind the filler
                    self.tts.interrupt()
            # caption is shown by the on_play callback the moment audio STARTS,
            # so the subtitle matches what you actually hear (no desync).
            self.tts.speak(spoken, persona, seed=seed, intensity=inten,
                           on_play=self._show_caption, urgent=urgent,
                           force=signature)
            # remember roughly when a colour/filler line will finish, so a live
            # call arriving during it can interrupt (above)
            if not urgent:
                self._filler_until = now + min(7.0, len(spoken) * 0.055 + 1.5)
            else:
                self._filler_until = 0.0
            if cat == "crosstalk_q":
                # full exchange: lead asks -> pundit answers -> lead hands back.
                # ALL force-queued so the conversation can't be half-dropped. The
                # answer is drawn from the SAME topic as the question (paired in
                # CROSSTALK) so it actually responds to what was asked, not a
                # random non-sequitur. CROSSTALK_ANSWERS is the safe fallback.
                topic = getattr(self, "_crosstalk_topic", None)
                apool = (CROSSTALK[topic]["a"] if topic in CROSSTALK
                         else CROSSTALK_ANSWERS)
                ans = _safe_format(self._pick(apool, ("XANS", topic or "")),
                                   {"drv": getattr(self, "_crosstalk_drv", ""),
                                    "pos": getattr(self, "_crosstalk_pos", 0),
                                    **nmkw})
                self.tts.speak(self._spoken(ans), "PUNDIT", seed="PUNDIT",
                               intensity=0, on_play=self._show_caption, force=True)
                if random.random() < 0.7:
                    self.tts.speak(_safe_format(self._pick(CROSSTALK_ACK, ("XACK",)),
                                   nmkw), "COMMENTATOR", seed="COMM", intensity=0,
                                   on_play=self._show_caption, force=True)
            elif cat == "driverstory_q":
                # the pundit recaps that driver's race from the RACE STORY data
                d = getattr(self, "_storyq_d", None)
                report = self._story_report(d) if d is not None else None
                if report:
                    self._story_told.add(d.driver_info.slot_id)   # don't repeat it
                    self.tts.speak(self._spoken(report), "PUNDIT", seed="PUNDIT",
                                   intensity=0, on_play=self._show_caption,
                                   force=True)
            elif cat in ("lore_q", "lore_q_rally"):
                # the OTHER voice answers from their racing past — track-specific
                # where we have a memory, else a named generic (force-queued so
                # the exchange always completes)
                ans_persona = "PUNDIT" if cat == "lore_q" else "COMMENTATOR"
                self.tts.speak(self._spoken(_safe_format(
                    self._lore_answer(ans_persona, trk), nmkw)),
                    ans_persona, seed=("PUNDIT" if ans_persona == "PUNDIT" else "COMM"),
                    intensity=0, on_play=self._show_caption, force=True)
            elif cat in ("track_fact", "track_generic") and random.random() < 0.8:
                # keep the booth conversational — whoever gave the track
                # knowledge, the OTHER voice responds, so it feels like the two of
                # them are watching together. Pundit-led coaching earns a "great
                # analysis" from the lead; a lead-told fact gets the pundit's take.
                if persona == "PUNDIT":
                    self.tts.speak(_safe_format(self._pick(CROSSTALK_ACK, ("XACK",)),
                                   nmkw), "COMMENTATOR", seed="COMM", intensity=0,
                                   on_play=self._show_caption, force=True)
                else:
                    self.tts.speak(self._spoken(_safe_format(
                                   self._track_pundit(trk), nmkw)),
                                   "PUNDIT", seed="PUNDIT", intensity=0,
                                   on_play=self._show_caption, force=True)
            # the OTHER voice in the booth chimes back on the big moments (banter)
            elif persona == "COMMENTATOR" and random.random() < PUNDIT_AFTER.get(cat, 0.0):
                pool = PUNDIT_LINES.get(cat, PUNDIT_LINES["generic"])
                self.tts.speak(self._spoken(self._pick(pool, ("PUNDIT", cat))),
                               "PUNDIT", seed="PUNDIT", intensity=1,
                               on_play=self._show_caption)
        else:
            self._show_caption(spoken, persona)
        self._radio_recent.append(
            f"{time.strftime('%H:%M:%S')} {persona[:4]}[{inten}] {text[:40]}")
        self._radio_recent = self._radio_recent[-7:]

    def _finish_sequence(self, n1, n2, n3, trk, chasers=None, include_win=True):
        """Scripted post-race wrap, played as a CONVERSATION between the lead and
        the pundit — queued in order with synced captions (force=True so the
        chatter-drop never eats the wrap-up). The lead calls the win as P1 crosses
        the line; the pundit then singles out a standout drive from P2-P5 (his
        'man of the race'); then they round off the podium and sign off.

        include_win=False skips the win call (used when the win was already
        announced at the leader's crossing and this is the FINAL-positions wrap)."""
        n = 0

        def say(cat, persona, inten, pool=None, **kw):
            nonlocal n
            kw.setdefault("trk", trk)
            kw.setdefault("comm", COMMENTATOR_NAME)
            kw.setdefault("pundit", PUNDIT_NAME)
            kw.setdefault("comm_full", COMMENTATOR_FULL)
            kw.setdefault("pundit_full", PUNDIT_FULL)
            src = pool if pool is not None else COMMENTARY_LINES.get(cat)
            if not src:
                return
            text = _safe_format(self._pick(src, ("FIN", cat)), kw)
            spoken = self._spoken(text)
            if self.tts:
                self.tts.speak(spoken, persona,
                               seed=("PUNDIT" if persona == "PUNDIT" else "COMM"),
                               intensity=inten, on_play=self._show_caption, force=True)
            else:
                self._show_caption(spoken, persona)
            n += 1

        # KEEP IT SHORT — a tight wrap, then sign off. The pundit picks his
        # standout drive; the lead rounds off the podium; then the closing
        # sign-off. (The win call is fired separately at the leader's crossing.)
        if include_win:
            say("win", "COMMENTATOR", 2, drv=n1)                          # lead
        pick = random.choice(chasers) if chasers else (n2 or n1)
        say("ppick", "PUNDIT", 1, pool=PUNDIT_PICK, p1=n1, pick=pick)     # pundit
        say("summary", "COMMENTATOR", 1, p1=n1, p2=n2, p3=n3)            # lead
        # CLIMACTIC close: the winner crosses the line to take victory at the
        # venue, then the RacerTV sign-off — the signature send-off.
        say("victory_signoff", "COMMENTATOR", 2, p1=n1)                  # sign off

        # protect the whole wrap from the leave-session flush: ~6.5s per line is
        # a safe upper bound for the queued conversation to play out even as the
        # player drops to the results screen.
        self._wrap_until = time.time() + max(20.0, n * 6.5)

    def _report_wide(self, name, now):
        """Lighter booth note for a MODERATE off — you ran wide / had a moment but
        didn't spin. The pundit flags it; no dramatic sting, short window so it
        never escalates the way a real incident does. Skipped if a bigger incident
        is already mid-report."""
        if now < getattr(self, "_incident_until", 0.0):
            return
        txt = _safe_format(
            self._pick(COMMENTARY_LINES["ranwide"], ("COMM", "ranwide")),
            {"drv": name, "comm": COMMENTATOR_NAME, "pundit": PUNDIT_NAME})
        if self.tts:
            self.tts.speak(self._spoken(txt), "PUNDIT", seed="PUNDIT",
                           intensity=1, on_play=self._show_caption, force=True)
            self._incident_until = now + 4.0
        else:
            self._show_caption(txt, "PUNDIT")

    def _report_offtrack(self, name, now, primary=False):
        """Single entry point for EVERY off-track call (your car and rivals), so
        multiple incidents are handled coherently instead of interrupting one
        another mid-sentence. The model:

          • FRESH report — the pundit names the car (after an instant bridging
            sting) and the lead hands back ('hope they're okay'). Opens a ~7s
            'incident window'.
          • A car going off DURING that window is folded in as a follow-up queued
            BEHIND (never cuts the first call): the 1st extra -> 'and {drv} is off
            too!', a 2nd+ -> one 'chaos, multiple cars off!' line, then we go
            quiet so it can't become a spammy roll-call.

        primary=True (YOUR car) ALWAYS gets the full named report + ack — it is
        never downgraded to a follow-up. This matters because going off often
        brings out a yellow a beat earlier, which would otherwise 'open' the
        window and swallow your own off into a terse 'and X is off too'.

        Rivals are detected via position loss (the only signal we get for other
        cars, so slightly delayed); your own car is caught instantly upstream."""
        if not self.tts:
            return

        def say(cat, persona, cutoff=False, **kw):
            pool = COMMENTARY_LINES.get(cat)
            if not pool:
                return
            kw.setdefault("comm", COMMENTATOR_NAME)
            kw.setdefault("pundit", PUNDIT_NAME)
            kw.setdefault("comm_full", COMMENTATOR_FULL)
            kw.setdefault("pundit_full", PUNDIT_FULL)
            text = _safe_format(self._pick(pool, ("COMM", cat)), kw)
            if cutoff:
                self.tts.interrupt()
            self.tts.speak(self._spoken(text), persona,
                           seed=("PUNDIT" if persona == "PUNDIT" else "COMM"),
                           intensity=(2 if persona == "PUNDIT" else 0),
                           on_play=self._show_caption, force=True)

        active = now < getattr(self, "_incident_until", 0.0)
        if primary or not active:                            # FULL named report
            cutting_lead = self.tts.speaking_persona() == "COMMENTATOR"
            # INSTANT bridging sting ("Oh, trouble — looks like someone's gone
            # off!") + subtitle, filling the ~1s while the NAMED line renders. But
            # don't sting if something incident-ish is ALREADY playing (e.g. a
            # yellow just stung) — a second sting would purge that audio; instead
            # the named line cuts in itself. The sting does its own interrupt, so
            # when it fires the named line must NOT interrupt again.
            stung = (not active) and self.tts.sting(
                "alert", "PUNDIT", on_play=self._show_caption)
            cat = ("offtrack" if (stung or not cutting_lead) else "offtrack_cut")
            say(cat, "PUNDIT", cutoff=not stung, drv=name)
            say("offtrack_ack", "COMMENTATOR")
            self._incident_until = now + 7.0
            self._incident_extra = 0
        else:                                                # during a report
            self._incident_extra = getattr(self, "_incident_extra", 0) + 1
            if self._incident_extra == 1:
                say("offtrack_more", "PUNDIT", drv=name)     # queued behind
                self._incident_until = max(self._incident_until, now + 4.0)
            elif self._incident_extra == 2:
                say("offtrack_chaos", "PUNDIT")
                self._incident_until = max(self._incident_until, now + 4.0)
            # 3rd+ extra in the window: stay quiet (no spam)

    def _story_arc(self, order):
        """For a driver who had an early incident (a 'spun' story tag), judge how
        their race played out vs where they STARTED: did it cost them (still well
        down on the grid slot) or did they bounce back (recovered to/above it)?
        Returns (category, driver_name) or None."""
        picks = []
        for d in order:
            sl = d.driver_info.slot_id
            if "spun" not in self._story.get(sl, []):
                continue
            grid = self.grid_place.get(sl)
            if grid is None:
                continue
            if d.place <= grid:
                picks.append(("arc_recovered", self._dname(d)))
            elif d.place > grid + 2:
                picks.append(("arc_cost", self._dname(d)))
        return random.choice(picks) if picks else None

    def _story_pick(self, order):
        """Pick a driver whose race has an INTERESTING arc worth discussing
        (climbed a lot, fell a lot, or fell-then-recovered). Returns a driver or
        None. Prefers bigger swings; the player is eligible too."""
        told = getattr(self, "_story_told", set())
        elig = []
        for d in order:
            sl = d.driver_info.slot_id
            if sl in told:                  # already recapped this driver — skip
                continue
            st = self._race_story.get(sl)
            grid = self.grid_place.get(sl)
            if not st or grid is None:
                continue
            net = grid - st["now"]          # + climbed / - dropped
            dip = st["worst"] - grid        # how far below the start they fell
            if abs(net) >= 3 or dip >= 4:
                elig.append((d, abs(net) + dip))
        if not elig:
            return None
        elig.sort(key=lambda e: -e[1])
        return random.choice(elig[:4])[0]   # one of the most eventful

    def _story_report(self, d):
        """A spoken summary of a driver's race so far, built from their RACE
        STORY (grid -> best/worst -> now). Returns text or None."""
        sl = d.driver_info.slot_id
        st = self._race_story.get(sl)
        grid = self.grid_place.get(sl)
        if not st or grid is None:
            return None
        nm, now, best, worst = self._dname(d), st["now"], st["best"], st["worst"]
        net = grid - now
        dip = worst - grid
        if net >= 3:                        # net climber
            if dip >= 3:
                return random.choice([
                    f"{nm} started P{grid}, dropped as low as P{worst}, but he's recovered superbly to P{now}.",
                    f"Rough start for {nm} — down to P{worst} from P{grid} — but he's fought all the way back to P{now}.",
                ])
            return random.choice([
                f"{nm} started P{grid} and has climbed to P{now} — a brilliant drive.",
                f"{nm} has been on a charge — up from P{grid} to P{now}.",
            ])
        if net <= -3:                       # net loser
            if worst > now + 2:             # fell further, then clawed some back
                return random.choice([
                    f"{nm} started P{grid}, dropped as low as P{worst}, and has recovered to P{now} — still down on the start, but fighting back.",
                    f"Tough race for {nm} — P{grid} to as low as P{worst} — but he's climbing again, up to P{now} now. Hopefully more to come.",
                ])
            if best <= grid - 1:
                return f"{nm} started P{grid}, ran as high as P{best}, but has slipped back to P{now} — a tough watch."
            return random.choice([
                f"{nm} started P{grid} but has slid back to P{now} — not the race he'd have wanted.",
                f"It's gone the wrong way for {nm} — from P{grid} down to P{now}.",
            ])
        if dip >= 4:                        # steady net, but a mid-race scare
            return f"{nm} started P{grid}, had a scare down to P{worst}, but fought back to hold P{now}."
        return random.choice([
            f"{nm} has run a steady race, holding around P{now} since starting P{grid}.",
            f"Quietly solid from {nm} — P{grid} at the start, P{now} now.",
        ])

    def _fmt_gap(self, g):
        """Speak a gap naturally: 'under a second' / '1.8 seconds'."""
        if g is None:
            return "moments"
        if g < 1.0:
            return "under a second"
        return f"{g:.1f} seconds"

    def _insight(self, placemap, n1, n2, n3, total, togo, mins_left=None):
        """The pundit's 'meaning' line — framed from the LIVE race state so the
        viewer understands the race as a whole: what the front gap is worth,
        what's at stake in the podium fight, how the time/laps remaining change
        the picture. Returns (category, kwargs) or None (caller falls back)."""
        def gap_to(place):
            d = placemap.get(place)
            return self.interval.get(d.driver_info.slot_id) if d is not None else None

        timed = not (total and total > 0)
        cands = []
        front = gap_to(2)            # leader -> P2
        p4 = gap_to(4)              # P3 -> P4 (is the podium under threat?)

        if front is not None and n1 and n2:
            if front < 2.5 and not timed:
                cands.append(("insight_lead_slim",
                              {"p1": n1, "p2": n2, "gap": self._fmt_gap(front),
                               "togo": togo}))
            elif front > 6.0:
                cands.append(("insight_lead_big",
                              {"p1": n1, "gap": self._fmt_gap(front)}))
                cands.append(("insight_field_spread", {}))
        if p4 is not None and p4 < 1.3 and n3:
            cands.append(("insight_podium_fight",
                          {"p3": n3, "gap": self._fmt_gap(p4)}))
        if not timed and 1 <= togo <= 12:
            cands.append(("insight_laps_left", {"togo": togo, "total": total}))
        # TIMED race: frame the clock instead of laps
        if timed and mins_left is not None and 1 <= mins_left <= 12:
            cands.append(("insight_time_left", {"mins": mins_left}))

        return random.choice(cands) if cands else None

    def _stat_line(self, placemap, n1, n2):
        """A factual filler built from real numbers (gaps / fastest lap)."""
        opts = []
        p2 = placemap.get(2)
        if p2 is not None:
            g = self.interval.get(p2.driver_info.slot_id)
            if g and g > 0.1:
                opts.append(f"{n1} leads {n2} by {g:.1f} seconds at the front.")
        if self.fastest.get("time") and self.fastest.get("name"):
            opts.append(f"The fastest lap of the race belongs to "
                        f"{self.fastest['name']}, a {R.fmt_time(self.fastest['time'])}.")
        return random.choice(opts) if opts else None

    def _load_car_names(self):
        """Map model_id -> car name from Sector3's r3e-data.json (sits next to
        this script). Lets the commentators name the car the player is driving.
        Optional: if the file's missing/unreadable, car mentions just stay off."""
        try:
            path = os.path.join(_DIR, "r3e-data.json")
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            out = {}
            for cid, c in data.get("cars", {}).items():
                nm = c.get("Name")
                if nm:
                    try:
                        out[int(cid)] = nm
                    except (ValueError, TypeError):
                        pass
            return out
        except Exception:
            return {}

    def _player_car(self, s):
        """Friendly name of the car being viewed/driven, or None if unknown."""
        if not self._car_names:
            return None
        return self._car_names.get(int(s.vehicle_info.model_id))

    def _short_track(self, trk):
        """Broadcast-friendly short name for a track (RaceRoom's track_name is
        often verbose). Substring match; falls back to trimming common verbose
        words/suffixes off the raw name so even unknown tracks read cleanly."""
        low = (trk or "").lower()
        for key, short in SHORT_TRACK.items():
            if key in low:
                return short
        name = trk or "the circuit"
        # drop a layout descriptor after a separator ("Hockenheimring - GP")
        name = re.split(r"\s[-–—]\s", name)[0].strip()
        for junk in (" Grand Prix", " Circuit", " International", " Raceway",
                     " Speedway", " Motorsport Park", " Motor Speedway", " GP"):
            name = name.replace(junk, "")
        return name.strip() or "the circuit"

    def _track_tip(self, trk):
        """A real 'find more time here' coaching tip the engineer can relay, or
        None if we don't have tips for this track."""
        low = (trk or "").lower()
        for key, tips in TRACK_TIPS.items():
            if key in low:
                return self._pick(tips, ("TIP", key))
        return None

    def _track_fact(self, trk):
        """Circuit knowledge if we recognise the track, else None — a mix of
        history (TRACK_FACTS) and 'where to find time / how to attack' coaching
        (TRACK_COACH), so the booth is both colourful AND genuinely useful."""
        low = (trk or "").lower()
        for key, facts in TRACK_FACTS.items():
            if key in low:
                pool = facts + TRACK_COACH.get(key, [])
                return self._pick(pool, ("TRACKFACT", key))
        return None

    def _track_knowledge(self, trk):
        """A BIG track-specific pool for the quali/practice booth's 'track
        knowledge' colour — history + analysis + the deep per-corner tips — so a
        long solo session stays richly track-focused (history, the works) without
        looping the same handful of lines."""
        low = (trk or "").lower()
        pool = []
        for key, facts in TRACK_FACTS.items():
            if key in low:
                pool += facts + TRACK_COACH.get(key, [])
                break
        for key, tips in TRACK_TIPS.items():
            if key in low:
                pool += tips
                break
        if pool:
            return self._pick(pool, ("TRACKKNOW", low[:12]))
        return None

    def _track_pundit(self, trk):
        """The pundit's follow-up after a track fact. Track-SPECIFIC colour if we
        recognise the circuit, else a VARIED generic line — never the same 'so
        much history' every race, which is what made the booth sound repetitive."""
        low = (trk or "").lower()
        for key, pool in TRACK_PUNDIT_BY_TRACK.items():
            if key in low:
                # blend the track-specific colour with the varied generic pool so
                # a long (especially solo) session doesn't loop the same couple of
                # specific lines — a real pundit talks racing, not just the one
                # famous corner over and over.
                if random.random() < 0.5:
                    return self._pick(pool, ("TPUNK", key))
                return self._pick(TRACK_PUNDIT, ("TPUN",))
        return self._pick(TRACK_PUNDIT, ("TPUN",))

    def _lore_answer(self, persona, trk):
        """A booth lore answer drawing on the speaker's real racing past. A
        track-SPECIFIC memory if we have one for this circuit (Miles' F1-title
        battles / Brett's WEC easter eggs), else a varied generic one named with
        the track — so the lore stops being the same story every race."""
        low = (trk or "").lower()
        if persona == "PUNDIT":                       # Brett: Le Mans / WEC champ
            for key, pool in LORE_PUNDIT_BY_TRACK.items():
                if key in low and random.random() < 0.7:
                    return self._pick(pool, ("LOREPK", key))
            return self._pick(COMMENTARY_LINES["lore_a"], ("COMM", "lore_a"))
        for key, pool in LORE_COMM_BY_TRACK.items():  # Miles: F1 champ -> rally
            if key in low and random.random() < 0.7:
                return self._pick(pool, ("LORECK", key))
        return self._pick(COMMENTARY_LINES["lore_a_rally"], ("COMM", "lore_a_rally"))

    # ---- corner LEARNING: place an overtake on track ('into Turn 6' / a named
    # corner / the sector). The shared memory has no corner data, so the overlay
    # learns each track's corner POSITIONS from the player's speed trace — the
    # speed minima are the corners. Universal (every track/layout), accumulates
    # across practice/quali/race of the same event, and degrades safely.
    def _corner_tick(self, s):
        """Per-tick: fold the player's speed at their current lap fraction into a
        per-track MAX-speed histogram; rebuild the corner list each lap. Cheap.
        Max (the fastest seen at each point) — NOT min — so a single slow lap
        (out-lap, traffic, spin) can't drag the whole profile down: straights
        stay fast, corners stay slow, and the minima are the real corners."""
        vslot = s.vehicle_info.slot_id
        me = next((d for d in s.all_drivers_data_1
                   if d.driver_info.slot_id == vslot), None)
        if me is None:
            return
        key = (R.u8_to_str(s.track_name), s.layout_id)
        if key != getattr(self, "_corner_key", None):
            self._corner_key = key
            self._corner_bins = [None] * CORNER_NBINS
            self._corner_fracs = []
            self._corner_prevfrac = None
            self._corner_laps_seen = 0
        if me.in_pitlane == 1:
            return
        spd, frac = me.car_speed, me.lap_distance_fraction
        if spd <= 0 or not (0.0 <= frac <= 1.0):
            return
        b = min(CORNER_NBINS - 1, int(frac * CORNER_NBINS))
        cur = self._corner_bins[b]
        if cur is None or spd > cur:
            self._corner_bins[b] = spd
        pf = self._corner_prevfrac
        if pf is not None and frac + 0.5 < pf:        # wrapped past the line
            self._corner_laps_seen += 1
            self._rebuild_corners()
        self._corner_prevfrac = frac

    def _rebuild_corners(self):
        """Find corner fractions = local minima in the binned min-speed trace."""
        bins = list(self._corner_bins)
        n = len(bins)
        last = None                                    # forward-fill empty bins
        for i in range(n):
            if bins[i] is None:
                bins[i] = last
            else:
                last = bins[i]
        last = None                                    # back-fill the leading gap
        for i in range(n - 1, -1, -1):
            if bins[i] is None:
                bins[i] = last
            else:
                last = bins[i]
        if any(v is None for v in bins):
            return                                     # not enough of the lap yet
        vmax, vmin = max(bins), min(bins)
        if vmax <= 0 or vmax - vmin < 1e-3:
            return
        sm = [(bins[(i - 1) % n] + bins[i] + bins[(i + 1) % n]) / 3.0
              for i in range(n)]
        thresh = vmin + (vmax - vmin) * 0.55           # "slow zone" cut-off
        corners, i = [], 0
        while i < n:
            if sm[i] < thresh:
                j = i
                while j < n and sm[j] < thresh:
                    j += 1
                mb = min(range(i, j), key=lambda k: sm[k])
                corners.append(mb / float(n))
                i = j
            else:
                i += 1
        # merge a slow zone that straddles the start/finish line
        if len(corners) >= 2 and corners[0] < 0.04 and corners[-1] > 0.96:
            corners = corners[:-1]
        self._corner_fracs = corners

    def _corner_names(self, trk):
        low = (trk or "").lower()
        for key, names in CORNER_NAMES.items():
            if key in low:
                return names
        return None

    def _where_on_track(self, s, frac):
        """A spoken location for a lap fraction: a named corner on a recognised
        circuit, else 'into Turn N' once corners are learned, else the sector as
        a safe fallback. Returns '' if nothing can be said."""
        fracs = getattr(self, "_corner_fracs", [])
        if fracs and getattr(self, "_corner_laps_seen", 0) >= 1:
            best_i, best_d = 0, 1e9
            for i, cf in enumerate(fracs):
                d = abs(cf - frac)
                d = min(d, 1.0 - d)
                if d < best_d:
                    best_i, best_d = i, d
            if best_d < 0.05:                          # genuinely AT a corner
                names = self._corner_names(R.u8_to_str(s.track_name))
                if (names and abs(len(names) - len(fracs)) <= 1
                        and best_i < len(names)):
                    return "into " + names[best_i]
                return f"into Turn {best_i + 1}"
        # FALLBACK: the real sector index (1/2/3), never a guessed corner name
        vslot = s.vehicle_info.slot_id
        me = next((d for d in s.all_drivers_data_1
                   if d.driver_info.slot_id == vslot), None)
        sec = getattr(me, "track_sector", 0) if me else 0
        if sec in (1, 2, 3):
            return "in " + {1: "the opening sector", 2: "the middle sector",
                            3: "the final sector"}[sec]
        return ""

    def _show_caption(self, text, persona="COMMENTATOR"):
        """Set the lower-third caption (called when audio actually starts, so it
        stays in sync). Runs on the TTS worker thread — a plain assignment."""
        self._comm_caption = {"text": text, "persona": persona,
                              "until": time.time() + 5.5}

    def _air_bubble(self, msg):
        """Put a team-radio bubble on screen the instant its audio starts, so
        the bubble matches what's heard. Called from the TTS worker thread."""
        msg["until"] = time.time() + self.RADIO_HOLD
        self.radio_msgs.append(msg)
        self.radio_msgs = self.radio_msgs[-6:]

    def draw_commentary(self, s):
        """Lower-third broadcast caption for the latest commentary line."""
        cap = self._comm_caption
        if not cap or time.time() >= cap["until"]:
            return
        lines = self._wrap(cap["text"], width=64, maxlines=2)
        pundit = cap.get("persona") == "PUNDIT"
        label = "● ANALYSIS" if pundit else "● COMMENTARY"
        lcol = "#7fd1ff" if pundit else COMMENTATOR_COLOR
        w = 760
        x = (self.sw - w) // 2
        h = 30 + 20 * len(lines)
        y = self.sh - 118 - h
        self._begin_panel("commentary", x, y, w, h)
        self._card(x, y, w, h, fill=CARD_BG2, accent=lcol, side="left")
        self.text(x + 16, y + 13, label, fill=lcol, font=self.f_row_b, anchor="w")
        ly = y + 32
        for ln in lines:
            self.text(x + 16, ly, ln, fill=TEXT, font=self.f_hdr, anchor="w")
            ly += 20

    def draw_radio(self, s):
        now = time.time()
        self.radio_msgs = [m for m in self.radio_msgs if m["until"] > now]
        if not self.radio_msgs:
            return
        show = self.radio_msgs[-self.RADIO_MAX_BUBBLES:]   # oldest..newest
        w = 340
        x = self.sw - w - 24
        gap = 10
        # position each bubble by its ACTUAL height (stacked, never overlapping)
        heights = [_BUBBLE_H(len(self._wrap(m["text"], width=30))) for m in show]
        total = sum(heights) + gap * (len(show) - 1)
        bottom = self.sh - 150
        top = bottom - total
        self._begin_panel("radio", x, top, w, total)
        y = top
        for m, h in zip(show, heights):    # oldest at top, newest at bottom
            self._draw_bubble(x, y, w, m)
            y += h + gap

    def draw_debug(self, s, game_running, in_action):
        """Live diagnostics HUD (Ctrl+Shift+D). Shows why radio/podium/audio
        may not be firing and how fast data is actually updating."""
        if self.tts is None:
            tts_s = "TTS = None  (import/init FAILED -> no audio)"
        else:
            tts_s = (f"TTS engine={self.tts.engine}  "
                     f"{'ENABLED' if self.tts.enabled else 'MUTED (Ctrl+Shift+M)'}")
        drv = self._drivers(s)
        foc = next((d for d in drv
                    if d.driver_info.slot_id == s.vehicle_info.slot_id), None)
        lines = [
            f"tick={self._tick_ms:5.1f}ms  ~{1000.0/max(self._tick_ms,1):.0f}fps"
            f"   cars={len(drv)}  moves_seen={self._dbg_moves}",
            f"replay={s.game_in_replay}  phase={s.session_phase}  "
            f"type={s.session_type}  start_lights={s.start_lights}",
            f"laps_total={s.number_of_laps}  "
            f"t_remain={R.fmt_time(s.session_time_remaining)}  "
            f"checkered={s.flags.checkered}",
            f"you: slot={s.vehicle_info.slot_id} "
            f"place={foc.place if foc else '-'} "
            f"laps={foc.completed_laps if foc else '-'} "
            f"finish={foc.finish_status if foc else '-'}",
            f"podium={'shown' if (self._podium and time.time()<self._podium_until) else ('captured' if self._podium else 'none')}"
            f"   in_action={in_action}",
            tts_s,
        ]
        # corner-learning diagnostics (so you can SEE if overtake-placement works)
        fr = getattr(self, "_corner_fracs", [])
        nm = self._corner_names(R.u8_to_str(s.track_name)) if fr else None
        where = (self._where_on_track(s, foc.lap_distance_fraction)
                 if foc is not None else "")
        lines.append(
            f"corners: learned={len(fr)} laps_seen={getattr(self,'_corner_laps_seen',0)}"
            f"  named_list={len(nm) if nm else 0}"
            f"  -> here='{where}'")
        if self._stage_err:
            lines.append("ERR " + " | ".join(f"{k}:{v}"
                                             for k, v in self._stage_err.items())[:120])
        lines.append("-- recent radio --")
        lines += self._radio_recent or ["(none emitted yet)"]

        w = 640
        x, y = 30, 360
        h = 16 + 16 * len(lines)
        self._begin_panel("debug", x, y, w, h)
        self.panel(x, y, w, h, fill="#05080d")
        self.canvas.create_rectangle(x, y, x + w, y + 18, fill="#ff5a3c", outline="")
        self.text(x + 8, y + 9, "DEBUG  (Ctrl+Shift+D to hide)",
                  fill="#0b0e13", font=self.f_small_b, anchor="w")
        ly = y + 26
        for ln in lines:
            col = "#ff7b7b" if ln.startswith("ERR") else TEXT
            self.text(x + 8, ly, ln, fill=col, font=self.f_small, anchor="w")
            ly += 16

    def draw_podium(self, s):
        """When the race finishes, show a broadcast top-3 podium for a while."""
        now = time.time()
        if getattr(self, "_podium_key", None) != self._sess_key:   # new session
            self._podium_key = self._sess_key
            self._podium = None
            self._podium_until = 0.0
            self._podium_seen_at = 0.0

        # capture the top-3 once the race ends — but only once those three cars
        # have actually CROSSED THE LINE (finish_status == 1), so a fight to the
        # flag is classified correctly. A grace timeout covers odd cases.
        if self._podium is None and s.session_type == 2:           # races only
            finished = (s.session_phase == 6 or s.flags.checkered == 1
                        or (s.number_of_laps > 0
                            and any(d.completed_laps >= s.number_of_laps
                                    for d in self._drivers(s))))
            if finished and not self._podium_seen_at:
                self._podium_seen_at = now
            top = sorted(self._drivers(s), key=lambda d: d.place)[:3]
            top_done = len(top) >= 3 and all(d.finish_status == 1 for d in top)
            if (finished and len(top) >= 3
                    and (top_done or now - self._podium_seen_at > 10.0)):
                self._podium = [{
                    "place": d.place,
                    "name": self._dname(d),
                    "car": d.driver_info.car_number,
                    "color": self._color_for_name(self._dname(d)),
                } for d in top]
                self._podium_at = now
                self._podium_until = now + self.PODIUM_HOLD

        if not self._podium or now >= self._podium_until:
            return

        # --- compact top-3 strip that DROPS DOWN from under the header bar ---
        # (the old version was a 560x330 centre-screen panel that blocked the
        # track). The header is centred at y14 h48 -> bottom at y62; this slides
        # out just below it, top-centre, leaving the racing line clear.
        full_w, full_h = 520, 76
        DROP, FY = 0.45, 64                       # drop duration, final top y
        t = (now - getattr(self, "_podium_at", now)) / DROP
        t = 1.0 if t >= 1.0 else (0.0 if t < 0 else t)
        ease = 1 - (1 - t) * (1 - t)              # ease-out
        h = max(2, int(full_h * ease))            # window grows downward
        x0 = (self.sw - full_w) // 2
        y0 = FY
        self._begin_panel("podium", x0, y0, full_w, h)
        self.panel(x0, y0, full_w, full_h, fill="#0b1019")
        # thin accent header
        self.canvas.create_rectangle(x0, y0, x0 + full_w, y0 + 22,
                                     fill=ACCENT, outline="")
        self.text(x0 + full_w / 2, y0 + 11, "🏁  RACE RESULT",
                  fill="#0b0e13", font=self.f_row_b, anchor="center")

        # three side-by-side entries, gold / silver / bronze
        medal = {1: "#d9b54a", 2: "#c2cad4", 3: "#cd7f32"}
        by_place = {p["place"]: p for p in self._podium}
        cw = full_w / 3
        for i, place in enumerate((1, 2, 3)):
            p = by_place.get(place)
            if p is None:
                continue
            cx = x0 + cw * i + cw / 2
            ry = y0 + 26
            mcol = medal[place]
            # driver colour chip
            self.canvas.create_rectangle(cx - cw / 2 + 8, ry + 4,
                                         cx - cw / 2 + 14, ry + 38,
                                         fill=p["color"], outline="")
            self.text(cx - cw / 2 + 22, ry + 8, f"P{place}", fill=mcol,
                      font=self.f_hdr, anchor="nw")
            self.text(cx - cw / 2 + 22, ry + 30,
                      f"#{p['car']} {p['name'][:13]}", fill=TEXT,
                      font=self.f_sub, anchor="nw")

    def draw_sectors(self, s):
        vslot = s.vehicle_info.slot_id
        drv = None
        for d in self._drivers(s):
            if d.driver_info.slot_id == vslot:
                drv = d
                break
        if drv is None:
            return
        sw_, h = 360, 30
        x = (self.sw - sw_) // 2
        y = self.sh - 64
        self._begin_panel("sectors", x, y, sw_, h)
        self.panel(x, y, sw_, h)
        # running lap time (fall back to last completed lap when not live, e.g.
        # in replays where the current-lap time isn't published)
        lt = drv.lap_time_current_self
        if not (lt and lt > 0):
            st = drv.sector_time_previous_self
            lt = st[2] if all(t > 0 for t in st) else None   # cumulative last = lap
        self.text(x + 12, y + h / 2, R.fmt_time(lt if lt else -1),
                  fill=TEXT, font=self.f_hdr, anchor="w")
        bw = 70
        bx = x + sw_ - bw * 3 - 8
        for i in range(3):
            cur = drv.sector_time_current_self[i]
            prev = drv.sector_time_previous_self[i]
            pbest = drv.sector_time_best_self[i]
            sbest = s.session_best_lap_sector_times[i]
            val = (cur if cur and cur > 0 else
                   prev if prev and prev > 0 else None)
            col = self._sector_color(val, pbest, sbest)
            txt = f"{val:.1f}" if val else "--"
            self.text(bx + i * bw + bw / 2, y + h / 2, txt, fill=col,
                      font=self.f_row_b, anchor="center")

    def draw_map(self, s):
        drivers = self._drivers(s)
        if not drivers:
            return
        # reset the traced outline when the track changes
        tid = (s.track_id, s.layout_id)
        if getattr(self, "_map_tid", None) != tid:
            self._map_tid = tid
            self.track_cells = {}
            self.sf_xy = None

        # sample car positions -> {cell: lap_fraction}; traces shape + sectors
        cell = self.MAP_CELL
        for d in drivers:
            px, pz = d.position.x, d.position.z
            if px == 0 and pz == 0:
                continue
            self.track_cells[(round(px / cell), round(pz / cell))] = \
                d.lap_distance_fraction
            # capture the start/finish line (a car right at fraction ~0)
            if self.sf_xy is None and 0 <= d.lap_distance_fraction < 0.01:
                self.sf_xy = (px, pz)
        if not self.track_cells:
            return
        # bounds from the full sampled outline (stable shape)
        xs = [k[0] * cell for k in self.track_cells]
        zs = [k[1] * cell for k in self.track_cells]
        self.minx, self.maxx = min(xs), max(xs)
        self.minz, self.maxz = min(zs), max(zs)
        if self.maxx <= self.minx or self.maxz <= self.minz:
            return

        size = 240
        pad = 18
        bx = 18
        by = self.sh - size - 60
        self._begin_panel("map", bx, by, size, size)
        self.panel(bx, by, size, size)

        span_x = self.maxx - self.minx
        span_z = self.maxz - self.minz
        span = max(span_x, span_z)
        usable = size - 2 * pad
        scale = usable / span
        # center the shorter axis within the square
        off_x = (usable - span_x * scale) / 2
        off_z = (usable - span_z * scale) / 2

        def to_xy(px, pz):
            mx = off_x + (px - self.minx) * scale
            mz = off_z + (pz - self.minz) * scale
            return bx + pad + mx, by + pad + (usable - mz)

        # which sectors are under yellow -> tint those track cells
        sf = s.sector_start_factors
        bounds = [0.0, sf.sector2, sf.sector3, 1.0]
        if sf.sector2 <= 0 or sf.sector3 <= 0:   # fall back to even thirds
            bounds = [0.0, 1 / 3, 2 / 3, 1.0]
        yellow_sectors = {i + 1 for i in range(3) if s.flags.sector_yellow[i] == 1}

        def sector_of(frac):
            for i in range(3):
                if bounds[i] <= frac < bounds[i + 1]:
                    return i + 1
            return 3

        # draw the track outline (sampled cells) under the cars
        for (qx, qz), frac in self.track_cells.items():
            cx, cy = to_xy(qx * cell, qz * cell)
            col = ("#ffd23f" if (yellow_sectors and frac is not None
                                 and sector_of(frac) in yellow_sectors)
                   else "#5b6470")
            self.canvas.create_rectangle(cx - 1, cy - 1, cx + 1, cy + 1,
                                         fill=col, outline="")

        # start/finish marker
        if self.sf_xy is not None:
            fx, fy = to_xy(*self.sf_xy)
            self.canvas.create_rectangle(fx - 2, fy - 6, fx + 2, fy + 6,
                                         fill="#ffffff", outline="#000000")

        # multiclass colouring (only when >1 class on track)
        classes = {d.driver_info.class_id for d in drivers}
        multiclass = len(classes) > 1
        palette = ["#c9ced6", "#ff922b", "#74c0fc", "#b197fc", "#63e6be"]
        cls_color = {cid: palette[i % len(palette)]
                     for i, cid in enumerate(sorted(classes))}

        viewed_slot = s.vehicle_info.slot_id
        for d in drivers:
            px, pz = d.position.x, d.position.z
            if px == 0 and pz == 0:
                continue
            cx, cy = to_xy(px, pz)
            is_viewed = (viewed_slot >= 0 and d.driver_info.slot_id == viewed_slot)
            is_leader = (d.place == 1)
            r = 6 if is_viewed else 4
            base = cls_color[d.driver_info.class_id] if multiclass else "#c9ced6"
            col = ACCENT if is_viewed else (LEADER if is_leader else base)
            self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                    fill=col, outline="#000000")
            self.canvas.create_text(cx, cy, text=str(d.driver_info.car_number),
                                    fill="#000000", font=("Consolas", 7, "bold"))

    def run(self):
        self.root.mainloop()


def _single_instance():
    """Return True if no other overlay instance is already running."""
    kernel32.CreateMutexW(None, False, "R3EOverlay_singleton_mutex")
    return ctypes.get_last_error() != 183  # 183 = ERROR_ALREADY_EXISTS


if __name__ == "__main__":
    if not _single_instance():
        raise SystemExit("R3E overlay already running")
    Overlay().run()
