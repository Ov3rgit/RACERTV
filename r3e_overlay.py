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
import threading
import time
from ctypes import wintypes
import tkinter as tk
import tkinter.font as tkfont

import r3e_data as R
import avatars
import helmet as helmet_mod
from overlay_panel import (_TC)
from overlay_common import (_dim_hex, CARD_BG, CARD_BG2, CORNER_NBINS, DIM, DRIVER_COLORS, GREEN,
    HEADER_ACCENT, PLACE_CONFIRM_TICKS, PURPLE, TYRE_COLORS, UPDATE_MS,
    VK_C, VK_CONTROL, VK_E, VK_LBUTTON, VK_M, VK_O, VK_Q, VK_SHIFT, VK_D,
    VK_R, YELLOWT, _LEET)
from overlay_booth import BoothMixin
from overlay_objective import ObjectiveMixin
from overlay_draw import DrawMixin
from overlay_radio import RadioMixin
from lines import (PERSONA_KEYS, SHORT_TRACK, CORNER_NAMES)

import sys as _sys
if getattr(_sys, "frozen", False):       # PyInstaller: assets sit next to the exe
    _DIR = os.path.dirname(_sys.executable)
else:
    _DIR = os.path.dirname(os.path.abspath(__file__))

# SPECTATOR MODE, remembered between runs. Someone who watches replays wants
# the broadcast, not the cockpit, and having to re-tick that box every launch
# would make the mode feel like a debug switch rather than a way to watch.
_PREFS_FILE = os.path.join(_DIR, "_prefs.json")


