"""
Team-radio text-to-speech for the RaceRoom overlay.

Primary engine: edge-tts (Microsoft's free online NEURAL voices — genuinely
human, real accents). Decoded with miniaudio, then run through a radio-FX chain
(band-pass + static + squelch click). Falls back to offline System.Speech
(SAPI) if edge-tts / internet isn't available, so it still works as a portable
mod. A TTS failure can never affect the overlay.
"""
import hashlib
import itertools
import math
import os
import queue
import random
import re
import shutil
import struct
import subprocess
import threading
import time
import json
import wave

try:
    import winsound
except Exception:
    winsound = None

try:
    import edge_tts
    import miniaudio
    import asyncio
    _HAVE_EDGE = True
    _EDGE_ERR = ""
except Exception as _ex:
    _HAVE_EDGE = False
    _EDGE_ERR = f"{type(_ex).__name__}: {_ex}"   # logged at INIT for diagnosis

# base dir: next to the exe when frozen (PyInstaller), next to this file in dev
# — assets (stings cache, worker script) and temp wavs must live somewhere
# persistent and writable, not the frozen bundle's extraction dir
import sys as _sys
if getattr(_sys, "frozen", False):
    _DIR = os.path.dirname(_sys.executable)
else:
    _DIR = os.path.dirname(os.path.abspath(__file__))
_LOG = os.path.join(_DIR, "_tts_debug.log")
# CLEAN TRANSCRIPT: every line that actually AIRS, in order, with its FULL text
# (the debug log truncates to 30 chars, which is useless for judging whether
# the writing repeats itself). One line per aired message: time, persona, text.
# This is the file to copy-paste to review a whole race for repetition.
_TRANSCRIPT = os.path.join(_DIR, "_transcript.log")


def _log(msg):
    try:
        import time as _t
        with open(_LOG, "a", encoding="utf-8") as f:
            f.write(f"{_t.strftime('%H:%M:%S')} {msg}\n")
    except Exception:
        pass


def _transcript(persona, text):
    try:
        import time as _t
        with open(_TRANSCRIPT, "a", encoding="utf-8") as f:
            f.write(f"{_t.strftime('%H:%M:%S')}  {persona:<11}  {text}\n")
    except Exception:
        pass


_WORKER = os.path.join(_DIR, "tts_worker.ps1")
_OUT = os.path.join(_DIR, "_tts_render.wav")
_MP3 = os.path.join(_DIR, "_tts_render.mp3")
_PLAY = os.path.join(_DIR, "_tts_play.wav")
_STING_DIR = os.path.join(_DIR, "stings")    # pre-rendered instant incident clips
# Concurrent edge-tts renders. 3 covers the burst the booth actually caps
# itself at (speak() allows 3-4 pending), without opening more sockets to the
# service than a busy moment can use.
_GEN_WORKERS = 3
_CREATE_NO_WINDOW = 0x08000000

# NAME-FREE incident reactions pre-rendered once to disk so they play instantly
# (no network synth). These are BRIDGING lines (~1.5s) on purpose: they react the
# instant it happens AND fill the ~1s it takes to render the named detail line
# that follows, so there's no dead-air gap. Delivered in the PUNDIT voice.
STING_LINES = {
    "alert": [
        "Oh, trouble — looks like someone's gone off!",
        "Oh, that's a mistake — somebody's run wide there!",
        "Trouble on track — looks like someone's off!",
        "Oh, here's some drama — somebody's gone off!",
        "Ooh, that's not good — someone's off the track!",
        "Hang on, hang on — looks like someone's gone off!",
        "Oh dear, somebody's run wide and off there!",
        "There's a moment — looks like someone's in trouble!",
        "Oh, big moment — somebody's off the track!",
        "Wait — looks like we've got someone off out there!",
        # a wider pool so a crash-happy field doesn't loop the same alert — with
        # the shuffle-bag below, every one airs before any repeats
        "Ooh — someone's lost the back end there!",
        "That's a big slide — and off into the run-off!",
        "A lock-up, and somebody's gone straight on!",
        "Whoa — a moment for somebody, right off the racing line!",
        "Someone's caught it wrong and slithered off!",
        "That's a spin — a car pointing the wrong way!",
        "Deep into the gravel for somebody there!",
        "A wobble, and someone's dropped it off the circuit!",
    ],
    # name-free LIGHTS-OUT call in the COMMENTATOR voice — fires the instant the
    # race goes green (the _racing edge) so there's NO edge-tts render latency on
    # the signature moment. The named follow-up ("…and {leader} leads them away!")
    # is queued straight after, WITHOUT its own interrupt, while it renders.
    # A TOP-FIVE PASS THAT HAS STUCK. Name-free for the same reason the
    # incident alert is: at the instant the move is confirmed, rendering a
    # line with the driver's name in it takes a second or more, and a pass
    # called a second late has already been followed by the next corner. The
    # clip lands on the moment; the named call follows it.
    #
    # These are deliberately NOT lap-one start calls or incident shouts. They
    # must all read correctly for a pass for P5 as much as for the lead, so
    # none of them says "the lead" -- the named line behind it does that.
    "overtake": [
        "And that's the move!",
        "He's done it!",
        "Through he goes!",
        "And that one sticks!",
        "Got him!",
        "There it is!",
        "What a move!",
        "And he makes it stick!",
    ],

    "lightsout": [
        "And it's lights out, and away we go!",
        "Lights out — and they're racing!",
        "It's lights out, and the race is on!",
        "And we are go, go, go — lights out!",
        "Lights out and away they go — green flag!",
        "And there's the lights — go, go, go!",
        "It's lights out and they are away!",
        "Lights out — and we're underway!",
    ],
    # name-free VICTORY sting in the COMMENTATOR voice — fires the instant the
    # leader takes the flag (zero render latency on the signature moment); the
    # named "…and {winner} takes victory!" line is queued straight after.
    "victory": [
        "And here comes the chequered flag!",
        "The chequered flag is out — and that's the race!",
        "Here's the chequered flag, and it's all over!",
        "The flag falls — and the race is run!",
        "And there's the chequered flag at the end of it all!",
        "Here comes the flag — and we have our winner!",
        "The chequered flag waves — what a race it's been!",
    ],
}
# which persona voice each sting group is pre-rendered in
STING_PERSONA = {"alert": "PUNDIT", "lightsout": "COMMENTATOR", "overtake": "COMMENTATOR",
                 "victory": "COMMENTATOR"}

# ---- neural voice cast (edge-tts) -------------------------------------------
ENGINEER_VOICE = "en-GB-ThomasNeural"             # your engineer: calm British male
NEURAL_VOICES = [
    # Rival drivers: foreign-accented English. These read the English radio
    # lines in their own accent, which is the flavour that landed. (The older
    # cast of Irish / Indian / South African ENGLISH tiers sounded off and is
    # deliberately not here — this list is continental-European only.)
    # Three voices across a full grid meant several drivers sounded identical;
    # the per-driver prosody offsets below break that up further.
    "de-DE-ConradNeural",     # German
    "es-ES-AlvaroNeural",     # Spanish
    "fr-FR-HenriNeural",      # French
    "it-IT-DiegoNeural",      # Italian
    "pt-BR-AntonioNeural",    # Brazilian
    "nl-NL-MaartenNeural",    # Dutch
    "pl-PL-MarekNeural",      # Polish
    "sv-SE-MattiasNeural",    # Swedish
    "cs-CZ-AntoninNeural",    # Czech
]
# Native-language radio (audio in the driver's own tongue, English subtitle on
# the bubble) is DORMANT: the mapping is empty so every rival speaks accented
# English. To re-enable for a voice, map it back to its NATIVE_RADIO key
# (e.g. "fr-FR-HenriNeural": "fr") — the pipeline downstream still supports it.
NATIVE_VOICE_LANG = {}
# the play-by-play race commentator + colour co-commentator (clean broadcast
# voices, NO radio FX — they're in the booth, not on a team radio)
# strongly-accented voices on purpose: a clean RP-English read is the easiest
# to clock as TTS, whereas natural regional accents carry prosody that masks it
COMMENTATOR_VOICE = "en-GB-RyanNeural"      # lead play-by-play (British)
PUNDIT_VOICE = "en-AU-WilliamNeural"        # colour/analysis man (Australian)
# NB this name is NOT in edge_tts.list_voices(), but the service accepts and
# renders it perfectly well (verified directly). Absence from that list does
# not mean a voice is broken — do not "fix" this one on that basis again.
CLEAN_PERSONAS = ("COMMENTATOR", "PUNDIT")

