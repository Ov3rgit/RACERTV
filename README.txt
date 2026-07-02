RaceRoom Replay Overlay
=======================

A transparent, always-on-top, click-through, broadcast-style overlay that
reads RaceRoom's live shared memory (works in races AND replays):

  - Timing tower: position box, ▲/▼ position-change arrows vs grid, tyre
    compound dot, car number, driver name, P2P/DRS tag, INT (interval to car
    ahead) and LEAD (cumulative gap to leader) columns. Viewed car = gold,
    leader = blue, fastest-lap holder = purple edge. Close battles (<1s)
    are highlighted white.
  - Relative panel (right): the cars immediately around the focused car with
    +/- time gaps - best for following a battle.
  - Fastest-lap banner (lower third): purple flash when a new fastest lap is
    set, with driver + time.
  - Focused-car sector strip: running lap time + S1/S2/S3 colored purple
    (session best) / green (personal best) / yellow.
  - Flag & penalty chips: yellow (per sector), blue, black, white, chequered,
    and the viewed car's penalty.
  - Header: track + layout, session type, REPLAY flag, lap counter / time left.
  - Track map (bottom-left): auto-traced circuit outline with start/finish
    marker, yellow-sector highlighting, multiclass car colors, and live dots.

HOW TO RUN
----------
1. In RaceRoom video settings set Display Mode to BORDERLESS (or Windowed).
   Exclusive Fullscreen will hide any overlay.
2. Double-click "Start Overlay.bat"  (or run: python r3e_overlay.py)
3. Load a replay or session. The overlay updates automatically.

TOGGLE BUTTON
-------------
A small "● OVERLAY" button stays pinned to the top-left of the game and is
ALWAYS visible (in races, menus, and even if you click to another window), so
you always know the overlay is there. Click it to hide/show. It shows status:
  LIVE (green) = race/replay        standby (yellow) = in menus
  waiting (yellow) = game not up     OFF (orange) = you hid it
The full overlay (tower, map, etc.) only appears during a RACE or REPLAY;
otherwise just the toggle button shows.

TEAM RADIO
----------
Driver radio bubbles pop up (bottom-right) reacting to the action around the
car you're watching. Each driver has a PERSONALITY (hothead / cocky / veteran /
dramatic / joker), assigned consistently by name, with its own explicit lines:
  - you pass a driver  -> they complain (in character)
  - a driver passes you -> they taunt you
  - you're closing on the car ahead -> they react
  - any spin/crash (loses 2+ places) -> they react to their new position
Crashes near your battle are high priority; crashes elsewhere still get an
occasional reaction but yield to your own race.
Up to 3 bubbles can stack at once (a big multi-car incident airs a burst),
each gone after ~6s, hard-capped at 3 on screen so it never floods. Then a
~6s quiet window. Tunables at top of r3e_overlay.py: RADIO_GLOBAL_CD,
RADIO_DRIVER_CD, RADIO_NEAR, RADIO_FAR_CHANCE, RADIO_MAX_BUBBLES,
RADIO_MAX_BURST. Seven personalities (HOTHEAD, COCKY, VETERAN, DRAMATIC,
JOKER, ROOKIE, VILLAIN) live in the PERSONAS dict - add your own lines freely.

CONTROLS (work even though clicks pass through to the game)
----------------------------------------------------------
  Click "● OVERLAY"  hide / show the overlay
  Ctrl + Shift + O   hide / show the overlay (toggle)
  Ctrl + Shift + E   compact tower (racing) <-> full tower (replay watching)
  Ctrl + Shift + M   mute / unmute spoken team radio (TTS)
  Ctrl + Shift + Q   close the overlay

TEAM RADIO VOICE (TTS)
----------------------
Radio messages are spoken aloud through a "team radio" effect (band-pass +
static + squelch click), each driver with a persona voice.

VOICES: nothing to install. The overlay uses Microsoft's online neural
voices (edge-tts) — a full international cast of accents, synthesized in
the cloud — so you get broadcast-quality voices out of the box. The only
requirement is an INTERNET CONNECTION while playing.

OFFLINE FALLBACK: with no internet, the overlay automatically drops back
to Windows' built-in offline voices (System.Speech). Most PCs only have
one or two of these, so it sounds far more robotic — that's expected.
To improve the fallback, install extra voices via Windows Settings ->
Time & Language -> Speech -> Add voices, reboot, then run
setup_voices.ps1 AS ADMINISTRATOR (it exposes the new voices to the
overlay). This is optional and only affects offline play.

tts.py holds the FX knobs (NOISE, DRIVE, MASTER_VOL) and the voice cast
tables (NEURAL_VOICES, PERSONA_VOICE).

NOTE: data only streams while a replay is PLAYING (RaceRoom freezes the field
when paused). Press play and the timing appears within ~2s.

The overlay stays on top of the game and keeps showing the last frame if you
briefly click away, so it won't blink out. It also shows yellow/blue/black/
white/chequered flags and the viewed car's penalty as broadcast chips under
the header.

NOTES
-----
- The overlay is click-through: it never steals mouse/keyboard from the game.
- It reads only; it cannot affect your race or inputs.
- Files:
    r3e_data.py     shared-memory struct + reader (matches r3e.h v3.5)
    r3e_overlay.py  the GUI overlay
    r3e.h / R3E.cs  official Sector3 reference (for future tweaks)

TWEAKS (top of r3e_overlay.py)
------------------------------
  WIN_ALPHA   overall opacity
  MAX_ROWS    how many cars to show in the tower
  UPDATE_MS   refresh rate (80 = ~12.5 fps)
  colors      ACCENT / LEADER / panel colors
Tell me what to change and I'll adjust it.