def _load_prefs():
    try:
        with open(_PREFS_FILE, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _save_pref(key, value):
    if os.environ.get("RACERTV_EPHEMERAL"):    # tests: never touch the disk
        return
    d = _load_prefs()
    d[key] = value
    try:
        with open(_PREFS_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f)
    except Exception:
        pass


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

# How many booth lines must go by before any one line may be heard again,
# across every pool and both voices. An instrumented race airs roughly 12 lines
# a minute, so 60 is about five minutes between repeats — comfortably longer
# than anyone holds a line in their head, without starving the smaller pools
# (when everything on offer is recent the least recently used one is dealt).
RECENT_LINE_WINDOW = 60


# Smallest window that can plausibly BE the game, rather than RaceRoom's
# loading splash (~750x475). Sits under the 1024x768 minimum the game itself
# supports, so it never rejects a real window, windowed play included.
MIN_GAME_W, MIN_GAME_H = 900, 600


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
        # SKIP THE SPLASH. RaceRoom's "Loading RaceRoom..." window belongs to
        # rrre64.exe like the game does, so the old 200x200 floor accepted it
        # and the overlay pinned its chrome to the corner of a red splash
        # screen — reported as the settings button being stuck in the small
        # launcher window, with no way back short of killing the app.
        # Measured from a screenshot of it: roughly 750x475. RaceRoom will not
        # run below 1024x768, so nothing this small can be the game window,
        # while any real resolution (windowed included) clears it comfortably.
        if w >= MIN_GAME_W and h >= MIN_GAME_H and area > best["area"]:
            best["area"] = area
            best["rect"] = (r.left, r.top, w, h)
        return True

    user32.EnumWindows(_WNDENUMPROC(cb), 0)
    return best["rect"]

# ----- look & feel -----------------------------------------------------------
                        # stipple behind text) but slightly see-through over the game
                          # the data); transparency now comes from WIN_ALPHA + CHROMA
# broadcast "card" styling — dark fill, thin subtle border, rounded corners,
# coloured accent strip (shared by the header, radio bubbles and commentary)




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





# how hyped the booth voice gets per event (0 calm .. 2 max)
# spoken penalty names by penaltyType (RaceRoom PenaltyType enum)
# which events earn a co-commentator follow-up (and how often) — keep the booth
# chatting back and forth on the big moments
# RECAP categories describe something still true seconds later (a driver's
# race arc, a lore anecdote) — unlike a live gap/lap call, they tolerate
# airing a little late, so they're exempt from the numeric-content TTL AND
# from the "queue busy" gate (both in update_commentary / _emit_commentary).
# Without this, driverstory (rare — its own 30s+ gate — and number-heavy,
# quoting grid/finish positions) got dropped almost every time it was picked.


# radio category -> driver-avatar emotion (the face drawn in the bubble)
# vivid, broadcast-style per-driver colours (assigned consistently by name)
# 20 distinct, well-spaced colours (assigned sequentially per driver, so the
# first 20 cars on track each get a unique one before any repeat)
# tyre compound dot colors, keyed by tire_subtype (2=soft,3=med,4=hard,
# 0=primary,1=alternate)
# radio_msgs is mutated from BOTH the TTS play thread (_air_bubble) and the tk
# loop (draw_radio's prune rebuilds the list) — an unguarded append between the
# prune's read and reassign was silently lost (audio played, no card). Module
# level so the headless test harness (object.__new__, no __init__) has it too.
                         # the booth/radio treat it as a REAL change. This kills
                         # the side-by-side flicker that made the booth call a
                         # pass when two cars were merely running level. The TIMING
                         # TOWER is unaffected — it sorts by live track position —
                         # so the display stays instant; only the spoken overtake
                         # CALLS wait for the new order to actually stick.



def key_down(vk):
    return ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000


# HAS THE FIELD LAUNCHED? The green-flag latch's answer when the player's own
# car cannot give one — a replay, or spectating.
#
# A MAJORITY, NOT THE LEADER. One car is not a start: a driver creeping on the
# grid, or one who jumped it, moves while the race has not begun, and on a
# standing grid a single twitchy reading would call the green early. At lights
# out the whole field goes at once, so half of it moving is unambiguous and is
# reached within a few tenths of the real moment.
#
# The same 4.0 threshold the player's own test uses, deliberately: the two are
# answering one question and a field that launched by a different definition
# than the driver did would make the call land in a different place depending
# on whether he happened to be driving.
def _field_launched(order, thresh=4.0):
    n = len(order or ())
    if not n:
        return False
    movers = sum(1 for d in order if abs(getattr(d, "car_speed", 0.0)) > thresh)
    # A ONE- OR TWO-CAR SESSION HAS NO MAJORITY WORTH THE NAME. Half of two is
    # one, and demanding two movers in a two-car race would hang the start on
    # the slower of them. Below three cars, one car moving IS the field.
    need = 1 if n <= 2 else max(2, n // 2)
    return movers >= need









# WHICH BUILD IS THIS. There was no way to tell, which matters the moment a
# report arrives ("it is still lagging ALOT") and the first thing worth
# knowing is whether the reporter is running the fix at all. Shown in the
# debug HUD (Ctrl+Shift+D). VERSION is the release; BUILD is the commit the
# exe was made from, and is rewritten by the release script.
VERSION = "1.3.0"
BUILD = "dev"

class Overlay(BoothMixin, RadioMixin, DrawMixin, ObjectiveMixin):
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

        # BROADCAST-GRAPHICS look: a wide engineered DISPLAY face on the chyron
        # (Michroma — motorsport-livery feel) paired with a crisp technical
        # BODY face on the data (Chakra Petch, with a SemiBold for emphasis).
        # Both are SIL Open Font License (shippable) and loaded PRIVATELY at
        # runtime next to the exe (no install; FR_PRIVATE=0x10). Falls back to
        # Bahnschrift if a ttf is missing so a bad copy never blanks the UI.
        _DISP = "Bahnschrift SemiBold SemiConden"   # header / display
        _BC = "Bahnschrift SemiCondensed"           # body / data
        _BCB = "Bahnschrift SemiBold SemiConden"    # body emphasis
        try:
            loaded = 0
            for _ttf in ("Michroma-Regular.ttf", "ChakraPetch-Regular.ttf",
                         "ChakraPetch-SemiBold.ttf", "ChakraPetch-Bold.ttf"):
                _fp = os.path.join(_DIR, _ttf)
                if os.path.exists(_fp):
                    loaded += bool(ctypes.windll.gdi32.AddFontResourceExW(
                        _fp, 0x10, 0))
            if loaded >= 4:
                _DISP = "Michroma"
                _BC = "Chakra Petch"
                _BCB = "Chakra Petch SemiBold"
        except Exception:
            pass
        self._DISP, self._BC, self._BCB = _DISP, _BC, _BCB
        self.f_row = tkfont.Font(family=_BC, size=11)
        self.f_row_b = tkfont.Font(family=_BCB, size=11)
        # Michroma is wide + tall — the chyron title uses it a size smaller so
        # a long track name still fits the header
        self.f_hdr = tkfont.Font(family=_DISP,
                                 size=12 if _DISP == "Michroma" else 14)
        self.f_sub = tkfont.Font(family=_BC, size=10)

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
        self.f_small = tkfont.Font(family=_BC, size=9)
        self.f_small_b = tkfont.Font(family=_BCB, size=9)
        # slightly larger fonts dedicated to the timing tower (so it can grow
        # without enlarging the other panels)
        self.f_tow = tkfont.Font(family=_BC, size=11)
        self.f_tow_b = tkfont.Font(family=_BCB, size=11)
        # the speedo readout. Michroma is wide, so the speed sits a size down
        # from what the dial diameter would suggest — "289" has to fit inside
        # the face without touching the sweep.
        self.f_spd = tkfont.Font(family=_DISP, size=20 if _DISP == "Michroma"
                                 else 24)
        self.f_gear = tkfont.Font(family=_DISP, size=14 if _DISP == "Michroma"
                                  else 17)

        # broadcast stats (reset per session). Initialised here too — not just in
        # update_stats' per-session reset — so the radio/commentary stages can
        # never hit an AttributeError if the stats stage ever throws first.
        self._sess_key = None
        self.grid_place = {}     # slot -> first-seen place (for ▲▼ arrows)
        self.last_laps = {}      # slot -> completed_laps (detect lap done)
        self.best_lap = {}       # slot -> best lap time (quali/practice tower)
        self.recent_laps = {}    # slot -> last few lap times (rolling race pace)
        self._obj_damaged = False
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
        self._prev_rem = None        # session clock last tick — a jump UP is a
                                     # restart (it only ever counts down)
        self._prev_my_laps = None    # your own lap count — it only ever rises,
                                     # so a fall means the session was replaced
        self._prev_simt = None       # game_simulation_time last tick — THE
                                     # restart signal (see update_stats)
        self._last_found_t = 0.0     # last time the RaceRoom window was seen
        self._tts_silenced = False   # audio stopped because the game is gone

        # SPECTATOR MODE: watching, not driving. Suppresses everything that
        # only makes sense addressed to a driver — team radio, the objective
        # card, the relative panel — and leaves the broadcast: booth, tower,
        # map, flags, sectors, fastest lap.
        self.spectator = bool(_load_prefs().get("spectator", False))
        self._auto_spec = False    # set per tick from game_in_replay

        # SPEEDO. One control, three states: OFF -> KM/H -> MPH. A separate
        # units switch would be a second row in the menu for a setting nobody
        # changes twice, and it would have to grey itself out when the dial is
        # off. Cycling reads as one idea: "the speedo, in these units".
        _sp = _load_prefs().get("speedo", "kmh")
        self.speedo = _sp if _sp in ("off", "kmh", "mph") else "kmh"
        # ON BY DEFAULT: turning a feature off for everyone who never
        # asked would be a regression, so it is opt-out, and remembered.
        self.objectives_on = bool(_load_prefs().get("objectives", True))

        # REPLAY PLAYBACK. A loaded-but-paused replay still publishes a full
        # session, and the booth used to spend its whole introduction on a
        # frozen frame while the viewer was still setting up their camera.
        self._rep_rolling = False    # replay is actually PLAYING right now
        self._rep_moving_since = None  # first tick we saw it advance
        self._rep_prev = None        # (sim time, field distance, clock) last
                                     # tick — is the replay actually PLAYING?
        self._rep_still_since = None # first tick the replay stopped advancing

        # FORMATION LAP (session_phase 3, incl. rolling starts).
        self._formation = False      # currently on the formation lap
        self._form_seen = False      # this session HAD a formation lap
        self._form_said = set()      # formation beats already called
        self._form_open_t = 0.0      # when the formation opener was spoken

        # team-radio engine state
        self.radio_on = True     # engineer + driver radio VOICE on/off (bubbles
                                 # still show as silent tickers when off)
        self.prev_places = {}    # slot -> place last tick
        self.prev_int_focus = None
        self.radio_msgs = []     # active bubbles [{name,text,color,until}]
        self.last_radio_t = 0.0
        self._rival_card_t = 0.0   # rival cards keep their own clock
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
        # ...and the space that frees up goes to YOUR engineer, who is the
        # voice that actually helps you drive.
        self.RADIO_ENG_CD = 15.0   # min seconds between engineer messages

        # team-radio voice (TTS) — optional; never breaks the overlay
        self.tts = None
        try:
            import tts as _tts
            self.tts = _tts.Tts()
            # drop the lower-third the moment its audio finishes (plus a short
            # linger) — the length-estimated hold could outlive the voice by
            # seconds, which read as "captions out of sync with the audio"
            self.tts.on_line_end = self._caption_line_end
        except Exception:
            self.tts = None
        self._m_prev = False
        self.RADIO_GLOBAL_CD = 5.5   # min seconds between any two bubbles
        # RIVAL CARDS PACE THEMSELVES. The shared clock (last_radio_t) is
        # stamped only by the ENGINEER now, so that a silent rival card can no
        # longer hold his next line back. The cost of that was rival cards
        # having NO global spacing left at all: reported as cards "firing one
        # after another, one on top of another". Audio used to pace them by
        # taking time to say; a caption takes none, so it needs a clock of its
        # own. FACTORtv, where rival radio has been silent from the start,
        # runs 38s between cards — this is a shorter track-side version of the
        # same rule, on top of the 30s per-driver cooldown below.
        self.RADIO_RIVAL_CD = 20.0   # min seconds between two rival cards
        # Rival chatter is colour, not information — it was firing far too
        # often and drowning the engineer. ~20% longer spacing, and the
        # relevance filter in update_radio now favours the cars you are
        # actually racing (see RADIO_FAR_CHANCE).
        self.RADIO_DRIVER_CD = 30.0  # min seconds between same driver's bubbles
        self.RADIO_HOLD = 6.0        # how long a bubble stays on screen
        # HOW MANY LINES MAY FAIL TO SOUND, with nothing ever having
        # played, before the overlay concludes there is no voice channel
        # and shows its cards without one. One or two failures are a busy
        # queue; three at the start of a session is a renderer that is
        # never going to work. See the drop handler in overlay_radio.
        self.VOICE_DEAD_AFTER = 3
        self._voice_fails = 0        # consecutive lines that never sounded
        self._voice_ok = False       # has ANY line actually played yet?
        self.RADIO_NEAR = 4          # crashes within N places of you = high priority
        # a moment involving a car you are NOT racing rarely deserves a voice
        self.RADIO_FAR_CHANCE = 0.3  # chance a far-away crash gets a reaction
        self.RADIO_MAX_BUBBLES = 4   # max bubbles on screen at once (no flooding;
                                     # simultaneous driver+engineer calls stack)
        # ONE radio line per tick. Three at once queued three voices back to
        # back, and anything that then missed its TTL was dropped while its
        # card still aired — silent cards. A genuine multi-car incident still
        # gets its extra lines, just on the following ticks.
        self.RADIO_MAX_BURST = 1     # max new messages per tick
        # card/audio sync: cards waiting for their audio's on_play; tick()
        # airs any whose deadline passed without the audio ever starting
        self._pending_bubbles = []
        self._bubble_lock = threading.Lock()

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
        self._r_prev = False
        # How long a blocked booth call may WAIT for a free queue slot before
        # it is abandoned (see the arbitration buffer in _emit_commentary).
        # Short on purpose: play-by-play rots, and "takes P3" a few seconds
        # late is wrong rather than merely old. Airing a stale call is worse
        # than staying quiet, so this errs towards dropping.
        self.COMMENTARY_HOLD_TTL = 4.0
        self._comm_hold = None       # the one deferred call, or None
        self.COMMENTARY_CD = 4.0     # min seconds between commentary lines (the
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
        self._toast_msg = None       # {text, until} transient hotkey feedback
        self._pron = {}              # display name -> TTS pronunciation
        self._dcolor = {}            # driver name -> assigned colour (unique-ish)
        self._dcolor_n = 0           # next colour index to hand out
        self._dvariant = {}          # driver name -> helmet PNG variant index
        self._dhelmet = {}           # driver name -> rendered helmet spec
        # HIS OWN HELMET. Everyone else's is generated from their name; this
        # is the one design in the session that was CHOSEN, and it is the only
        # one persisted. {} means "not chosen", which is a real answer and the
        # default: he keeps the generated one like everybody else.
        self._my_helmet = dict(_load_prefs().get("helmet") or {})
        self._my_name = ""           # the local account, from s.player
        self._menu_page = "main"     # "main" | "helmet"

        # diagnostics (Ctrl+Shift+D toggles an on-screen HUD)
        self.debug = False
        self._d_prev = False
        self._tick_ms = 0.0
        self._stage_ms = {}        # rolling ms per draw stage
        self._stage_peak = {}      # worst single frame per stage
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
        # EXCLUDE the radio-card art: this glob takes the first *.png in the
        # folder, so a user's helmet/engineer icons would otherwise be picked
        # up as the broadcast logo (they sort before racer-tv.png)
        # ...AND NOT THE WORKING FILES EITHER. This takes the first *.png in
        # the folder, and every scratch file this project writes is named with
        # a leading underscore — `_transcript.log`, `_heard.json`,
        # `_tts_debug.log`, `_speedo_preview.png`. Underscore sorts before
        # lowercase, so `_speedo_preview.png` beat `racer-tv.png` and the
        # broadcast logo has quietly been a screenshot of the speedometer
        # since it was first generated. Rendering more previews into the
        # folder made it obvious rather than causing it.
        #
        # One rule, matching the convention the rest of the project already
        # follows: a leading underscore means "mine, not the product's".
        cands += [p for p in sorted(glob.glob(os.path.join(_DIR, "*.png")))
                  if not os.path.basename(p).startswith(("icon_", "_"))]
        cands += [p for p in sorted(glob.glob(os.path.join(_DIR, "*.gif")))
                  if not os.path.basename(p).startswith("_")]
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



    def _build_toggle_button(self):
        """Small always-on-top CLICKABLE window (the main overlay is
        click-through, so the toggle lives in its own window)."""
        self.btn_win = tk.Toplevel(self.root)
        self.btn_win.overrideredirect(True)
        self.btn_win.attributes("-topmost", True)
        self.btn_win.configure(bg="#0a0d12")
        # padding tuned to leave a comfortable click target around a chip that
        # is usually a single dot — it is still the control that shows a hidden
        # overlay, so it must not shrink to something you have to aim at
        self.btn_lbl = tk.Label(self.btn_win, text="●", fg=GREEN,
                                bg="#0a0d12", font=("Segoe UI", 10, "bold"),
                                padx=9, pady=4, cursor="hand2")
        self.btn_lbl.pack()
        # NB no tk <Button-1> bindings: click events don't arrive reliably
        # over the game, so clicks on this chip are POLLED and hit-tested in
        # draw_settings (a tk binding here would double-toggle on the systems
        # where the event DOES fire)
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
        self.clock_win.configure(bg=CARD_BG2)
        # DRAWN, not labelled, so the digits can carry the accent GLOW that
        # made this readable at a glance in the first place. A flat tk.Label
        # can only be one colour; the glow is built by stacking the same text
        # several times — widest and darkest first, brightest last — which on a
        # dark panel reads as light bleeding off the numerals.
        #
        # Hours:minutes hold the glow and the eye. The seconds sit beside them
        # small and unlit: they are the fastest-moving thing on screen and the
        # least important, and at full brightness they were the loudest object
        # in the corner. They stay, though — timing the top of the hour for an
        # online session start is the whole reason this clock exists.
        self._clk_f = tkfont.Font(family="Consolas", size=12)
        self._clk_fs = tkfont.Font(family="Consolas", size=8)
        pad_x, pad_y = 10, 5
        w = pad_x * 2 + self._clk_f.measure("00:00") + 4 + self._clk_fs.measure("00")
        h = pad_y * 2 + self._clk_f.metrics("linespace")
        self.clock_cv = tk.Canvas(self.clock_win, width=w, height=h,
                                  bg=CARD_BG2, highlightthickness=0)
        self.clock_cv.pack()
        self._clk_geom = (pad_x, h // 2, w)
        self._clk_text = None

    # Glow stack: (offset in px, colour), drawn outermost-first so the core
    # lands on top. Tk has no alpha, so the falloff is hand-mixed against the
    # panel background rather than computed.
    #
    # Kept DELIBERATELY faint. The first attempt stacked three rings out to 3px
    # in near-core brightness and read as a neon sign — "wayyyy too bright" —
    # which is the opposite of the point: this is a small clock in the corner
    # of a racing game, and the glow is meant to lift the digits off the panel,
    # not light the room. Two close rings, both much darker than the core.
    # WARM, like everything else in the corner. These were dark teals chosen
    # to sit under a cyan clock; against the red one they read as a blue
    # shadow, which is what "the time is a mix of red and blue" was.
    _CLK_GLOW = ((2, "#2a0b0e"), (1, "#57171d"))

    def _paint_clock(self, hhmm, ss):
        """Repaint the clock only when the digits actually change — this runs
        at 20Hz and redrawing ~14 canvas items every tick for a value that
        moves once a second is free frame time thrown away."""
        if (hhmm, ss) == self._clk_text:
            return
        self._clk_text = (hhmm, ss)
        c = self.clock_cv
        c.delete("all")
        x, cy, w = self._clk_geom
        for off, col in self._CLK_GLOW:
            for dx, dy in ((-off, 0), (off, 0), (0, -off), (0, off)):
                c.create_text(x + dx, cy + dy, text=hhmm, fill=col,
                              font=self._clk_f, anchor="w")
        c.create_text(x, cy, text=hhmm, fill=HEADER_ACCENT, font=self._clk_f,
                      anchor="w")
        # THE SECONDS ARE A DIMMED ACCENT, not their own colour. Hard-coded
        # teal here while the hours above use HEADER_ACCENT is precisely how
        # the clock ended up two-tone when the theme changed; deriving it
        # means it can never fall out of step again.
        c.create_text(x + self._clk_f.measure(hhmm) + 4, cy + 3, text=ss,
                      fill=_dim_hex(HEADER_ACCENT, 0.55), font=self._clk_fs,
                      anchor="w")
        try:
            h = ctypes.windll.user32.GetAncestor(self.clock_win.winfo_id(), 2)
            ex = ctypes.windll.user32.GetWindowLongW(h, -20)
            ctypes.windll.user32.SetWindowLongW(h, -20, ex | 0x80)   # toolwindow
            self._clock_hwnd = h
        except Exception:
            self._clock_hwnd = None

    # ---- top-left corner: ONE ROW of [status] [menu] [clock] ---------------
    # These three were stacked over two rows, which is a lot of vertical
    # furniture for a status light, a button and a clock. Side by side they
    # read as one strip of chrome instead of three separate announcements.
    CORNER_X = 12            # left margin, shared with the canvas panels
    CORNER_Y = 8             # every chip sits on this baseline
    CORNER_GAP = 6
    CORNER_GEAR_W = 29       # the menu button is a square

    def _corner_layout(self):
        """Canvas-space x for the menu button and the clock.

        The status chip changes width with its state: normally a bare dot, but
        "● SHOW" when the overlay is hidden, because that is the one state that
        has to advertise itself. draw_settings runs even with the UI off, so
        both neighbours have to step aside for the wide form or they end up
        underneath it. One helper so the canvas and the toplevel windows can
        never disagree about where the row sits."""
        status_w = 26 if self.visible else 70
        gear_x = self.CORNER_X + status_w + self.CORNER_GAP
        clock_x = gear_x + self.CORNER_GEAR_W + self.CORNER_GAP
        return gear_x, clock_x

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
        # clock finishes the row, to the right of the menu button
        try:
            _, _clock_x = self._corner_layout()
            self.clock_win.geometry(
                f"+{lx + (_clock_x - self.CORNER_X)}+{by}")
            self.clock_win.attributes("-topmost", True)
            chwnd = (user32.GetAncestor(self.clock_win.winfo_id(), 2)
                     or self._clock_hwnd)
            if chwnd:
                self._clock_hwnd = chwnd
                user32.SetWindowPos(chwnd, HWND_TOPMOST, 0, 0, 0, 0,
                                    SWP_NOMOVE_NOSIZE_NOACT)
        except Exception:
            pass


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
            self._bag_save(force=True)     # persist the shuffle-bag decks
            self.reader.close()
            if self.tts:
                self.tts.close()
        finally:
            self.root.destroy()

    # ---- drawing helpers (draw into the current panel via translating canvas) -



    # ---- main loop ----
    def tick(self):
        t0 = time.perf_counter()
        if key_down(VK_CONTROL) and key_down(VK_SHIFT) and key_down(VK_Q):
            return self.quit()
        o = bool(key_down(VK_CONTROL) and key_down(VK_SHIFT) and key_down(VK_O))
        if o and not self._o_prev:
            self._do_toggle_ui()
        self._o_prev = o
        e = bool(key_down(VK_CONTROL) and key_down(VK_SHIFT) and key_down(VK_E))
        if e and not self._e_prev:
            self._do_toggle_compact()
        self._e_prev = e
        m = bool(key_down(VK_CONTROL) and key_down(VK_SHIFT) and key_down(VK_M))
        if m and not self._m_prev:
            self._do_toggle_mute()
        self._m_prev = m
        dk = bool(key_down(VK_CONTROL) and key_down(VK_SHIFT) and key_down(VK_D))
        if dk and not self._d_prev:
            self.debug = not self.debug
        self._d_prev = dk
        ck = bool(key_down(VK_CONTROL) and key_down(VK_SHIFT) and key_down(VK_C))
        if ck and not self._c_prev:
            self._do_toggle_booth()
        self._c_prev = ck
        rk = bool(key_down(VK_CONTROL) and key_down(VK_SHIFT) and key_down(VK_R))
        if rk and not self._r_prev:
            self._do_toggle_radio()
        self._r_prev = rk
        # POLLED mouse click for the settings menu (and the ● OVERLAY chip).
        # The overlay windows are click-through and the game constantly
        # re-asserts itself over the z-order, so tk <Button-1> events never
        # arrive reliably — instead the click is polled like the hotkeys and
        # hit-tested against the rects drawn last frame (see draw_settings).
        st = ctypes.windll.user32.GetAsyncKeyState(VK_LBUTTON)
        lmb = bool(st & 0x8000)
        # bit 0 = "pressed since the last GetAsyncKeyState call": catches a
        # click shorter than one 50ms tick, which pure state-edge polling missed
        self._click = None
        if (lmb and not getattr(self, "_lmb_prev", False)) or (st & 0x0001):
            try:
                pt = wintypes.POINT()
                ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
                self._click = (pt.x - self.game_x, pt.y - self.game_y)
            except Exception:
                pass
        self._lmb_prev = lmb

        # card/audio sync fallback: air any radio card whose audio never
        # started (TTL-dropped / purged / render error) once its deadline
        # passes — a card may arrive late and silent, but never not at all
        if getattr(self, "_pending_bubbles", None):
            _nowb = time.time()
            _keep = []
            for _m, _dl, _st in self._pending_bubbles:
                if _st["aired"]:
                    continue                       # audio played; card aired
                if _nowb >= _dl:
                    with self._bubble_lock:
                        if _st["aired"]:
                            continue
                        _st["aired"] = True
                    self._air_bubble(_m)
                else:
                    _keep.append((_m, _dl, _st))
            self._pending_bubbles = _keep

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
            self._paint_clock(time.strftime("%H:%M"), time.strftime("%S"))
        except Exception:
            pass
        self._place_button(found)

        # draw the panels (each into its own small window). Each stage is
        # isolated: a failure in one (e.g. update_radio) must NOT abort the
        # rest of the frame, or panels drawn after it would appear frozen.
        self._used = set()
        if in_action and self._drivers(s):
            # UPDATE stages always run during action — hiding the UI
            # (Ctrl+Shift+O) must NOT kill the broadcast: audio-only mode is
            # "radio on, telly off". Only the DRAW stages are gated on visible.
            # SPECTATOR MODE drops the driver-facing half of the product: the
            # radio engine (and its bubbles), the objective card and the
            # relative panel all address a driver who, in a replay of someone
            # else's race, isn't watching. The radio is skipped at the UPDATE
            # stage rather than muted at the speak() call, so it never builds
            # the messages in the first place.
            # ...AND A REPLAY IS SPECTATING WHETHER OR NOT ANYONE TICKED THE
            # BOX. RaceRoom publishes `game_in_replay`, so the overlay never
            # had to be TOLD this: in a replay there is, definitionally, no
            # driver in the seat to talk to, and an engineer calling tyre
            # temperatures at a recording is the single most immersion-breaking
            # thing the product does. Watching one back was the common case and
            # it required remembering a menu toggle first.
            #
            # IT DOES NOT TOUCH THE SAVED PREFERENCE. `self.spectator` stays
            # exactly as he set it, and `_save_pref` is not called — the mode
            # lifts by itself when the replay ends. Auto-detection that
            # silently rewrote his setting would be a worse bug than the one it
            # fixes.
            self._auto_spec = bool(getattr(s, "game_in_replay", 0) == 1)
            spec = self.spectating
            stages = [("stats", self.update_stats),
                      ("comm", self.update_commentary)]
            if not spec:
                stages.insert(1, ("radio", self.update_radio))
            if self.visible:
                # the gated stages are FILTERED OUT of the list rather than
                # appended after it, so spectator mode cannot quietly reorder
                # the frame
                stages += [(nm, fn) for nm, fn in [
                      ("header", self.draw_header), ("flags", self.draw_flags),
                      ("penalty", self.draw_penalty),
                      ("tower", self.draw_tower), ("relative", self.draw_relative),
                      ("fastest", self.draw_fastest_banner),
                      ("objective", self.draw_objective),
                      ("sectors", self.draw_sectors), ("map", self.draw_map),
                      ("speedo", self.draw_speedo),
                      ("bubbles", self.draw_radio), ("caption", self.draw_commentary),
                      ("podium", self.draw_podium)]
                    if not (spec and nm in ("relative", "objective", "bubbles"))]
            for nm, fn in stages:
                # PER-STAGE TIMING, so "the overlay feels slow" can be
                # answered by looking rather than guessing. The debug HUD
                # (Ctrl+Shift+D) prints the worst offenders. perf_counter
                # twice per stage is tens of nanoseconds; it stays on.
                _t = time.perf_counter()
                try:
                    fn(s)
                except Exception as ex:
                    self._stage_err[nm] = f"{type(ex).__name__}: {ex}"
                _d = (time.perf_counter() - _t) * 1000.0
                # a rolling mean, so one slow frame doesn't dominate the
                # reading and a genuinely slow stage cannot hide in an average
                self._stage_ms[nm] = self._stage_ms.get(nm, _d) * 0.9 + _d * 0.1
                self._stage_peak[nm] = max(self._stage_peak.get(nm, 0.0), _d)
        elif self.visible and in_action:
            try:
                self.draw_header(s)
                self._no_data_notice(s)
            except Exception:
                pass
        try:
            self.draw_settings()     # clickable menu — shows even with UI off
        except Exception as ex:
            self._stage_err["settings"] = f"{type(ex).__name__}: {ex}"
        try:
            self.draw_toast()        # hotkey feedback — shows even with UI off
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
            # A REPLAY THAT IS LOADED IS NOT A REPLAY THAT IS PLAYING.
            #
            # RaceRoom publishes the whole session the moment a replay is
            # loaded, and this used to return True on that first frame. So the
            # broadcast opened — welcome, drivers, track, the pregrid build-up
            # — into a frozen picture, while the viewer was still choosing a
            # camera and arming their recorder. By the time they pressed play
            # the introduction had already been spoken to nobody, and the
            # opening lap's events had been consumed by edge detectors that had
            # long since seen them. Reported as the intro being lost and the
            # first lap never being picked up.
            #
            # WHAT "MOVING" IS MEASURED FROM, and why it is not one field.
            #
            # `game_simulation_time` is documented as VIRTUAL PHYSICS TIME, and
            # a replay is played back rather than simulated — so there is no
            # guarantee it advances during playback at all. Betting the whole
            # gate on it risks a far worse bug than the one being fixed: an
            # overlay that never comes on air in replays. So three independent
            # signals, OR-ed, and the gate opens if ANY of them says the
            # picture is moving:
            #
            #   - the CARS. Track position is what the overlay already trusts
            #     in replays (R3E's own deltas are garbage there, which is why
            #     the gap engine derives everything from distance). If the
            #     field's cumulative distance is growing, the replay is
            #     playing. This is the signal that cannot be wrong.
            #   - the SESSION CLOCK. Covers the case the cars cannot: a replay
            #     playing while the field sits on a standing grid, where
            #     nothing moves but the countdown. Without this the broadcast
            #     would miss the whole pre-start build-up.
            #   - the PHYSICS CLOCK, if this build happens to advance it.
            #
            # The hysteresis is the point of the two thresholds. Starting needs
            # 0.35s of genuine movement, so a single-frame nudge while
            # scrubbing doesn't open the show; stopping allows 1.2s of stall,
            # so a stutter or a camera cut mid-replay doesn't tear the
            # broadcast down and rebuild it.
            now = time.time()
            simt = float(getattr(s.player, "game_simulation_time", 0.0) or 0.0)
            # cumulative field distance: laps dominate so it cannot go
            # backwards at a start/finish line crossing
            dist = 0.0
            for d in s.all_drivers_data_1:
                if d.place > 0:
                    dist += d.completed_laps * 1e6 + max(0.0, d.lap_distance)
            rem = float(getattr(s, "session_time_remaining", 0.0) or 0.0)
            prev = getattr(self, "_rep_prev", None)
            self._rep_prev = (simt, dist, rem)
            if prev is None:
                return False
            p_simt, p_dist, p_rem = prev
            moving = (dist > p_dist + 0.05 or simt > p_simt + 1e-4
                      or abs(rem - p_rem) > 1e-3)
            # RE-CUEING THE REPLAY. Dragging the scrubber back to the start to
            # record the race properly is, for the broadcast, a new session:
            # the intro should play again, and lap one should be lap one. The
            # field's distance collapsing is that gesture. Small rewinds
            # (watching a corner twice) are left alone — the threshold is what
            # separates re-cueing from rewinding.
            if dist < p_dist - 5e5 or simt < p_simt - 10.0:
                self._sess_gen += 1
                self._rep_rolling = False
                self._rep_moving_since = None
            if moving:
                if getattr(self, "_rep_moving_since", None) is None:
                    self._rep_moving_since = now
                if now - self._rep_moving_since >= 0.35:
                    self._rep_rolling = True
                self._rep_still_since = None
            else:
                self._rep_moving_since = None
                if getattr(self, "_rep_still_since", None) is None:
                    self._rep_still_since = now
                elif now - self._rep_still_since > 1.2:
                    self._rep_rolling = False
            return getattr(self, "_rep_rolling", False)
        if not self._drivers(s):
            return False
        return (s.game_in_menus != 1 and s.game_player_in_garage != 1
                and s.session_phase in (3, 4, 5, 6))


    def _update_button(self, game_running, in_action):
        """STATE AS A LAMP, not a sentence. This chip used to read "● OVERLAY:
        waiting for RaceRoom" — a caption longer than most of the timing tower,
        parked over the game's top-left corner for an entire session. It is a
        status light, so it now looks like one:

            ●  green   LIVE, on air
            ●  yellow  standby — game is up, you're in the menus
            ●  dim     no RaceRoom window yet
            ●  amber   overlay hidden (keeps the word, see below)

        COLOUR, not shape, carries the state, and that is a deliberate limit
        rather than a preference. Only ● and ≡ are proven to render here — both
        are on screen in the build today — and the obvious alternatives (◐, ○,
        ■, ▶) could not be told apart from a missing-glyph box by width or by
        bounding box when measured. A tofu square in the corner of the screen
        would be a worse outcome than the words were, so they are not used.

        The hidden state keeps its word. It is the one state where the icon has
        to advertise that clicking does something, and the only one you can sit
        in while not racing — so the width costs nothing when it matters."""
        if not self.visible:
            txt, col = "● SHOW", "#ffa94d"
        elif not game_running:
            txt, col = "●", DIM
        elif in_action:
            txt, col = "●", GREEN
        else:
            txt, col = "●", YELLOWT
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



    # ---------- stats engine ----------
    def update_stats(self, s):
        # GONE detection (runs before _drivers is used downstream): a car frozen
        # on track during a green race — same lap + track position for 20s+, not
        # in the pits, not the player — is treated as retired/disconnected so the
        # booth/radio stop talking about it. DNF/DQ are handled in _drivers. Scans
        # the RAW array so a car that recovers can un-freeze and return.
        now = time.time()
        # the freeze rule NEVER applies in replays: pausing/scrubbing freezes
        # every car at once, they all got flagged 'gone', and the broadcast
        # went dark ("waiting for replay data" that never cleared)
        green = (s.session_type == 2 and self._racing
                 and s.game_in_replay != 1)
        vslot = s.vehicle_info.slot_id
        # FOCUS CHANGE (replay camera hop / spectate switch): every "player"
        # telemetry field (lap-valid, cut counter, penalty state) suddenly
        # describes a DIFFERENT car — reseed the edge trackers without firing,
        # or each camera hop sprays phantom "track limits" / off-track calls.
        if getattr(self, "_focus_prev", None) != vslot:
            self._focus_prev = vslot
            self._q_off_lv = s.current_lap_valid
            self._q_off_watch = None
            self._q_lvs = getattr(s, "lap_valid_state", -1)
            self._q_cuts = max(0, s.cut_track_warnings)
            self._eng_cuts = max(0, s.cut_track_warnings)
            self._eng_plv = s.current_lap_valid
            self._eng_lvs = getattr(s, "lap_valid_state", -1)
            self._eng_off_watch = None
            self._eng_pen = -1
            self._pen_lvs = getattr(s, "lap_valid_state", -1)
            self._pen_lvs_at = 0.0
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

        # RESTART DETECTION, the other two ways round.
        #
        # The session key is (track, layout, type, iteration, gen), and
        # restarting the SAME session at the same track changes none of the
        # first four — RaceRoom does not always advance session_iteration. That
        # left `gen` above as the only signal, and it needs the leader's lap
        # count to fall by two or more. Restart during the opening laps and it
        # never fires: reported as the overlay still showing the previous
        # session's data instead of starting fresh.
        #
        # Two unambiguous signals. A session clock only ever counts DOWN while
        # you are in a session, so it jumping up is a new one. And your own lap
        # count only ever goes up, so it falling means the session under you was
        # replaced. Either alone is enough; both are cheap.
        # RESTART DETECTION, the signal that actually arrives in time.
        #
        # Everything above is DERIVED from race progress — lap counts, the
        # session clock — so none of it can fire during the seconds when a
        # restart is most likely: on the grid, before a lap exists and before
        # the clock has moved enough to be sure. That is the reported bug. The
        # overlay carried the old session's grid, best laps and objectives into
        # the new race because, by every measure it was watching, nothing had
        # happened yet.
        #
        # `game_simulation_time` is the session's own clock. It starts at the
        # session and only ever advances, so it falling is not an inference
        # about a restart — it IS the restart, on the first tick of the new
        # session, whatever the lap counters say. (FACTORtv reads rF2's
        # mCurrentET exactly this way; R3E has always published the same thing
        # and nothing here read it.)
        #
        # NOT IN REPLAYS. Scrubbing a replay backwards drags this clock with
        # it, and rewinding to watch a corner again is not a new session.
        simt = float(getattr(s.player, "game_simulation_time", 0.0) or 0.0)
        _psim = getattr(self, "_prev_simt", None)
        if s.game_in_replay != 1:
            if _psim is not None and simt < _psim - 2.0:
                self._sess_gen += 1
            self._prev_simt = simt
        else:
            self._prev_simt = None

        rem = getattr(s, "session_time_remaining", 0.0) or 0.0
        prev_rem = getattr(self, "_prev_rem", None)
        me_now = next((d for d in order
                       if d.driver_info.slot_id == s.vehicle_info.slot_id), None)
        my_laps = me_now.completed_laps if me_now is not None else 0
        prev_my = getattr(self, "_prev_my_laps", None)
        if ((prev_rem is not None and rem > prev_rem + 5.0)
                or (prev_my is not None and my_laps < prev_my)):
            self._sess_gen += 1
        self._prev_rem = rem
        self._prev_my_laps = my_laps

        # reset everything on a new session/track/restart
        key = (s.track_id, s.layout_id, s.session_type, s.session_iteration,
               self._sess_gen)
        if key != self._sess_key:
            self._sess_key = key
            self.grid_place = {}
            self.last_laps = {}
            self.best_lap = {}       # slot -> best lap time (for quali/practice tower)
            self.recent_laps = {}    # slot -> last few lap times (rolling pace)
            self._obj_damaged = False  # severe damage -> objectives switch to salvage
            self._obj_reset()          # race-objective state (overlay_objective)
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
            # seed from the LIVE counter, not 0 — the game can carry the count
            # across the session boundary for a few ticks, and a 0 seed turned
            # that leftover into a false rising edge ("mind the track limits"
            # spoken the moment the new session opened)
            self._q_cuts = max(0, s.cut_track_warnings)
            self._sec_laps = {}      # slot -> completed_laps (sector-coach lap edge)
            self._formation = False  # the new session gets its own formation lap
            self._form_seen = False
            self._form_said = set()
            self._form_open_t = 0.0
            self._prev_simt = None   # don't measure the new clock against the old
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
                old = self.cplace.get(sl)
                if old is not None and old != raw:
                    # tower row flash: green = gained, red = lost (~1s)
                    if not hasattr(self, "_row_flash"):
                        self._row_flash = {}
                    self._row_flash[sl] = ("#123a1c" if raw < old else "#3a1414",
                                           time.time() + 1.1)
                self.cplace[sl] = raw          # seed immediately, else confirm

        # HAS THE RACE GONE GREEN? On the standing grid the cars are stationary
        # and nose-to-tail, which otherwise triggers bogus "he's catching you /
        # in my mirrors" radio. We latch on the one signal that's reliable in
        # every mode: the field is actually MOVING (lights out), or a lap has
        # been completed. (session_phase / start_lights proved unreliable — they
        # were flipping this true ON the grid, flooding the radio AND breaking
        # the start call.) The START announcement fires on this same transition.
        # Non-races have no grid start, so they're always 'racing'.
        #
        # THE ROLLING START. The movement latch is right for a standing start
        # and wrong for every rolling one: the field forms up at 80 km/h, the
        # speed test passes a whole lap early, and the booth calls lights-out
        # somewhere on the formation lap — reported as the overlay treating the
        # formation as if it were already the race.
        #
        # Phase 3 is Formation (see R3E.cs SessionPhase) and it is the one
        # phase reading that is unambiguous: it means the field is circulating
        # BEFORE the start, which is exactly the state the speed test cannot
        # tell from racing. It is used only to HOLD the latch, never to set it
        # — that asymmetry is deliberate. Phase was untrustworthy here as a
        # trigger (it flipped this true on the grid, which is what the note
        # above is about); as a veto the worst it can do is call the green a
        # moment late, which is a far cheaper failure than calling the race
        # underway while everyone is still weaving behind the safety car.
        # WHOSE OVERLAY IS THIS? `s.player_name` is the local ACCOUNT,
        # not the car being viewed — which is the distinction that matters in
        # a replay or while spectating, where the viewed car is somebody else
        # and his chosen helmet should still be his.
        try:
            # TOP-LEVEL, NOT `s.player`. `player_name` is a field of the shared
            # block itself (r3e_data.R3EShared), not of PlayerData. Reading it
            # off `s.player` raised, the except below swallowed it, and the name
            # was never learned: the player's radio card said "YOU", and the
            # helmet he designed -- matched by this name -- never appeared on
            # his own card. Reported as the card not showing his account name.
            nm = R.u8_to_str(s.player_name).strip()
            if nm:
                self._my_name = nm
        except Exception:
            pass

        phase = getattr(s, "session_phase", -1)
        self._formation = (s.session_type == 2 and phase == 3
                           and not self._racing)
        if self._formation:
            self._form_seen = True
            self._form_said = getattr(self, "_form_said", set())
        if not self._racing:
            if s.session_type != 2:
                self._racing = True
            elif any(d.completed_laps >= 1 for d in order):
                # A completed lap outranks the veto. If a build ever leaves
                # phase parked at 3 or 4, the race must still go green.
                self._racing = True
            elif phase in (3, 4):
                pass                     # formation lap / countdown: not yet
            elif abs(s.car_speed) > 4.0 or _field_launched(order):
                # trigger as soon as the field launches (lower threshold) so the
                # 'lights out' call lands closer to the actual moment
                #
                # ...AND THE FIELD'S SPEED, NOT ONLY THE PLAYER'S. `s.car_speed`
                # is YOUR car, and in a REPLAY or while SPECTATING there is no
                # car of yours to read — it sits at zero through the whole
                # start. The latch then had exactly one route left, the
                # completed-lap test above, so the green flag was declared when
                # the leader crossed the line and the booth called lights-out a
                # lap late. Reported precisely:
                #
                #   *"race starts are very underwhelming and not accurate, and
                #     it always only starts around lap 2"*
                #
                # Lap 2 was not an approximation. It was `completed_laps >= 1`.
                #
                # Every driver carries `car_speed` (see r3e_data.DriverData), so
                # the field can answer the same question the player's car was
                # being asked, in every mode. The player's own speed is kept and
                # tried FIRST because it is one read and it is right the instant
                # he launches; the field is the fallback that makes replays and
                # spectator mode behave like driving.
                self._racing = True
            if self._racing:
                # Green-flag stamp for the RADIO. The booth keeps its own
                # (_green_at), but that is set in update_commentary, which runs
                # AFTER update_radio in the tick — so on the very first racing
                # tick the engineer saw no stamp at all and any "wait N seconds
                # after the green" guard passed trivially. Stamped here, at the
                # same latch as _racing, both are true from the same instant.
                self._green_t = time.time()

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
            # lap DELETED — flying lap invalidated (track limits) out of the pits.
            # NOT during the chequered/teardown phase: session end invalidates
            # EVERYONE's current lap at once, which read as a burst of phantom
            # "lap deleted — track limits" booth calls right as the next
            # session was loading.
            if is_lap_sess:
                cv = d.current_lap_valid
                pv = self._q_valid.get(slot, 1)
                self._q_valid[slot] = cv
                if (pv == 1 and cv == 0 and d.in_pitlane != 1
                        and slot in self._q_set and s.session_phase != 6):
                    self._q_events.append((slot, "deleted", None))
            p = prog(d)
            g = (lead_prog - p) * ref
            self.cum_gap[slot] = g if g >= 0 else 0.0
            self.interval[slot] = ((prog(prev_car) - p) * ref
                                   if prev_car is not None else 0.0)
            # LIVE sessions: the game computes real inter-car time deltas —
            # trust them over our track-position estimate. The estimate drifts
            # with the median-lap conversion (tower said 3.0s while the
            # engineer's line said 'right behind' — every consumer reads this
            # map, so the whole broadcast inherited the error). Replays keep
            # the estimate: the delta fields are garbage there (huge/NaN).
            if s.game_in_replay != 1 and prev_car is not None:
                tdf = d.time_delta_front
                # 0.0 doubles as "no data" (and -1 = N/A) — keep the estimate
                # then; a real dead-heat gap of 0.005s is indistinguishable
                # from unset and the estimate handles it fine
                if 0.005 < tdf < 600.0:
                    self.interval[slot] = tdf
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
                    # ROLLING PACE: the last few laps, which is what a race
                    # objective must be judged on. A best lap is a one-off and
                    # would promise catches that current pace can't deliver.
                    rl = self.recent_laps.setdefault(slot, [])
                    rl.append(lap)
                    del rl[:-4]                    # keep the last 4
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

        # rebuild gap-to-leader as the running sum of the (game-authoritative,
        # where live) intervals so the tower, relative panel and radio all
        # quote the SAME numbers
        if s.game_in_replay != 1:
            run = 0.0
            for d in order:
                run += max(0.0, self.interval.get(d.driver_info.slot_id, 0.0))
                self.cum_gap[d.driver_info.slot_id] = run
            if order:
                self.cum_gap[order[0].driver_info.slot_id] = 0.0

        # PLAYER off-track in PRACTICE / QUALIFYING — the race off-track call is
        # handled by the incident system in update_commentary, but in non-race
        # sessions the engineer still needs to know you've had a moment so he can
        # warn you. Same confirm logic as the race path: a lap going invalid is
        # only a CANDIDATE (it includes a harmless kerb clip); we confirm a real
        # excursion by a genuine COLLAPSE in speed (grass / gravel / a spin).
        if is_lap_sess:
            now = time.time()
            # only warn while the session is RUNNING — at the chequered flag
            # the game invalidates the current lap and the player naturally
            # slows for the pits, which the watch used to "confirm" as a
            # phantom off (the engineer scolded you on the cool-down lap).
            # "not checkered" rather than "== green": the phase field is often
            # unset in replays, and detection must keep working there.
            live = (s.session_phase != 6)
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
            if (live and moving and self._q_off_lv == 1 and plv == 0
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
                if in_pit or not live:
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
            if live and cuts > self._q_cuts:
                self._q_events.append((vslot, "limits", None))
            self._q_cuts = max(0, cuts)   # a decrease = counter reset, no edge
            # NEXT LAP WON'T COUNT — lap_valid_state == 2 means THIS and the next
            # lap are both invalid. Fire on each rising edge so the engineer warns
            # you every time it happens.
            lvs = getattr(s, "lap_valid_state", -1)
            if live and lvs == 2 and getattr(self, "_q_lvs", -1) != 2:
                self._q_events.append((vslot, "nextlap_invalid", None))
            self._q_lvs = lvs

        # RACE OBJECTIVE — TRACKED EVERY TICK, deliberately here rather than
        # inside the engineer's ladder. It used to be reached only when that
        # ladder got that far, which on most ticks it never does (it returns
        # early on damage, gaps, temps, pit calls...). Two consequences: the
        # HUD chip showed stale laps/gap/progress, and a target being MET or
        # MISSED went undetected until the ladder happened to reach it — so
        # the engineer frequently never announced it at all. Tracking here
        # keeps the chip live and resolution instant; anything to SAY is
        # parked in _obj_say for the radio to drain on its next pass.
        try:
            _pm = {d.place: d for d in order if d.place > 0}
            _ev = self.objective_event(s, order, _pm, time.time())
            if _ev:
                self._obj_say = _ev
                # (the booth's cue is posted by _obj_notice inside the
                # objective module itself — it needs the objective's KIND,
                # which is gone by the time the category reaches us here)
        except Exception as ex:
            self._stage_err["objective"] = f"{type(ex).__name__}: {ex}"

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

    # ---------- relative panel (cars around the focused car) ----------

    # ---------- fastest lap banner + focused-car sectors (lower third) ----------

    # ---------- team-radio engine ----------
    def _dname(self, d):
        return (R.u8_to_str(d.driver_info.name) or "DRIVER").upper()

    _LAP_WORDS = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
                  7: "seven", 8: "eight", 9: "nine", 10: "ten"}


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
            # USER HELMET ART drives the palette when present: each driver is
            # assigned the next helmet variant (same sequential scheme), and
            # their colour is sampled FROM that helmet — so the card accent,
            # the name and the timing tower always match the helmet on screen
            # instead of clashing with a fixed palette entry.
            n = self._dcolor_n
            c = None
            # A HELMET RENDERED FROM THE NAME, not dealt from a deck of nine.
            #
            # The sequential scheme below assigned `icon_helmet_N.png` in order
            # of FIRST SIGHTING. Three things follow from that, and all three
            # are wrong in an online lobby:
            #
            #   * it wraps at nine. A twenty-car grid had duplicates
            #     guaranteed, and the duplicates were also colour-twins.
            #   * it depends on arrival order, so the SAME opponent wore a
            #     different helmet in a different session.
            #   * it is local. You and he saw different helmets for the same
            #     driver, because you sighted people in a different order.
            #
            # Rendering from the name fixes all three at once: one driver, one
            # helmet, for ever — and the same helmet on every machine, with no
            # networking, because the name is the only input and everybody has
            # it. That is what makes a lobby of strangers feel like a grid of
            # people rather than a list of lap times.
            #
            # The colour still comes FROM the helmet (`card_colour`), so the
            # card accent, the name and the timing tower keep matching the
            # picture — which is the property the old sampling scheme existed
            # to provide, and is preserved rather than re-invented.
            try:
                # HIS CHOICE OUTRANKS THE GENERATOR, and nothing else does.
                # Every other driver on the grid is generated, because nobody
                # else's design can reach this machine — RaceRoom's shared
                # memory carries names, not liveries.
                spec = None
                if name and name == getattr(self, "_my_name", ""):
                    spec = dict(getattr(self, "_my_helmet", None) or {}) or None
                if spec is None:
                    spec = helmet_mod.generated(name)
                if spec:
                    self._dhelmet[name] = spec
                    # LIFTED UNTIL IT CAN BE READ. This colour is not just the
                    # accent strip — it is the driver's NAME, on a near-black
                    # card, and a navy or forest shell straight from
                    # `card_colour` measures barely over 1:1 against it. The
                    # helmet stays its true colour; the text gets the same hue
                    # walked towards white only as far as it has to go.
                    #
                    # Found by LOOKING at a rendered lobby, not by a test: four
                    # of twenty names came out unreadable and every assertion
                    # still passed, because "is it a distinct colour" and "can
                    # you read it" are different questions.
                    c = helmet_mod.readable(helmet_mod.card_colour(spec),
                                            CARD_BG)
            except Exception:
                c = None
            # USER-DRAWN ART STILL WINS. Someone who has put their own
            # `icon_helmet_*.png` next to the exe chose those on purpose, and a
            # generator must not overrule a decision.
            if c is None:
                vs = avatars.helmet_variants()
                if vs:
                    self._dvariant[name] = n % len(vs)
                    c = avatars.variant_color(n % len(vs))
            if c is None:                      # no art (or unreadable) — palette
                c = DRIVER_COLORS[n % len(DRIVER_COLORS)]
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

    # ---- shuffle-bag line selection (persistent across sessions) ------------
    # Every pool is dealt like a deck of cards: a line can't repeat until the
    # WHOLE pool has been heard, and the deck state is saved to disk so it
    # carries across sessions — a nightly player keeps hearing fresh lines
    # instead of the same "random" favourites every evening. Lines are tracked
    # by a hash of their text (not index) so editing/adding lines between
    # versions never corrupts the state.
    _BAG_FILE = os.path.join(_DIR, "_heard.json")
    _HCACHE = {}

    @property
    def _recent_lines(self):
        """{line hash: the pick number it was last dealt on} — the global
        anti-repeat memory shared by every pool and both booth voices. In
        memory only: it is about not repeating yourself within a broadcast,
        which the persistent per-pool decks already handle across sessions."""
        r = getattr(self, "_recent_lines_map", None)
        if r is None:
            r = self._recent_lines_map = {}
        return r

    @_recent_lines.setter
    def _recent_lines(self, v):
        self._recent_lines_map = v

    @classmethod
    def _line_h(cls, text):
        h = cls._HCACHE.get(text)
        if h is None:
            import hashlib
            h = hashlib.md5(text.encode("utf-8", "ignore")).hexdigest()[:10]
            cls._HCACHE[text] = h
        return h

    def _bag_state(self):
        """Lazy-loaded {key: {"bag": set(remaining hashes), "last": hash}}."""
        bags = getattr(self, "_bags", None)
        if bags is None:
            bags = {}
            try:
                if os.environ.get("RACERTV_EPHEMERAL"):
                    raise RuntimeError    # tests: in-memory decks, no disk state
                with open(self._BAG_FILE, encoding="utf-8") as f:
                    for k, v in json.load(f).items():
                        bags[k] = {"bag": set(v.get("bag") or []),
                                   "last": v.get("last")}
            except Exception:
                pass                              # missing/corrupt -> fresh decks
            self._bags = bags
            self._bag_saved_t = time.time()
        return bags

    def _bag_save(self, force=False):
        """Throttled write (every ~20s and on quit) — the file is tiny but
        there's no need to hit the disk on every single line."""
        if os.environ.get("RACERTV_EPHEMERAL"):
            return                        # tests never touch the real deck state
        now = time.time()
        if not force and now - getattr(self, "_bag_saved_t", 0) < 20:
            return
        self._bag_saved_t = now
        try:
            bags = getattr(self, "_bags", None)
            if bags is None:
                return
            out = {k: {"bag": sorted(v["bag"]), "last": v["last"]}
                   for k, v in bags.items()}
            tmp = self._BAG_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(out, f)
            os.replace(tmp, self._BAG_FILE)
        except Exception:
            pass

    # ---- career memory (the booth remembers YOU across sessions) ------------
    # A tiny persistent record of the player's results per track, so the booth
    # can say "back at Monza — won here last time out, didn't he Brett?" months
    # into a live-service game. Recorded at the finish, referenced once early
    # in each race. Same ephemeral rule as the shuffle-bags for tests.
    _CAREER_FILE = os.path.join(_DIR, "_career.json")

    def _career(self):
        c = getattr(self, "_career_data", None)
        if c is None:
            c = {"races": 0, "wins": 0, "podiums": 0, "tracks": {},
                 # PHASE 3: race-objective record, so the engineer can refer to
                 # your form across sessions ("that's four targets in five")
                 "obj_set": 0, "obj_met": 0, "obj_races": []}
            try:
                if not os.environ.get("RACERTV_EPHEMERAL"):
                    with open(self._CAREER_FILE, encoding="utf-8") as f:
                        d = json.load(f)
                    for k in c:
                        c[k] = d.get(k, c[k])
            except Exception:
                pass                          # missing/corrupt -> fresh career
            self._career_data = c
        return c

    def _career_record(self, trk, pos, field):
        """Record the player's finishing position at this track."""
        if not pos or pos < 1:
            return
        c = self._career()
        c["races"] += 1
        # fold this race's objective record into the career file. obj_races is
        # a short rolling window (last 8) so "targets in recent races" stays
        # about CURRENT form rather than a lifetime average.
        n_set = getattr(self, "_obj_count", 0)
        if n_set:
            n_met = getattr(self, "_obj_met", 0)
            c["obj_set"] = c.get("obj_set", 0) + n_set
            c["obj_met"] = c.get("obj_met", 0) + n_met
            hist = list(c.get("obj_races") or [])
            hist.append([n_met, n_set])
            c["obj_races"] = hist[-8:]
        if pos == 1:
            c["wins"] += 1
        if pos <= 3:
            c["podiums"] += 1
        key = (trk or "").lower()[:24] or "unknown"
        t = c["tracks"].setdefault(key, {"visits": 0, "wins": 0,
                                         "best": 0, "last": 0})
        t["visits"] += 1
        if pos == 1:
            t["wins"] += 1
        if not t["best"] or pos < t["best"]:
            t["best"] = pos
        t["last"] = pos
        if os.environ.get("RACERTV_EPHEMERAL"):
            return
        try:
            tmp = self._CAREER_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(c, f)
            os.replace(tmp, self._CAREER_FILE)
        except Exception:
            pass

    def _career_note(self, trk):
        """(category, kwargs) for a booth callback to the player's history at
        this track, or None when there's no history worth mentioning."""
        t = self._career()["tracks"].get((trk or "").lower()[:24])
        if not t or not t.get("visits"):
            return None
        times = {1: "once", 2: "twice"}.get(t["visits"], f'{t["visits"]} times')
        kw = {"times": times, "best": t["best"], "last": t["last"]}
        if t.get("wins"):
            kw["wins"] = ("once" if t["wins"] == 1 else
                          "twice" if t["wins"] == 2 else f'{t["wins"]} times')
            return ("career_won_here", kw)
        if t.get("best") and t["best"] <= 3:
            return ("career_podium_here", kw)
        return ("career_back", kw)

    def _pick(self, pool, key):
        """Deal a line from the pool's shuffle-bag: no repeats for this key
        until every line in the pool has been used once, AND no repeat of any
        line the booth has aired in the last RECENT_LINE_WINDOW picks, whatever
        pool or persona it came from.

        The per-key bag alone was not enough, for three measured reasons. The
        `analysis` filler pool supplies the overwhelming majority of booth lines
        (516 of 538 in an instrumented race), so its 77-line deck reshuffles
        every few minutes and starts dealing the same lines again — one race
        aired 110 duplicate lines, several of them five and six times. The
        COMMENTATOR and the PUNDIT keep SEPARATE bags for the same pool, so
        both could deal the same line independently. And 31 lines exist in more
        than one pool, each with its own bag.

        All three are the same symptom to a listener: the booth repeating
        itself. A global recency window over the line TEXT catches all of them
        at once. When every candidate is recent (a small pool under pressure)
        the least recently used one is dealt rather than going silent."""
        if not pool:
            return ""
        if len(pool) == 1:
            return pool[0]
        bags = self._bag_state()
        k = "|".join(str(p) for p in key) if isinstance(key, tuple) else str(key)
        hs = [self._line_h(t) for t in pool]
        st = bags.get(k)
        choices = ([i for i, h in enumerate(hs) if h in st["bag"]]
                   if st else [])
        if not choices:
            # deck exhausted (or pool changed under us): reshuffle everything
            # back in, but never deal the very last line again immediately
            last = st["last"] if st else None
            choices = [i for i, h in enumerate(hs) if h != last] or \
                      list(range(len(pool)))
            st = {"bag": set(hs), "last": last}
            bags[k] = st
        # GLOBAL RECENCY, across every pool, key and persona.
        seen = self._recent_lines
        self._pick_n = n = getattr(self, "_pick_n", 0) + 1
        # the window must be at least a full trip through this pool, or a line
        # becomes legal again before its own deck has finished cycling — which
        # is exactly how a 77-line pool still managed to repeat itself
        win = max(RECENT_LINE_WINDOW, len(pool) - 1)
        fresh = [i for i in choices
                 if n - seen.get(hs[i], -10 ** 9) > win]
        if fresh:
            choices = fresh
        else:
            # everything on offer has been heard recently — take whichever was
            # heard longest ago instead of repeating the most recent one
            choices = [min(choices, key=lambda i: seen.get(hs[i], -10 ** 9))]
        idx = random.choice(choices)
        seen[hs[idx]] = n
        if len(seen) > 4000:                  # keep the map from growing forever
            cut = n - max(RECENT_LINE_WINDOW, 200)
            self._recent_lines = {h: t for h, t in seen.items() if t >= cut}
        st["bag"].discard(hs[idx])
        st["last"] = hs[idx]
        self._bag_save()
        return pool[idx]













    # crosstalk topics that only make sense when pit stops are part of the race
    _PIT_TOPICS = ("pitwall", "strategy", "tyres")



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







            # 3rd+ extra in the window: stay quiet (no spam)








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


    @staticmethod
    def _short_car(nm):
        """Broadcast-friendly short car name. RaceRoom's full names can run to
        40+ characters ('AMG-Mercedes 190 E 2.5-16 Evolution II 1992') and the
        booth was reading them out in FULL — a commentator says 'the Porsche
        911 GT3 Cup', never '(991.2) Endurance'. Strips parentheticals, years
        and series/spec suffixes, then caps at 4 words."""
        if not nm:
            return nm
        nm = re.sub(r"\([^)]*\)", " ", nm)              # (2019), (991.2)...
        words = [w for w in nm.split()
                 if not re.fullmatch(r"(19|20)\d\d", w)  # bare years
                 and w not in ("Endurance", "Esports", "eDTM", "GTM15")]
        return " ".join(words[:4]) or nm.strip()

    def _player_car(self, s):
        """Friendly SHORT name of the car being viewed/driven, or None."""
        if not self._car_names:
            return None
        return self._short_car(self._car_names.get(int(s.vehicle_info.model_id)))

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

    # ---- toggle actions (shared by hotkeys AND the clickable menu) ----------
    def _do_toggle_ui(self):
        self.toggle_visible()
        self._toast("UI ON" if self.visible
                    else "UI HIDDEN — broadcast audio stays live"
                         "  (Ctrl+Shift+O, or click ● SHOW top-left)")

    def _do_toggle_booth(self):
        self.commentary_on = not self.commentary_on
        if not self.commentary_on and self.tts:
            # cut queued booth audio NOW (radio/engineer jobs survive) —
            # without this the booth keeps talking for many seconds after
            # the player asked it to shut up
            self.tts.interrupt()
        self._toast("BOOTH ON — Miles & Brett are back" if self.commentary_on
                    else "BOOTH OFF — engineer & driver radio stay live")

    def _do_toggle_radio(self):
        self.radio_on = not self.radio_on
        if not self.radio_on and self.tts:
            # silence what's queued/playing, but keep booth colour alive: purge
            # only the non-booth jobs by cutting current radio audio
            self.tts.interrupt()
        self._toast("TEAM RADIO ON — engineer & drivers" if self.radio_on
                    else "TEAM RADIO MUTED — booth stays live")

    def _do_toggle_mute(self):
        if not self.tts:
            return self._toast("TTS unavailable — no voices to mute")
        on = self.tts.toggle()
        self._toast("ALL VOICES ON" if on else "ALL VOICES MUTED")

    @property
    def spectating(self):
        """Is the driver-facing half of the product addressed to NOBODY?

        Two ways to be true and they are kept apart on purpose: `spectator` is
        what he CHOSE and is persisted, `_auto_spec` is what the game SAYS
        about this moment and is not. Everything that asks "should the engineer
        talk" asks this; everything that renders or writes the setting asks
        `spectator`.
        """
        return bool(getattr(self, "spectator", False)
                    or getattr(self, "_auto_spec", False))

    def _do_toggle_spectator(self):
        """Watching, not driving.

        Everything RacerTV says to a driver — the engineer in your ear, the
        objective card, the relative panel — assumes there IS a driver, and in
        a replay of someone else's race, or a race you are only spectating,
        that half of the product is talking to nobody. Spectator mode drops it
        and keeps the broadcast: booth, tower, map, flags, sectors, fastest
        lap. The radio is silenced through the same path as the manual mute, so
        anything already queued goes with it rather than arriving alone."""
        self.spectator = not self.spectator
        _save_pref("spectator", self.spectator)
        if self.spectator and self.tts:
            self.tts.interrupt()
        self._toast("SPECTATOR MODE — broadcast only, no team radio"
                    if self.spectator
                    else "SPECTATOR MODE OFF — engineer & objectives are back")

    # ---- the helmet designer ------------------------------------------
    #
    # Fitted to RacerTV's menu rather than ported with FACTORtv's: this one is
    # a flat list of rows drawn on a click-through overlay whose clicks are
    # POLLED, so the whole designer is spin rows with two arrows each, on a
    # second PAGE of the settings menu. No modal, no keyboard.

    # WHICH FIELDS SPIN, AND THROUGH WHAT. One table, read by both the drawing
    # and the click handling, so a row cannot offer a value the action cannot
    # set.
    def _helmet_fields(self):
        cols = [h for _n, h in helmet_mod.PALETTE]
        return {
            "base":     cols,
            "accent":   cols,
            "ink":      cols,
            "accent2":  cols,
            "pattern":  list(helmet_mod.PATTERNS),
            "pattern2": ["none"] + list(helmet_mod.PATTERNS),
            "number":   [None] + list(range(0, 100)),
            "weight":   list(helmet_mod.WEIGHTS),
            "weight2":  list(helmet_mod.WEIGHTS),
        }

    def _helmet_spec(self):
        """The design being edited, always a FULL spec."""
        return dict(helmet_mod.normalise(getattr(self, "_my_helmet", None))
                    or helmet_mod.DEFAULT)

    def _helmet_save(self, spec):
        """Store it, persist it, and make the next card wear it.

        THE CACHES MUST BE DROPPED OR NOTHING VISIBLE CHANGES. `_dcolor` and
        `_dhelmet` are filled on a driver's FIRST sighting and never revisited
        — that is what makes them cheap — so editing the helmet without
        clearing his entries left the old one on screen and looked like the
        menu was broken.
        """
        spec = dict(helmet_mod.normalise(spec) or {})
        self._my_helmet = spec
        _save_pref("helmet", spec)
        nm = getattr(self, "_my_name", "")
        if nm:
            self._dcolor.pop(nm, None)
            self._dhelmet.pop(nm, None)
            self._dvariant.pop(nm, None)

    def _helmet_spin(self, field, step):
        """Move one field along its list, wrapping."""
        vals = self._helmet_fields().get(field)
        if not vals:
            return
        spec = self._helmet_spec()
        cur = spec.get(field)
        try:
            i = vals.index(cur)
        except ValueError:
            i = 0
        spec[field] = vals[(i + step) % len(vals)]
        self._helmet_save(spec)

    def _helmet_toggle(self, field):
        spec = self._helmet_spec()
        spec[field] = not bool(spec.get(field))
        self._helmet_save(spec)

    def _helmet_random(self):
        """One click, a whole livery.

        CONTRAST IS NOT OPTIONAL. A random accent lands on a near-identical
        colour often enough to produce an invisible pattern, which reads as
        the button being broken rather than as a choice.
        """
        cols = [h for _n, h in helmet_mod.PALETTE]
        base = random.choice(cols)
        accent = random.choice([c for c in cols
                                if helmet_mod.contrast(base, c) > 2.2] or cols)
        pat2 = (random.choice(list(helmet_mod.PATTERNS))
                if random.random() < 0.45 else "none")
        self._helmet_save({
            "base": base, "accent": accent,
            "pattern": random.choice(list(helmet_mod.PATTERNS)),
            "weight": random.choice(list(helmet_mod.WEIGHTS)),
            "flip": random.random() < 0.5,
            "pattern2": pat2,
            "accent2": random.choice([c for c in cols
                                      if helmet_mod.contrast(base, c) > 2.2
                                      and helmet_mod.contrast(accent, c) > 1.6]
                                     or cols),
            "weight2": random.choice(list(helmet_mod.WEIGHTS)),
            "flip2": random.random() < 0.5,
            "number": random.choice([None] + list(range(1, 100))),
            "ink": random.choice([c for c in cols
                                  if helmet_mod.contrast(base, c) > 3.0] or cols),
            "trim": "",
        })

    def _helmet_reset(self):
        """Back to the one his NAME would have given him — which is a real
        answer, not an absence: it is what every other driver wears."""
        self._my_helmet = {}
        _save_pref("helmet", {})
        nm = getattr(self, "_my_name", "")
        if nm:
            self._dcolor.pop(nm, None)
            self._dhelmet.pop(nm, None)
            self._dvariant.pop(nm, None)

    def _menu_goto(self, page):
        self._menu_page = page

    def _do_toggle_objectives(self):
        """Race objectives on or off. Remembered between launches."""
        self.objectives_on = not getattr(self, "objectives_on", True)
        _save_pref("objectives", self.objectives_on)
        if not self.objectives_on:
            self._obj = None
            self._obj_say = None
        self._toast("OBJECTIVES ON" if self.objectives_on
                    else "OBJECTIVES OFF — no targets, just racing")

    def _do_cycle_speedo(self):
        """OFF -> KM/H -> MPH -> OFF."""
        nxt = {"off": "kmh", "kmh": "mph", "mph": "off"}
        self.speedo = nxt[self.speedo]
        _save_pref("speedo", self.speedo)
        self._toast({"off": "SPEEDO OFF",
                     "kmh": "SPEEDO ON — km/h",
                     "mph": "SPEEDO ON — mph"}[self.speedo])

    def _do_toggle_compact(self):
        self.compact = not self.compact
        self._toast("COMPACT TOWER" if self.compact else "FULL TOWER")

    def _do_toggle_debug(self):
        self.debug = not self.debug
        self._toast("DEBUG HUD ON" if self.debug else "DEBUG HUD OFF")

    def _menu_flip(self):
        self._menu_open = not getattr(self, "_menu_open", False)
        # CLOSING RETURNS TO THE TOP. Re-opening the menu into the designer,
        # several clicks deep in a page he was last on ten sessions ago, is
        # disorienting — the hamburger should always show the same thing.
        if not self._menu_open:
            self._menu_page = "main"




    def _show_caption(self, text, persona="COMMENTATOR"):
        """Set the lower-third caption (called when audio actually starts, so it
        stays in sync). Runs on the TTS worker thread — a plain assignment."""
        # hold scales with how long the line takes to SAY — a fixed 5.5s left
        # long lines captionless while still being spoken (looked out of sync)
        hold = max(4.5, min(12.0, len(text) * 0.055 + 2.0))
        self._comm_caption = {"text": text, "persona": persona,
                              "at": time.time(),
                              "until": time.time() + hold}

    def _caption_line_end(self, text, persona):
        """TTS play thread: a line just finished playing. If the lower-third
        still shows it, let it linger only briefly — the length-estimated hold
        was regularly outliving the audio, which looked like caption desync."""
        cap = self._comm_caption
        if cap and cap.get("text") == text:
            cap["until"] = min(cap["until"], time.time() + 1.2)








    def run(self):
        self.root.mainloop()


_INSTANCE_MUTEX = None          # kept alive for the life of the process


def _single_instance():
    """Return True if no other overlay instance is already running.

    NB the kernel32 handle has to be opened with use_last_error=True. Plain
    ctypes.windll.kernel32 does NOT copy the Win32 last-error into ctypes'
    thread-local storage, so ctypes.get_last_error() came back 0 instead of
    183 and this guard silently passed EVERY time — which is how you end up
    with two overlays running, hearing and seeing everything twice.
    """
    global _INSTANCE_MUTEX
    try:
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        h = k32.CreateMutexW(None, False, "R3EOverlay_singleton_mutex")
        err = ctypes.get_last_error()
        if err == 183:                     # ERROR_ALREADY_EXISTS
            return False
        _INSTANCE_MUTEX = h                # hold it open, else the next
        return True                        # launch would think it is free
    except Exception:
        return True                        # never block startup on this


if __name__ == "__main__":
    if not _single_instance():
        # The app is windowed, so a bare SystemExit would vanish without a
        # trace and a second launch would look like nothing happened at all.
        # Say so, otherwise the only symptom is doubled audio and visuals.
        try:
            ctypes.windll.user32.MessageBoxW(
                None,
                "RacerTV is already running.\n\n"
                "Close the existing overlay first "
                "(Ctrl+Shift+Q), then start it again.",
                "RacerTV", 0x40)          # MB_ICONINFORMATION
        except Exception:
            pass
        raise SystemExit("RacerTV already running")
    Overlay().run()
