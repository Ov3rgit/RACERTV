"""CONCURRENT RENDERING MUST NOT REORDER A SINGLE WORD OF THE BROADCAST.

Why the pool exists: an edge-tts call was measured on this machine at ~1.9s for
a ONE-WORD line and ~2.0s for a 24-word one -- almost entirely fixed service
turnaround, with DNS at 22ms and TCP+TLS at 175ms, so there is nothing to shave
off a single line. Rendering one at a time therefore made a BURST cost the sum
of those turnarounds (3 lines = 7.1s serial vs 2.7s concurrent), and that
backlog is what put commentary seconds behind the move it described.

The danger the pool introduces is reordering: a short line finishing its render
first must not jump ahead of the line queued before it, or the booth starts
answering questions it hasn't asked yet. _gen_loop still pops gen_q alone and
stamps a ticket; _commit releases to play_q strictly in ticket order.

This drives the REAL Tts pipeline with the network render stubbed out (that is
the part under test -- ordering and bookkeeping, not Microsoft's servers), using
deliberately inverted render times so any order-blind implementation fails.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import sys
import time
import threading

sys.path.insert(0, r"D:\R3EOverlay")
import tts as T                                           # noqa: E402


def engine(delays, record):
    """A Tts whose render is replaced by a timed stub.

    `delays` maps text -> seconds that line takes to 'render'. Everything after
    the render (the ordered commit, the play queue) is the real code.
    """
    t = object.__new__(T.Tts)
    t.enabled = True
    t.engine = "stub"
    t.volume = 1.0
    t.gen_q = T.queue.PriorityQueue()
    t.play_q = T.queue.PriorityQueue(maxsize=64)
    t._seq = T.itertools.count()
    t._wav_i = 0
    t._job_q = T.queue.Queue()
    t._ticket = T.itertools.count()
    t._commit_next = 0
    t._commit_cv = threading.Condition()
    t._mp3_i = 0
    t._tmp_lock = threading.Lock()
    t._epoch = t._eng_epoch = 0
    t._topics = {}
    t._answer_due = 0.0
    t._speaking = False
    t._speaking_persona = None
    t.on_line_end = None

    def _stub_render(text, persona, voice, intensity=0, cue=None, epoch=0,
                     deadline=None, topic=None, prio=1):
        time.sleep(delays.get(text, 0.05))
        record.append(("rendered", text))
        return ((f"{text}.wav", cue, text, persona, epoch, deadline, topic,
                 prio), persona, prio)
    t._render = _stub_render

    threading.Thread(target=t._gen_loop, daemon=True).start()
    for _ in range(T._GEN_WORKERS):
        threading.Thread(target=t._gen_worker, daemon=True).start()
    return t


def drain(t, n, timeout=20.0):
    """Pop n jobs off play_q in the order the player would see them."""
    out = []
    end = time.time() + timeout
    while len(out) < n and time.time() < end:
        try:
            _p, _s, job = t.play_q.get(timeout=0.2)
        except Exception:
            continue
        if job is None:
            continue
        out.append(job[2])                       # text
    return out


# ---- 1. ORDER IS PRESERVED even when render times are inverted -----------
# "first" is slow, "third" is fast: an order-blind pool commits third first.
rec = []
delays = {"first": 0.60, "second": 0.30, "third": 0.05}
t = engine(delays, rec)
for txt in ("first", "second", "third"):
    t._qput(t.gen_q, "COMMENTATOR", (txt, "COMMENTATOR", "v", 0, None, 0,
                                     None, None, 1), prio=1)
played = drain(t, 3)
assert played == ["first", "second", "third"], (
    "concurrent rendering reordered the broadcast: played %r, expected the "
    "order they were queued in" % (played,))
print("  inverted render times still play in queue order: OK -> %r" % (played,))

# and prove the stub really did finish out of order, or the test proves nothing
rendered = [x[1] for x in rec]
assert rendered != ["first", "second", "third"], (
    "the renders completed in queue order anyway (%r) -- this run did not "
    "actually exercise reordering" % (rendered,))
print("  ...while the renders themselves finished out of order: OK -> %r"
      % (rendered,))

# ---- 2. IT IS ACTUALLY CONCURRENT (the whole point) ----------------------
rec = []
delays = {f"L{i}": 0.50 for i in range(3)}
t = engine(delays, rec)
t0 = time.time()
for i in range(3):
    t._qput(t.gen_q, "COMMENTATOR", (f"L{i}", "COMMENTATOR", "v", 0, None, 0,
                                     None, None, 1), prio=1)
played = drain(t, 3)
elapsed = time.time() - t0
assert played == ["L0", "L1", "L2"], "order broke under equal render times"
assert elapsed < 1.2, (
    "3 x 0.5s renders took %.2fs -- that is serial (1.5s+), so the pool is "
    "not rendering concurrently" % elapsed)
print("  3 x 0.5s renders finish in %.2fs (serial would be 1.5s+): OK"
      % elapsed)

# ---- 3. A DROPPED RENDER MUST NOT STALL THE LINES BEHIND IT --------------
# Every early return in _render yields None. If a ticket that renders nothing
# failed to commit, every later line would wait on it forever -- silent audio
# for the rest of the race.
rec = []
t = engine({}, rec)


def _drop_middle(text, persona, voice, intensity=0, cue=None, epoch=0,
                 deadline=None, topic=None, prio=1):
    time.sleep(0.05)
    if text == "dropped":
        return None                              # TTL expired / stale / no wav
    return ((f"{text}.wav", cue, text, persona, epoch, deadline, topic, prio),
            persona, prio)


t._render = _drop_middle
for txt in ("before", "dropped", "after"):
    t._qput(t.gen_q, "COMMENTATOR", (txt, "COMMENTATOR", "v", 0, None, 0,
                                     None, None, 1), prio=1)
played = drain(t, 2, timeout=8.0)
assert played == ["before", "after"], (
    "a dropped render stalled or reordered the queue behind it: got %r"
    % (played,))
print("  a dropped render commits its ticket and lets the rest through: OK")

# ---- 4. A RAISING RENDER MUST NOT STALL EITHER ---------------------------
rec = []
t = engine({}, rec)


def _boom(text, persona, voice, intensity=0, cue=None, epoch=0,
          deadline=None, topic=None, prio=1):
    time.sleep(0.05)
    if text == "boom":
        raise RuntimeError("render exploded")
    return ((f"{text}.wav", cue, text, persona, epoch, deadline, topic, prio),
            persona, prio)


t._render = _boom
for txt in ("ok1", "boom", "ok2"):
    t._qput(t.gen_q, "COMMENTATOR", (txt, "COMMENTATOR", "v", 0, None, 0,
                                     None, None, 1), prio=1)
played = drain(t, 2, timeout=8.0)
assert played == ["ok1", "ok2"], (
    "an exception in one render stalled the pipeline behind it: got %r"
    % (played,))
print("  a raising render still commits its ticket: OK")

# ---- 5. PRIORITY still decides ORDER, and it is decided ONCE -------------
# The engineer (prio 0) must still beat queued booth colour (prio 1). With a
# pool that is only true if the ordering is fixed at dispatch, not by whoever
# renders quickest.
rec = []
t = engine({"booth": 0.05, "eng": 0.40}, rec)
t._qput(t.gen_q, "COMMENTATOR", ("booth", "COMMENTATOR", "v", 0, None, 0,
                                 None, None, 1), prio=1)
t._qput(t.gen_q, "ENGINEER", ("eng", "ENGINEER", "v", 0, None, 0,
                              None, None, 0), prio=0)
time.sleep(0.02)
played = drain(t, 2, timeout=8.0)
assert played[0] == "eng", (
    "the engineer no longer outranks queued booth colour: %r" % (played,))
print("  engineer still pre-empts booth colour despite rendering slower: OK")

# ---- 6. the temp-file paths are per-render, not one shared file ----------
t = engine({}, [])
paths = set()
threads = [threading.Thread(target=lambda: paths.add(t._next_mp3()))
           for _ in range(32)]
[x.start() for x in threads]
[x.join() for x in threads]
assert len(paths) == 32, (
    "concurrent _next_mp3() handed out duplicate paths (%d unique of 32) -- "
    "two renders would overwrite each other's audio" % len(paths))
wavs = set()
threads = [threading.Thread(target=lambda: wavs.add(t._next_wav()))
           for _ in range(32)]
[x.start() for x in threads]
[x.join() for x in threads]
assert len(wavs) == 32, (
    "concurrent _next_wav() handed out duplicate paths (%d unique of 32) -- "
    "the file collision that causes the Windows default beep" % len(wavs))
print("  32 concurrent renders get 32 distinct mp3 and wav paths: OK")

print("\nGEN-POOL CHECKS PASSED")
