# -*- coding: utf-8 -*-
"""THE HELMET DESIGNER, DRIVEN THE WAY A USER DRIVES IT.

Everyone on the grid gets a helmet generated from their name. Exactly one
person can CHOOSE theirs, and this is the page where they do it.

Fitted to RacerTV's menu rather than ported from FACTORtv's: this overlay is
click-through with POLLED clicks, so there is no modal and no keyboard -- the
designer is a second PAGE of the settings slab, built from spin rows with an
arrow either side of each value.

WHAT THIS FILE HOLDS.

  1. The fields spin, wrap, and persist.
  2. Editing actually CHANGES WHAT IS ON SCREEN. The colour and helmet stores
     are filled on a driver's first sighting and never revisited -- that is
     what makes them cheap -- so an edit that does not drop his entries leaves
     the old helmet on the card and looks like a broken menu.
  3. His choice beats the generator, and ONLY for him. Nobody else's design
     can reach this machine: RaceRoom's shared memory carries names, not
     liveries.
  4. Reset is a real answer, not an absence: it returns the helmet his NAME
     would have given him, which is what every other driver wears.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import sys

sys.path.insert(0, r"D:\R3EOverlay")
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])

import helmet as H                                        # noqa: E402

fails = []


def check(ok, what, detail=""):
    print("  [%s] %s%s" % ("OK" if ok else "FAIL", what,
                           ("  " + str(detail)) if detail else ""))
    if not ok:
        fails.append(what)


def designer(name="Dante_K"):
    o = headless_overlay(fake_tts=True)
    o._my_helmet = {}
    o._my_name = name
    o._menu_page = "main"
    return o


print("\n1. THE FIELDS SPIN, AND WRAP")
o = designer()
first = o._helmet_spec()["base"]
o._helmet_spin("base", 1)
second = o._helmet_spec()["base"]
check(first != second, "the shell colour moves when spun", "%s -> %s" % (first, second))
o._helmet_spin("base", -1)
check(o._helmet_spec()["base"] == first, "and comes back when spun the other way")

# WRAPPING MATTERS ON A TWO-ARROW CONTROL. There is no scrollbar and no way to
# jump; if the ends did not wrap, the last colour would be a dead end.
cols = [h for _n, h in H.PALETTE]
o = designer()
for _ in range(len(cols)):
    o._helmet_spin("base", 1)
check(o._helmet_spec()["base"] == first,
      "a full lap of the palette returns to the start (the ends wrap)")

# THE NUMBER INCLUDES "none", which is a value and not a missing one.
o = designer()
seen = set()
for _ in range(105):
    seen.add(o._helmet_spec().get("number"))
    o._helmet_spin("number", 1)
check(None in seen, "'no number' is reachable on the number row")
check(len([x for x in seen if x is not None]) >= 99,
      "and every race number from 0 to 99 is", len(seen))


print("\n2. AN EDIT CHANGES WHAT IS ON SCREEN")
# The regression this guards: `_dcolor`/`_dhelmet` are first-sighting caches.
o = designer()
o._color_for_name("Dante_K")               # sighted: helmet + colour cached
before = dict(o._dhelmet.get("Dante_K") or {})
check(bool(before), "his helmet is cached on first sighting")
o._helmet_spin("base", 3)
check("Dante_K" not in o._dhelmet,
      "editing drops his cached helmet, so the next card re-renders it")
o._color_for_name("Dante_K")
after = dict(o._dhelmet.get("Dante_K") or {})
check(before != after, "and the helmet on the card actually changed",
      "%s -> %s" % (before.get("base"), after.get("base")))


print("\n3. HIS CHOICE BEATS THE GENERATOR -- AND ONLY HIS")
o = designer()
o._helmet_save({"base": "#d4ff00", "accent": "#161616", "pattern": "blade",
                "number": 4, "ink": "#161616"})
o._color_for_name("Dante_K")
check(o._dhelmet["Dante_K"]["base"] == "#d4ff00",
      "the helmet he designed is the one he wears")
o._color_for_name("SomeOtherDriver")
check(o._dhelmet["SomeOtherDriver"] == H.generated("SomeOtherDriver"),
      "everyone else still gets the one generated from their name")
check(o._dhelmet["SomeOtherDriver"]["base"] != "#d4ff00",
      "...and nobody else inherits his design")


print("\n4. RESET GIVES BACK THE ONE HIS NAME WOULD HAVE")
o = designer()
o._helmet_save({"base": "#d4ff00", "pattern": "blade"})
o._helmet_reset()
check(o._my_helmet == {}, "reset clears the stored design")
o._color_for_name("Dante_K")
check(o._dhelmet["Dante_K"] == H.generated("Dante_K"),
      "and he is back to the helmet his name gives him")


print("\n5. SURPRISE ME PRODUCES SOMETHING WEARABLE")
# A random accent lands on a near-identical colour often enough to make an
# invisible pattern, which reads as the button being broken.
import random as _rnd                                     # noqa: E402
_rnd.seed(3)
_flat = []
for _ in range(40):
    o = designer()
    o._helmet_random()
    sp = o._helmet_spec()
    if H.contrast(sp["base"], sp["accent"]) <= 2.2:
        _flat.append((sp["base"], sp["accent"]))
    if H.render(sp, 28) is None:
        _flat.append(("render", "failed"))
check(not _flat, "40 random helmets all have a visible pattern", _flat[:2])


print("\n6. THE PAGE IS REACHABLE AND LEAVEABLE")
o = designer()
o._menu_open = True
o._menu_goto("helmet")
check(o._menu_page == "helmet", "the designer page opens")
o._menu_goto("main")
check(o._menu_page == "main", "and Back returns to the settings list")
o._menu_goto("helmet")
o._menu_flip()                             # close the whole menu
check(o._menu_page == "main",
      "closing the menu returns to the top, so it never re-opens mid-designer")

print("\n" + ("FAILED: %d" % len(fails) if fails else "ALL PASSED"))
sys.exit(1 if fails else 0)
