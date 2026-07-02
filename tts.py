"""
Team-radio text-to-speech for the RaceRoom overlay.

Primary engine: edge-tts (Microsoft's free online NEURAL voices — genuinely
human, real accents). Decoded with miniaudio, then run through a radio-FX chain
(band-pass + static + squelch click). Falls back to offline System.Speech
(SAPI) if edge-tts / internet isn't available, so it still works as a portable
mod. A TTS failure can never affect the overlay.
"""
import hashlib
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


def _log(msg):
    try:
        import time as _t
        with open(_LOG, "a", encoding="utf-8") as f:
            f.write(f"{_t.strftime('%H:%M:%S')} {msg}\n")
    except Exception:
        pass


_WORKER = os.path.join(_DIR, "tts_worker.ps1")
_OUT = os.path.join(_DIR, "_tts_render.wav")
_MP3 = os.path.join(_DIR, "_tts_render.mp3")
_PLAY = os.path.join(_DIR, "_tts_play.wav")
_STING_DIR = os.path.join(_DIR, "stings")    # pre-rendered instant incident clips
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
    ],
    # name-free LIGHTS-OUT call in the COMMENTATOR voice — fires the instant the
    # race goes green (the _racing edge) so there's NO edge-tts render latency on
    # the signature moment. The named follow-up ("…and {leader} leads them away!")
    # is queued straight after, WITHOUT its own interrupt, while it renders.
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
STING_PERSONA = {"alert": "PUNDIT", "lightsout": "COMMENTATOR",
                 "victory": "COMMENTATOR"}

# ---- neural voice cast (edge-tts) -------------------------------------------
ENGINEER_VOICE = "en-GB-ThomasNeural"             # your engineer: calm British male
NEURAL_VOICES = [
    # Rival drivers, in 3 tiers for an authentic international grid:
    #  A) correct-English accents — pronounce the English radio lines properly.
    #     (edge-tts has only two en-GB MALE voices and both are on the booth, so
    #     the strongest natural male British-Isles accent left is Irish.)
    "en-IE-ConnorNeural",   # Irish (strong, male, English-language)
    "en-IN-PrabhatNeural",  # Indian
    "en-ZA-LukeNeural",     # South African
    #  B) foreign-accented English — speak the English lines with their accent
    #     (mispronounce a little, but sound natural — the flavour you liked)
    "de-DE-ConradNeural",   # German
    "es-ES-AlvaroNeural",   # Spanish
    "it-IT-DiegoNeural",    # Italian
    #  C) NATIVE LANGUAGE — the audio is in their own tongue; the on-screen
    #     subtitle is the English translation (see NATIVE_VOICE_LANG / NATIVE_RADIO)
    "fr-FR-HenriNeural",    # French
    "pt-BR-AntonioNeural",  # Brazilian Portuguese
    "ru-RU-DmitryNeural",   # Russian
]
# Tier-C voices speak generic radio chatter in their NATIVE language; the overlay
# shows the English translation as the subtitle. Maps voice -> NATIVE_RADIO key.
NATIVE_VOICE_LANG = {
    "fr-FR-HenriNeural": "fr",
    "pt-BR-AntonioNeural": "pt",
    "ru-RU-DmitryNeural": "ru",
}
# the play-by-play race commentator + colour co-commentator (clean broadcast
# voices, NO radio FX — they're in the booth, not on a team radio)
# strongly-accented voices on purpose: a clean RP-English read is the easiest
# to clock as TTS, whereas natural regional accents carry prosody that masks it
COMMENTATOR_VOICE = "en-GB-RyanNeural"      # lead play-by-play (British)
PUNDIT_VOICE = "en-AU-WilliamNeural"        # colour/analysis man (Australian)
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


def _write_wav(path, rate, samples):
    frames = bytearray()
    for s in samples:
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


