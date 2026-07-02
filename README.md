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
pip install pyinstaller edge-tts miniaudio
pyinstaller --noconfirm --windowed --name RacerTV --hidden-import _cffi_backend r3e_overlay.py
```

Then copy `r3e-data.json`, `racer-tv.png`, `tts_worker.ps1`, `README.txt`,
`setup_voices.ps1`, `stings/` and `lines_data/` into `dist/RacerTV/`.

## Layout

| Path | What it is |
|---|---|
| `r3e_overlay.py` | The overlay engine (window, graphics, events, commentary direction) |
| `tts.py` | Voice engine: edge-tts neural voices + radio FX, SAPI fallback |
| `lines.py` + `lines_data/` | All dialogue: booth commentary, driver personas, track lore |
| `r3e_data.py` | RaceRoom shared-memory reader (matches Sector3's spec) |
| `avatars.py` | Driver avatar generation |
| `tests/` | Headless test suite (`python tests/<name>.py` from `tests/`) |

## License

Source-available for reading, auditing and building for personal use.
All rights reserved — please don't redistribute modified builds without asking.
