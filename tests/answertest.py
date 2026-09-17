# -*- coding: utf-8 -*-
"""A QUESTION THAT AIRED GETS ITS ANSWER.

Reported: "Brett sometimes still doesnt immediately respond after Miles asks a
question". The debug log from a real race showed it was not slowness. Three of
six questions were never answered at all, and every one died the same way:

    08:13:06 play START :: Score this field for me, Brett
    08:13:06 speak QUEUE persona=PUNDIT     <- the answer, rendering
    08:13:08 purge                          <- an interrupt lands
    08:13:13 render DROP-cut persona=PUNDIT :: Seven, with bonus points pending

`_purge` already refused to drop an answer whose question had aired -- but
only while it sat in a QUEUE. An answer the render worker had already picked
up carried the old epoch, and `_stale` killed it the moment rendering
finished. The protection and the check disagreed, and the check won.

Tested against `_stale` itself, so it needs no audio device and no timing.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import sys
import types

sys.path.insert(0, r"D:\R3EOverlay")

import tts as T                                           # noqa: E402

fails = []


def check(ok, what, detail=""):
    print("  [%s] %s%s" % ("OK" if ok else "FAIL", what,
                           ("  " + str(detail)) if detail else ""))
    if not ok:
        fails.append(what)


def pipeline(epoch=5, eng_epoch=5):
    return types.SimpleNamespace(_epoch=epoch, _eng_epoch=eng_epoch)


stale = T.Tts._stale
EXCHANGE, RADIO, BOOTH = -1, 0, 1

print("\n1. AN INTERRUPT (booth epoch moves, radio epoch does not)")
p = pipeline(epoch=6, eng_epoch=5)          # a job started at epoch 5
check(stale(p, "COMMENTATOR", 5, BOOTH),
      "loose booth chatter caught mid-render is still cut, as before")
check(not stale(p, "PUNDIT", 5, EXCHANGE),
      "an ANSWER to a question that aired survives, even mid-render")
check(not stale(p, "ENGINEER", 5, RADIO),
      "the engineer survives, as before")

print("\n2. A FULL STOP (both epochs move)")
p = pipeline(epoch=6, eng_epoch=6)
check(stale(p, "PUNDIT", 5, EXCHANGE),
      "a full stop still takes the answer -- nothing outlives a flush")
check(stale(p, "ENGINEER", 5, RADIO), "...and the engineer")

print("\n3. NOTHING HAPPENED")
p = pipeline(epoch=5, eng_epoch=5)
check(not any(stale(p, per, 5, pr) for per, pr in
              (("COMMENTATOR", BOOTH), ("PUNDIT", EXCHANGE),
               ("ENGINEER", RADIO))),
      "a job from the current epoch is never stale")

print("\n4. EVERY CALL SITE PASSES THE PRIORITY")
# The fix is only as good as its callers: a site that still calls
# _stale(persona, epoch) silently defaults to booth priority and reintroduces
# the bug. All three pipeline stages are checked.
src = open(T.__file__, encoding="utf-8").read()
calls = [ln.strip() for ln in src.splitlines()
         if "self._stale(" in ln and "def _stale" not in ln]
bare = [c for c in calls if c.count(",") < 2]
check(len(calls) >= 3, "found the render and play staleness checks",
      len(calls))
check(not bare, "none of them omits the priority", bare)

print("\n" + ("FAILED: %d" % len(fails) if fails else "ALL PASSED"))
sys.exit(1 if fails else 0)
