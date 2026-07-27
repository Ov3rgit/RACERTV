"""A SPIN MUST BE COVERED, AND THE LAP COUNT MUST NEVER READ "LAP 0".

Three findings from one race, all proven from the debug log rather than the
transcript (the transcript only shows what AIRED — the whole problem is what
didn't):

  * "Lap 0 of 11 done. 11 left" — queued at 17:18:29, play DROP-stale at
    17:18:53. Wrong number AND silent: completed_laps is 0 for the whole of
    lap one, and the line sat 24s in a busy queue until its TTL expired.

  * The player spun P3 -> P14 and the ENGINEER's only acknowledgement, a
    one-place ack, TTL-dropped. The old trigger (confirmed place falling 2+ in
    ONE tick) never fires in practice: debounced places fall one step at a
    time, so an eleven-place fall reads as eleven single steps.

  * Four booth lines naming the player's spin all died as render DROP-cut —
    each purged by the NEXT incident's interrupt. force=True protects against
    TTL but not against an epoch purge; only the exchange lane (prio -1)
    survives an interrupt since the exchange fix.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import sys

sys.path.insert(0, r"D:\R3EOverlay")
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])
from lines import ENGINEER_LINES                          # noqa: E402
from overlay_common import _safe_format                   # noqa: E402
from poolmatch import from_pool                           # noqa: E402


def race(ncars=16, my_place=3, laps=11):
    o = headless_overlay(fake_tts=True)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    s = make_shared(2, ncars=ncars)
    s.number_of_laps = laps
    you = s.all_drivers_data_1[0]
    others = list(s.all_drivers_data_1[1:ncars])
    places = [p for p in range(1, ncars + 1) if p != my_place]
    for d in s.all_drivers_data_1[:ncars]:
        d.car_speed, d.completed_laps = 60.0, 3
    you.place = my_place
    for d, p in zip(others, places):
        d.place = p
    for _ in range(8):
        drive(o, s, 1)
    o._green_at = o._green_t = time.time() - 60.0
    o._racing = True
    return o, s, you


# ---- 1. the big-fall latch arms on a CUMULATIVE fall --------------------
o, s, you = race(my_place=3)
vslot = you.driver_info.slot_id
o._radio_my_place = 3
o._fall_t = -1e9
o._fall_said_t = -1e9
for p in (4, 5, 6):                       # one place at a time, like reality
    you.place = p
    o.cplace[vslot] = p
    drive(o, s, 2)
assert getattr(o, "_fall_say", None) or any(
    from_pool(t, ENGINEER_LINES["fell_big"])
    for pp, t in o.tts.spoken if pp == "ENGINEER"), (
    "falling three places one step at a time armed nothing — this is exactly "
    "how the P3->P14 spin went unacknowledged (single-tick trigger never "
    "fires on debounced places)")
# let the engineer drain it if still latched
for _ in range(6):
    o._eng_cd = 0.0
    o.last_radio_t = 0.0
    drive(o, s, 1)
fell = [t for pp, t in o.tts.spoken
        if pp == "ENGINEER" and from_pool(t, ENGINEER_LINES["fell_big"])]
assert fell, "the latched big-fall line never reached the radio"
print("  a 3-place step-by-step fall gets ONE engineer acknowledgement: OK\n"
      "    -> %s" % fell[0][:64])

# ...and it doesn't re-fire for the same fall
o._eng_cd = 0.0
drive(o, s, 3)
fell2 = [t for pp, t in o.tts.spoken
         if pp == "ENGINEER" and from_pool(t, ENGINEER_LINES["fell_big"])]
assert len(fell2) == len(fell), "the big-fall call repeated for the same fall"
print("  ...and only once per fall: OK")

# the pool itself formats
for ln in ENGINEER_LINES["fell_big"]:
    _safe_format(ln, {"pos": 14, "n": 11})
print("  fell_big pool formats cleanly (%d lines): OK"
      % len(ENGINEER_LINES["fell_big"]))

# ---- 2. "Lap 0 of 11" can never air -------------------------------------
def laps_events(o, s, you, done, pend=0):
    o.tts._pend = pend
    o._eng_laps_cd = 0.0
    you.completed_laps = done
    evts = []
    o._engineer_events(s, you, {d.place: d for d in s.all_drivers_data_1[:16]},
                       evts, time.time())
    o.tts._pend = 0
    return [e[3] for e in evts if "of %d" % s.number_of_laps in e[3]
            or "laps in" in e[3] or "left" in e[3].lower()]


o, s, you = race()
o._enc_cd = time.time()                    # keep idle filler out of the way
got0 = laps_events(o, s, you, done=0)
assert not any("0" == t.split()[1] or " 0 of" in t for t in got0), (
    "the engineer still reads out a lap count of ZERO on lap one: %r" % got0)
print("  no laps update on lap one (completed_laps=0): OK")

got1 = laps_events(o, s, you, done=1)
assert any("1" in t for t in got1), (
    "with one lap complete the update no longer fires at all: %r" % (got1,))
print("  fires from lap two with a real number: OK -> %s"
      % (got1[0][:56] if got1 else "?"))

# busy queue: skipped WITHOUT burning the 70s cooldown
o, s, you = race()
o._enc_cd = time.time()
got_busy = laps_events(o, s, you, done=2, pend=3)
assert not got_busy, "the laps update queued into a busy pipeline again"
assert o._eng_laps_cd == 0.0, (
    "the busy skip burned the cooldown — the update goes quiet for 70s "
    "instead of retrying when the queue clears")
print("  busy queue -> skipped without burning the cooldown: OK")

# ---- 3. the player's named off-track report rides the exchange lane -----
o, s, you = race()
calls = []
real = o.tts.speak
def rec(text, persona="ENGINEER", **kw):
    calls.append({"text": text, "persona": persona, **kw})
    return real(text, persona, **kw)
o.tts.speak = rec
o._report_offtrack("Over Boy", time.time(), primary=True)
named = [c for c in calls if "Over Boy" in c["text"]]
assert named, "the player's off produced no named line at all"
assert named[0].get("exchange") is True, (
    "the player's own named report is not on the exchange lane, so the next "
    "incident's purge kills it mid-render — the four DROP-cut lines from the "
    "debug log")
print("  player's named off report uses the exchange lane: OK")

# a RIVAL's report must NOT: rival colour is exactly what an incident cut
# should be allowed to clear
calls.clear()
o2, s2, _ = race()
o2.tts.speak = lambda text, persona="ENGINEER", **kw: (
    calls.append({"text": text, "persona": persona, **kw}))
o2._report_offtrack("Some Rival", time.time(), primary=False)
rn = [c for c in calls if "Some Rival" in c["text"]]
if rn:
    assert rn[0].get("exchange") is not True, (
        "rival incident reports are now uninterruptible too — the exchange "
        "lane must stay reserved for the player and Q/A pairs")
    print("  rival reports stay interruptible: OK")
else:
    print("  rival report gated this tick (cooldown) — skipped")

print("\nFALL-COVERAGE CHECKS PASSED")
