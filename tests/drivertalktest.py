# -*- coding: utf-8 -*-
"""THE DRIVER TALKS BACK.

Asked for directly: a back-and-forth between the race engineer and the
driver, and *"he must respond to objectives and completing or not completing
objectives"*.

Ported from FACTORtv's design rather than invented: the driver's half is TEXT
ONLY, a card a beat after the engineer's. Three rendered voices already work
and a fourth would fight them for the audio channel.

DETERMINISTIC. The reply is scheduled against a clock this file controls, and
the dice are pinned where a check depends on them, so nothing here can pass
by luck.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import random
import sys

sys.path.insert(0, r"D:\R3EOverlay")
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])

import overlay_radio as ORAD                              # noqa: E402
from lines import DRIVER_REPLIES, ENGINEER_LINES          # noqa: E402

fails = []


def check(ok, what, detail=""):
    print("  [%s] %s%s" % ("OK" if ok else "FAIL", what,
                           ("  " + str(detail)) if detail else ""))
    if not ok:
        fails.append(what)


def radio():
    o = headless_overlay(fake_tts=True)
    o.radio_msgs = []
    o._driver_replies = []
    o._eng_line_cat = {}
    o._driver_reply_t = -1e9
    o._my_name = "Dante_K"
    o.spoke = []
    rs = o.tts.speak
    o.tts.speak = lambda t, p, **k: (o.spoke.append((p, t)), rs(t, p, **k))[1]
    return o


def engineer_says(o, cat, at):
    """An engineer line for `cat` airs at time `at` (its card appears)."""
    line = ENGINEER_LINES[cat][0]
    o._eng_tag(line, cat)
    ORAD.time.time, _real = (lambda: at), ORAD.time.time
    try:
        o._air_bubble({"name": "RACE ENGINEER", "text": line, "color": "#fff",
                       "emotion": "neutral", "engineer": True})
    finally:
        ORAD.time.time = _real
    return line


def driver_cards(o):
    return [m for m in o.radio_msgs if m.get("driver")]


print("\n1. EVERY OBJECTIVE VERDICT IS ANSWERED")
for cat, pool in (("obj_set_defend", "drv_obj_set"),
                  ("obj_met_pass", "drv_obj_met"),
                  ("obj_miss_defend", "drv_obj_miss")):
    for trial in range(8):              # not luck: every single time
        o = radio()
        engineer_says(o, cat, 1000.0)
        o._driver_reply_drain(1000.0 + ORAD.DRIVER_REPLY_DELAY + 0.05)
        c = driver_cards(o)
        if not (len(c) == 1 and c[0]["text"] in DRIVER_REPLIES[pool]):
            break
    check(len(c) == 1 and c[0]["text"] in DRIVER_REPLIES[pool],
          "%s -> a %s reply, 8 times out of 8" % (cat, pool),
          c[0]["text"] if c else "no reply")


print("\n2. THE REPLY COMES AFTER THE ENGINEER, NEVER BEFORE")
o = radio()
engineer_says(o, "obj_met_pass", 1000.0)
o._driver_reply_drain(1000.0 + ORAD.DRIVER_REPLY_DELAY * 0.5)
check(not driver_cards(o), "nothing before the reply delay has passed")
o._driver_reply_drain(1000.0 + ORAD.DRIVER_REPLY_DELAY + 0.05)
check(len(driver_cards(o)) == 1, "the reply lands once it has")


print("\n3. THE DRIVER IS TEXT ONLY")
check(not any(p != "ENGINEER" and p != "COMMENTATOR" and p != "PUNDIT"
              for p, _ in o.spoke),
      "no voice was rendered for the driver", o.spoke)
check(driver_cards(o) and driver_cards(o)[0]["name"] == "Dante_K",
      "the card carries the player's own name")


print("\n4. A VERDICT BEATS CHATTER WHEN BOTH LAND TOGETHER")
o = radio()
random.seed(1)
engineer_says(o, "gained", 1000.0)
engineer_says(o, "obj_met_pass", 1000.0)
o._driver_reply_drain(1000.0 + ORAD.DRIVER_REPLY_DELAY + 0.05)
c = driver_cards(o)
check(len(c) == 1, "two engineer lines at once get ONE reply", len(c))
check(c and c[0]["text"] in DRIVER_REPLIES["drv_obj_met"],
      "...and it answers the objective, not the place", c[0]["text"] if c else "")


print("\n5. CHATTER RESPECTS THE COOLDOWN; VERDICTS DO NOT")
o = radio()
o._driver_reply_t = 1000.0                   # he just spoke
_real_random = ORAD.random.random
ORAD.random.random = lambda: 0.0             # the dice always say yes
try:
    engineer_says(o, "gained", 1001.0)
    o._driver_reply_drain(1001.0 + ORAD.DRIVER_REPLY_DELAY + 0.05)
    check(not driver_cards(o),
          "a routine call inside the cooldown gets no reply")
    engineer_says(o, "obj_miss_pass", 1002.0)
    o._driver_reply_drain(1002.0 + ORAD.DRIVER_REPLY_DELAY + 0.05)
    check(len(driver_cards(o)) == 1,
          "an objective verdict inside the cooldown is STILL answered")
finally:
    ORAD.random.random = _real_random


print("\n6. THE MAPPING COVERS WHAT THE ENGINEER ACTUALLY SAYS")
_obj = [k for k in ENGINEER_LINES if k.startswith(("obj_set_", "obj_met_",
                                                    "obj_miss_"))]
_miss = [k for k in _obj if ORAD.driver_reply_for(k)[1] < 1.0]
check(not _miss, "all %d objective verdict pools are answered every time"
      % len(_obj), _miss[:3])
_pools = {pool for _, pool, _ in ORAD.DRIVER_REPLY_POOL} | {
    ORAD.DRIVER_REPLY_DEFAULT[0]}
_absent = [p for p in _pools if not DRIVER_REPLIES.get(p)]
check(not _absent, "every pool the mapping names actually exists", _absent)
_braces = [t for k, v in DRIVER_REPLIES.items() if not k.startswith("_")
           for t in v if "{" in t]
check(not _braces, "no driver line has a placeholder that could go unfilled",
      _braces[:1])

print("\n" + ("FAILED: %d" % len(fails) if fails else "ALL PASSED"))
sys.exit(1 if fails else 0)
