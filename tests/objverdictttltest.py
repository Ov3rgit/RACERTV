"""AN OBJECTIVE SET/MET/MISS LINE MUST CARRY NO EXPIRY DEADLINE.

The emit loop in overlay_radio.update_radio has always said, in a comment, that
ONE-SHOT bypass lines (lights-out start call, severe damage, incident points,
objective set/met) "must not carry the short 'numbers go stale' TTL ... being
heard matters more than the number being seconds fresh", and it set `_ttl =
None` to express that.

`_ttl = None` did not do that. Tts.speak() reads:

    if ttl is None and not force:
        ttl = TTL_BOOTH if persona in CLEAN_PERSONAS else TTL_RADIO

-- so a None ttl was quietly REPLACED by TTL_RADIO (22s) and the line got a
deadline after all, droppable in _render/_play_loop like any other. On a busy
queue an objective verdict could therefore age out and vanish silently, which
is the one failure mode overlay_radio.py:567 calls out by name ("a dropped line
is a verdict the driver never hears -- there is no second chance at it"), and
which bypass=True was introduced to prevent.

Fix: the bypass branch also passes force=True, the only flag that actually
suppresses the default deadline.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import sys

sys.path.insert(0, r"D:\R3EOverlay")
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])
import tts as _tts_mod                                    # noqa: E402
from lines import ENGINEER_LINES                          # noqa: E402
from poolmatch import from_pool                           # noqa: E402


def recording_overlay():
    """A race overlay whose TTS records the FULL kwargs of every speak().

    FakeTts swallows kwargs into **kw, so `ttl` and `force` -- the two things
    this file is about -- are invisible to it by default.
    """
    o = headless_overlay(fake_tts=True)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    calls = []
    real = o.tts.speak

    def rec(text, persona="ENGINEER", **kw):
        calls.append({"text": text, "persona": persona, **kw})
        return real(text, persona, **kw)
    o.tts.speak = rec
    o.calls = calls
    return o


import inspect                                            # noqa: E402


# ---- 1. THE CONTRACT: speak() must not default a None ttl for these -------
# Proven against the real Tts.speak source, not a mock: this is the exact line
# that silently reintroduced the deadline.
_speak_src = inspect.getsource(_tts_mod.Tts.speak)
assert "if ttl is None and not force:" in _speak_src, (
    "Tts.speak no longer defaults a None ttl -- this test's premise is stale "
    "and the fix in overlay_radio may no longer be needed")
print("  Tts.speak still substitutes a default TTL for ttl=None: OK")

# ---- 2. the emit loop passes force alongside the bypass ttl=None ----------
import overlay_radio as _rad                              # noqa: E402
_emit_src = inspect.getsource(_rad.RadioMixin.update_radio) \
    if hasattr(_rad, "RadioMixin") else None
if _emit_src is None:                                     # find it generically
    for _n in dir(_rad):
        _o = getattr(_rad, _n)
        if inspect.isclass(_o) and hasattr(_o, "update_radio"):
            _emit_src = inspect.getsource(_o.update_radio)
            break
assert _emit_src, "could not locate update_radio to inspect"
assert "_no_deadline" in _emit_src, (
    "the emit loop has no flag threading force= through for bypass one-shots, "
    "so `_ttl = None` is still silently converted to TTL_RADIO by speak()")
assert "force=_no_deadline" in _emit_src, (
    "the bypass branch computes a no-deadline flag but never passes it to "
    "speak(force=...), which is the only thing that suppresses the default")
print("  emit loop threads force= through for bypass one-shots: OK")

def race():
    o = recording_overlay()
    s = make_shared(2, ncars=8)
    s.number_of_laps = 20
    for i, d in enumerate(s.all_drivers_data_1[:8]):
        d.car_speed, d.place, d.completed_laps = 60.0, i + 1, 4
    for _ in range(8):
        drive(o, s, 1)
    o._green_at = time.time() - 60.0
    o._green_t = time.time() - 60.0
    o.last_radio_t = 0.0
    o._eng_cd -= 40
    o.calls.clear()
    return o, s


# ---- 3. END TO END: a real objective verdict reaches speak() deadline-free -
o, s = race()
# park a real met-verdict the way objective_event does, then let update_radio
# drain it through the genuine emit path
o._obj_say = ("obj_met_pass", {"drv": "Rossi", "laps": 4, "pos": 5,
                                   "gap": "1s"})
o.update_radio(s)

verdict = [c for c in o.calls if c["persona"] == "ENGINEER"
           and from_pool(c["text"], ENGINEER_LINES["obj_met_pass"])]
assert verdict, ("the objective verdict never reached speak() at all -- "
                 "cannot check its deadline")
v = verdict[0]
assert v.get("ttl") is None, (
    "the verdict was given an explicit TTL (%r); a one-shot verdict must not "
    "expire" % v.get("ttl"))
assert v.get("force") is True, (
    "the verdict reached speak() with force=%r, so speak() will replace its "
    "ttl=None with TTL_RADIO (%ss) and it can be silently dropped from the "
    "queue -- exactly the 'set and resolved in silence' failure overlay_radio "
    "warns about" % (v.get("force"), _tts_mod.TTL_RADIO))
print("  objective verdict reaches speak() with ttl=None AND force=True: OK")

# ---- 4. a NUDGE is NOT force'd (it must still yield and go stale) ---------
# The fix must not blanket-force every engineer line: mid-objective colour is
# the thing that SHOULD drop when the queue is busy.
o, s = race()
o._obj_say = ("obj_nudge_closing", {"drv": "Rossi", "laps": 4, "pos": 5,
                                     "gap": "1s"})
o.update_radio(s)
# match the NUDGE back to its own pool. A plain "first ENGINEER line" filter
# picks up the lights-out start call instead -- itself a legitimate forced
# one-shot -- and the test would fail on correct code.
nudge = [c for c in o.calls if c["persona"] == "ENGINEER"
         and from_pool(c["text"], ENGINEER_LINES["obj_nudge_closing"])]
if nudge:
    assert nudge[0].get("force") is not True, (
        "a mid-objective NUDGE was forced through with no deadline; only "
        "set/met/miss are one-shots -- colour must still be droppable")
    print("  mid-objective nudge stays droppable (force=%r): OK"
          % nudge[0].get("force"))
else:
    print("  mid-objective nudge did not emit this tick (spacing) -- skipped")

print("\nOBJECTIVE-VERDICT-TTL CHECKS PASSED")