# how long a queued line stays AIRABLE (seconds). Play-by-play goes stale fast —
# "5 minutes remaining" heard after the flag breaks the illusion completely —
# while driver radio/engineer banter tolerates a longer wait. Checked when the
# line is RENDERED and again when it's PLAYED, not when it's queued. force=True
# (scripted finish wrap / crosstalk) is exempt: those sequences must complete.
TTL_BOOTH = 12.0     # COMMENTATOR / PUNDIT live calls & colour
TTL_RADIO = 22.0     # drivers + engineer

# per-persona speaking rate (edge-tts), keeps the natural neural cadence
PERSONA_RATE = {
    "HOTHEAD": "+16%", "COCKY": "+0%", "VETERAN": "-6%", "DRAMATIC": "+12%",
    "JOKER": "+4%", "ROOKIE": "+18%", "VILLAIN": "-8%", "ENGINEER": "+2%",
    "COMMENTATOR": "+9%", "PUNDIT": "+2%",
}

# ---- SAPI fallback voice colour (rate, pitch, deepen) -----------------------
PERSONA_VOICE = {
    "HOTHEAD": ("fast", "medium", 1.0), "COCKY": ("medium", "medium", 1.0),
    "VETERAN": ("medium", "low", 1.0), "DRAMATIC": ("fast", "high", 1.0),
    "JOKER": ("medium", "medium", 1.0), "ROOKIE": ("fast", "high", 1.0),
    "VILLAIN": ("slow", "low", 1.0), "ENGINEER": ("medium", "medium", 1.0),
}

NOISE = 0.012        # static floor — kept low so the voice stays clean
DRIVE = 1.03         # very light distortion (keep voice clear)
MASTER_VOL = 0.97    # base level
LOUDNESS = 1.31      # +31% makeup gain (was 1.25; +5% across the board)


def _soft(x):
    """Soft limiter: transparent up to ~0.8, then compresses toward 1.0 so the
    extra makeup gain reads as louder without nasty hard-clipping."""
    a = abs(x)
    if a <= 0.8:
        return x
    return math.copysign(0.8 + (1.0 - math.exp(-(a - 0.8) * 3.0)) * 0.199, x)


_VOL_FILE = os.path.join(_DIR, "_volume.json")


def _load_volume():
    """Master voice level from disk, 0.0-1.0 (default full)."""
    try:
        with open(_VOL_FILE, encoding="utf-8") as f:
            v = float(json.load(f).get("volume", 1.0))
        return max(0.0, min(VOL_MAX, v))
    except Exception:
        return 1.0


def save_volume(v):
    try:
        with open(_VOL_FILE, "w", encoding="utf-8") as f:
            json.dump({"volume": round(float(v), 3)}, f)
    except Exception:
        pass


def _seed_hash(seed):
    """Stable small hash of a driver name — same scheme already used to pick
    their voice, so a driver's whole vocal identity (voice + prosody offset)
    is consistent for as long as they are on track."""
    return sum((seed or "").encode("utf-8", "ignore"))


class _Cue:
    """Carries a caller's on_play AND on_drop through the pipeline in ONE
    payload slot.

    Deliberately not two separate tuple fields: _purge() tells gen jobs from
    play jobs by their LENGTH (9 vs 8), so widening either tuple would break
    it in a way nothing would catch. Keeping the arity identical means the
    queue plumbing is untouched.

    Exactly one of play()/drop() ever fires — whichever happens first — so a
    caller can rely on being told the line's fate precisely once.
    """
    __slots__ = ("play_cb", "drop_cb", "done")

    def __init__(self, play_cb=None, drop_cb=None):
        self.play_cb, self.drop_cb, self.done = play_cb, drop_cb, False

    def play(self, text, persona):
        if self.done:
            return
        self.done = True
        if self.play_cb:
            self.play_cb(text, persona)

    def drop(self):
        if self.done:
            return
        self.done = True
        if self.drop_cb:
            try:
                self.drop_cb()
            except Exception:
                pass


def _cue_drop(payload, is_gen):
    """Fire the drop callback on a purged queue payload."""
    try:
        c = payload[4] if is_gen else payload[1]
        if isinstance(c, _Cue):
            c.drop()
    except Exception:
        pass


# ----------------------------------------------------------------- wav helpers
def _read_wav(path):
    with wave.open(path, "rb") as w:
        rate, ch, sw, n = (w.getframerate(), w.getnchannels(),
                           w.getsampwidth(), w.getnframes())
        raw = w.readframes(n)
    if sw != 2:
        return rate, []
    data = struct.unpack("<%dh" % (len(raw) // 2), raw)
    if ch == 2:
        data = [(data[i] + data[i + 1]) * 0.5 for i in range(0, len(data) - 1, 2)]
    return rate, [s / 32768.0 for s in data]


# Master volume can exceed unity so quiet neural voices can be pushed above
# the game. Anything over 1.0 risks clipping, so boosted audio is SOFT
# limited rather than hard clamped — see _write_wav.
VOL_MAX = 1.3
_SOFT_KNEE = 0.82        # below this, boosted samples pass through untouched


def _soft_limit(x):
    """Smoothly tame peaks above the knee instead of squaring them off.

    A plain clamp turns every over-unity peak into a flat top, which is
    audible as crunch on exactly the loud, excited lines you boosted the
    volume to hear. This leaves everything under the knee alone and
    compresses the rest into the remaining headroom."""
    a = abs(x)
    if a <= _SOFT_KNEE:
        return x
    over = (a - _SOFT_KNEE) / (1.0 - _SOFT_KNEE)
    a = _SOFT_KNEE + (1.0 - _SOFT_KNEE) * math.tanh(over)
    return a if x >= 0 else -a


def _write_wav(path, rate, samples, gain=1.0):
    frames = bytearray()
    boost = gain > 1.0
    for s in samples:
        if gain != 1.0:
            s *= gain
            if boost:
                s = _soft_limit(s)
        frames += struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32767))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))


def _decode_mp3(path):
    dec = miniaudio.mp3_read_file_f32(path)
    s = list(dec.samples)
    if dec.nchannels == 2:
        s = [(s[i] + s[i + 1]) * 0.5 for i in range(0, len(s) - 1, 2)]
    return dec.sample_rate, s


# ------------------------------------------------------------ sound synthesis
def _click(rate, ms=80):
    n = int(rate * ms / 1000.0)
    out = [0.0] * n
    for i in range(n):
        t = i / n
        env = (t / 0.15) if t < 0.15 else max(0.0, 1.0 - (t - 0.15) / 0.85)
        out[i] = (random.uniform(-1, 1) * 0.6
                  + math.sin(2 * math.pi * 1650 * i / rate) * 0.3) * env
    return out


# ---- OBJECTIVE CHIMES ---------------------------------------------------
# UI sound for the objective card: one motif when a target is given, one when
# it is met, one when it is missed. NOT the "stings" above — those are
# pre-rendered VOICE clips. These are synthesised tones.
#
# TELEMETRY-BLIP style, not a melody. The first attempt used long pure sines
# and was rightly called "a clown car hoot": slow attack + long decay + a
# single sine partial IS a toy horn, whatever notes you play. What reads as
# race/sim UI instead is percussive and dry —
#   * SHORT notes (~60ms), not a third of a second each
#   * an instant attack with a tiny noise transient, so it TICKS rather than
#     swells — that's the "clickable" quality
#   * fast exponential decay and no tail
#   * odd harmonics (3rd/5th) for a squarer, more digital edge
# Told apart by contour, in the "duudup" shape asked for:
#   set   du-dup   two quick, low then high, unresolved  -> here's a job
#   met   du-du-dip three rising, last one bright        -> arrival
#   miss  dup-du   two falling, duller                   -> deflation
# Still deliberately not a harsh buzzer on miss: missing a target already
# stings, and an ugly noise on top is cheap.
# Chime loudness. These sit against speech that has been peak-normalised and
# driven hard, so a "polite" UI level is inaudible next to the engineer —
# reported as the cues being too quiet to register.
CHIME_LEVEL = 0.62

CHIME_NOTES = {
    "set":  [(784.00, 0.000, 0.055), (1174.66, 0.075, 0.075)],
    "met":  [(784.00, 0.000, 0.050), (1046.50, 0.068, 0.050),
             (1567.98, 0.136, 0.110)],
    "miss": [(698.46, 0.000, 0.060), (523.25, 0.080, 0.100)],
}


