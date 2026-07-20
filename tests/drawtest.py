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
o._obj = None
o._obj_result = {"ok": True, "hud": "Pass Pierre Dubois",
                 "until": 9e18}
check("draw_objective (result chip)", lambda: o.draw_objective(None))

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

# and the radio path must not band-pass the voice — it eats the accents
import inspect as _inspect                                # noqa: E402
_src = _inspect.getsource(_tts.Tts._render)
assert "_radioize(samples" not in _src, (
    "the band-pass is back on the radio voices — it flattens neural prosody "
    "and strips the accents the foreign-voice cast exists for")
print("  no band-pass on radio voices (accents preserved): OK")
print("\nALL DRAW + CUE + VOICE CHECKS PASSED")
