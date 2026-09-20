# -*- coding: utf-8 -*-
"""THE DIAL MUST NOT BE RENDERED ON THE FRAME THAT NEEDS IT.

Reported: *"the whole overlay is slow, as in the speedo and everything is
janky, when i accelerate it looks like the speedo is lagging, i think the
size of the speedo is making it slow"*. Right on both counts, and the cause
is arithmetic rather than a bug:

  * The face is cached per REV BUCKET -- 73 of them -- so the first time the
    revs reach a bucket, that face is rendered.
  * The render supersamples by SS and resizes down, so its cost goes with the
    SQUARE of the dial. Measured here on this machine before the fix:

        dial 168px  ->  8.6ms      dial 389px  -> 36.1ms
        dial 292px  -> 22.4ms      dial 489px  -> 58.2ms

  * The overlay's whole frame budget is UPDATE_MS = 50ms.

Accelerating walks up through the buckets, so on a screen-sized dial nearly
every frame of every acceleration paid 36-58ms for a face -- over budget on
its own, before the tower, the radio and the booth. The dial fell behind the
engine, and the overlay pegged a core doing it, which is the second half of
the report ("my PC is dropping the frames a lot").

Two changes, both checked below:

  1. MAX_SS_PX caps the supersample buffer, so the worst render is bounded
     no matter how large the dial gets.
  2. prewarm() renders every face this car will ever need on a daemon
     thread, the moment the shift point is known. The UI thread then never
     renders a face at all -- it only converts one to a Tk image.

WHAT THIS FILE DOES NOT CLAIM: that any particular millisecond figure holds
on any particular machine. Wall-clock budgets in a test suite are a way of
failing on a busy CI box. The checks here are about MECHANISM -- the cap is
applied, and the UI thread's path does no rendering once warm.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import sys
import time

sys.path.insert(0, r"D:\R3EOverlay")

import speedo as S                                        # noqa: E402

fails = []


def check(ok, what, detail=""):
    print("  [%s] %s%s" % ("OK" if ok else "FAIL", what,
                           ("  " + str(detail)) if detail else ""))
    if not ok:
        fails.append(what)


if not S.HAVE_PIL:
    print("  PIL unavailable — skipped")
    raise SystemExit(0)


print("\n1. THE SUPERSAMPLE BUFFER IS CAPPED")
# Recorded rather than timed: _face is handed the buffer's edge length, which
# is the thing that actually decides the cost.
sizes = []
_face = S._face
S._face = lambda d, big, *a, **k: (sizes.append(big), _face(d, big, *a, **k))[1]
try:
    for dial in (168, 292, 389, 489, 800):
        S.render(dial, 0.5, 0.88, 0.98)
finally:
    S._face = _face
print("     buffers: %s (cap %d)" % (sizes, S.MAX_SS_PX))
check(max(sizes) <= S.MAX_SS_PX,
      "no render exceeds the cap", "largest %d" % max(sizes))
check(sizes[0] == 168 * S.SS,
      "a small dial is untouched by the cap — it still gets full SS",
      "%d" % sizes[0])
check(sizes[-1] == S.MAX_SS_PX,
      "a huge dial is clamped rather than rendered at SS")
# THE CAP MUST STILL ANTIALIAS. Below 2x supersampling the tick marks show
# stair-stepping, which is the whole reason the face is a PIL image and not
# tk primitives.
check(S.MAX_SS_PX / 489.0 >= 2.0,
      "the largest dial the overlay can ask for is still supersampled >=2x",
      "%.2fx" % (S.MAX_SS_PX / 489.0))


print("\n2. PREWARM RENDERS EVERY FACE THE CAR WILL NEED")
S.clear_cache()
S.prewarm(200, 0.88, 0.98, "#16100f")
t0 = time.time()
while time.time() - t0 < 60:
    with S._img_lock:
        n = len(S._img_cache)
    if n > S.BUCKETS:
        break
    time.sleep(0.05)
with S._img_lock:
    n = len(S._img_cache)
check(n == S.BUCKETS + 1,
      "every rev bucket is rendered ahead of time",
      "%d of %d" % (n, S.BUCKETS + 1))
# ...AND ONLY ONCE. draw_speedo calls prewarm on EVERY frame, so a second
# sweep per frame would be far worse than the problem it fixes.
_again = []
_flat = S._flat
S._flat = lambda *a, **k: (_again.append(a), _flat(*a, **k))[1]
try:
    for _ in range(20):
        S.prewarm(200, 0.88, 0.98, "#16100f")
    time.sleep(0.5)
finally:
    S._flat = _flat
check(not _again,
      "asking again for the same dial is a no-op, not another sweep",
      "%d extra renders" % len(_again))


print("\n3. THE UI THREAD RENDERS NOTHING ONCE WARM")
# This is the check the report is actually about. `photo` is the only thing
# draw_speedo calls, and on a warm cache it must not reach `render` for ANY
# rev -- that is what kept the dial with the engine.
try:
    import tkinter as tk
    _root = tk.Tk()
    _root.withdraw()
except Exception as ex:
    print("  no display (%s) — the rest is skipped" % type(ex).__name__)
    print("\n%s" % ("ALL OK" if not fails else "FAILED: %s" % fails))
    assert not fails
    raise SystemExit(0)


class Rendered(Exception):
    pass


_r = S.render
S.render = lambda *a, **k: (_ for _ in ()).throw(Rendered())
try:
    missed = []
    for b in range(S.BUCKETS + 1):
        try:
            S.photo(200, b / float(S.BUCKETS), 0.88, 0.98, "#16100f")
        except Rendered:
            missed.append(b)
finally:
    S.render = _r
check(not missed,
      "no rev, anywhere on the dial, makes the UI thread render",
      "missed %s" % missed[:8])

# ...AND A COLD ONE STILL DRAWS. The fallback matters: prewarm runs on a
# thread, so the first frame or two of a session can legitimately arrive
# before it has finished, and a dial that refused to draw then would be
# worse than a slow one.
S.clear_cache()
check(S.photo(120, 0.5, 0.88, 0.98, "#16100f") is not None,
      "a cold cache still produces a dial rather than nothing")


print("\n4. ONE CAR'S WORTH OF MEMORY, NOT EVERY CAR'S")
# Each car has its own shift point, so each is a fresh set of 73 faces.
# Without a bound, a long session in a lobby of twenty cars would hold
# twenty sets.
S.clear_cache()
S.prewarm(120, 0.80, 0.98, "#16100f")
time.sleep(0.4)
S.prewarm(120, 0.90, 0.98, "#16100f")      # a different car
t0 = time.time()
while time.time() - t0 < 60:
    with S._img_lock:
        keys = {k[2] for k in S._img_cache}
        n = len(S._img_cache)
    if n > S.BUCKETS:
        break
    time.sleep(0.05)
with S._img_lock:
    keys = {k[2] for k in S._img_cache}
check(keys == {0.9},
      "the previous car's faces are dropped when a new one starts",
      "shift points held: %s" % sorted(keys))
S.clear_cache()

print("\n%s" % ("ALL OK" if not fails else "FAILED: %s" % fails))
assert not fails
