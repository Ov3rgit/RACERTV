RacerTV  —  a broadcast for your RaceRoom races
===============================================
v1.0.7

RacerTV turns a RaceRoom session into a televised race. A commentary booth
(Miles Crawford on play-by-play, Brett Calloway on colour) calls the action,
your race engineer talks to you on team radio, and rival drivers key the mic
about their own races. On screen you get a broadcast timing tower, a relative
panel, sector times, flags, and a race-objective card.

It reads RaceRoom's shared memory and nothing else. It is read-only: it cannot
touch your race, your inputs or your files.


-------------------------------------------------------------------------
INSTALL  —  three steps
-------------------------------------------------------------------------

1. UNZIP the whole folder anywhere you like (Desktop is fine).
   Keep the folder together — RacerTV.exe needs the files next to it.

2. In RaceRoom: Settings -> Video -> Display Mode = BORDERLESS or WINDOWED.
   *** Exclusive Fullscreen hides ALL overlays, including this one. ***

3. Double-click RacerTV.exe, then load a session.

That's it. Nothing to install, no drivers, no config files.

Windows may warn about an unknown publisher the first time (the app isn't
code-signed). Click "More info" -> "Run anyway". The full source is public at
github.com/Ov3rgit/RACERTV if you want to check it first.

You need an INTERNET CONNECTION for the good voices — they are Microsoft's
online neural voices, so there is nothing to download. Offline, RacerTV falls
back to Windows' built-in voices, which sound noticeably more robotic. That is
expected, not a bug. (Optional: to improve the offline fallback, add voices in
Windows Settings -> Time & Language -> Speech, reboot, then right-click
setup_voices.ps1 -> Run as administrator.)


-------------------------------------------------------------------------
THE CORNER  —  what the top-left icons mean
-------------------------------------------------------------------------

  ●        status light.  green = on air        yellow = in the menus
                          dim   = no RaceRoom   amber "SHOW" = overlay hidden
  ≡        settings menu — click it, everything is in there
  19:04    the real-world clock (handy for online session start times)

Click the dot to hide or show the overlay. Clicks pass straight through to the
game everywhere else, so the overlay never steals your mouse or keyboard.


-------------------------------------------------------------------------
RACE OBJECTIVES  —  new in 1.0.7
-------------------------------------------------------------------------

Your engineer now sets you real targets and holds you to them: pass the car
ahead, close a gap, defend a place, recover after an incident, nurse the
tyres, keep it clean, or bring the lead home.

He only sets a target the maths says is actually on. If nothing is realistic,
he says nothing — a goal you could never reach is worse than no goal.

The card sits under the relative panel on the right:

  TARGET        what you're being asked to do, with laps left and live gap
  progress bar  fills as you close it out
  border glow   green while a gain is being confirmed, red while a loss is
                counting down, solid on the verdict

Targets resolve out loud — "that's the job done" or "just didn't have it" —
and the booth reacts to what it can see you doing.


-------------------------------------------------------------------------
CONTROLS
-------------------------------------------------------------------------

Everything is in the ≡ menu, so you never need a hotkey. If you prefer them:

  Ctrl+Shift+O   overlay UI on / off  (audio KEEPS running — commentary-only)
  Ctrl+Shift+C   booth commentary on / off  (engineer + radio stay live)
  Ctrl+Shift+R   team radio on / off  (booth stays live)
  Ctrl+Shift+M   mute ALL spoken audio
  Ctrl+Shift+E   compact tower <-> full tower
  Ctrl+Shift+D   debug HUD
  Ctrl+Shift+Q   quit

The menu also has a master volume slider for the voices.


-------------------------------------------------------------------------
WHAT'S ON SCREEN
-------------------------------------------------------------------------

  Timing tower (left)     position, gain/loss vs grid, tyre compound, car
                          number, name, P2P/DRS, interval + gap to leader.
                          You = gold, leader = blue, fastest lap = purple.
  Relative panel (right)  the cars immediately around you, with gaps
  Objective card          under the relative panel (see above)
  Sector strip            running lap + S1/S2/S3, purple/green/yellow
  Lower third             what the booth is saying, in sync with the audio
  Radio cards             engineer and rival drivers, bottom right
  Header                  track, session, lap/time left, LIVE tag
  Flags & penalties       yellow, blue, black, white, chequered

Works in replays too.


-------------------------------------------------------------------------
TROUBLESHOOTING
-------------------------------------------------------------------------

I can't see the overlay
  Display Mode must be Borderless or Windowed, not Exclusive Fullscreen.

No voices, or robotic voices
  Robotic = you're offline and on the Windows fallback. Silent = check the
  ≡ menu (All voices may be muted) and your internet connection.

The timing is frozen in a replay
  RaceRoom stops sending data while a replay is paused. Press play and it
  comes back within a couple of seconds.

It says nothing and the dot stays dim
  The dot stays dim until the real game window is up. RacerTV deliberately
  ignores the small red "Loading RaceRoom" splash and waits for the game.


-------------------------------------------------------------------------
CREDITS & LICENCE
-------------------------------------------------------------------------

RacerTV is a fan-made overlay for RaceRoom Racing Experience. It is not
affiliated with, endorsed by or connected to Sector3 Studios or KW Studios,
and it is not a copy of any real broadcaster — Miles and Brett are original
characters for an invented channel.

Fonts: Michroma and Chakra Petch, both SIL Open Font License, bundled and
loaded at runtime (nothing is installed on your system).

Source: github.com/Ov3rgit/RACERTV
