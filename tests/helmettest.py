# -*- coding: utf-8 -*-
"""ONE DRIVER, ONE HELMET, EVERYWHERE.

RacerTV shipped nine helmet PNGs and handed them out IN ORDER OF FIRST
SIGHTING. Three consequences, and in an online lobby all three are wrong:

  * it wraps at nine, so a twenty-car grid had duplicates guaranteed
  * it depends on arrival order, so the same opponent wore a different helmet
    in a different session
  * it is local, so you and he saw DIFFERENT helmets for the same driver

`helmet.py` renders a design from the driver's NAME instead. The name is the
only input and every machine in the lobby has it, so the same driver gets the
same helmet everywhere with no networking at all. RaceRoom is pure online
multiplayer and the people you race are usernames; a stable face for a
username is most of what makes a grid feel like people.

This file guards the three properties above, plus the two that keep the port
honest: user-drawn art still wins, and nothing here can take the overlay down.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import sys

sys.path.insert(0, r"D:\R3EOverlay")

import helmet as H                                        # noqa: E402

fails = []


def check(ok, what, detail=""):
    print("  [%s] %s%s" % ("OK" if ok else "FAIL", what,
                           ("  " + str(detail)) if detail else ""))
    if not ok:
        fails.append(what)


print("\n1. THE ART THE MODULE WAS MEASURED ON IS THE ART SHIPPED HERE")
# Every constant in helmet.py -- the number plate, the visor box, the shell
# anatomy -- was measured off one silhouette. The module is portable ONLY
# because RacerTV ships that same silhouette; if the art is ever replaced,
# this is the check that says so before anything looks subtly wrong.
_m = H._mask()
check(_m is not None, "the shell mask loads")
if _m is not None:
    check(_m.size == (256, 256), "and is the size the constants assume", _m.size)
    import glob
    _alphas = set()
    try:
        from PIL import Image
        for _p in glob.glob(_os.path.join(r"D:\R3EOverlay", "icon_helmet_*.png")):
            _alphas.add(Image.open(_p).convert("RGBA").split()[3].tobytes())
    except Exception:
        pass
    check(len(_alphas) == 1,
          "all nine shipped icons are ONE silhouette, as the module assumes",
          "%d distinct" % len(_alphas))


print("\n2. ONE DRIVER, ONE HELMET, FOR EVER")
check(H.generated("Dante_K") == H.generated("Dante_K"),
      "the same name always gives the same helmet")
check(H.generated("Alpha") != H.generated("Beta"),
      "and two different names give two different ones")
# THE CROSS-MACHINE CLAIM. It is only true if nothing but the name is read --
# no clock, no counter, no order of sighting. Generating a name in a DIFFERENT
# order must not change it, which is precisely what the old scheme got wrong.
_a = [H.generated(n) for n in ("one", "two", "three")]
_b = [H.generated(n) for n in ("three", "two", "one")][::-1]
check(_a == _b,
      "and the order names are first seen changes nothing "
      "(this is what makes two machines agree)")


print("\n3. A FULL LOBBY DOES NOT COLLIDE")
import random                                             # noqa: E402
import string                                             # noqa: E402
random.seed(11)
_names = ["".join(random.choice(string.ascii_letters + string.digits + "_")
                  for _ in range(random.randint(4, 14))) for _ in range(32)]
_specs = [tuple(sorted(H.generated(n).items())) for n in _names]
check(len(set(_specs)) == len(_names),
      "32 drivers get 32 distinct helmets (the old scheme capped at 9)",
      "%d distinct" % len(set(_specs)))
# AND THEY MUST BE TELLABLE APART AT CARD SIZE, not merely unequal as dicts.
# Two helmets differing only in a field nobody can see would pass the check
# above and fail the player.
_cols = [H.card_colour(H.generated(n)) for n in _names[:12]]
check(len(set(_cols)) >= 8,
      "and the card colours they drive are varied, not all one family",
      "%d distinct of 12" % len(set(_cols)))


print("\n4. EVERY GENERATED HELMET ACTUALLY RENDERS")
_bad = []
for _n in _names:
    try:
        if H.render(H.generated(_n), 28) is None:
            _bad.append(_n)
    except Exception as _ex:
        _bad.append("%s:%s" % (_n, type(_ex).__name__))
check(not _bad, "all 32 render at card size", _bad[:3])


# LABELLED, NOT ECHOED. An earlier version printed the name itself and died
# on the CJK case -- not in the helmet code, which handled it fine, but in
# the test's own print() on a cp1252 console. Worth remembering: RaceRoom is
# online and real usernames carry accents, CJK and emoji, so anything that
# ECHOES a driver name needs more care than anything that HASHES one.
for _label, _odd in (("empty", ""),
                     ("spaces", "   "),
                     ("CJK", "中文名"),
                     ("emoji", "🏎🔥"),
                     ("punctuation", "!!!"),
                     ("very long", "x" * 200),
                     ("non-breaking space", "P1 ")):
    try:
        _s = H.generated(_odd)
        _ = H.card_colour(_s)
        _ = H.render(_s, 28)
        check(True, "an odd name is handled: %s" % _label)
    except Exception as _ex:
        check(False, "an odd name raised: %s" % _label, type(_ex).__name__)
        check(False, "an odd name raised: %r" % _odd[:12], type(_ex).__name__)


print("\n6. USER-DRAWN ART STILL WINS")
# Someone who dropped their own icon_helmet_*.png next to the exe chose those
# on purpose. The generator must not overrule a decision.
_src = open(r"D:\R3EOverlay\r3e_overlay.py", encoding="utf-8").read()
check("avatars.helmet_variants()" in _src,
      "the variant path is still reachable in _color_for_name")
_i_gen = _src.index("helmet_mod.generated(name)")
_i_var = _src.index("vs = avatars.helmet_variants()", _i_gen)
check(_i_var > _i_gen,
      "...and sits AFTER the generator as the fallback it now is")

print("\n7. EVERY NAME ON A CARD CAN BE READ")
# FOUND BY LOOKING, NOT BY ASSERTING. A rendered lobby of twenty came out with
# four names effectively invisible -- a black shell and two navies straight
# from `card_colour` measure barely over 1:1 against the near-black card --
# and every check in section 3 passed regardless, because "is this a distinct
# colour" and "can you read this" are different questions.
#
# The helmet keeps its true colour; the TEXT is lifted. This is the guard that
# stops the generator quietly reintroducing an unreadable name.
from overlay_common import CARD_BG                        # noqa: E402
_dim = []
for _n in _names:
    _c = H.readable(H.card_colour(H.generated(_n)), CARD_BG)
    if H.contrast(_c, CARD_BG) < 4.0:
        _dim.append((_n[:10], _c, round(H.contrast(_c, CARD_BG), 2)))
check(not _dim, "all 32 driver names clear 4:1 against the card", _dim[:3])

# ...AND THE LIFT IS ONLY APPLIED WHERE IT IS NEEDED. A colour that already
# reads must come back untouched, or every driver drifts towards grey and the
# grid stops being colourful.
_bright = "#00a3a3"
check(H.readable(_bright, CARD_BG) == _bright,
      "a colour that already reads is left exactly alone")

# AND THE OVERLAY ACTUALLY DOES IT. The three checks above test the helper;
# this one tests that `_color_for_name` calls it.
check("helmet_mod.readable(helmet_mod.card_colour(spec)" in _src,
      "the card colour is passed through readable() before it is stored")

print("\n" + ("FAILED: %d" % len(fails) if fails else "ALL PASSED"))
sys.exit(1 if fails else 0)