def _chime(rate, kind):
    """Render one objective chime as float samples."""
    notes = CHIME_NOTES.get(kind) or CHIME_NOTES["set"]
    total = max(st + dur for _f, st, dur in notes) + 0.02
    out = [0.0] * int(rate * total)
    for freq, start, dur in notes:
        n = int(rate * dur)
        off = int(rate * start)
        for i in range(n):
            t = i / n
            j = off + i
            if j >= len(out):
                break
            # near-instant attack (~1.5ms, just enough not to pop) then a fast
            # exponential decay — this is what makes it a blip, not a note
            atk = min(1.0, (i / rate) / 0.0015)
            env = atk * math.exp(-5.5 * t)
            ph = 2 * math.pi * freq * i / rate
            v = (math.sin(ph) + 0.30 * math.sin(3 * ph)
                 + 0.12 * math.sin(5 * ph))
            # tiny filtered noise tick on the leading edge = the "click"
            if i < rate * 0.004:
                v += random.uniform(-1, 1) * 0.35 * (1 - i / (rate * 0.004))
            out[j] += v * env * CHIME_LEVEL
    return [_soft(v) for v in out]


def _radioize(samples, rate, drive=None, noise=None, lo=220.0, hi=5200.0,
              shimmer=0.05):
    """Band-pass to the radio band + light distortion + static baked in. Kept
    fairly open so accents/clarity survive. The default preset is the DRIVER
    radio; the engineer gets a much gentler pass (see _render) — he's on a
    modern intercom, and the heavy chain was flattening the neural prosody
    that makes the voice sound human."""
    drive = DRIVE if drive is None else drive
    noise = NOISE if noise is None else noise
    out = [0.0] * len(samples)
    dt = 1.0 / rate
    a_lp = dt / (1.0 / (2 * math.pi * hi) + dt)
    rc_hp = 1.0 / (2 * math.pi * lo)
    a_hp = rc_hp / (rc_hp + dt)
    lp = prev_x = prev_hp = 0.0
    for i, x in enumerate(samples):
        lp += a_lp * (x - lp)
        hp = a_hp * (prev_hp + lp - prev_x)
        prev_x, prev_hp = lp, hp
        v = math.tanh(hp * drive)
        n = random.uniform(-1, 1)
        env = abs(v)
        # gentle AM shimmer + a low static floor that only sits UNDER the voice
        # (scaled by envelope) so silences stay quiet and speech stays clear
        v = v * (1.0 + n * shimmer) + n * noise * env
        out[i] = max(-1.0, min(1.0, v * 0.97))
    return out