def _radioize(samples, rate):
    """Band-pass to the radio band + light distortion + static baked in. Kept
    fairly open (250 Hz - 4.2 kHz) so accents/clarity survive."""
    out = [0.0] * len(samples)
    dt = 1.0 / rate
    a_lp = dt / (1.0 / (2 * math.pi * 5200.0) + dt)   # wider top = clearer
    rc_hp = 1.0 / (2 * math.pi * 220.0)
    a_hp = rc_hp / (rc_hp + dt)
    lp = prev_x = prev_hp = 0.0
    for i, x in enumerate(samples):
        lp += a_lp * (x - lp)
        hp = a_hp * (prev_hp + lp - prev_x)
        prev_x, prev_hp = lp, hp
        v = math.tanh(hp * DRIVE)
        n = random.uniform(-1, 1)
        env = abs(v)
        # gentle AM shimmer + a low static floor that only sits UNDER the voice
        # (scaled by envelope) so silences stay quiet and speech stays clear
        v = v * (1.0 + n * 0.05) + n * NOISE * env
        out[i] = max(-1.0, min(1.0, v * 0.97))
    return out


# ----------------------------------------------------------------- the engine
class Tts:
    def __init__(self):
        try:
            open(_LOG, "w").close()                 # fresh log each launch
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
        self.engine = "edge" if _HAVE_EDGE else "sapi"
        # two-stage pipeline: the GENERATE thread renders the next line's audio
        # while the PLAY thread is still playing the current one, so there's no
        # dead air waiting on edge-tts network latency between lines
        self.gen_q = queue.Queue()
        self.play_q = queue.Queue(maxsize=6)
        self._wav_i = 0
        self._speaking = False     # True while a wav is actually playing (so the
                                   # booth knows when it's cutting someone off)
        self._speaking_persona = None  # WHO is currently playing (persona)
        self._epoch = 0            # bumped on interrupt/flush/stop; anything
                                   # rendered under an older epoch is discarded so
                                   # an incident truly CUTS IN instead of waiting
                                   # for in-flight/queued audio to finish first
        # SAPI fallback worker + voice list
        self.proc = None
        self.voices = _list_voices()
        self.names = [v[0] for v in self.voices]
        self._start_sapi()
        self._stings = {}          # (persona, group) -> [cached wav paths]
        self._topics = {}          # topic -> pending count (dedup, see speak())
        threading.Thread(target=self._gen_loop, daemon=True).start()
        threading.Thread(target=self._play_loop, daemon=True).start()
        threading.Thread(target=self._build_stings, daemon=True).start()
        _log(f"INIT engine={self.engine} have_edge={_HAVE_EDGE} "
             f"winsound={winsound is not None} voices={len(self.voices)}"
             + (f" edge_err={_EDGE_ERR}" if _EDGE_ERR else ""))

    def _next_wav(self):
        # plenty of unique names so a force-queued burst can never overwrite a
        # file that's still waiting to play (that collision = the Windows beep)
        self._wav_i = (self._wav_i + 1) % 64
        return os.path.join(_DIR, f"_tts_play{self._wav_i}.wav")

    def _pending(self):
        return self.gen_q.qsize() + self.play_q.qsize()

    def speaking(self):
        """True if a line is actually being played right now."""
        return self._speaking

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

    def sting(self, group="alert", persona="PUNDIT", on_play=None):
        """Play a pre-rendered incident sting RIGHT NOW (no synth wait). Cuts the
        current audio (epoch bump + purge) and jumps the cached clip to the front
        of the play queue. `on_play(text, persona)` fires the instant it starts so
        the SUBTITLE shows in sync. Returns True if a sting played, False if none
        are ready yet (caller then falls back to a normal interrupt+render). The
        named detail line should be queued straight after, WITHOUT its own
        interrupt (that would purge this sting)."""
        if not self.enabled:
            return False
        clips = self._stings.get((persona, group))
        if not clips:
            return False
        src, text = random.choice(clips)
        if not os.path.exists(src):
            return False
        self._epoch += 1                           # invalidate in-flight audio
        for q in (self.gen_q, self.play_q):
            try:
                while True:
                    q.get_nowait()
            except Exception:
                pass
        self._topics.clear()               # purged lines can't hold their topic
        if winsound:
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
        try:
            dst = self._next_wav()                 # copy so play_loop can delete it
            shutil.copyfile(src, dst)
        except Exception:
            return False
        self.play_q.put((dst, on_play, text, persona, self._epoch, None, None))
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
              force=False, urgent=False, ttl=None, topic=None):
        if not self.enabled or not text:
            _log(f"speak SKIP enabled={self.enabled} text={bool(text)}")
            return
        # keep the booth CURRENT: commentary is play-by-play, so a line that
        # can't be spoken promptly is stale (you hear "takes the lead" seconds
        # after the move). Drop surplus commentary rather than let a backlog
        # build. `urgent` events get a little more headroom but are STILL capped
        # (otherwise a busy race buries the booth seconds behind the action).
        # `force` is only for scripted sequences (finish wrap / crosstalk reply)
        # that must complete intact.
        if not force and persona in CLEAN_PERSONAS:
            cap = 3 if urgent else 2
            if self._pending() >= cap:
                _log(f"speak DROP-busy persona={persona} urgent={urgent} "
                     f"pending={self._pending()}")
                return
        # topic dedup: only one line per topic may be pending at a time, so a
        # busy moment can't stack near-identical calls (two winner lines, two
        # "gap closing" reads) that then air back to back
        if topic and self._topics.get(topic, 0) > 0:
            _log(f"speak DROP-dupe topic={topic} :: {text[:40]}")
            return
        if ttl is None and not force:
            ttl = TTL_BOOTH if persona in CLEAN_PERSONAS else TTL_RADIO
        deadline = (time.time() + ttl) if ttl else None
        if topic:
            self._topics[topic] = self._topics.get(topic, 0) + 1
        self.gen_q.put((text, persona, self._voice_for(persona, seed), intensity,
                        on_play, self._epoch, deadline, topic))
        _log(f"speak QUEUE persona={persona} i={intensity} pending={self._pending()} "
             f":: {text[:40]}")

    def _topic_done(self, topic):
        if topic and topic in self._topics:
            self._topics[topic] -= 1
            if self._topics[topic] <= 0:
                del self._topics[topic]

    def _gen_loop(self):
        """Render audio to a wav file, then hand it to the player. Runs ahead of
        playback so the next line is ready the instant the current one ends."""
        while True:
            item = self.gen_q.get()
            if item is None:
                break
            try:
                self._render(*item)
            except Exception as ex:
                _log(f"gen ERROR {type(ex).__name__}: {ex}")

    def _play_loop(self):
        while True:
            job = self.play_q.get()
            if job is None:
                break
            wav, on_play, text, persona, epoch, deadline, topic = job
            # stale (an interrupt happened after this was rendered, or the line
            # outlived its TTL waiting in the queue — e.g. "5 minutes remaining"
            # after the flag) or stopped — drop without playing
            if (not self.enabled or epoch < self._epoch
                    or (deadline and time.time() > deadline)):
                if deadline and time.time() > deadline:
                    _log(f"play DROP-stale persona={persona} :: {text[:40]}")
                try:
                    os.remove(wav)
                except Exception:
                    pass
                self._topic_done(topic)
                continue
            try:
                if on_play:
                    on_play(text, persona)             # caption/bubble IN SYNC
                if winsound and os.path.exists(wav):
                    _log(f"play START :: {text[:30]}")
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
                    os.remove(wav)
                except Exception:
                    pass

    def _render(self, text, persona, voice, intensity=0, on_play=None, epoch=0,
                deadline=None, topic=None):
        # already superseded before we even started rendering — skip the (slow)
        # synthesis entirely so the queue clears fast after an interrupt
        if not self.enabled or epoch < self._epoch:
            self._topic_done(topic)
            return
        # gone stale in the gen queue (a backlog built up) — don't waste a slow
        # network synth on a line that will be dropped at play time anyway
        if deadline and time.time() > deadline:
            _log(f"render DROP-stale persona={persona} :: {text[:40]}")
            self._topic_done(topic)
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
            vs = _radioize(samples, srate)
            vpk = max((abs(x) for x in vs), default=0.0) or 1.0
            vs = [x * (0.95 / vpk) for x in vs]
            # softer radio beep: the click sat much louder than the voice and was
            # harsh on the ears — drop it well under the voice and shorten it
            mixed = ([c * 0.35 for c in _click(srate)] + vs
                     + [c * 0.22 for c in _click(srate, 50)])
            mixed = [_soft(s * MASTER_VOL * LOUDNESS * 1.2) for s in mixed]
        wav = self._next_wav()
        _write_wav(wav, srate, mixed)
        # one last staleness check — an interrupt may have landed during the slow
        # render; if so, drop this rather than play it ahead of the incident
        if epoch < self._epoch:
            try:
                os.remove(wav)
            except Exception:
                pass
            self._topic_done(topic)
            return
        # blocks if behind
        self.play_q.put((wav, on_play, text, persona, epoch, deadline, topic))

    # ---- neural generation ----
    # excitement ladder for the booth voices: as intensity climbs the delivery
    # gets faster, higher and louder — the way commentators lift on a big moment
    # energy comes mostly from RATE + VOLUME; pitch is kept low so the voice
    # stays natural (a big pitch boost was making it sound high/robotic)
    _HYPE = {0: ("+0%", "-9Hz", "+4%"), 1: ("+7%", "-3Hz", "+12%"),
             2: ("+14%", "+3Hz", "+20%")}

    def _gen_edge(self, text, persona, voice, intensity=0):
        # BIG MOMENTS (intensity 2, booth voices): build the excitement THROUGH
        # the sentence — start grounded at normal volume, then swell louder and
        # a touch faster clause by clause, the way a real commentator lifts on a
        # move. Returns a 3-tuple (sr, samples, True) that _render passes through
        # WITHOUT its usual peak-normalise (which would flatten the ramp).
        if intensity >= 2 and persona in CLEAN_PERSONAS:
            built = self._gen_edge_build(text, voice)
            if built is not None:
                return built                      # (sr, samples, prebuilt=True)
            # single-clause line (e.g. a short incident call): fall through to a
            # normal render so we don't pay the multi-render cost for nothing.

        if persona == "PUNDIT":
            # Warm, authoritative analysis man. Rate kept near-natural so the
            # phonemes don't get clipped (that was the "robotic" symptom —
            # rushing the voice past its natural cadence breaks the delivery).
            com = edge_tts.Communicate(text, voice, rate="+2%", pitch="-4Hz",
                                       volume="+18%")
        elif persona in CLEAN_PERSONAS:          # COMMENTATOR play-by-play
            rate, pitch, volume = self._HYPE.get(max(0, min(2, intensity)),
                                                 self._HYPE[0])
            com = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch,
                                       volume=volume)
        else:
            com = edge_tts.Communicate(text, voice,
                                       rate=PERSONA_RATE.get(persona, "+0%"))
        asyncio.run(com.save(_MP3))
        return _decode_mp3(_MP3)

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
            asyncio.run(com.save(_MP3))
            sr, s = _decode_mp3(_MP3)
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
        self._epoch += 1                       # invalidate anything in flight
        for q in (self.gen_q, self.play_q):
            try:
                while True:
                    q.get_nowait()
            except Exception:
                pass
        self._topics.clear()               # purged lines can't hold their topic
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
        self._epoch += 1                       # invalidate anything in flight
        for q in (self.gen_q, self.play_q):
            try:
                while True:
                    q.get_nowait()
            except Exception:
                pass
        self._topics.clear()               # purged lines can't hold their topic
        if winsound:
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass

    def interrupt(self):
        """Cut current audio mid-sentence and drain queues — for on-track
        incidents that must be heard NOW. Bumping the epoch discards any line
        that's mid-render or already queued (rendered under the old epoch), so the
        incident truly CUTS IN instead of waiting for that audio to finish first.
        SND_PURGE stops the wav that's actually playing mid-file. Stays enabled."""
        self._epoch += 1
        for q in (self.gen_q, self.play_q):
            try:
                while True:
                    q.get_nowait()
            except Exception:
                pass
        self._topics.clear()               # purged lines can't hold their topic
        if winsound:
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass

    def close(self):
        try:
            self.stop()                       # kill audio immediately first
            self.gen_q.put(None)
            self.play_q.put(None)
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
    import time
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
