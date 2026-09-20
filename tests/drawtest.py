"""Every draw stage must actually RUN without raising.

Why this exists: the radio cards silently stopped appearing because
_draw_bubble called _card(glass=False) while _card had never gained that
parameter — a script that was meant to add it aborted before writing the
file. Every bubble raised TypeError, the draw loop swallowed it into
_stage_err, and nothing else looked wrong. py_compile and pyflakes both pass
that happily, because the call is only wrong at RUNTIME.

So this drives the real drawing code against a real tk canvas with realistic
state, and fails on any exception. It needs a display; if tkinter can't open
one it skips rather than failing the suite.
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

# Build on the REAL headless harness so every core Overlay method exists —
# stubbing them one by one just moves the goalposts (and would hide exactly
# the kind of missing-attribute break this file is meant to catch).
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "smoke.py")).read()
exec(_src.split('run_session("RACE"')[0])          # noqa: E402
from overlay_common import CARD_BG, ACCENT          # noqa: E402

CV = tk.Canvas(_root, width=1920, height=1080)


def make_overlay():
    """A real Overlay with the tk drawing surface attached."""
    o = headless_overlay(fake_tts=True)
    # `canvas` is a PROPERTY that wraps _cv_real in the translating _TC, so
    # set the real canvas and let the property build the wrapper as it does
    # in the running app — assigning o.canvas would just raise.
    o._cv_real = CV
    o._bg_real = None
    o._ox = o._oy = 0
    o.sw, o.sh = 1920, 1080
    o.f_row = tkfont.Font(family="Segoe UI", size=10)
    o.f_row_b = tkfont.Font(family="Segoe UI", size=10, weight="bold")
    o.f_small_b = tkfont.Font(family="Segoe UI", size=8, weight="bold")
    o.f_sub = o.f_row
    # THE REST OF THE FACES. The header, tower and speedo stages were never
    # driven from here, so the fonts they need were never defined -- which is
    # part of why a speedo that raised every frame went unnoticed. Names, not
    # metrics, are what matter to these checks.
    o.f_hdr = tkfont.Font(family="Segoe UI", size=12, weight="bold")
    o.f_small = tkfont.Font(family="Segoe UI", size=9)
    o.f_tow = tkfont.Font(family="Segoe UI", size=11)
    o.f_tow_b = tkfont.Font(family="Segoe UI", size=11, weight="bold")
    o.f_tiny = tkfont.Font(family="Segoe UI", size=8)
    o.f_spd = tkfont.Font(family="Segoe UI", size=20, weight="bold")
    o.f_gear = tkfont.Font(family="Segoe UI", size=14, weight="bold")
    o._obj = None
    o._obj_result = None
    o._rel_box = None
    o._begin_panel = lambda *a, **k: o.canvas
    o.text = lambda x, y, t, fill="#fff", font=None, anchor="w":         CV.create_text(x, y, text=t, fill=fill, font=font, anchor=anchor)
    o.radio_msgs = []
    return o


o = make_overlay()
fails = []


def check(name, fn):
    try:
        fn()
    except Exception as ex:
        fails.append(f"{name}: {type(ex).__name__}: {ex}")
    else:
        print(f"  {name}: OK")


print("===== CARD PRIMITIVES =====")
check("_card (glass default)",
      lambda: o._card(10, 10, 300, 60, accent=ACCENT, side="top"))
check("_card (glass=False, radio bubbles)",
      lambda: o._card(10, 90, 300, 60, fill=CARD_BG, accent=ACCENT,
                      side="top", glass=False))
check("panel", lambda: o.panel(10, 200, 300, 80))

print("\n===== RADIO BUBBLE (the one that was silently failing) =====")
for msg in (
    {"name": "RACE ENGINEER", "text": "Box this lap, box box box.",
     "color": ACCENT, "emotion": "neutral", "engineer": True},
    {"name": "M. Hill", "text": "He pushed me wide, that was never his corner!",
     "color": "#e23b3b", "emotion": "angry", "engineer": False},
):
    who = "engineer" if msg["engineer"] else "driver"
    check(f"_draw_bubble ({who})",
          lambda m=msg: o._draw_bubble(20, 300, 380, m))

print("\n===== OBJECTIVE HUD =====")
check("draw_objective (no objective -> draws nothing)",
      lambda: o.draw_objective(None))
o._obj = {"hud": "Pass Pierre Dubois", "_prog": 0.5, "_badge": "P4",
          "_laps_left": 3, "_gap": 1.8, "_trend": -1, "kind": "position",
          "goal_pos": 4, "laps": 4, "lap0": 2}
check("draw_objective (active target)", lambda: o.draw_objective(None))
# NEW-target blink: an overlay border drawn on top of _card's own frame. It
# only runs on alternate half-seconds, so pin _new_until far ahead and draw
# repeatedly to be sure the lit frame is actually executed, not skipped.
o._obj["_new_until"] = 9e18
check("draw_objective (new-target blink)",
      lambda: [o.draw_objective(None) for _ in range(4)])
o._obj.pop("_new_until")
# EVERY objective kind draws its own glyph. Each is a separate branch of
# vector primitives, and an unexercised branch is exactly how the _card(glass=)
# TypeError shipped -- so drive them all, plus an unknown kind for the
# text-badge fallback.
for _kind, _goal in (("position", 2), ("chase", 3), ("recover", 5),
                     ("defend", 4), ("damage", 6), ("clean", None),
                     ("tyres", None), ("leadhome", 1), ("pb", None),
                     ("pole", None), ("nonsense_kind", 9)):
    o._obj = {"hud": f"{_kind} target", "_prog": 0.4, "_badge": "P2",
              "_laps_left": 2, "_gap": 0.9, "_trend": -1, "kind": _kind,
              "goal_pos": _goal, "laps": 4, "lap0": 2}
    check(f"draw_objective (icon: {_kind})", lambda: o.draw_objective(None))
# HOLD-STATE GLOW: a maturing loss (red ramp), a maturing gain (green ramp)
# and the fractional ring maths at several ages — an unexercised glow branch
# is exactly the _card(glass=) class of bug this file exists to catch.
import time as _t
for _key, _age in (("_hold_lose", 0.5), ("_hold_lose", 6.0),
                   ("_hold_pass", 0.2), ("_hold_pass", 2.9),
                   ("_hold_clear", 3.9)):
    o._obj = {"hud": "Hold P5", "_prog": 0.5, "_badge": "P5",
              "_laps_left": 2, "_gap": 0.6, "_trend": 1, "kind": "defend",
              "goal_pos": 5, "laps": 4, "lap0": 2, _key: _t.time() - _age}
    check(f"draw_objective (glow {_key} @{_age}s)",
          lambda: o.draw_objective(None))
o._obj = None
o._obj_result = {"ok": True, "hud": "Pass Pierre Dubois",
                 "until": 9e18}
check("draw_objective (result chip / tick glyph)",
      lambda: o.draw_objective(None))
o._obj_result = {"ok": False, "hud": "Pass Pierre Dubois", "until": 9e18}
check("draw_objective (result chip / cross glyph)",
      lambda: o.draw_objective(None))

# DOCKING: with a tower box, the card sits BELOW it; with NO box (tower not
# drawn this frame) the fallback must NOT land on the tower's rows (y=110) —
# that was the overlap. Capture the y the card is drawn at.
import overlay_draw as _od                              # noqa: E402
_ys = []
_real_card = o._card
o._card = lambda x, y, w, h, **k: (_ys.append(y), _real_card(x, y, w, h, **k))[-1]
o._obj_result = None
o._obj = {"hud": "x", "_prog": 0.4, "_badge": "P4", "_laps_left": 2,
          "_gap": 0.9, "_trend": 0, "kind": "defend", "goal_pos": 4,
          "laps": 4, "lap0": 2}
o._rel_box = (1590, 110, 300, 190)                      # tower spans 110..300
o.draw_objective(None)
assert _ys[-1] >= 300, f"card docked INTO the tower (y={_ys[-1]}, tower ends 300)"
o._rel_box = None                                       # tower gone this frame
o.draw_objective(None)
assert _ys[-1] > 110, f"fallback docked the card on the tower rows (y={_ys[-1]})"
o._card = _real_card
print("  objective card never overlaps the relative tower: OK")


# ---- THE HELMET DESIGNER PAGE -------------------------------------------
# This file exists for bugs that are only wrong at RUNTIME, and the designer
# produced a textbook one: it called `self.canvas.create_image`, and `canvas`
# is the translating `_TC` wrapper, which has no such method. py_compile was
# perfectly happy about it. It was found by RENDERING the page (see
# tests/designershot.py), and this is what stops it coming back.
#
# IT SITS ABOVE THE `assert not fails` BELOW, and that is not incidental.
# `check()` COLLECTS failures rather than raising them, so a block appended
# after that assertion throws silently and the suite still passes -- which is
# exactly what happened when these checks were first added: four of them
# raised and nothing said a word.
#
# Every optional row is forced on, because a row that only appears for
# certain patterns is a row that only breaks for certain patterns.
print("\n===== HELMET DESIGNER =====")
o._my_name = "Dante_K"
o._menu_page = "helmet"
for _label, _spec in (
        ("default", {}),
        ("every optional row", {"base": "#161616", "accent": "#d4ff00",
                                "pattern": "blade", "weight": "bold",
                                "pattern2": "visorband", "accent2": "#ff3d7a",
                                "weight2": "normal", "number": 4,
                                "ink": "#f2f2f2"}),
        ("no number, no layer", {"base": "#2340d8", "accent": "#f2f2f2",
                                 "pattern": "solid", "pattern2": "none",
                                 "number": None}),
        ("mirrored", {"base": "#ff7a1a", "accent": "#161616",
                      "pattern": "sweep", "flip": True, "number": 81})):
    o._my_helmet = dict(_spec)
    check("_draw_helmet_page (%s)" % _label,
          lambda: o._draw_helmet_page(x=10, y=10))

# ...AND THE ROWS IT DREW ARE CLICKABLE. A page whose arrows register no hit
# boxes looks perfect and does nothing at all.
o._menu_hits = []
o._my_helmet = {}
o._draw_helmet_page(x=10, y=10)
assert len(o._menu_hits) >= 12, (
    "the designer registered %d hit boxes -- its arrows are not clickable"
    % len(o._menu_hits))
print("  %d clickable regions: OK" % len(o._menu_hits))


# ---- THE STAGES THAT HAD NO COVERAGE AT ALL ------------------------------
#
# `draw_speedo` called `self.canvas.create_image`, and `canvas` is the `_TC`
# wrapper, which proxies rectangle/oval/text/line/polygon and NOT images. It
# raised on every frame, the stage loop swallowed it into `_stage_err`, and
# the dial, the speed and the gear never drew -- for a whole release, in the
# very commit that added the speedometer.
#
# `speedoshot.py` passed the whole time because it calls `speedo.render()`
# directly and never touches the line that was wrong. The art was fine; the
# one line that puts it on screen was not.
#
# Nothing here asserts what the panels LOOK like. It asserts that they run,
# which is the bar the speedo failed to clear.
print("\n===== FULL DRAW STAGES =====")
_s = make_shared(2, ncars=8)
_s.session_phase = 5
_s.number_of_laps = 14
_s.car_speed = 61.0
_s.engine_rps = 780.0
_s.max_engine_rps = 900.0
_s.gear = 5
for _i, _d in enumerate(_s.all_drivers_data_1[:8]):
    _d.place = _i + 1
    _d.completed_laps = 6
    _d.car_speed = 61.0
    _d.lap_distance_fraction = 0.4 - _i * 0.01
    _d.time_delta_front = 0.4 + _i * 0.3
o.speedo = "kmh"
o.compact = False
o.game_x = o.game_y = 0
for _ in range(2):
    o.update_stats(_s)
for _nm, _fn in (("draw_header", lambda: o.draw_header(_s)),
                 ("draw_flags", lambda: o.draw_flags(_s)),
                 ("draw_penalty", lambda: o.draw_penalty(_s)),
                 ("draw_tower", lambda: o.draw_tower(_s)),
                 ("draw_relative", lambda: o.draw_relative(_s)),
                 ("draw_speedo", lambda: o.draw_speedo(_s))):
    check(_nm, _fn)

# THE SPEEDO SPECIFICALLY: it must put an IMAGE on the canvas, not merely
# fail to raise. A future edit that quietly drops the dial would still pass
# the check above, because the exception was never the point -- the missing
# picture was.
assert getattr(o, "_speedo_img", None) is not None, (
    "draw_speedo ran but put no dial image on the canvas -- the image call is silently doing nothing again")
print("  the speedo actually placed its dial: OK")

# THE TELEMETRY PANEL. Asked for twice ("there is still NO telemetry"): the
# engineer had fuel and tyre calls, but nothing was on SCREEN. It must run
# with real data, and it must extend the speedo's published box so the radio
# cards and the caption keep clear of it too.
_s.fuel_use_active = 1
_s.fuel_left = 23.4
_s.fuel_per_lap = 2.7
_s.tire_wear_active = 1
for _i, (_w, _c) in enumerate(((0.8, 92.0), (0.7, 60.0), (0.4, 118.0), (0.2, 90.0))):
    _s.tire_wear[_i] = _w
    _t = _s.tire_temp[_i]
    _t.current_temp[1] = _c
    _t.cold_temp, _t.optimal_temp, _t.hot_temp = 75.0, 90.0, 105.0
# RECORD WHERE THE PANELS ACTUALLY LAND. Reported: "the cards are
# overlapping with the hud telemetry, put the speedo and telemetry next to
# each other instead of on top of each other". Stacked, the pair was a tall
# column in the bottom-right corner and the radio cards -- which live in that
# same column, stacking up from the speedo's top edge -- landed on the
# telemetry. Side by side the pair is no taller than the dial.
_seen = {}
_bp = o._begin_panel
o._begin_panel = lambda nm, lx, ly, w, h: (
    _seen.__setitem__(nm, (lx, ly, w, h)), _bp(nm, lx, ly, w, h))[1]
check("draw_telemetry (via draw_speedo)", lambda: o.draw_speedo(_s))
o._begin_panel = _bp
_sp, _tl = _seen.get("speedo"), _seen.get("telemetry")
assert _sp and _tl, "speedo/telemetry did not both place a panel: %r" % (_seen,)


def _overlap(a, b):
    return (a[0] < b[0] + b[2] and b[0] < a[0] + a[2]
            and a[1] < b[1] + b[3] and b[1] < a[1] + a[3])


assert not _overlap(_sp, _tl), (
    "the telemetry panel overlaps the dial: speedo=%r telemetry=%r"
    % (_sp, _tl))
assert _tl[0] + _tl[2] <= _sp[0], (
    "the telemetry is not BESIDE the dial -- it is stacked again: "
    "speedo=%r telemetry=%r" % (_sp, _tl))
assert _tl[1] + _tl[3] == _sp[1] + _sp[3], (
    "the telemetry's bottom edge does not line up with the dial's: "
    "speedo=%r telemetry=%r" % (_sp, _tl))
_box = getattr(o, "_speedo_box", None)
assert _box is not None, "the speedo published no box"
_x0, _y0 = min(_sp[0], _tl[0]), min(_sp[1], _tl[1])
assert _box == (_x0, _y0,
                max(_sp[0] + _sp[2], _tl[0] + _tl[2]) - _x0,
                max(_sp[1] + _sp[3], _tl[1] + _tl[3]) - _y0), (
    "the published box is not the union of the two panels, so the radio "
    "cards and the caption will draw over one of them: box=%r speedo=%r "
    "telemetry=%r" % (_box, _sp, _tl))
print("  telemetry sits beside the dial, and the box is their union: OK")
# AND THE PAIR IS A ROW, NOT A COLUMN. This is the property the radio cards
# actually care about: they stack up from _speedo_box[1], so a short box
# leaves them room and a tall one does not.
assert _box[2] > _box[3], (
    "the speedo and telemetry are taller than they are wide -- the cards "
    "will be pushed off the top of the screen again: %r" % (_box,))
print("  the corner is a row, not a tall column: OK")
assert [o._tyre_state(_s, _k)[1] for _k in range(4)] == ["ok", "cold", "hot", "ok"], (
    "tyre temperatures are not judged against the game's own cold/hot figures")
print("  tyre temperatures judged against the compound's own range: OK")

assert not fails, "draw stages raised:\n  " + "\n  ".join(fails)
print("\nALL DRAW CHECKS PASSED")
_root.destroy()


print("\n===== TTS CUE CONTRACT (card/audio sync) =====")
# The radio card's fate is decided by the cue: on_play when audio starts,
# on_drop the instant it can't. Exactly one must ever fire — if both could,
# a card would either double-air or never air.
import tts as _tts                                       # noqa: E402

_log = []
_c = _tts._Cue(lambda t, p: _log.append("play"), lambda: _log.append("drop"))
_c.play("x", "ENGINEER"); _c.play("x", "ENGINEER"); _c.drop()
assert _log == ["play"], f"play path fired {_log}"
_log = []
_c = _tts._Cue(lambda t, p: _log.append("play"), lambda: _log.append("drop"))
_c.drop(); _c.drop(); _c.play("x", "ENGINEER")
assert _log == ["drop"], f"drop path fired {_log}"
print("  exactly one of play/drop, exactly once: OK")

_tts._Cue(None, lambda: 1 / 0).drop()      # must not escape to the audio thread
print("  a raising drop callback is contained: OK")

# _purge tells gen jobs from play jobs by LENGTH, so the cue had to fit in the
# existing on_play slot rather than widen either tuple. Pin that.
_log = []
_tts._cue_drop(("t", "p", "v", 0, _tts._Cue(None, lambda: _log.append("g")),
                0, None, None, 1), True)
_tts._cue_drop(("w.wav", _tts._Cue(None, lambda: _log.append("p")),
                "t", "p", 0, None, None, 1), False)
assert _log == ["g", "p"], _log
print("  cue found at the right index in both payload shapes: OK")
print("\nALL DRAW + CUE CHECKS PASSED")


print("\n===== VOICE CONFIG =====")
# FORMAT check only, deliberately. Do NOT assert membership of
# edge_tts.list_voices(): "en-AU-WilliamNeural" is ABSENT from that list and
# yet renders perfectly (verified by synthesising with it), so 'not listed'
# does not mean 'broken'. Inferring otherwise led to the pundit's voice being
# changed for no reason. The only reliable check is an actual render, which
# needs the network and so stays a manual step.
import re as _re                                          # noqa: E402
_VOICE_RE = _re.compile(r"^[a-z]{2}-[A-Z]{2}-[A-Za-z]+Neural$")
_bad = [v for v in (_tts.NEURAL_VOICES
                    + [_tts.ENGINEER_VOICE, _tts.COMMENTATOR_VOICE,
                       _tts.PUNDIT_VOICE])
        if not _VOICE_RE.match(v)]
assert not _bad, f"malformed voice names: {_bad}"
print(f"  {len(_tts.NEURAL_VOICES)} rival + 3 named voices, all well-formed: OK")

# the two radio paths stay SPLIT — settled by ear in a direct A/B: rivals on
# the intercom band-pass, the engineer clean (it flattened his prosody)
import inspect as _inspect                                # noqa: E402
_src = _inspect.getsource(_tts.Tts._render)
assert 'persona == "ENGINEER"' in _src and "vs = list(samples)" in _src, (
    "the engineer lost his clean path — the band-pass flattens his prosody")
assert "_radioize(samples" in _src, "the rivals lost the intercom band-pass"
print("  radio split: rivals band-passed, engineer clean: OK")

# every rival read must actually reach edge-tts. This line referenced an
# undefined `seed`, and the bare `except Exception` in _render turned that
# NameError into a silent fallback to offline SAPI for EVERY driver — the real
# cause of the "robotic drivers" report. Compilers don't catch it; this does.
# Any name _gen_edge loads as a GLOBAL must actually exist in the module. A
# name that is neither a local nor a real global (`seed` was a leftover of a
# removed parameter) compiles fine and only explodes at render time.
# (read LOAD_GLOBAL from the bytecode, not co_names — co_names also holds
# attribute names like .save/.rstrip, which are not globals at all)
import dis as _dis                                        # noqa: E402
import builtins as _bi                                    # noqa: E402
_missing = sorted({i.argval for i in _dis.get_instructions(_tts.Tts._gen_edge)
                   if i.opname == "LOAD_GLOBAL"}
                  - set(_tts.__dict__) - set(vars(_bi)))
assert not _missing, (
    f"_gen_edge loads undefined global name(s) {_missing} — rival renders "
    "raise and the bare except in _render silently falls back to SAPI")
print("  _gen_edge references no undefined globals: OK")
print("\nALL DRAW + CUE + VOICE CHECKS PASSED")

# ---- OBJECTIVE CHIMES -----------------------------------------------------
# The card's UI sound: given / met / missed. Distinct MOTIFS, not just three
# copies of one beep -- the point is knowing which fired without looking.
print("\n===== OBJECTIVE CHIMES =====")
_rates = {}
for _k in ("set", "met", "miss"):
    _smp = _tts._chime(24000, _k)
    assert _smp, f"chime {_k} rendered nothing"
    _peak = max(abs(v) for v in _smp)
    assert 0.05 < _peak < 0.95, f"chime {_k} peak out of range: {_peak:.2f}"
    # no click at either end: a chime that starts or ends on a non-zero sample
    # pops, which is exactly what "smooth" rules out
    assert abs(_smp[0]) < 0.02 and abs(_smp[-1]) < 0.02, (
        f"chime {_k} starts/ends on a step -- that clicks")
    _rates[_k] = (len(_smp), _peak)
    print(f"  {_k}: {len(_smp)/24000:.2f}s peak {_peak:.2f}: OK")
assert len({v[0] for v in _rates.values()}) == 3, (
    "the three chimes are the same length -- they need to be tellable apart "
    f"by shape, not volume: {_rates}")
print("  three distinct motifs: OK")
