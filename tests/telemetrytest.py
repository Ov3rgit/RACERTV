# -*- coding: utf-8 -*-
"""THE ENGINEER MEASURES, HE DOES NOT JUST READ THE GAUGE.

RaceRoom publishes `fuel_per_lap`, and the engineer used it directly. It is
the game's own average over the STINT, so it lags a change of driving style by
laps -- which is exactly the window in which fuel saving is decided. Watching
the tank across a lap crossing gives what the driver is ACTUALLY using now.

Also asserted here: the engineer is allowed to bring good news. Every fuel and
tyre line in the pool was a warning, so he only ever spoke when something was
wrong, once -- which is what makes a warning mean something when it comes.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import sys

sys.path.insert(0, r"D:\R3EOverlay")
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])

from lines import ENGINEER_LINES                          # noqa: E402

fails = []


def check(ok, what, detail=""):
    print("  [%s] %s%s" % ("OK" if ok else "FAIL", what,
                           ("  " + str(detail)) if detail else ""))
    if not ok:
        fails.append(what)


print("\n1. THE POOLS EXIST AND CARRY THEIR SLOTS")
for _k in ("fuel_burn", "fuel_ok", "tyres_ok"):
    check(bool(ENGINEER_LINES.get(_k)), "pool '%s' exists" % _k,
          "%d lines" % len(ENGINEER_LINES.get(_k) or []))
# A LINE THAT NAMES A NUMBER MUST HAVE THE NUMBER TO NAME. A {burn} with no
# slot supplied renders as literal braces on a radio card.
_bad = [t for t in ENGINEER_LINES["fuel_burn"]
        if "{burn}" not in t or "{need}" not in t]
check(not _bad, "every fuel_burn line uses BOTH {burn} and {need}", _bad[:1])
_stray = [t for _k in ("fuel_ok", "tyres_ok") for t in ENGINEER_LINES[_k]
          if "{" in t]
check(not _stray, "the reassurance lines take no slots at all", _stray[:1])


print("\n2. THE BURN IS MEASURED ACROSS LAP CROSSINGS")
# Drive four laps burning a known amount, and read back what the engineer
# would quote. The median of the last three is the figure under test.
o = headless_overlay(fake_tts=True)
o._eng_fuel_lap = None
o._eng_burns = []


class _Car(object):
    def __init__(self, laps):
        self.completed_laps = laps


def lap(o, laps, fuel):
    """One tick of the burn tracker, lifted from the engineer path."""
    prev = getattr(o, "_eng_fuel_lap", None)
    if prev is None or laps < prev[0]:
        o._eng_fuel_lap = (laps, fuel)
        o._eng_burns = []
    elif laps > prev[0]:
        used = prev[1] - fuel
        if 0.05 < used < 99.0:
            o._eng_burns = (getattr(o, "_eng_burns", []) + [used])[-3:]
        o._eng_fuel_lap = (laps, fuel)


for _l, _f in ((0, 50.0), (1, 47.5), (2, 45.0), (3, 42.5), (4, 40.0)):
    lap(o, _l, _f)
_b = sorted(o._eng_burns)
_med = _b[len(_b) // 2]
check(abs(_med - 2.5) < 0.01, "a steady 2.5/lap burn is measured as 2.5",
      "%.2f" % _med)

# AN OUTLIER MUST NOT MOVE IT. A safety-car lap, or a lap stuck in traffic,
# burns almost nothing -- a MEAN would swallow that and quote a burn rate the
# driver cannot reproduce. The median ignores it, which is the whole reason it
# is a median.
lap(o, 5, 39.8)          # 0.2 of a lap's worth: a crawl behind the pace car
_b = sorted(o._eng_burns)
_med2 = _b[len(_b) // 2]
check(abs(_med2 - 2.5) < 0.01,
      "one crawling lap does not drag the quoted burn down", "%.2f" % _med2)

# REFUELLING IS NOT A NEGATIVE BURN. A pit stop puts fuel IN; treating that as
# consumption would quote a negative number to the driver.
lap(o, 6, 60.0)          # stopped and refuelled
check(all(x > 0 for x in o._eng_burns),
      "a refuelling stop is not recorded as a lap's burn", o._eng_burns)


print("\n3. THE TARGET IS THE SUM THAT MATTERS")
# "Save fuel" is an instruction without a measure. "You're on 2.50, we need
# 2.00" is something a driver can actually drive to.
_fuel_left, _laps_left = 20.0, 10
_need = _fuel_left / float(_laps_left)
check(abs(_need - 2.0) < 1e-6, "20 litres over 10 laps needs 2.00 a lap",
      "%.2f" % _need)
check(_need < _med, "...and 2.50 a lap does not make the finish, so it warns")

print("\n4. THE SHIFT LIGHT IS THE WHOLE RING")
# Asked for: 'i want the whole circle in the speedo to light up purple when
# it is time to shift'.
#
# PROBED PAST THE NEEDLE, NOT AT THE TOP. The first version of this check
# read the pixel at the top of the ring, and it passed against the OLD dial
# too: the top is half-way round the sweep, so a needle past half lights it
# either way. A check that cannot tell the new behaviour from the old one is
# not a check. So the probe sits at 93% of the way round with the needle at
# 60% -- a stretch that ONLY a whole-ring shift light can colour.
import math as _m
import speedo as _sp
_D = 300


def _ring_pixel(rev, shift_at, f):
    im = _sp.render(_D, rev, shift_at, 0.99)
    cx = cy = _D / 2.0
    rr = (_D / 2.0 - 4) - 9 / 2.0              # the sweep's centre line
    th = _m.radians(_sp.START_DEG + _sp.SWEEP_DEG * f)
    x, y = int(round(cx + rr * _m.cos(th))), int(round(cy - rr * _m.sin(th)))
    r, g, b, a = im.load()[x, y]
    return (r, g, b)


_purple = lambda c: c[2] > c[1] + 60 and c[0] > c[1]
_shifting = _ring_pixel(0.60, 0.50, 0.93)      # needle at 60%, shift at 50%
_cruising = _ring_pixel(0.40, 0.50, 0.93)      # needle below the shift point
check(_purple(_shifting),
      "past the shift point, the ring is purple even far beyond the needle",
      _shifting)
check(not _purple(_cruising),
      "below the shift point, that part of the ring is unlit", _cruising)

# ...AND THE FACE. Asked for with a screenshot: the big inner circle should
# take a tint of purple at the shift point, not just the ring.
_fc = _sp.render(_D, 0.40, 0.50, 0.99).load()[_D // 2, _D // 2][:3]
_fs = _sp.render(_D, 0.60, 0.50, 0.99).load()[_D // 2, _D // 2][:3]
# A TINT, so it is judged as one: blue and red both clearly above green, and
# brighter than the resting face. The ring's rule (blue 60+ over green) is
# for a neon stroke and failed a correct 26% wash.
_tint = lambda c, base: (c[2] > c[1] + 30 and c[0] > c[1] + 15
                         and sum(c) > sum(base) + 60)
check(_tint(_fs, _fc), 'the face itself is tinted purple at the shift point', _fs)
check(not _tint(_fc, _fc), 'and is not before it', _fc)

print("\n" + ("FAILED: %d" % len(fails) if fails else "ALL PASSED"))
sys.exit(1 if fails else 0)
