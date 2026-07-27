"""THE OVERLAY MUST NOT PIN ITSELF TO RACEROOM'S LOADING SPLASH.

Reported with a screenshot: the settings button sitting in the corner of the
small red "Loading RaceRoom..." window, with no way back short of killing the
whole app.

That splash belongs to rrre64.exe exactly like the game window does, so the
old "any visible rrre64 window bigger than 200x200" rule accepted it and the
overlay locked its whole coordinate space to it. Everything then positions
itself relative to a 750x475 box in the middle of the desktop.

Measured from the screenshot the splash is roughly 750x475. RaceRoom does not
run below 1024x768, so a floor beneath that separates the two cleanly without
ever rejecting a real window — windowed play included.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import sys

sys.path.insert(0, r"D:\R3EOverlay")
from r3e_overlay import MIN_GAME_W, MIN_GAME_H            # noqa: E402


def accepted(w, h):
    """The size test find_game_rect applies to each rrre64.exe window."""
    return w >= MIN_GAME_W and h >= MIN_GAME_H


# ---- 1. the splash is rejected -----------------------------------------
# The measurement is off a screenshot, so check a spread around it rather than
# one exact number.
for w, h in ((750, 475), (800, 500), (640, 480), (860, 560)):
    assert not accepted(w, h), (
        "a %dx%d window would still be treated as the game — that is the "
        "loading splash, and the overlay would pin itself to it" % (w, h))
print("  splash-sized windows (up to 860x560) rejected: OK")

# ---- 2. every real game resolution is accepted -------------------------
# Including the smallest RaceRoom itself supports. Rejecting a real window
# would be a worse bug than the one being fixed: the overlay would simply
# never appear.
for w, h in ((1024, 768), (1280, 720), (1280, 1024), (1600, 900),
             (1920, 1080), (2560, 1440), (3440, 1440), (3840, 2160)):
    assert accepted(w, h), (
        "%dx%d is a real resolution and would be rejected — the overlay would "
        "never lock to the game at all" % (w, h))
print("  every real resolution accepted, down to 1024x768: OK")

# ---- 3. the floor sits BELOW what the game supports ---------------------
# If the threshold ever creeps above RaceRoom's own minimum, windowed play at
# that size silently stops working.
assert MIN_GAME_W < 1024 and MIN_GAME_H <= 768, (
    "the floor (%dx%d) has crept up to or past RaceRoom's own 1024x768 "
    "minimum — a legitimate window size would be rejected"
    % (MIN_GAME_W, MIN_GAME_H))
# ...and above the splash, or it does nothing at all
assert MIN_GAME_W > 750 and MIN_GAME_H > 475, (
    "the floor (%dx%d) no longer clears the measured splash size"
    % (MIN_GAME_W, MIN_GAME_H))
print("  floor %dx%d sits between the splash and RaceRoom's minimum: OK"
      % (MIN_GAME_W, MIN_GAME_H))

print("\nSPLASH-WINDOW CHECKS PASSED")
