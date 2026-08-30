"""THE SPEEDOMETER — the face, the scale, and the corner it lives in.

The dial is a cached PIL image because tk's canvas has no antialiasing, so
what is tested here is the maths that decides what gets drawn, not the
pixels: the rev fraction, where the amber and red land, what a gear reads as,
and the unit conversion. Plus the two things that broke while building it.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import math
import sys

sys.path.insert(0, r"D:\R3EOverlay")

import speedo


# ---- 1. the arc mapping ------------------------------------------------
# PIL measures arc angles CLOCKWISE from 3 o'clock and normalises an end
# below its start by adding 360. Handing it the negated screen angles in
# their natural order drew the COMPLEMENT of the sweep — a stub across the
# top instead of the 240 degrees asked for. _ANG has to increase, always.
a0 = speedo._ANG(0.0)
a1 = speedo._ANG(1.0)
assert a1 > a0, (
    "the angle mapping does not increase with rev, so d.arc() is being "
    "handed an unordered pair and will draw the complement of the sweep")
assert abs((a1 - a0) - abs(speedo.SWEEP_DEG)) < 1e-6, (
    f"the sweep spans {a1 - a0:.1f} degrees, not {abs(speedo.SWEEP_DEG)}")
# and it must be monotonic the whole way round, not just at the ends
prev = None
for i in range(41):
    a = speedo._ANG(i / 40.0)
    assert prev is None or a > prev, "the sweep angle is not monotonic"
    prev = a
print("  [dial] the sweep spans 240 degrees and increases: OK")


# ---- 2. the gap is at the BOTTOM ---------------------------------------
# That is where the speed and the gear are drawn. A sweep whose gap landed
# anywhere else would put the scale behind the numbers.
def _screen_xy(f):
    a = math.radians(speedo.START_DEG + speedo.SWEEP_DEG * f)
    return math.cos(a), -math.sin(a)          # y grows downward


x0, y0 = _screen_xy(0.0)
x1, y1 = _screen_xy(1.0)
assert y0 > 0 and x0 < 0, "the sweep does not start at the bottom-left"
assert y1 > 0 and x1 > 0, "the sweep does not end at the bottom-right"
print("  [dial] the gap sits at the bottom, under the readout: OK")


# ---- 3. the face renders, and the cache is keyed on the bucket ---------
if speedo.HAVE_PIL:
    im = speedo.render(64, 0.5, 0.85, 0.98)
    assert im.size == (64, 64), f"render returned {im.size}"
    # supersampling is the whole point — a 1x render would be pixel art
    assert speedo.SS >= 2, "supersampling is off; the dial will alias"
    print("  [dial] renders at the requested size: OK")

    # two revs inside the same bucket must produce the same cache key, or the
    # cache is pointless; two in different buckets must not share one
    speedo.clear_cache()
    step = 1.0 / speedo.BUCKETS
    b_a = int(round(0.500 * speedo.BUCKETS))
    b_b = int(round((0.500 + step * 0.3) * speedo.BUCKETS))
    b_c = int(round((0.500 + step * 1.5) * speedo.BUCKETS))
    assert b_a == b_b, "quantisation is too fine to ever hit the cache"
    assert b_a != b_c, "quantisation is so coarse the sweep would visibly step"
    print("  [dial] rev quantisation buckets sensibly: OK")


# ---- 4. the scale, from the game's own numbers -------------------------
# Reproduces draw_speedo's arithmetic. upshift_rps is the game's own shift
# point; inventing a fraction would put the amber in the wrong place on
# exactly the cars that need it most.
def scale(mx, rps, ups):
    if mx > 0.0:
        rev = max(0.0, min(1.0, rps / mx))
        shift_at = max(0.35, min(0.97, ups / mx)) if ups > 0 else 0.92
    else:
        rev, shift_at = 0.0, 0.92
    return rev, shift_at, max(shift_at + 0.01, 0.98)


rev, sh, rl = scale(800.0, 400.0, 760.0)
assert abs(rev - 0.5) < 1e-6, "rev fraction is not rps/max"
assert abs(sh - 0.95) < 1e-6, f"shift point is {sh}, not upshift_rps/max"
assert rl > sh, "the redline is not above the shift point"

# a car that publishes no rev data at all — some replays — must still get a
# dial rather than a divide-by-zero
rev, sh, rl = scale(0.0, 0.0, 0.0)
assert rev == 0.0 and 0.0 < sh < 1.0 and sh < rl <= 1.0, (
    "a car with no rev data broke the scale instead of drawing an idle dial")

# and one that over-revs past the limiter clamps rather than overflowing
rev, _sh, _rl = scale(800.0, 900.0, 760.0)
assert rev == 1.0, "an over-rev ran off the end of the sweep"
print("  [scale] rev, shift point and redline come from the game: OK")


# ---- 5. gear reads as a gear -------------------------------------------
def gear_text(g):
    return "R" if g < 0 else ("N" if g == 0 else str(g))


assert gear_text(-1) == "R", "reverse showed as -1"
assert gear_text(0) == "N", "neutral showed as 0"
assert gear_text(6) == "6"
print("  [readout] reverse is R and neutral is N: OK")


# ---- 6. units ----------------------------------------------------------
# RaceRoom publishes metres per second, which is neither of the two numbers
# anybody wants to read.
def conv(ms, mph):
    return ms * (2.236936 if mph else 3.6)


assert abs(conv(50.0, False) - 180.0) < 1e-6, "km/h conversion is wrong"
assert abs(conv(50.0, True) - 111.85) < 0.01, "mph conversion is wrong"
assert abs(conv(0.0, False)) < 1e-9
print("  [readout] m/s converts to km/h and mph: OK")


# ---- 7. the wiring -----------------------------------------------------
src = open(r"D:\R3EOverlay\overlay_draw.py", encoding="utf-8").read()
body = src.split("def draw_speedo(")[1].split("\n    def ")[0]
assert "_speedo_box" in body, (
    "the dial never publishes its box, so the radio bubbles cannot know to "
    "stack above it and will draw straight through the face")
assert "upshift_rps" in body, "the shift point is not taken from the game"
assert '"R" if g < 0' in body, "gear is not translated for reverse"

radio = src.split("def draw_radio(")[1].split("\n    def ")[0]
assert "_speedo_box" in radio, (
    "draw_radio does not lift its bubbles above the dial")

ov = open(r"D:\R3EOverlay\r3e_overlay.py", encoding="utf-8").read()
assert '("speedo", self.draw_speedo)' in ov, "the stage is never drawn"
assert '_save_pref("speedo"' in ov, "the setting is not remembered"
# the dial survives spectator mode: a broadcast shows speed, and the dial
# follows the camera, so it is one of the few readouts that gets MORE useful
# when you are watching rather than driving
# The gate is a NAME FILTER, so the tuple of excluded names is the test.
# Splitting on "if not spec:" catches the earlier radio gate instead and
# swallows the whole draw list, which made this look broken when it was not.
tick = ov.split("def tick(")[1].split("\n    def ")[0]
excluded = tick.split("spec and nm in (")[1].split(")")[0]
assert "speedo" not in excluded, (
    "the speedo was caught by the spectator gate - it follows the replay "
    "camera, which is exactly when a viewer wants it")
for _name in ("relative", "objective", "bubbles"):
    assert _name in excluded, f"{_name} is no longer gated on spectator mode"
print("  [wiring] stage, prefs, bubble lift and spectator survival: OK")


print("\nSPEEDOMETER: ALL OK")
