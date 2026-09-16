# -*- coding: utf-8 -*-
"""THE BROADCAST LOGO MUST BE THE LOGO.

`_build_logo` takes the first *.png in the app folder that is not radio-card
art. Every scratch file this project writes is named with a leading underscore
-- `_transcript.log`, `_heard.json`, `_tts_debug.log`, `_speedo_preview.png` --
and underscore sorts BEFORE lowercase, so `_speedo_preview.png` beat
`racer-tv.png` and the overlay displayed a screenshot of the speedometer where
the logo belongs. It had been doing that since the file was first generated;
rendering more previews into the folder made it obvious rather than causing it.

Reported, live, in the first minute of the first real launch:

  *"the top right where the racertv logo is supposed to be is replaced by the
    helmet Menu"*

That was a preview PNG of the helmet designer, being shown as the logo.

One rule, the one the rest of the project already follows: a leading
underscore means "a working file, not the product's".
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import glob
import os
import sys

sys.path.insert(0, r"D:\R3EOverlay")

_DIR = r"D:\R3EOverlay"
fails = []


def check(ok, what, detail=""):
    print("  [%s] %s%s" % ("OK" if ok else "FAIL", what,
                           ("  " + str(detail)) if detail else ""))
    if not ok:
        fails.append(what)


def candidates():
    """The same list `_build_logo` builds, read from the source so this test
    cannot drift away from the code it is guarding."""
    src = open(os.path.join(_DIR, "r3e_overlay.py"), encoding="utf-8").read()
    assert 'startswith(("icon_", "_"))' in src, (
        "the logo glob no longer excludes underscore-prefixed working files")
    c = [os.path.join(_DIR, n) for n in ("logo.png", "logo.gif", "logo.ppm")]
    c += [p for p in sorted(glob.glob(os.path.join(_DIR, "*.png")))
          if not os.path.basename(p).startswith(("icon_", "_"))]
    c += [p for p in sorted(glob.glob(os.path.join(_DIR, "*.gif")))
          if not os.path.basename(p).startswith("_")]
    return [p for p in c if os.path.exists(p)]


print("\n1. THE FILE THE OVERLAY WOULD ACTUALLY SHOW")
c = candidates()
check(bool(c), "something is picked as the logo")
if c:
    first = os.path.basename(c[0])
    check(not first.startswith("_"),
          "the logo is not a working file", first)
    check(not first.startswith("icon_"),
          "the logo is not radio-card art", first)
    check(first in ("logo.png", "logo.gif", "logo.ppm", "racer-tv.png"),
          "the logo is the broadcast logo", first)


print("\n2. A STRAY SCREENSHOT CANNOT HIJACK IT")
# The exact failure, reproduced: drop a preview PNG in the folder and confirm
# it is skipped. Named to sort first, which is what made the original bite.
_probe = os.path.join(_DIR, "_aaa_probe_preview.png")
try:
    from PIL import Image
    Image.new("RGB", (8, 8), (255, 0, 255)).save(_probe)
    c2 = candidates()
    check(bool(c2) and os.path.basename(c2[0]) == os.path.basename(c[0]),
          "a preview PNG sorting first is ignored",
          os.path.basename(c2[0]) if c2 else "nothing")
finally:
    if os.path.exists(_probe):
        os.remove(_probe)


print("\n3. THE SHOT TOOLS DO NOT WRITE INTO THE APP FOLDER")
# Belt and braces: the glob now skips them, AND they no longer land where the
# glob looks. Either fix alone would do; both means a future tool that forgets
# the underscore convention still cannot break the logo.
for _t in ("designershot", "themeshot", "uishot", "speedoshot"):
    _p = os.path.join(_DIR, "tests", _t + ".py")
    if not os.path.exists(_p):
        continue
    _src = open(_p, encoding="utf-8").read()
    check("_previews" in _src,
          "%s writes into _previews/, not the app folder" % _t)

print("\n" + ("FAILED: %d" % len(fails) if fails else "ALL PASSED"))
sys.exit(1 if fails else 0)
