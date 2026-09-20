# -*- coding: utf-8 -*-
"""THE FLOOR RULE: nobody queues routine talk over a busy channel.

Asked for: "look at how factortv does its commentary and race cards flow with
the engineer and improve on it". FACTORtv's blend rests on one line in both
its booth and its engineer -- "never talk over the previous line unless this
is genuinely urgent". RacerTV's booth instead kept a line or two waiting at
all times, blind to three more rendering, and everything behind that pile
went stale. Measured side by side in a flow simulator (the real audio engine
with the network voice and the speaker faked), two rounds each, old code
against new:

    commentator lines wasted          6 -> 2      8 -> 2
    commentator worst chosen->heard   43s -> 19s  23s -> 16s

The simulator is too slow for the suite, so this file pins the MECHANICS the
improvement rests on. Nothing here sleeps and nothing here plays audio.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import queue
import sys
import threading

sys.path.insert(0, r"D:\R3EOverlay")

import tts as T                                           # noqa: E402

fails = []


def check(ok, what, detail=""):
    print("  [%s] %s%s" % ("OK" if ok else "FAIL", what,
                           ("  " + str(detail)) if detail else ""))
    if not ok:
        fails.append(what)


def engine():
    """A Tts with its queues and counters but NO threads: nothing renders or
    plays, so every check is about the bookkeeping alone."""
    t = object.__new__(T.Tts)
    t.gen_q, t.play_q = queue.PriorityQueue(), queue.PriorityQueue()
    t._speaking, t._speaking_persona = False, None
    t._inflight, t._inflight_lock = 0, threading.Lock()
    t._epoch = t._eng_epoch = 0
    t._answer_due = 0.0
    t._topics = {}
    t._seq = __import__("itertools").count()
    return t


def queued(t, persona, prio, text="x"):
    t._qput(t.play_q, persona, ("w.wav", None, text, persona, t._epoch,
                                None, None, prio), prio=prio)


print("\n1. BUSY MEANS PLAYING, WAITING, OR MID-RENDER")
t = engine()
check(not t.channel_busy(), "an idle engine is free")
t._inflight = 1
check(t.channel_busy(),
      "a line being RENDERED makes it busy (the blind spot that let the "
      "booth stack lines)")
t._inflight = 0
t._speaking = True
check(t.channel_busy(), "a line playing makes it busy")
t._speaking = False
queued(t, "COMMENTATOR", 1)
check(t.channel_busy(), "a line waiting makes it busy")

print("\n2. YIELDING THE FLOOR CLEARS CHATTER, KEEPS WHAT MATTERS")
t = engine()
queued(t, "COMMENTATOR", 1, "colour one")
queued(t, "ENGINEER", 0, "box this lap")
queued(t, "PUNDIT", -1, "brett's answer")
queued(t, "COMMENTATOR", 1, "colour two")
_calls = []
_real = getattr(T.winsound, "PlaySound", None) if T.winsound else None
if T.winsound:
    T.winsound.PlaySound = lambda *a, **k: _calls.append(a)
try:
    t.yield_floor()
finally:
    if T.winsound and _real is not None:
        T.winsound.PlaySound = _real
left = []
while not t.play_q.empty():
    left.append(t.play_q.get()[2][2])
check("box this lap" in left, "the engineer's waiting line survives")
check("brett's answer" in left, "an answer to a question already asked survives")
check("colour one" not in left and "colour two" not in left,
      "waiting booth chatter is cleared", left)
check(not _calls,
      "and the line already playing is NOT cut off mid-word (no SND_PURGE)")

print("\n3. THE BOOTH ASKS BEFORE IT TALKS")
src = open(r"D:\R3EOverlay\overlay_booth.py", encoding="utf-8").read()
check("free, ahead = self._channel_state()" in src,
      "the booth reads the channel before choosing a line")
check("busy = (self.tts is not None and not free" in src,
      "a routine line waits for a FREE channel, not a short queue")
check("if self.tts is not None and ahead >= 1:" in src,
      "an urgent call queues behind the playing line only, never a pile")
check("_yf = getattr(self.tts, \"yield_floor\", None)" in src,
      "a confirmed top-five pass clears the chatter ahead of it")

print("\n" + ("FAILED: %d" % len(fails) if fails else "ALL PASSED"))
sys.exit(1 if fails else 0)
