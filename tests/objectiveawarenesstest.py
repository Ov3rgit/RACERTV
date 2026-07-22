"""OBJECTIVE / BIG-MOMENT AWARENESS — a real two-race transcript showed:

  * the commentators never once reacted to an objective being set, passed, or
    failed, across the WHOLE race.
  * the race engineer's own set/met/miss line for the FIRST objective never
    aired either -- only its later resolution happened to survive.
  * the player's own overtake for P1 went completely unacknowledged until much
    later in the race.

Root causes, confirmed against the debug log:
  A. `_obj_say` (the engineer's queued objective line) is drained into a local
     `events` list inside `_engineer_events`, but the OUTER global-cooldown
     gate in `update_radio` could still discard the WHOLE tick's `events`
     afterwards -- silently losing an already-drained, bypass=True objective
     announcement, with no retry (it had already been cleared).
  B. the booth's objective-awareness reaction required `not busy` (TTS queue
     idle) within a 12s window; in a commentary-dense race that window can
     close having NEVER seen a gap, so it silently expired unheard.
  C. a lead change was built as a prio-0 candidate and DID get queued, but
     with only the default 12s TTL and no guaranteed interrupt, a busy queue
     let it sit until it TTL-dropped before its turn came (confirmed in the
     debug log: queued, then 'DROP-stale' 13s later).

Each fix is proven here to change behaviour versus the pre-fix code.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, r"D:\R3EOverlay")
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "smoke.py")).read()
exec(_src.split('run_session("RACE"')[0])

NCARS = 8


def race():
    o = headless_overlay(fake_tts=True)
    s = make_shared(2, ncars=NCARS)
    s.number_of_laps = 20
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    for i, d in enumerate(s.all_drivers_data_1[:NCARS]):
        d.car_speed = 60.0
        d.place = i + 1
        d.completed_laps = 4
    for _ in range(8):
        drive(o, s, 1)
    o._green_at = time.time() - 60.0
    o._green_t = time.time() - 60.0
    return o, s


print("===== A. an objective's engineer line survives an active global "
      "cooldown =====")
o, s = race()
o.last_radio_t = time.time()          # a line JUST aired -- global CD is fresh
o._eng_cd -= 40                       # clear the per-engineer cooldown too
o._obj_say = ("obj_set_defend",
              {"drv": "Rossi", "laps": 4, "pos": 5, "gap": "1s"})
before = len(o.tts.spoken)
o.update_radio(s)
eng_lines = [t for p, t in o.tts.spoken[before:] if p == "ENGINEER"]
assert eng_lines, (
    "the objective's set-line was discarded by the still-active global "
    "cooldown, exactly the reported bug (an objective's own engineer "
    "announcement silently lost, no retry possible)")
assert o._obj_say is None, "the objective line was drained but never sent"
print(f"  the set-line lands despite a fresh global cooldown: OK -> "
      f"{eng_lines[0][:60]}")


print("\n===== B. the booth's objective reaction lands before its window "
      "closes, even in a busy queue =====")
# a notice posted 10s ago -- still inside the 12s window, but past the new
# 9.5s force-through mark -- with a queue that has stayed busy the WHOLE time
# (exactly the reported "an entire commentary-dense race" scenario).
o, s = race()
posted_at = time.time() - 10.0
o._obj_eng_aired_t = posted_at        # the engineer's own call has already aired
o._obj_booth = ("set", "defend", "Rossi", posted_at, "the position")
o.tts._pend = 3                       # still busy -- old code would stay silent
before = len(o.tts.spoken)
o.update_commentary(s)
said = " || ".join(t for _p, t in o.tts.spoken[before:])
assert said, (
    "the booth's objective reaction never forced through near its deadline, "
    "in a queue that never cleared -- the reported 'zero booth objective "
    "lines all race' bug")
assert o._obj_booth is None, (
    "the notice was neither spoken nor cleared -- it will be attempted again "
    "redundantly next tick")
print(f"  the booth reaction forces through near the deadline instead of "
      f"expiring unheard: OK -> {said[:60]}")


print("\n===== C. a lead change is signature-tier: always interrupts, never "
      "TTL-dropped =====")
import inspect                                              # noqa: E402
import overlay_booth as _ob                                 # noqa: E402
_src_ec = inspect.getsource(_ob.BoothMixin._emit_commentary)
assert '"leadchange"' in _src_ec and "signature = cat in" in _src_ec, (
    "leadchange is no longer in the signature-tier category set")
_sig_line = [ln for ln in _src_ec.splitlines() if "signature = cat in" in ln][0]
assert "leadchange" in _sig_line, (
    f"leadchange dropped from the signature tier: {_sig_line}")
print("  leadchange is a signature-tier category (force + always interrupt): OK")

# behavioural: a leadchange candidate lands even with a queue full enough that
# an ordinary urgent (non-signature) candidate would be held and retried
o, s = race()
o.tts._pend = 4                        # queue full
before = len(o.tts.spoken)
ctx = SimpleNamespace(
    cands=[(0, "A new leader — Over Boy takes P1!", "leadchange", 2,
            "COMMENTATOR")],
    cur={}, is_race=True, now=time.time(), trk="Spa")
o._emit_commentary(ctx)
said3 = [t for _p, t in o.tts.spoken[before:]]
assert any("new leader" in t.lower() for t in said3), (
    "the lead change did not land immediately despite a full queue -- it "
    "should interrupt and force through like start/final_lap/pregrid")
assert o._comm_hold is None, (
    "the lead change was HELD rather than spoken immediately -- it should "
    "never enter the ordinary hold-and-retry path")
print("  a lead change lands immediately even with a full queue: OK")

print("\nOBJECTIVE / BIG-MOMENT AWARENESS CHECKS PASSED")
