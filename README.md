# RacerTV

Somewhere inside RaceRoom, there's a TV station. **RacerTV** is a broadcast
overlay for [RaceRoom Racing Experience](https://www.raceroom.com/) that turns
your races and replays into a live TV production — timing graphics, a track
map, team radio with voiced driver personalities, and a fully voiced
commentary booth: **Miles Crawford** (play-by-play) and **Brett Calloway**
(analysis) calling your race as it happens.

**Download:** grab the latest zip from
[Releases](../../releases/latest), extract anywhere, run `RacerTV.exe`.
Full setup notes are in [README.txt](README.txt).

## Is this safe? (source-available for auditing)

This repo contains the complete source the exe is built from, so you can see
exactly what it does — and run it from source instead of the exe if you prefer:

- It **reads** RaceRoom's public shared-memory telemetry (the same `$R3E`
  interface Sector3 documents in [r3e.h](r3e.h) / [R3E.cs](R3E.cs)).
  It never writes to the game, never touches your inputs, and cannot affect
  your race.
- The overlay window is click-through and draws on top of the game only.
- Voices use Microsoft's public edge-tts neural voice service (that's the only
  network traffic), falling back to Windows' built-in offline voices.
- No telemetry, no accounts, no data collection. Local state is two small
  JSON files next to the exe (line-variety decks + your race results, so the
  booth remembers you).

The exe is unsigned (hobby project), so Windows SmartScreen will warn on first
launch — that's expected. If your antivirus flags it, that's the usual
PyInstaller false positive; audit the source here or build it yourself below.

## Running from source

```
pip install edge-tts miniaudio
python r3e_overlay.py
```

Python 3.11+ on Windows. `edge-tts`/`miniaudio` are optional — without them
you get the offline Windows voices.

## Building the exe

```
pip install pyinstaller edge-tts miniaudio pillow
pyinstaller --noconfirm RacerTV.spec
```

Build from **`RacerTV.spec`**, not from `r3e_overlay.py` directly — the spec
collects every asset (`r3e-data.json`, `racer-tv.png`, the fonts, `stings/`,
`lines_data/`, the scripts and the radio-card art) into `dist/RacerTV/`
automatically, so there's no manual copy step to forget.

Pillow is required for the custom PNG radio-card icons; without it the app
still runs and falls back to the built-in vector helmets.

### Custom radio-card art (optional)

Drop these next to the exe (or next to `r3e_overlay.py` when running from
source) and they replace the built-in vector icons:

| File | Used for |
|---|---|
| `icon_helmet_1.png` … `icon_helmet_N.png` | Driver helmets — used **as drawn**; each driver is assigned one on first sighting and their overlay colour is sampled from it |
| `icon_helmet.png` (single file instead) | One helmet **tinted** per driver — draw it white/grey |
| `icon_engineer.png` | The race engineer |

Square, transparent background. An all-black silhouette is recoloured
automatically so it stays visible on the dark card. Any file named `icon_*`
is skipped by the broadcast-logo loader.

## Layout

| Path | What it is |
|---|---|
| `r3e_overlay.py` | The engine: session/telemetry state, the tick loop, and the `Overlay` class the mixins compose into |
| `overlay_booth.py` | `BoothMixin` — commentary direction: what the booth says and when, crosstalk, lore, race-story recaps, the finish |
| `overlay_radio.py` | `RadioMixin` — the race engineer (fuel, tyres, damage, limits, sector coaching) and rival driver radio |
| `overlay_draw.py` | `DrawMixin` — every drawn panel: tower, relative, sectors, flags, map, podium, settings, captions |
| `overlay_common.py` | Theme colours, tuning tables, small pure helpers. Imports nothing of the others (keeps the split acyclic) |
| `overlay_panel.py` | Click-through always-on-top window plumbing (tk + win32) |
| `tts.py` | Voice engine: edge-tts neural voices + radio FX, SAPI fallback |
| `lines.py` + `lines_data/` | All dialogue: booth commentary, driver personas, track lore |
| `r3e_data.py` | RaceRoom shared-memory reader (matches Sector3's spec) |
| `avatars.py` | Radio-card icons: user PNG art if present, built-in vectors otherwise |
| `tests/` | Headless test suite (`python tests/<name>.py` from `tests/`) |

The mixins are a file-level split only: they take the same `self` and call each
other freely, so behaviour is identical to the single-class version. Adding a
method to two mixins would let Python silently shadow one by MRO —
`tests/structuretest.py` guards against that and pins the full method list.

## License

Source-available for reading, auditing and building for personal use.
All rights reserved — please don't redistribute modified builds without asking.
