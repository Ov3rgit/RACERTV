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