# ----------------------------------------------------------------- the engine
class Tts:
    def __init__(self):
        try:
            open(_LOG, "w").close()                 # fresh log each launch
        except Exception:
            pass
        try:
            with open(_TRANSCRIPT, "w", encoding="utf-8") as _f:
                _f.write("# RacerTV transcript — every line as it aired, in "
                         "order. Copy-paste this to review a race for "
                         "repetition.\n")
        except Exception:
            pass
        # sweep temp render/play wavs left behind by a previous crash/kill so
        # the folder doesn't accumulate debris on users' machines
        try:
            import glob
            for f in (glob.glob(os.path.join(_DIR, "_tts_play*.wav"))
                      + [_OUT, _MP3]):
                try:
                    os.remove(f)
                except Exception:
                    pass
        except Exception:
            pass
        self.enabled = True
        # MASTER VOLUME for every RacerTV voice (0.0-1.0). Applied as sample
        # gain when the play wav is written, because winsound.PlaySound has no
        # level control of its own. Persisted by the overlay's settings.
        self.volume = _load_volume()
        self.engine = "edge" if _HAVE_EDGE else "sapi"
        # two-stage pipeline: the GENERATE thread renders the next line's audio
        # while the PLAY thread is still playing the current one, so there's no
        # dead air waiting on edge-tts network latency between lines.
        # PRIORITY queues: the ENGINEER is talking to YOU — his lines render and
        # play ahead of any waiting booth chatter (a saturated booth was starving
        # him past his TTL: launch calls and overtake acks silently vanished).
        # Everything else keeps strict FIFO via the sequence counter.
        self.gen_q = queue.PriorityQueue()
        self.play_q = queue.PriorityQueue(maxsize=6)
        self._seq = itertools.count()
        self._wav_i = 0
        # RENDER POOL. Measured on this machine: an edge-tts call costs ~1.9s
        # for a ONE-WORD line and ~2.0s for a 24-word one, so essentially all of
        # it is fixed per-request service turnaround, not synthesis — DNS is
        # 22ms and TCP+TLS 175ms, so it isn't local connection setup either and
        # there is nothing to shave off a single line. What it does mean is that
        # rendering lines one at a time made a burst cost the SUM of those
        # turnarounds: three queued lines took 7.1s serial vs 2.7s rendered
        # concurrently (2.6x), and that backlog is what put commentary seconds
        # behind the action it was describing.
        #
        # Order is preserved exactly. _gen_loop still pops gen_q alone, so the
        # priority/FIFO decision is made in one place as before; it just hands
        # each job to a worker with a ticket, and finished audio is committed to
        # play_q strictly in ticket order. The play sequence is therefore
        # identical to the single-worker pipeline — a short line that renders
        # faster can never overtake the line that was queued before it.
        self._job_q = queue.Queue()
        self._ticket = itertools.count()
        self._commit_next = 0
        self._commit_cv = threading.Condition()
        self._mp3_i = 0
        self._tmp_lock = threading.Lock()
        self._speaking = False     # True while a wav is actually playing (so the
                                   # booth knows when it's cutting someone off)
        self._speaking_persona = None  # WHO is currently playing (persona)
        self._epoch = 0            # bumped on interrupt/flush/stop; anything
                                   # rendered under an older epoch is discarded so
                                   # an incident truly CUTS IN instead of waiting
                                   # for in-flight/queued audio to finish first
        # LINES BEING RENDERED RIGHT NOW. They have left gen_q and have not
        # reached play_q, so _pending() cannot see them — and with three
        # renderers that is up to three lines, for two to six seconds, that
        # the booth believed did not exist. See channel_busy().
        self._inflight = 0
        self._inflight_lock = threading.Lock()
        self._eng_epoch = 0        # ENGINEER's own cutoff: only advances on a
                                   # FULL purge (stop/flush). A booth interrupt
                                   # keeps this behind _epoch so an engineer job
                                   # caught MID-RENDER (already popped from the
                                   # queue, so _purge can't re-stamp it) isn't
                                   # dropped as stale — his TTL still applies
        # SAPI fallback worker + voice list
        self.proc = None
        self.voices = _list_voices()
        self.names = [v[0] for v in self.voices]
        self._start_sapi()
        self._stings = {}          # (persona, group) -> [cached wav paths]
        self._sting_t = {}         # group -> when it last played (_STING_MIN_GAP)
        self._chime_cache = {}     # kind -> rendered objective-chime samples
        self._topics = {}          # topic -> pending count (dedup, see speak())
        self._answer_due = 0.0     # an exchange ANSWER is mid-render until this:
                                   # the play loop defers other jobs so nothing
                                   # (engineer included) wedges between a booth
                                   # question and its reply
        self.on_line_end = None    # optional hook(text, persona) fired when a
                                   # line FINISHES playing — the overlay uses it
                                   # to drop the caption in sync with the audio
        threading.Thread(target=self._gen_loop, daemon=True).start()
        for _ in range(_GEN_WORKERS):
            threading.Thread(target=self._gen_worker, daemon=True).start()
        threading.Thread(target=self._play_loop, daemon=True).start()
        threading.Thread(target=self._build_stings, daemon=True).start()
        _log(f"INIT engine={self.engine} have_edge={_HAVE_EDGE} "
             f"winsound={winsound is not None} voices={len(self.voices)}"
             + (f" edge_err={_EDGE_ERR}" if _EDGE_ERR else ""))

    def _purge(self, keep_engineer=False):
        """Epoch-bump and drain both queues (the interrupt mechanic). With
        keep_engineer, TEAM-RADIO jobs (engineer AND driver radio — any
        non-booth persona) are re-queued under the NEW epoch instead of being
        thrown away. A booth interrupt used to silently eat them: the engineer's
        launch calls and overtake acks first, and after that was fixed, driver
        radio still vanished — a busy race interrupts every few seconds, so
        queued driver voices never survived to air ("no radio voices at all").
        Only booth commentary is play-by-play and stale after a cut; radio
        lines still make sense a few seconds later (their TTL still applies)."""
        self._epoch += 1
        if not keep_engineer:
            # A FULL purge really does take everything, so there is no longer
            # an answer to wait for. An INTERRUPT keeps exchange replies now
            # (see below), so clearing the hold here would let other lines
            # wedge into the gap the hold exists to protect.
            self._answer_due = 0.0
            self._eng_epoch = self._epoch
        kept = []
        for q in (self.gen_q, self.play_q):
            try:
                while True:
                    _prio, _seq, payload = q.get_nowait()
                    if payload is None:
                        continue
                    per = payload[1 if len(payload) == 9 else 3]
                    # AN AIRED QUESTION MUST GET ITS ANSWER. prio < 0 is an
                    # exchange reply, queued from the moment its question
                    # actually started playing — so by the time it exists, the
                    # viewer has already heard "what do you make of that,
                    # Brett?" out loud. Dropping it here left the question
                    # hanging and the pundit apparently ignoring his co-host: a
                    # transcript shows two questions whose next pundit line was
                    # an incident call, and one that went 72 seconds before he
                    # spoke again, by which point he answered a LATER question.
                    # Incidents are frequent, and a booth interrupt is exactly
                    # when this used to happen. A full purge (stop/flush) still
                    # takes everything; this only survives an interrupt.
                    if keep_engineer and (per not in CLEAN_PERSONAS
                                          or payload[-1] < 0):
                        kept.append((q, per, payload))
                    else:
                        _log(f"purge DROP persona={per}")
                        _cue_drop(payload, len(payload) == 9)
            except Exception:
                pass
        self._topics.clear()               # purged lines can't hold their topic
        for q, per, payload in kept:
            lst = list(payload)
            # gen jobs are 9-tuples (epoch at [5]), play jobs 8-tuples ([4]);
            # stamp the new epoch so the survivor isn't dropped as stale
            lst[5 if len(lst) == 9 else 4] = self._epoch
            # KEEP THE PRIORITY. _qput recomputes it from the persona when it
            # isn't given one, which would demote a surviving exchange reply
            # from -1 to 1 and bury it behind the very commentary it is meant
            # to pre-empt — the answer would survive the purge only to arrive
            # far too late to belong to its question.
            self._qput(q, per, tuple(lst), prio=lst[-1])

    def _stale(self, persona, epoch, prio=1):
        """True if a pipeline job was superseded by an interrupt. Team radio
        (engineer + driver voices) is judged against the radio epoch, which
        booth interrupts don't advance — otherwise a radio job caught
        mid-render is silently cut.

        AN EXCHANGE ANSWER (prio < 0) IS JUDGED THE SAME WAY. `_purge` already
        refuses to drop an answer whose question has aired ("AN AIRED QUESTION
        MUST GET ITS ANSWER") — but only while it sits in a queue. An answer
        already pulled out by the render worker carries the OLD epoch, and this
        check then killed it the instant it finished rendering. The debug log
        shows it exactly: "Score this field for me, Brett" plays at 08:13:06,
        its answer starts rendering the same second, an overtake sting
        interrupts at 08:13:08, and at 08:13:13 `render DROP-cut PUNDIT ::
        Seven, with bonus points pending`. Three of six questions in that race
        went unanswered this way. The queue and the renderer now agree: only a
        FULL stop (which advances the radio epoch too) can take an answer.
        """
        if prio < 0 or persona not in CLEAN_PERSONAS:
            return epoch < self._eng_epoch
        return epoch < self._epoch

    def _qput(self, q, persona, payload, prio=None):
        """Queue a pipeline job by priority class: -1 = an atomic booth
        exchange follow-up (the pundit's answer / the lead's ack — nothing may
        wedge between a question and its answer, not even the engineer),
        0 = ENGINEER (talking to YOU, beats loose booth colour), 1 = everything
        else. The sequence counter keeps FIFO order within each class."""
        if prio is None:
            prio = 0 if persona == "ENGINEER" else 1
        if prio < 0 and q is self.play_q:
            self._answer_due = 0.0     # the awaited answer is ready to air
        q.put((prio, next(self._seq), payload))

    def expect_answer(self, within=8.0):
        """A booth exchange answer is being rendered: hold every prio>=0 job
        at the play stage until it lands (or the window expires). Priority
        alone couldn't do this — the engineer's ALREADY-rendered line was
        popped the instant the question's audio ended, while the answer was
        still seconds away in edge-tts ('question -> engineer gap call ->
        answer' broke the conversation)."""
        self._answer_due = time.time() + within

    def _next_wav(self):
        # plenty of unique names so a force-queued burst can never overwrite a
        # file that's still waiting to play (that collision = the Windows beep)
        # LOCKED: several render workers call this at once now, and an
        # unsynchronised read-modify-write could hand two of them the same name
        # — the exact file collision this counter exists to prevent.
        with self._tmp_lock:
            self._wav_i = (self._wav_i + 1) % 64
            return os.path.join(_DIR, f"_tts_play{self._wav_i}.wav")

    def _next_mp3(self):
        """A private mp3 scratch path per render. The module-level _MP3 was a
        SINGLE shared file, so two concurrent renders would overwrite each
        other's audio mid-download and both decode garbage."""
        with self._tmp_lock:
            self._mp3_i = (self._mp3_i + 1) % 64
            return os.path.join(_DIR, f"_tts_render{self._mp3_i}.mp3")

    def _pending(self):
        return self.gen_q.qsize() + self.play_q.qsize()

    def speaking(self):
        """True if a line is actually being played right now."""
        return self._speaking

    def _inflight_bump(self, d):
        """Count a line into or out of the renderers.

        NEVER RAISES, because it runs inside the render DISPATCHER: an
        exception there kills that thread silently and nothing ever plays
        again. It did exactly that the first time, in genpooltest, which builds
        the engine without __init__ and so had no lock — "played []". The
        running app always has the lock; this makes that a convenience rather
        than a condition of the broadcast staying on air.
        """
        try:
            lock = getattr(self, "_inflight_lock", None)
            if lock is None:
                lock = self._inflight_lock = threading.Lock()
            with lock:
                self._inflight = max(0, getattr(self, "_inflight", 0) + d)
        except Exception:
            pass

    def channel_busy(self):
        """Is anything playing, waiting, or being rendered?

        THE QUESTION FACTORtv's BOOTH ASKS BEFORE EVERY ROUTINE LINE, and the
        reason its blend works: "never talk over the previous line unless this
        is genuinely urgent". A line chosen while the channel is busy waits,
        and waiting is where lines go stale and the engineer gets buried. A
        line chosen when the channel is free airs one render later, with the
        race still as it described it.

        Wider than FACTORtv's `speaking`, because this engine renders three
        lines at once: a line mid-render is neither playing nor queued, and a
        check that missed it let the booth stack new lines on top.
        """
        return bool(self._speaking or self._pending() > 0
                    or getattr(self, "_inflight", 0) > 0)

    def speaking_persona(self):
        """Which persona is playing right now (or None) — so an interrupting
        incident only apologises when it's actually cutting the LEAD off."""
        return self._speaking_persona if self._speaking else None

    def native_lang(self, persona, seed):
        """If the rival voice assigned to this driver is a tier-C NATIVE-language
        voice, return its NATIVE_RADIO key (e.g. 'fr'); else None. Deterministic
        per driver, since the voice is hash-assigned by name."""
        if self.engine != "edge":
            return None
        return NATIVE_VOICE_LANG.get(self._voice_for(persona, seed))

    # ---- pre-rendered instant incident stings -------------------------------
    def _build_stings(self):
        """Render the name-free incident stings ONCE to a disk cache (keyed by
        voice+text, so a voice change re-renders automatically). Runs on a daemon
        thread at startup; incidents before it finishes simply skip the sting."""
        if self.engine != "edge" or not _HAVE_EDGE:
            return
        try:
            os.makedirs(_STING_DIR, exist_ok=True)
        except Exception:
            return
        for group, lines in STING_LINES.items():
            persona = STING_PERSONA.get(group, "PUNDIT")
            voice = self._voice_for(persona, persona)
            clips = []
            for txt in lines:
                h = hashlib.md5(f"{voice}|{txt}".encode("utf-8")).hexdigest()[:10]
                p = os.path.join(_STING_DIR, f"{group}_{h}.wav")
                if not os.path.exists(p):
                    try:
                        self._render_sting(txt, voice, p, persona)
                    except Exception as ex:
                        _log(f"sting build ERR {type(ex).__name__}: {ex}")
                        continue
                if os.path.exists(p):
                    clips.append((p, txt))        # keep text for the caption
            if clips:
                self._stings[(persona, group)] = clips
        _log(f"stings ready: {sum(len(v) for v in self._stings.values())} clips")

    def _sting_choose(self, group, clips):
        """Deal a sting via an ANTI-REPEAT SHUFFLE-BAG: every clip in the group
        airs once before any repeats. Pure random.choice gave 'someone's off the
        track!' four times in one race; even avoid-the-last scattered repeats
        across a crash-happy field. Returns (src_path, caption_text)."""
        if not hasattr(self, "_sting_last"):
            self._sting_last = {}
        if not hasattr(self, "_sting_bag"):
            self._sting_bag = {}
        bag = self._sting_bag.get(group)
        pool = [c for c in clips if c[0] in bag] if bag else []
        if not pool:                        # bag empty/exhausted -> refill it
            last = self._sting_last.get(group)
            pool = [c for c in clips if c[0] != last] or clips
            self._sting_bag[group] = {c[0] for c in clips}
        src, text = random.choice(pool)
        self._sting_bag[group].discard(src)
        self._sting_last[group] = src
        return src, text

    def _render_sting(self, text, voice, outpath, persona="PUNDIT"):
        """Synthesize one sting and write the FINAL mixed wav (same processing a
        normal booth line gets, so its loudness matches), straight to the cache."""
        res = self._gen_edge(text, persona, voice, 1)
        srate, samples = res[0], res[1]            # single clause never 'builds'
        if not samples:
            return
        peak = max((abs(x) for x in samples), default=0.0) or 1.0
        g = min(4.0, 0.97 / peak) * MASTER_VOL * LOUDNESS
        mixed = [_soft(x * g) for x in samples]
        _write_wav(outpath, srate, mixed)

    # minimum seconds between two stings of the same group. Only the incident
    # ALERT is limited: it is the name-free bridging line ("someone's gone
    # off!"), it fires from two independent paths (an off-track report and a
    # yellow flag) that had no shared cooldown, and a busy AI race triggers
    # both within seconds of each other. A transcript showed two of these four
    # seconds apart with no named follow-up between them, and fifteen across
    # one race — by far the most repeated thing in the broadcast. The NAMED
    # line still airs; only the redundant generic bridge in front of it is
    # dropped. lightsout / victory are one-shot signature moments: never gated.
    # "overtake" gets a SHORT gap, not the incident's twelve seconds. Two
    # top-five passes in one corner deserve two named calls, but two
    # identical shouts one second apart sound like a stuck record -- the
    # second pass gets its named line without a second sting.
    _STING_MIN_GAP = {"alert": 12.0, "overtake": 4.0}

    def sting(self, group="alert", persona="PUNDIT", on_play=None, cut=True):
        """Play a pre-rendered incident sting RIGHT NOW (no synth wait). Cuts the
        current audio (epoch bump + purge) and jumps the cached clip to the front
        of the play queue. `on_play(text, persona)` fires the instant it starts so
        the SUBTITLE shows in sync. Returns True if a sting played, False if none
        are ready yet (caller then falls back to a normal interrupt+render). The
        named detail line should be queued straight after, WITHOUT its own
        interrupt (that would purge this sting)."""
        if not self.enabled:
            return False
        gap = self._STING_MIN_GAP.get(group)
        if gap is not None:
            last = self._sting_t.get(group, -1e9)
            if time.time() - last < gap:
                _log(f"sting SKIP-recent group={group}")
                return False
        clips = self._stings.get((persona, group))
        if not clips:
            return False
        src, text = self._sting_choose(group, clips)
        if not os.path.exists(src):
            return False
        # cut=False: A PASS IS NOT AN INCIDENT. The incident alert cuts the
        # booth mid-word because a car in the wall is an emergency. An overtake
        # sting did the same, and passes near the front happen every few
        # seconds: in one race it cut three of Brett's six answers dead and
        # stranded the engineer's track-limits warnings. It now queues like the
        # objective chime (see `chime`) -- next in line, nobody interrupted.
        if cut:
            self._purge(keep_engineer=True)    # booth cut, engineer lines survive
            if winsound:
                try:
                    winsound.PlaySound(None, winsound.SND_PURGE)
                except Exception:
                    pass
        try:
            dst = self._next_wav()                 # copy so play_loop can delete it
            if self.volume >= 0.999:
                shutil.copyfile(src, dst)
            else:
                # the sting CACHE is rendered once at full level, so the
                # user's volume has to be applied to this copy or stings
                # would always play at 100% while everything else scaled
                _rate, _smp = _read_wav(src)
                if not _smp:
                    shutil.copyfile(src, dst)
                else:
                    _write_wav(dst, _rate, _smp, gain=self.volume)
        except Exception:
            return False
        # stamp only once it is genuinely going to play — a sting that bailed
        # out above must not start the cooldown for one that would have worked
        self._sting_t[group] = time.time()
        # A CUTTING sting jumps everything (prio -1). A non-cutting one queues
        # at prio 0, which `expect_answer` holds back: while Brett is answering
        # a question, a pass waits for him to finish instead of landing in the
        # gap between question and answer. Q, A, "What a move!" -- in that
        # order.
        _sp = -1 if cut else 0
        self._qput(self.play_q, "ENGINEER",       # sting jumps any queue
                   (dst, _Cue(on_play), text, persona, self._epoch, None,
                    None, _sp), prio=_sp)
        return True

    def chime(self, kind):
        """Play the objective chime for `kind` ("set" / "met" / "miss").

        Jumps the queue (prio -1) like a sting, but does NOT purge: cutting the
        booth mid-word to play a UI sound would be worse than waiting a beat,
        and the engineer's line is queued right behind this — chime then
        verdict is the order you want anyway. Rendered once on first use and
        cached; the file is rewritten per call only so the user's current
        volume applies. Silent (and harmless) if audio is off."""
        if not self.enabled:
            return False
        try:
            samples = self._chime_cache.get(kind)
            if samples is None:
                samples = _chime(24000, kind)
                self._chime_cache[kind] = samples
            dst = self._next_wav()
            _write_wav(dst, 24000, samples, gain=self.volume)
        except Exception as ex:
            _log(f"chime ERR {type(ex).__name__}: {ex}")
            return False
        # persona ENGINEER so _purge spares it: the chime belongs to the same
        # private conversation as the line it introduces
        self._qput(self.play_q, "ENGINEER",
                   (dst, _Cue(None), "", "CHIME", self._epoch, None, None, -1),
                   prio=-1)
        _log(f"chime {kind}")
        return True

    # ---- voice selection ----
    def _voice_for(self, persona, seed):
        if self.engine == "edge":
            if persona == "ENGINEER":
                return ENGINEER_VOICE
            if persona == "COMMENTATOR":
                return COMMENTATOR_VOICE
            if persona == "PUNDIT":
                return PUNDIT_VOICE
            idx = sum((seed or persona).encode("utf-8", "ignore")) % len(NEURAL_VOICES)
            return NEURAL_VOICES[idx]
        # sapi
        if persona == "ENGINEER" or not self.names:
            male_en = [n for n, c in self.voices if c.lower().startswith("en")
                       and any(x in n for x in ("David", "Mark", "George"))]
            en = [n for n, c in self.voices if c.lower().startswith("en")]
            return (male_en or en or self.names or [""])[0]
        idx = sum((seed or persona).encode("utf-8", "ignore")) % len(self.names)
        return self.names[idx]

    def speak(self, text, persona="ENGINEER", seed="", intensity=0, on_play=None,
              force=False, urgent=False, ttl=None, topic=None, exchange=False,
              on_drop=None):
        """`on_drop` fires if the line will NEVER sound (queue too busy, TTL
        expired, interrupted, render failed). Callers that put something on
        screen with the audio use it to react immediately rather than waiting
        out a fixed timeout."""
        def _dropped():
            if on_drop:
                try:
                    on_drop()
                except Exception:
                    pass
        if not self.enabled or not text:
            _log(f"speak SKIP enabled={self.enabled} text={bool(text)}")
            _dropped()
            return
        # keep the booth CURRENT: commentary is play-by-play, so a line that
        # can't be spoken promptly is stale (you hear "takes the lead" seconds
        # after the move). Drop surplus commentary rather than let a backlog
        # build. `urgent` events get a little more headroom but are STILL capped
        # (otherwise a busy race buries the booth seconds behind the action).
        # `force` is only for scripted sequences (finish wrap / crosstalk reply)
        # that must complete intact.
        if not force and persona in CLEAN_PERSONAS:
            # one slot more headroom than before ("we need a bit more
            # commentary") — the stale-number risk this used to carry is now
            # handled by the short TTL on any line that quotes a figure
            cap = 4 if urgent else 3
            if self._pending() >= cap:
                _log(f"speak DROP-busy persona={persona} urgent={urgent} "
                     f"pending={self._pending()}")
                _dropped()
                return
        # topic dedup: only one line per topic may be pending at a time, so a
        # busy moment can't stack near-identical calls (two winner lines, two
        # "gap closing" reads) that then air back to back
        if topic and self._topics.get(topic, 0) > 0:
            _log(f"speak DROP-dupe topic={topic} :: {text[:40]}")
            _dropped()
            return
        if ttl is None and not force:
            ttl = TTL_BOOTH if persona in CLEAN_PERSONAS else TTL_RADIO
        deadline = (time.time() + ttl) if ttl else None
        if topic:
            self._topics[topic] = self._topics.get(topic, 0) + 1
        # priority: -1 = atomic booth exchange reply; 0 = ALL TEAM RADIO
        # (engineer AND rival drivers — the immersive "on the radio" layer that
        # should be heard, so it jumps ahead of loose booth colour); 1 = booth
        # play-by-play/colour. Team radio is rate-limited upstream, so giving
        # it priority can't flood the booth — it just stops driver voices from
        # being perpetually starved behind commentary.
        prio = -1 if exchange else (1 if persona in CLEAN_PERSONAS else 0)
        self._qput(self.gen_q, persona,
                   (text, persona, self._voice_for(persona, seed), intensity,
                    _Cue(on_play, on_drop), self._epoch, deadline, topic,
                    prio), prio=prio)
        _log(f"speak QUEUE persona={persona} i={intensity} pending={self._pending()} "
             f":: {text[:40]}")

    def _topic_done(self, topic):
        if topic and topic in self._topics:
            self._topics[topic] -= 1
            if self._topics[topic] <= 0:
                del self._topics[topic]

    def _gen_loop(self):
        """DISPATCHER. Pops gen_q in priority/FIFO order exactly as before and
        hands each job to a render worker with a ticket. Keeping the pop in one
        thread is what makes the pool safe: the ordering decision is still made
        in a single place, and the ticket freezes it, so concurrent rendering
        can reorder nothing (see _commit)."""
        while True:
            _prio, _seq, item = self.gen_q.get()
            if item is None:
                # one sentinel per worker, each with its own ticket, so every
                # worker wakes AND the commit sequence stays gap-free
                for _ in range(_GEN_WORKERS):
                    self._job_q.put((next(self._ticket), None))
                break
            self._inflight_bump(1)
            self._job_q.put((next(self._ticket), item))

    def _gen_worker(self):
        """Render audio to a wav file. Several of these run at once so a burst
        of events costs one service turnaround instead of one per line; the
        finished audio is still committed to the play queue in ticket order."""
        while True:
            ticket, item = self._job_q.get()
            if item is None:
                # shutdown: release our ticket so no worker waits on it forever
                self._commit(ticket, None)
                break
            job = None
            try:
                job = self._render(*item)
            except Exception as ex:
                _log(f"gen ERROR {type(ex).__name__}: {ex}")
            finally:
                # ALWAYS commit, even on a drop or an exception. A ticket that
                # never commits would stall every later line permanently.
                self._commit(ticket, job)
                # counted out only AFTER it is in play_q, so there is never a
                # moment where a real line is visible to neither count
                self._inflight_bump(-1)

    def _commit(self, ticket, job):
        """Hand a rendered line to the player, but only once every earlier
        ticket has gone. Renders finish out of order (a short line beats a long
        one); playback must not."""
        with self._commit_cv:
            while self._commit_next != ticket:
                self._commit_cv.wait()
        try:
            if job is not None:
                payload, persona, prio = job
                # NB blocks while play_q is full — deliberate backpressure, and
                # the same behaviour the single-threaded pipeline had. Done
                # OUTSIDE the condition lock so a full queue can't freeze the
                # commit order bookkeeping.
                self._qput(self.play_q, persona, payload, prio=prio)
        finally:
            with self._commit_cv:
                self._commit_next += 1
                self._commit_cv.notify_all()

    def _play_loop(self):
        while True:
            _prio, _seq, job = self.play_q.get()
            if job is None:
                break
            # an exchange answer is still rendering — defer everything else so
            # the reply airs right after its question (see expect_answer)
            if _prio >= 0 and time.time() < self._answer_due:
                self.play_q.put((_prio, _seq, job))
                time.sleep(0.12)
                continue
            wav, cue, text, persona, epoch, deadline, topic, _prio = job
            # stale (an interrupt happened after this was rendered, or the line
            # outlived its TTL waiting in the queue — e.g. "5 minutes remaining"
            # after the flag) or stopped — drop without playing
            if (not self.enabled or self._stale(persona, epoch, _prio)
                    or (deadline and time.time() > deadline)):
                if deadline and time.time() > deadline:
                    _log(f"play DROP-stale persona={persona} :: {text[:40]}")
                elif self.enabled:
                    _log(f"play DROP-cut persona={persona} :: {text[:40]}")
                try:
                    os.remove(wav)
                except Exception:
                    pass
                self._topic_done(topic)
                if cue:
                    cue.drop()          # tell the caller it will never sound
                continue
            try:
                playable = bool(winsound) and os.path.exists(wav)
                if cue and playable:
                    # Caption/bubble fires ONLY when audio is actually about to
                    # sound. It used to fire unconditionally, one line earlier —
                    # so a line whose render had failed (no wav on disk) still
                    # put a caption on screen with nothing to hear, which reads
                    # exactly like "captions not matching the audio".
                    cue.play(text, persona)            # caption/bubble IN SYNC
                elif cue:
                    _log(f"play NO-WAV (caption suppressed) :: {text[:40]}")
                    cue.drop()          # nothing to hear — say so immediately
                if playable:
                    _log(f"play START :: {text[:30]}")
                    _transcript(persona, text)      # full-text race transcript
                    # SND_NODEFAULT: if the file can't be played, stay SILENT
                    # rather than letting Windows substitute its default *beep*
                    self._speaking = True
                    self._speaking_persona = persona
                    winsound.PlaySound(wav, winsound.SND_FILENAME
                                       | winsound.SND_NODEFAULT)   # blocking
                    _log("play DONE")
            except Exception as ex:
                _log(f"play ERROR {type(ex).__name__}: {ex}")
            finally:
                self._speaking = False
                self._speaking_persona = None
                self._topic_done(topic)
                try:
                    if self.on_line_end:
                        self.on_line_end(text, persona)   # caption end-sync
                except Exception:
                    pass
                try:
                    os.remove(wav)
                except Exception:
                    pass

    def _render(self, text, persona, voice, intensity=0, cue=None, epoch=0,
                deadline=None, topic=None, prio=1):
        # already superseded before we even started rendering — skip the (slow)
        # synthesis entirely so the queue clears fast after an interrupt
        if not self.enabled or self._stale(persona, epoch, prio):
            if self.enabled:
                _log(f"render DROP-old persona={persona} :: {text[:40]}")
            self._topic_done(topic)
            if cue:
                cue.drop()
            return
        # gone stale in the gen queue (a backlog built up) — don't waste a slow
        # network synth on a line that will be dropped at play time anyway
        if deadline and time.time() > deadline:
            _log(f"render DROP-stale persona={persona} :: {text[:40]}")
            self._topic_done(topic)
            if cue:
                cue.drop()
            return
        samples, srate, prebuilt = None, 24000, False
        if self.engine == "edge":
            try:
                res = self._gen_edge(text, persona, voice, intensity)
                if len(res) == 3:                 # big-moment build (pre-shaped)
                    srate, samples, prebuilt = res
                else:
                    srate, samples = res
            except Exception:
                samples = None
        if samples is None:
            try:
                srate, samples = self._gen_sapi(text, persona)
            except Exception:
                samples = None
        if not samples:
            _log(f"render NO-SAMPLES engine={self.engine} persona={persona}")
            self._topic_done(topic)
            return
        if prebuilt:
            # the build ramp already set the per-clause levels (clause 1 ≈ normal
            # loudness, later clauses swelling) — DON'T peak-normalise or re-gain,
            # that would undo the swell. Safety soft-limit only.
            mixed = [_soft(x) for x in samples]
        elif persona in CLEAN_PERSONAS:
            peak = max((abs(x) for x in samples), default=0.0) or 1.0
            g = min(4.0, 0.97 / peak) * MASTER_VOL * LOUDNESS
            mixed = [_soft(x * g) for x in samples]
        else:
            # team radio: the band-pass FX drops the level, so peak-normalise the
            # VOICE first then drive it harder — otherwise it's too quiet to hear
            # RIVALS get the intercom band-pass, the ENGINEER stays clean.
            # Settled by ear in a direct A/B once the voices were actually
            # rendering: the rivals sound better ON the radio chain, your
            # engineer sounds better off it (it flattened his prosody).
            #
            # NB the older "removing the band-pass made the drivers robotic"
            # report was a misattribution — rivals were failing to render at
            # all (see the seed/NameError note in _gen_edge) and falling back
            # to offline SAPI. The FX was never what anyone was hearing, so
            # don't re-litigate this from that comment.
            if persona == "ENGINEER":
                vs = list(samples)
            else:
                vs = _radioize(samples, srate)
            vpk = max((abs(x) for x in vs), default=0.0) or 1.0
            vs = [x * (0.95 / vpk) for x in vs]
            # softer radio beep: the click sat much louder than the voice and was
            # harsh on the ears — drop it well under the voice and shorten it
            mixed = ([c * 0.35 for c in _click(srate)] + vs
                     + [c * 0.22 for c in _click(srate, 50)])
            mixed = [_soft(s * MASTER_VOL * LOUDNESS * 1.2) for s in mixed]
        wav = self._next_wav()
        _write_wav(wav, srate, mixed, gain=self.volume)
        # one last staleness check — an interrupt may have landed during the slow
        # render; if so, drop this rather than play it ahead of the incident
        if self._stale(persona, epoch, prio):
            _log(f"render DROP-cut persona={persona} :: {text[:40]}")
            try:
                os.remove(wav)
            except Exception:
                pass
            self._topic_done(topic)
            if cue:
                cue.drop()
            return
        # hand back to the worker, which commits it to play_q in ticket order
        # (see _commit). Every early return above yields None and is treated as
        # a completed-but-silent ticket, so the ordering never stalls.
        return ((wav, cue, text, persona, epoch, deadline, topic, prio),
                persona, prio)

    # ---- neural generation ----
    # excitement ladder for the booth voices: as intensity climbs the delivery
    # gets faster, higher and louder — the way commentators lift on a big moment
    # energy comes mostly from RATE + VOLUME; pitch is kept low so the voice
    # stays natural (a big pitch boost was making it sound high/robotic)
    _HYPE = {0: ("+0%", "-9Hz", "+4%"), 1: ("+7%", "-3Hz", "+12%"),
             2: ("+14%", "+3Hz", "+20%")}

    def _gen_edge(self, text, persona, voice, intensity=0, mp3=None):
        # BOTH booth voices use the pundit's flat, warm, near-natural setting.
        # The lead used to have an excitement ladder (_HYPE) + a big-moment
        # loudness swell (_gen_edge_build) — it made him lurch louder out of
        # nowhere mid-race, while the flat pundit read sounded the most human.
        # The swell/hype code is kept below (unused) in case we ever re-tune it.
        if persona in CLEAN_PERSONAS:
            # Warm, authoritative booth read. Rate kept near-natural so the
            # phonemes don't get clipped (that was the "robotic" symptom —
            # rushing the voice past its natural cadence breaks the delivery).
            # a hair of per-line variation keeps the booth from sounding
            # metronomic across a long race, without touching the warm,
            # near-natural cadence that works
            com = edge_tts.Communicate(
                text, voice,
                rate=f"{2 + random.randint(-2, 2):+d}%",
                pitch=f"{-4 + random.randint(-2, 2):+d}Hz",
                volume="+18%")
        elif persona == "ENGINEER":
            # YOUR ENGINEER IS NOT ONE OF THE RIVALS. He is a single fixed
            # character, so the per-driver prosody spread below does nothing
            # for him — and the PITCH SHIFT it applied actively wrecked him:
            # shifting a neural voice off its natural pitch introduces
            # artefacts and strips the accent, which is the "completely
            # robotic, no accent" regression. He gets his natural pitch, a
            # near-natural rate, and only a hair of per-line movement.
            com = edge_tts.Communicate(
                text, voice,
                rate=f"{2 + random.randint(-1, 1):+d}%",
                volume="+12%")
        else:
            # RIVAL DRIVERS. Two hard lessons are baked in here:
            #   * NO PITCH SHIFT. Moving a neural voice off its natural pitch
            #     adds artefacts and strips the accent — that is what made the
            #     engineer AND the drivers sound robotic.
            #   * DON'T STACK RATE. PERSONA_RATE already sits at +16/+18% for
            #     the excitable ones, and this file's own notes say rushing a
            #     voice past its natural cadence is exactly what breaks the
            #     delivery. Piling another +5% on top did precisely that.
            # So the approved persona rate stands, with a SMALL stable
            # per-driver offset (so a driver still sounds like themselves) and
            # a tiny per-line jitter — clamped so it can never rush further
            # than the tuned values already do.
            base = PERSONA_RATE.get(persona, "+0%")
            try:
                b = int(base.rstrip("%"))
            except ValueError:
                b = 0
            # mix the hash first: the raw byte-sum correlates across small
            # moduli, so two drivers could share a voice AND an offset
            # key off the VOICE: _gen_edge never had a `seed` parameter, so
            # this line raised NameError on every rival read — swallowed by the
            # bare except in _render, which then fell back to offline SAPI.
            # That, not the band-pass, is why the drivers sounded robotic.
            h = (_seed_hash(voice or persona) * 2654435761) & 0xFFFFFFFF
            rate_v = b + ((h % 5) - 2) + random.randint(-1, 1)
            rate_v = max(-10, min(18, rate_v))
            com = edge_tts.Communicate(text, voice, rate=f"{rate_v:+d}%")
        mp3 = mp3 or self._next_mp3()
        asyncio.run(com.save(mp3))
        try:
            return _decode_mp3(mp3)
        finally:
            try:
                os.remove(mp3)
            except Exception:
                pass

    # excitement BUILD ladder (start, end) for a big-moment line — interpolated
    # across however many clauses the line splits into so the FIRST clause is
    # grounded at normal volume and the LAST peaks. Tuned and approved by ear.
    _BUILD = dict(rate0=0, rate1=4,       # +0% .. +4% speaking rate — barely a
                                          # nudge; the SWELL is carried by volume,
                                          # not speed (a faster peak read jarring)
                  pitch0=-2, pitch1=5,    # -2Hz .. +5Hz (per clause)
                  gain0=1.0, gain1=2.0)    # 1.0x .. 2.0x loudness — applied as a
                                           # CONTINUOUS eased envelope (no steps),
                                           # smaller range so the swell isn't jarring

    @staticmethod
    def _split_clauses(text):
        """Split a line into rising clauses on strong boundaries (em-dash,
        sentence end, comma). Tiny fragments are merged back so we never render
        a one-word snippet on its own."""
        parts = re.split(r'(?<=[!.?])(?=\s)|(?<=—)\s*|(?<=,)\s+', text)
        parts = [p.strip() for p in parts if p.strip()]
        merged = []
        for p in parts:
            if merged and len(p.split()) < 2:        # glue a stub to the prior
                merged[-1] = merged[-1] + " " + p
            else:
                merged.append(p)
        return merged

    @staticmethod
    def _gentle(x):
        """Gentle saturator (linear to 0.75, soft knee above) — fattens a gained
        clause so it reads LOUDER without the harsh wall of a hard limiter."""
        a = abs(x)
        if a <= 0.75:
            return x
        e = a - 0.75
        return math.copysign(0.75 + e / (1.0 + e * 2.5), x)

    def _gen_edge_build(self, text, voice):
        """Render a big-moment line so the excitement SWELLS smoothly through it.
        Returns (sr, samples, True) or None for a single-clause line (caller does
        a normal one-shot render).

        Two layers, kept separate so the swell is natural rather than stepped:
          • RATE/PITCH rise per clause (small, and far less audible than volume
            jumps, so discrete steps here are fine).
          • LOUDNESS rises as ONE CONTINUOUS eased envelope across the entire
            concatenated waveform — no per-clause level step, no hard jump. This
            was the jarring part before: a discrete gain leap at a clause/silence
            boundary. Now the volume glides up sample by sample.
        The first clause sits at ≈ a normal line's loudness so the opening
        matches the rest of the booth. _render passes the result through with a
        safety limit only (no re-normalise, which would undo the swell)."""
        clauses = self._split_clauses(text)
        if len(clauses) < 2:
            return None
        n = len(clauses)
        b = self._BUILD
        rendered = []
        srate = 24000
        for i, clause in enumerate(clauses):
            p = i / (n - 1)
            rate  = f"{int(round(b['rate0']  + p * (b['rate1']  - b['rate0']))):+d}%"
            pitch = f"{int(round(b['pitch0'] + p * (b['pitch1'] - b['pitch0']))):+d}Hz"
            com = edge_tts.Communicate(clause, voice, rate=rate, pitch=pitch,
                                       volume="+0%")
            _m = self._next_mp3()        # never the shared _MP3: see _next_mp3
            asyncio.run(com.save(_m))
            try:
                sr, s = _decode_mp3(_m)
            finally:
                try:
                    os.remove(_m)
                except Exception:
                    pass
            srate = sr
            rendered.append(s)
        # reference off the FIRST clause so the opening ≈ a normal line's level,
        # and apply that ONE factor to all clauses (preserves edge's natural
        # relative levels). A short breath sits between clauses.
        ref_pk = max((abs(x) for x in rendered[0]), default=0.0) or 1.0
        ref = 0.90 / ref_pk
        gap = [0.0] * int(srate * 0.045)            # 45ms breath between clauses
        joined = []
        for i, s in enumerate(rendered):
            joined.extend(x * ref for x in s)
            if i < n - 1:
                joined.extend(gap)
        # CONTINUOUS loudness swell over the whole line (smoothstep ease: stays
        # grounded early, lifts toward the climax) — applied per sample so there
        # is never a discrete level jump.
        N = len(joined) or 1
        g0, g1 = b['gain0'], b['gain1']
        out = []
        for i, x in enumerate(joined):
            p = i / (N - 1) if N > 1 else 1.0
            e = p * p * (3.0 - 2.0 * p)             # smoothstep
            out.append(self._gentle(x * (g0 + (g1 - g0) * e)))
        return srate, out, True

    # ---- SAPI fallback ----
    def _start_sapi(self):
        try:
            self.proc = subprocess.Popen(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", _WORKER],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, bufsize=1,
                creationflags=_CREATE_NO_WINDOW)
            self.proc.stdout.readline()
        except Exception:
            self.proc = None

    def _gen_sapi(self, text, persona):
        if self.proc is None or self.proc.poll() is not None:
            self._start_sapi()
        if self.proc is None:
            return 24000, []
        voice = self._voice_for_sapi(persona)
        rate_k, pitch, _ = PERSONA_VOICE.get(persona, PERSONA_VOICE["ENGINEER"])
        ssml = ("<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' "
                f"xml:lang='en-US'><prosody rate='{rate_k}' pitch='{pitch}'>"
                f"{_xml(text)}</prosody></speak>")
        self.proc.stdin.write(_OUT + "\t" + voice + "\t" + ssml + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if "OK" not in (line or "") or not os.path.exists(_OUT):
            return 24000, []
        return _read_wav(_OUT)

    def _voice_for_sapi(self, persona):
        if persona == "ENGINEER" or not self.names:
            male_en = [n for n, c in self.voices if c.lower().startswith("en")
                       and any(x in n for x in ("David", "Mark", "George"))]
            en = [n for n, c in self.voices if c.lower().startswith("en")]
            return (male_en or en or self.names or [""])[0]
        idx = sum(persona.encode()) % len(self.names)
        return self.names[idx]

    def toggle(self):
        self.enabled = not self.enabled
        if not self.enabled:
            self.stop()
        return self.enabled

    def stop(self):
        """Halt audio NOW: disable, drain both queues, and abort any sound that's
        currently playing. Used when RaceRoom closes / on quit so the booth
        doesn't keep talking over a dead session."""
        self.enabled = False
        self._purge()                      # session over: engineer clears too
        if winsound:
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)   # stop current sound
            except Exception:
                pass

    def resume(self):
        self.enabled = True

    def flush(self):
        """Drop all queued/playing audio but stay ENABLED — used on a session or
        race RESTART so the previous race's commentary doesn't carry over into
        the new one. (stop() disables; flush() keeps the booth ready to talk.)"""
        self._purge()                      # restart: engineer's race is gone too
        if winsound:
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass

    def yield_floor(self):
        """Clear the booth's WAITING chatter so the next call goes next.

        `interrupt` minus the cut: the line that is playing finishes its
        sentence. Queued and mid-render booth colour is dropped; the engineer
        and any answer to a question already asked survive, exactly as in an
        interrupt (see _purge and _stale).

        FOR A TOP-FIVE PASS. Measured in the flow simulator: with routine
        lines already waiting, every one of the six slowest lines heard was an
        overtake call, twelve to sixteen seconds after the move was confirmed
        — the "some overtakes are extremely delayed" report, still there. A
        confirmed pass for the top five outranks colour that has not started
        yet; it does not outrank a sentence already in the air.
        """
        self._purge(keep_engineer=True)

    def interrupt(self):
        """Cut current audio mid-sentence and drain queues — for on-track
        incidents that must be heard NOW. Bumping the epoch discards any line
        that's mid-render or already queued (rendered under the old epoch), so the
        incident truly CUTS IN instead of waiting for that audio to finish first.
        SND_PURGE stops the wav that's actually playing mid-file. Stays enabled.
        Queued ENGINEER lines survive the cut (see _purge).

        ONE EXCEPTION: if YOUR ENGINEER is mid-sentence, his audio is left
        alone. _purge already spared his QUEUED lines, but SND_PURGE was still
        chopping the one actually playing, so a booth call landing at the wrong
        moment truncated the most useful voice in the game — and left his card
        on screen next to half a sentence. The booth line simply queues behind
        him; engineer jobs already outrank booth colour in the play queue, so
        nothing is lost by waiting the second or two."""
        speaking_eng = (self._speaking and self._speaking_persona == "ENGINEER")
        self._purge(keep_engineer=True)
        if winsound and not speaking_eng:
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
        elif speaking_eng:
            _log("interrupt HELD — engineer mid-sentence, not cutting him")

    def close(self):
        try:
            self.stop()                       # kill audio immediately first
            self.gen_q.put((-1, -1, None))     # beats any queued job
            self.play_q.put((-1, -1, None))
            if self.proc and self.proc.poll() is None:
                self.proc.stdin.write("__QUIT__\n")
                self.proc.stdin.flush()
                self.proc.terminate()
        except Exception:
            pass


def _xml(t):
    return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&apos;"))


def _list_voices():
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command",
             "Add-Type -AssemblyName System.Speech; "
             "(New-Object System.Speech.Synthesis.SpeechSynthesizer)."
             "GetInstalledVoices() | %{ $_.VoiceInfo.Name + '|' + "
             "$_.VoiceInfo.Culture.Name }"],
            text=True, creationflags=_CREATE_NO_WINDOW, timeout=12,
            stderr=subprocess.DEVNULL)
        return [(ln.split("|", 1)[0].strip(), ln.split("|", 1)[1].strip())
                for ln in out.splitlines() if "|" in ln]
    except Exception:
        return []


if __name__ == "__main__":
    t = Tts()
    print("engine:", t.engine)
    demo = [("ENGINEER", "", "Radio check. P3, gap behind two seconds, manage it."),
            ("HOTHEAD", "RYAN", "He is all over me, do something about it!"),
            ("VILLAIN", "JORGE", "You will regret that move. I am coming back."),
            ("ROOKIE", "KATJA", "Guys, he is catching me, what do I do?!")]
    for persona, seed, line in demo:
        print("->", persona, t._voice_for(persona, seed))
        t.speak(line, persona, seed)
        time.sleep(4)
    time.sleep(1)
    t.close()
