# -*- coding: utf-8 -*-
"""
Everything drawn on the overlay: the
timing tower, relative, sectors, flags, penalties, the track map, podium,
settings menu, captions and debug panel.

Mixed into Overlay (see r3e_overlay.py) — these methods take the
same `self` and call the rest of the class freely; only the file
they live in changed.
"""
import r3e_data as R
import time
from overlay_panel import _Panel
from overlay_common import (BG_STIPPLE, _BUBBLE_H, ACCENT, CARD_BG, CARD_BG2, CARD_BORDER,
                            PUNDIT_COLOR, SHIFT_PURPLE, TALLY_RED,
                            CONTROL_BG,
    COMMENTATOR_COLOR, CYAN, DIM, GREEN, HEADER_ACCENT, LEADER, MAX_ROWS,
    PANEL_BG, PANEL_OUTLINE, PANEL_STIPPLE, PURPLE, TEXT, _RADIO_LOCK)
from overlay_objective import (OBJ_HOLD_GAIN, OBJ_HOLD_LOSE,
    OBJ_DEFEND_CLEAR_HOLD)
from lines import (COMMENTATOR_NAME, PUNDIT_NAME)

# The speedo face is PIL-rendered (see speedo.py). PIL is bundled in the
# frozen build, but the overlay must not refuse to start if a source run is
# missing it — the dial simply does not draw.
try:
    import speedo as _speedo
    _SPEEDO_OK = _speedo.HAVE_PIL
except Exception:
    _speedo, _SPEEDO_OK = None, False


class DrawMixin:
    """See module docstring."""

    def _begin_panel(self, name, lx, ly, w, h):
        """Start drawing a panel whose top-left is at game-relative (lx, ly).
        Positions its small window over the game and returns a translating
        canvas, so the existing game-relative draw code lands correctly."""
        p = self.panels.get(name)
        if p is None:
            p = _Panel(self.root)
            self.panels[name] = p
        # finish the PREVIOUS panel's glass before switching away from it
        prev = getattr(self, "_cur_panel", None)
        if prev is not None and prev is not p:
            prev.flush_glass()
        p.place(self.game_x + lx, self.game_y + ly, w, h)
        self._used.add(name)
        self._cur_panel = p
        self._cv_real = p.cv
        # Panel BODIES are drawn into the glass BUFFER (not straight onto the
        # backing canvas) so the backing window is only repainted when its
        # content actually changes — see _Panel.flush_glass. Everything else
        # goes on _cv_real above it and stays fully solid.
        self._bg_real = p.glass if p.bg_cv is not None else None
        self._ox, self._oy = lx, ly
        return self.canvas

    def _hide_unused_panels(self):
        # end of frame: flush the last panel's glass, then hide the unused
        cur = getattr(self, "_cur_panel", None)
        if cur is not None:
            cur.flush_glass()
            self._cur_panel = None
        for name, p in self.panels.items():
            if name not in self._used:
                p.hide()

    def _region(self, *a, **k):
        pass  # no longer used (each panel is its own window)

    def panel(self, x, y, w, h, fill=PANEL_BG, stipple=PANEL_STIPPLE):
        # fill goes on the GLASS layer (translucent), outline on the solid
        # layer above it so the border stays sharp
        bg = getattr(self, "_bg_real", None)
        if bg is not None:
            bg.create_rectangle(x - self._ox, y - self._oy,
                                x - self._ox + w, y - self._oy + h,
                                fill=fill, outline="", stipple=stipple or "")
        else:
            self.canvas.create_rectangle(x, y, x + w, y + h, fill=fill,
                                         outline="", stipple=stipple or "")
        self.canvas.create_rectangle(x, y, x + w, y + h, fill="",
                                     outline=PANEL_OUTLINE, width=1)

    def _card(self, x, y, w, h, fill=CARD_BG, accent=None, side="top", r=7,
              glass=True):
        """A retro PIXEL card: hard dark box with stepped (notched) corners and
        a chunky 2px border — the whole graphics package's signature frame.
        The notched corners read through to the game via the chroma key.
        (`r` kept for call-site compatibility; it just sets the notch size.)"""
        n = max(2, min(4, int(r / 2)))          # corner notch, in pixels
        c = self.canvas
        # body as a notched-corner cross (two overlapping rects). BG_STIPPLE
        # makes the BODY only semi-opaque — the border, accent and every bit
        # of text stay fully solid, which whole-window alpha could not do.
        _st = {"stipple": BG_STIPPLE} if BG_STIPPLE else {}
        # Draw the BODY on the glass layer when there is one, offset into that
        # canvas's own coordinates. The border, accent and text below all stay
        # on `c` (the solid layer), which is what keeps them crisp.
        # glass=False forces the body SOLID on this card — the radio bubbles
        # need it, because their icons carry an opaque CARD_BG square and a
        # translucent body would make that square visible as an image border.
        bg = getattr(self, "_bg_real", None) if glass else None
        if bg is not None:
            bx, by = x - self._ox, y - self._oy
            bg.create_rectangle(bx + n, by, bx + w - n, by + h,
                                fill=fill, outline="", **_st)
            bg.create_rectangle(bx, by + n, bx + w, by + h - n,
                                fill=fill, outline="", **_st)
        else:
            c.create_rectangle(x + n, y, x + w - n, y + h, fill=fill,
                               outline="", **_st)
            c.create_rectangle(x, y + n, x + w, y + h - n, fill=fill,
                               outline="", **_st)
        # chunky 2px pixel border traced around the notched outline
        bd = CARD_BORDER
        c.create_rectangle(x + n, y, x + w - n, y + 2, fill=bd, outline="")
        c.create_rectangle(x + n, y + h - 2, x + w - n, y + h, fill=bd, outline="")
        c.create_rectangle(x, y + n, x + 2, y + h - n, fill=bd, outline="")
        c.create_rectangle(x + w - 2, y + n, x + w, y + h - n, fill=bd, outline="")
        # corner steps (the single pixel that sells the notch)
        for cx, cy in ((x + n - 2, y + 2), (x + w - n, y + 2),
                       (x + n - 2, y + h - 4), (x + w - n, y + h - 4)):
            c.create_rectangle(cx, cy, cx + 2, cy + 2, fill=bd, outline="")
        if accent:
            if side == "left":
                c.create_rectangle(x + 2, y + n, x + 6, y + h - n,
                                   fill=accent, outline="")
            else:                                   # top strip
                c.create_rectangle(x + n, y + 2, x + w - n, y + 6,
                                   fill=accent, outline="")

    def text(self, x, y, s, fill=TEXT, font=None, anchor="nw"):
        self.canvas.create_text(x, y, text=s, fill=fill,
                                font=font or self.f_row, anchor=anchor)

    def _no_data_notice(self, s=None):
        w = 470
        x = (self.sw - w) // 2
        y = 96
        # diagnostic counts so a stuck notice is reportable ("feed 24 / shown
        # 0" = our filters ate the field; "feed 0" = the game isn't streaming)
        diag = ""
        if s is not None:
            try:
                raw = sum(1 for d in s.all_drivers_data_1 if d.place > 0)
                diag = f"   (feed {raw} / shown {len(self._drivers(s))})"
            except Exception:
                pass
        self._begin_panel("notice", x, y, w, 50)
        self.panel(x, y, w, 50)
        self.text(x + 16, y + 14, "Waiting for replay data…" + diag,
                  fill=ACCENT, font=self.f_hdr, anchor="w")
        self.text(x + 16, y + 36,
                  "Press PLAY — RaceRoom only streams the field while the "
                  "replay is actually playing.",
                  fill=DIM, font=self.f_sub, anchor="w")

    def draw_waiting(self, s):
        running = s is not None and s.version_major == 3
        x, y, w, h = 24, 24, 430, 70
        self.panel(x, y, w, h)
        self.canvas.create_oval(x + 14, y + 16, x + 26, y + 28,
                                fill=(GREEN if running else ACCENT), outline="")
        self.text(x + 38, y + 14, "RaceRoom Overlay – running", fill=TEXT,
                  font=self.f_hdr)
        msg = ("Connected. Load a session or replay to see timing."
               if running else
               "Waiting for RaceRoom… start the game in Borderless mode.")
        self.text(x + 38, y + 42, msg, fill=DIM, font=self.f_sub)
        self.text(x + w - 14, y + h - 6, "Ctrl+Shift+Q to close",
                  fill=DIM, font=self.f_sub, anchor="se")

    def draw_hint(self):
        self.text(self.sw - 12, self.sh - 8,
                  "Ctrl+Shift+O UI off (audio stays)  ·  Ctrl+Shift+C booth"
                  "  ·  Ctrl+Shift+M mute  ·  Ctrl+Shift+Q close",
                  fill=DIM, font=self.f_sub, anchor="se")

    def draw_flags(self, s):
        """Broadcast-style flag & penalty chips, centered under the header."""
        # while the end-of-race RESULT panel is dropped down (same top-centre
        # slot), suppress the flag row — otherwise the CHEQUERED chip sits right
        # on top of the podium strip.
        if self._podium and time.time() < self._podium_until:
            return
        chips = []  # (text, fg, bg)
        f = s.flags
        sectors = [i + 1 for i in range(3) if f.sector_yellow[i] == 1]
        if f.yellow == 1 or sectors:
            txt = "YELLOW FLAG" + (" S" + "".join(map(str, sectors)) if sectors else "")
            chips.append((txt, "#000000", "#ffd23f"))
        if f.blue == 1:
            chips.append(("BLUE FLAG", "#ffffff", "#2b6cff"))
        if f.black == 1:
            chips.append(("BLACK FLAG", "#ffffff", "#101010"))
        if f.black_and_white == 1:
            chips.append(("WARNING", "#101010", "#ffffff"))
        if f.white == 1:
            chips.append(("WHITE FLAG", "#101010", "#ffffff"))
        if f.checkered == 1:
            chips.append(("CHEQUERED", "#101010", "#ffffff"))

        # penalty for the currently-viewed car
        vslot = s.vehicle_info.slot_id
        pen_names = {0: "DRIVE-THROUGH", 1: "STOP & GO", 2: "PITSTOP",
                     3: "TIME PENALTY", 4: "SLOW DOWN", 5: "DISQUALIFIED"}
        for d in self._drivers(s):
            if d.driver_info.slot_id == vslot and d.penaltyType >= 0:
                chips.append((pen_names.get(d.penaltyType, "PENALTY"),
                              "#ffffff", "#e03131"))
                break

        if not chips:
            return
        # measure & center the row of chips
        pad_in, gap, h = 12, 8, 26
        widths = [self.f_row_b.measure(t) + pad_in * 2 for t, _, _ in chips]
        total = sum(widths) + gap * (len(chips) - 1)
        x = (self.sw - total) // 2
        y = 74
        self._begin_panel("flags", x, y, total, h)
        for (txt, fg, bg), w in zip(chips, widths, strict=False):
            self.canvas.create_rectangle(x, y, x + w, y + h, fill=bg, outline="")
            self.text(x + w / 2, y + h / 2, txt, fill=fg,
                      font=self.f_row_b, anchor="center")
            x += w + gap

    def draw_penalty(self, s):
        """RaceRoom-style penalty detail: the EXACT pending penalty and how to
        serve it — drive-through, stop-and-go duration, how much time to give
        back on a slow-down, a time penalty, plus the 'next lap won't count'
        warning. Reads the authoritative penalty amounts from s.penalties."""
        if self._podium and time.time() < self._podium_until:
            return
        p = s.penalties
        vslot = s.vehicle_info.slot_id
        pdrv = next((d for d in self._drivers(s)
                     if d.driver_info.slot_id == vslot), None)
        ptype = pdrv.penaltyType if pdrv is not None else -1
        preason = getattr(pdrv, "penaltyReason", -1) if pdrv is not None else -1
        reason = self._PEN_REASON.get((ptype, preason))

        lines = []   # (big_text, sub_text)
        # the five pending-penalty amounts (-1 = none). See r3e.h:
        # drive-through active = 0.0; stop-and-go = seconds to stay; slow-down =
        # seconds still to give back; time_deduction = seconds added.
        if p.drive_through >= 0:                       # 0.0 = active, -1 = none
            lines.append(("DRIVE-THROUGH PENALTY", "Enter the pit lane to serve it"))
        if p.stop_and_go > 0.05:                       # seconds to stay in the box
            lines.append((f"STOP & GO PENALTY — STOP {int(round(p.stop_and_go))}s",
                          "Pit and stop in your box"))
        if p.pit_stop >= 0:
            lines.append(("PIT-STOP PENALTY", "Serve a pit stop"))
        if p.slow_down > 0.05:                         # seconds still to give back
            lines.append((f"SLOW DOWN — GIVE BACK {p.slow_down:.1f}s",
                          "Lift until the time is repaid"))
        if p.time_deduction > 0.05:                    # seconds added to race time
            lines.append((f"TIME PENALTY +{p.time_deduction:.1f}s",
                          "Added to your race time"))
        # generic fallback if penaltyType is set but no amount surfaced
        if not lines and ptype >= 0:
            nm = {0: "DRIVE-THROUGH PENALTY", 1: "STOP & GO PENALTY",
                  2: "PIT-STOP PENALTY", 3: "TIME PENALTY",
                  4: "SLOW-DOWN PENALTY", 5: "DISQUALIFIED"}.get(ptype, "PENALTY")
            lines.append((nm, "Penalty pending"))
        if reason and lines:
            big, sub = lines[0]
            lines[0] = (big, sub + f"  ·  for {reason}")

        # 'lap won't count' warning — TRANSIENT: it flashes up for a few seconds
        # on the rising edge, then clears (it shouldn't sit on screen all lap).
        # Real pending PENALTIES above persist (you must serve them).
        now = time.time()
        lvs = getattr(s, "lap_valid_state", -1)
        prev = getattr(self, "_pen_lvs", -1)
        if lvs in (1, 2) and lvs != prev:     # entered/escalated -> start the flash
            self._pen_lvs_at = now
        elif lvs not in (1, 2):
            self._pen_lvs_at = 0.0
        self._pen_lvs = lvs
        warn = None
        if lvs in (1, 2) and now - getattr(self, "_pen_lvs_at", 0.0) < 5.0:
            warn = ("THIS & NEXT LAP WILL NOT COUNT" if lvs == 2
                    else "LAP INVALIDATED — TRACK LIMITS")

        if not lines and not warn:
            return
        w = 460
        rh = 44
        warn_h = 24 if warn else 0
        h = rh * len(lines) + warn_h
        x = (self.sw - w) // 2
        y = 104
        self._begin_panel("penalty", x, y, w, h)
        cy = y
        for big, sub in lines:
            self._card(x, cy, w, rh, fill="#2a0d0d", accent=TALLY_RED, side="left")
            self.text(x + 16, cy + 14, big, fill="#ff5a5a",
                      font=self.f_row_b, anchor="w")
            self.text(x + 16, cy + 31, sub, fill="#ffb3b3",
                      font=self.f_small_b, anchor="w")
            cy += rh
        if warn:
            self.canvas.create_rectangle(x, cy, x + w, cy + warn_h,
                                         fill="#5a3b00", outline="")
            self.text(x + w / 2, cy + warn_h / 2, warn, fill="#ffd23f",
                      font=self.f_small_b, anchor="center")

    @staticmethod
    def _fmt_clock(t):
        """A race clock, not a lap time. M:SS, or H:MM:SS for an endurance
        length. fmt_time() is for lap times and counts milliseconds, which is
        unreadable as a countdown and wrong as a piece of broadcast furniture."""
        t = max(0, int(t))
        h, rem = divmod(t, 3600)
        m, sec = divmod(rem, 60)
        if h:
            return f"{h}:{m:02d}:{sec:02d}"
        return f"{m}:{sec:02d}"

    def _is_timed(self, s):
        # NOT _timed: the booth stores a bool on self._timed (overlay_booth),
        # and a method of that name on the same object would be shadowed by it
        # the first tick the booth ran — then called, and crash.
        """Is this session run to a clock rather than a lap count?"""
        # 0 = TimeBased, 2 = TimeAndLapBased (an extra lap after time is up).
        # See R3E.cs SessionLengthFormat. The lap-count fallback covers builds
        # or modes that leave the format unset.
        fmt = getattr(s, "session_length_format", -1)
        if fmt in (0, 2):
            return True
        if fmt == 1:
            return False
        return not (s.number_of_laps and s.number_of_laps > 0)

    def _race_clock_ok(self, s):
        """Is session_time_remaining safe to PUT ON SCREEN?

        The old header refused to show a clock in replays at all, and it was
        right to be suspicious — but the cost of that suspicion was a timed
        replay with no indication of how long was left, which is exactly the
        case that got reported. So the value is verified rather than trusted:
        it has to be in range, and it has to have been SEEN COUNTING DOWN.
        A field that never moves, or moves upward, never reaches the screen.

        One observation is enough to start, and the clock is dropped again
        the moment it stops behaving — a scrubbed replay, a new session — so
        a stale number can't sit there looking authoritative."""
        if not self._is_timed(s):
            return False
        rem = getattr(s, "session_time_remaining", 0.0) or 0.0
        dur = getattr(s, "session_time_duration", 0.0) or 0.0
        if rem <= 0.0:
            # TIME UP is a legitimate reading, not a broken one. Clearing the
            # "seen counting down" flag here would erase the very knowledge
            # _timed_over needs to tell a finished clock from a field that was
            # always zero, and the header would fall back to a bare lap number
            # for the last lap and a half of every timed race.
            return False
        if rem > max(dur, 0.0) + 60.0:
            self._clock_seen = False
            return False
        prev = getattr(self, "_clock_prev", None)
        self._clock_prev = rem
        if prev is not None:
            if rem < prev:                     # counting down, as a clock does
                self._clock_seen = True
            elif rem > prev + 1.0:             # jumped up: new session or scrub
                self._clock_seen = False
        return bool(getattr(self, "_clock_seen", False))

    def _timed_over(self, s):
        """A timed race whose clock has run out but which is still running —
        RaceRoom finishes the leader's current lap."""
        if not self._is_timed(s) or s.session_type != 2:
            return False
        rem = getattr(s, "session_time_remaining", 0.0) or 0.0
        return bool(getattr(self, "_clock_seen", False)) and rem <= 0.0

    def draw_header(self, s):
        track = R.u8_to_str(s.track_name)
        if not track:
            return
        stype = {0: "PRACTICE", 1: "QUALIFY", 2: "RACE", 3: "WARMUP"}.get(
            s.session_type, "")

        # PROGRESS. A lap race has a lap counter; a timed race has a clock, and
        # until now it had neither — reported by a viewer running 25-minute
        # races with nothing on screen to say how much of it was left.
        #
        # The clock is the headline and the lap number goes underneath it,
        # because in a timed race the lap you are on tells you nothing about
        # how much racing is left, and the clock tells you everything. That is
        # also the way every real timed-race chyron is laid out.
        #
        # The old fallback formatted the remaining time with fmt_time, which is
        # the LAP-TIME format: a race clock read "12:38.417", counting
        # milliseconds down from twenty-five minutes.
        lead_laps = max((d.completed_laps for d in self._drivers(s)), default=0)
        total = s.number_of_laps
        sub_prog = ""
        prog_col = HEADER_ACCENT
        if total and total > 0:
            prog = f"LAP {min(lead_laps + 1, total)}/{total}"
        elif self._race_clock_ok(s):
            rem = s.session_time_remaining
            prog = self._fmt_clock(rem)
            sub_prog = f"LAP {lead_laps + 1}"
            # the last minute is the story of a timed race, so it changes
            # colour rather than relying on the viewer watching the digits
            if rem <= 10.0:
                prog_col = TALLY_RED
            elif rem <= 60.0:
                prog_col = "#ffb000"
        elif self._timed_over(s):
            # TIME UP. RaceRoom's timed races run to the end of the leader's
            # current lap, so zero on the clock is not the end of the race —
            # showing "0:00" for a lap and a half would be a lie, and hiding
            # the panel would be worse.
            prog = "FINAL LAP"
            prog_col = TALLY_RED
            sub_prog = f"LAP {lead_laps + 1}"
        else:
            prog = f"LAP {lead_laps + 1}"

        # bottom-row status: a blinking LIVE / REPLAY dot + tag,
        # then the session type. Kept on the LEFT row so it can never collide
        # with the track name (top-left) or the lap counter (top-right).
        is_rep = (s.game_in_replay == 1)
        tag = "REPLAY" if is_rep else "LIVE"
        # LIVE IS RED AND REPLAY IS NOT. This read `HEADER_ACCENT if is_rep`,
        # which was fine while the chrome was cyan and broke the instant it
        # became red: the accent is #ff3b47 and the live tally was #ff3b3b, so
        # the two states were the same colour and the dot stopped meaning
        # anything. A red on-air tally is the one colour convention a
        # broadcast overlay cannot borrow for furniture.
        tcol = "#ffb000" if is_rep else TALLY_RED
        bottom = tag + (("   " + stype) if stype else "")

        # size the panel to fit BOTH rows: top (title + gap + lap) and the
        # bottom status row (dot + tag + session), so nothing overlaps
        title = track[:30]
        tw = self.f_hdr.measure(title)
        pw = max(self.f_hdr.measure(prog), self.f_sub.measure(sub_prog))
        bw = 14 + self.f_sub.measure(bottom)
        w = max(420, 16 + max(tw, bw) + 40 + pw + 16)
        x = (self.sw - w) // 2
        self._begin_panel("header", x, 14, w, 50)
        self._card(x, 14, w, 50, fill=CARD_BG2, accent=HEADER_ACCENT, side="top")
        # CRT scanlines over the chyron (every 3rd row, barely-there dark line)
        for sy in range(14 + 8, 14 + 50 - 4, 3):
            self.canvas.create_line(x + 4, sy, x + w - 4, sy, fill="#070b10")
        self.text(x + 16, 29, title, fill=TEXT, font=self.f_hdr, anchor="w")
        self.text(x + w - 16, 31, prog, fill=prog_col, font=self.f_hdr,
                  anchor="e")
        if sub_prog:
            self.text(x + w - 16, 48, sub_prog, fill=DIM, font=self.f_sub,
                      anchor="e")
        # bottom status row (blink dot leads it), retro-camcorder 1s cycle
        by = 48
        if int(time.time() * 2) % 2 == 0:
            self.canvas.create_rectangle(x + 16, by - 5, x + 23, by + 2,
                                         fill=tcol, outline="")
        self.text(x + 28, by, tag, fill=tcol, font=self.f_sub, anchor="w")
        if stype:
            self.text(x + 28 + self.f_sub.measure(tag) + 12, by, stype,
                      fill=DIM, font=self.f_sub, anchor="w")

    # ---- speedometer --------------------------------------------------------
    SPEEDO_DIAL = 168        # floor: the smallest the dial may be
    # How far ahead of the game's optimal shift point the ring lights, as
    # a fraction of the rev range. About a reaction's worth of revs.
    SPEEDO_SHIFT_LEAD = 0.035
    # ONE SIZE, AND A MODEST ONE. Asked for directly: "make it a bit smaller
    # and keep it one size".
    #
    # The size was made a setting because the dial had been reported as too
    # small twice and a single number kept being the wrong one. Three sizes
    # answered that, and then the largest of them was reported as slow — so
    # the setting had turned a question of taste into a question of cost,
    # and offered the expensive answer.
    #
    # A fifth of screen height is legible in peripheral vision without
    # dominating the corner, and the ceiling stops a 4K screen asking for a
    # 430px dial nobody wanted. The dial's cost — the face render, and the
    # layered window the game has to composite every frame — goes with its
    # AREA, so this is a little over half what LARGE was asking for.
    SPEEDO_FRAC = 0.20
    SPEEDO_MAX = 260
    SPEEDO_PAD = 9

    def draw_speedo(self, s):
        """The broadcast dial, bottom-right.

        The face itself is a cached PIL image (see speedo.py — tk's canvas has
        no antialiasing, so an arc drawn with primitives reads as pixel art);
        only the numbers are tk, whose text rendering the platform already
        antialiases.

        EVERYTHING EXCEPT SPEED IS TOP-LEVEL in RaceRoom's shared memory —
        revs, gear and the shift point describe whichever car the camera is
        on, not a car you name. For a driver that is your car; in a replay it
        follows the director's cut, which is exactly what a broadcast wants.
        It does mean the dial can only ever show one car, so it lives in a
        corner rather than in the timing tower.
        """
        if getattr(self, "speedo", "kmh") == "off" or not _SPEEDO_OK:
            return
        # SIZED TO THE SCREEN, NOT TO A NUMBER. 168px was chosen once and
        # never revisited; on a 1440p or 4K display it is a postage stamp, and
        # it was reported as "very small and isnt helpfull" on 1080p too.
        #
        # A speedo is read in peripheral vision at 200km/h, so it has to be
        # legible without being looked AT. Roughly a fifth of screen height
        # puts the digits at a size you can catch out of the corner of your
        # eye; the floor keeps the old behaviour on very small windows, where
        # a fifth of the height would swallow the corner.
        dial = max(self.SPEEDO_DIAL,
                   min(self.SPEEDO_MAX, int(self.sh * self.SPEEDO_FRAC)))
        pad = self.SPEEDO_PAD
        w = h = dial + pad * 2
        x = self.sw - w - 24
        y = self.sh - h - 24
        # published so the radio bubbles can stack ABOVE us instead of behind
        self._speedo_box = (x, y, w, h)

        # THE SCALE IS max_engine_rps, so the top of the sweep is the limiter.
        # The shift point is the game's own upshift_rps rather than a guessed
        # fraction — every car in RaceRoom carries its own, and inventing one
        # would put the amber in the wrong place on exactly the cars that need
        # it most. Cars that publish no rev data at all (some replays) still
        # get a dial: the sweep sits at zero and the speed is the readout.
        mx = float(getattr(s, "max_engine_rps", 0.0) or 0.0)
        rps = float(getattr(s, "engine_rps", 0.0) or 0.0)
        ups = float(getattr(s, "upshift_rps", 0.0) or 0.0)
        if mx > 0.0:
            rev = max(0.0, min(1.0, rps / mx))
            shift_at = max(0.35, min(0.97, ups / mx)) if ups > 0 else 0.92
        else:
            rev, shift_at = 0.0, 0.92
        # the limiter is 1.0 by construction, so the red band is the last
        # sliver of the scale; the ticks carry the zone, the sweep carries
        # the cue
        redline_at = max(shift_at + 0.01, 0.98)
        # LIT A LITTLE EARLY, ON PURPOSE. Reported: "its turning purple to
        # shift to late". `upshift_rps` is the game's OPTIMAL shift point, and
        # a light that comes on exactly there is already late by the time a
        # human has seen it and pulled the paddle — the revs keep climbing
        # through the reaction. Real shift lights lead the optimum for this
        # reason. The limiter band is still measured from the true point.
        shift_at = max(0.30, shift_at - self.SPEEDO_SHIFT_LEAD)
        # THE LIMITER FLASHES THE RING rather than turning a second colour: one
        # colour means "shift", and that colour blinking means "you are late".
        # Eight times a second, drawn by alternating a full ring with an empty
        # one, both of which the dial cache already holds.
        on_limiter = rev >= redline_at
        shown_rev = (0.0 if (on_limiter and int(time.time() * 8) % 2)
                     else rev)

        # QUANTISED, for two reasons. The key is what decides whether a face
        # is already rendered, so a float that wobbles in its third decimal
        # would miss the cache on every frame. And every distinct shift point
        # is a fresh set of 73 faces: in a REPLAY the camera cuts between
        # cars, and a cut to a car whose shift point differs by a thousandth
        # would start the whole sweep again. A hundredth of the scale is
        # ~95rpm on a 9,500rpm engine — finer than the eye reads off a dial,
        # and coarse enough that similar cars share a set.
        shift_at = round(shift_at * 100.0) / 100.0
        redline_at = round(redline_at * 100.0) / 100.0
        # EVERY face this car will need, rendered on a daemon thread. See
        # speedo.prewarm: a cold face costs more than a whole frame, and
        # accelerating hits a new one almost every frame, which is what made
        # the dial trail the engine.
        _speedo.prewarm(dial, shift_at, redline_at, CARD_BG2)

        self._begin_panel("speedo", x, y, w, h)
        self._card(x, y, w, h, fill=CARD_BG2, accent=HEADER_ACCENT, side="top")
        img = _speedo.photo(dial, shown_rev, shift_at, redline_at, CARD_BG2)
        if img is not None:
            # `_cv_real` WITH THE OFFSET APPLIED, not `self.canvas`.
            #
            # THE DIAL NEVER DREW. `canvas` returns the translating `_TC`
            # wrapper, and `_TC` proxies rectangle/oval/text/line/polygon --
            # there is no `create_image` on it at all. So this raised
            # AttributeError on every single frame, the stage loop swallowed
            # it into `_stage_err`, and the whole of `draw_speedo` after this
            # line -- the dial, the RACERTV mark, the speed, the gear -- never
            # ran. The panel drew its empty card and died.
            #
            # `speedoshot.py` passed throughout, because it calls
            # `speedo.render()` directly and never goes near this line. The
            # art was right; the one line that puts it on screen was not.
            # Found by rendering the FULL overlay rather than one component.
            self._cv_real.create_image(x + pad - self._ox, y + pad - self._oy,
                                       image=img, anchor="nw")
            self._speedo_img = img      # a canvas item does not own its image

        cx = x + w // 2
        cy = y + h // 2
        mph = (getattr(self, "speedo", "kmh") == "mph")
        # RaceRoom publishes metres per second
        v = abs(float(getattr(s, "car_speed", 0.0) or 0.0))
        v = v * (2.236936 if mph else 3.6)
        # THE READOUT SCALES WITH THE DIAL. These offsets and font sizes were
        # set for the original 168px dial and never moved when the dial became
        # screen-sized: at MEDIUM on 1080p the speed sat small in a large
        # empty face and KM/H was pressed against the digits. Everything is
        # now multiplied by the dial's size relative to that 168px original.
        k = dial / 168.0
        # warm grey rather than the old slate blue #3f4b5c: readable on the
        # resting face (6.3:1) and on the purple shift tint (4.0:1)
        self.text(cx, cy - int(44 * k), "RACERTV", fill="#a89092",
                  font=self._speedo_font(self.f_small_b, 9 * k),
                  anchor="center")
        self.text(cx, cy - int(8 * k), "%d" % int(round(v)), fill=TEXT,
                  font=self._speedo_font(self.f_spd, 20 * k), anchor="center")
        self.text(cx, cy + int(20 * k), "MPH" if mph else "KM/H", fill=DIM,
                  font=self._speedo_font(self.f_small_b, 9 * k),
                  anchor="center")

        # GEAR reads as a gear, not as the integer behind it: RaceRoom uses
        # -1 for reverse and 0 for neutral, and a dial showing "0" down a
        # straight or "-1" in the pits is just wrong.
        g = int(getattr(s, "gear", 0) or 0)
        gtxt = "R" if g < 0 else ("N" if g == 0 else str(g))
        # the gear follows the ring: purple from the shift point on
        gcol = SHIFT_PURPLE if rev >= shift_at else HEADER_ACCENT
        self.text(cx, cy + int(48 * k), gtxt, fill=gcol,
                  font=self._speedo_font(self.f_gear, 14 * k), anchor="center")
        self.draw_telemetry(s, x, y, w, h)

    def _speedo_font(self, base, size):
        """`base`'s family at `size` points, cached. The dial's readout is
        drawn every frame, and creating a Tk font per frame would leak them."""
        size = max(6, int(round(size)))
        cache = getattr(self, "_spd_font_cache", None)
        if cache is None:
            cache = self._spd_font_cache = {}
        key = (base.cget("family"), base.cget("weight"), size)
        f = cache.get(key)
        if f is None:
            import tkinter.font as _tkf
            f = cache[key] = _tkf.Font(family=key[0], weight=key[1], size=size)
        return f

    # ---- telemetry: fuel and tyres, on top of the speedo -----------------
    #
    # Asked for twice: "there is still NO telemetry". The engineer had been
    # given fuel burn and tyre calls, but that is the VOICE; nothing was on
    # screen. This sits directly on the speedo because that is where the eye
    # already goes for car state, and it widens the speedo's published box so
    # the radio cards and the caption keep clear of both.
    TELEM_H = 96

    def _tyre_state(self, s, i):
        """(wear 0..1 or None, temperature state) for tyre `i` (FL FR RL RR).

        Temperatures come from RaceRoom's OWN cold/optimal/hot figures for
        this compound, not from a guessed range: the same number is cold on
        one tyre and fine on another.
        """
        wear = None
        if getattr(s, "tire_wear_active", 0):
            try:
                w_ = float(s.tire_wear[i])
                wear = w_ if w_ >= 0 else None
            except Exception:
                wear = None
        state = None
        try:
            t = s.tire_temp[i]
            cur = float(t.current_temp[1])          # the tread's centre
            cold, hot = float(t.cold_temp), float(t.hot_temp)
            if cur > 0 and hot > cold > 0:
                state = ("cold" if cur < cold else "hot" if cur > hot
                         else "ok")
        except Exception:
            state = None
        return wear, state

    def draw_telemetry(self, s, sx, sy, sw_, sh_):
        # BESIDE THE DIAL, NOT ABOVE IT. Stacked, the pair was a tall column
        # in the bottom-right corner, and the radio cards and caption — which
        # live in that same column — sat on top of the telemetry. Side by side
        # the pair is no taller than the dial, so the cards stack clear of
        # both, and nothing in the corner is tall enough to reach them.
        h = self.TELEM_H
        w = sw_
        x = sx - w - 8
        y = sy + max(0, sh_ - h)          # bottom edges aligned with the dial
        if x < 8:                         # no room beside it on a narrow
            x, y = sx, sy - h - 8         # window — fall back to stacked
        self._begin_panel("telemetry", x, y, w, h)
        self._card(x, y, w, h, fill=CARD_BG2, accent=HEADER_ACCENT, side="top")
        pad = 12

        # FUEL — litres, and laps of fuel from the MEASURED burn when there is
        # one (the engineer's median of the last three laps), else the game's
        # own estimate. "--" rather than a made-up number when neither exists.
        self.text(x + pad, y + 18, "FUEL", fill=DIM, font=self.f_small_b,
                  anchor="w")
        fuel_txt = "--"
        if getattr(s, "fuel_use_active", 0) and s.fuel_left >= 0:
            burns = sorted(getattr(self, "_eng_burns", []) or [])
            burn = (burns[len(burns) // 2] if burns
                    else float(getattr(s, "fuel_per_lap", 0.0) or 0.0))
            laps = ("  ·  %.1f laps" % (s.fuel_left / burn)) if burn > 0 else ""
            fuel_txt = "%.1f L%s" % (s.fuel_left, laps)
        self.text(x + w - pad, y + 18, fuel_txt, fill=TEXT,
                  font=self.f_row_b, anchor="e")

        # TYRES — a 2x2 of the car seen from above. The number is wear LEFT;
        # the bar under it is temperature: cool below the compound's working
        # range, green inside it, red above. Cold being cool-toned is a
        # meaning, like purple and green on the tower, not chrome.
        col_for = {"cold": "#8fb3cf", "ok": GREEN, "hot": TALLY_RED}
        names = ("FL", "FR", "RL", "RR")
        cw = (w - pad * 3) // 2
        for i, nm in enumerate(names):
            cx0 = x + pad + (i % 2) * (cw + pad)
            cy0 = y + 34 + (i // 2) * 30
            wear, state = self._tyre_state(s, i)
            self.text(cx0, cy0 + 8, nm, fill=DIM, font=self.f_small_b,
                      anchor="w")
            if wear is None:
                wtxt, wcol = "--", DIM
            else:
                pct = int(round(wear * 100))
                wtxt = "%d%%" % pct
                wcol = TEXT if pct >= 50 else ("#ffb000" if pct >= 25
                                               else TALLY_RED)
            self.text(cx0 + cw, cy0 + 8, wtxt, fill=wcol, font=self.f_row_b,
                      anchor="e")
            self.canvas.create_rectangle(
                cx0, cy0 + 18, cx0 + cw, cy0 + 21,
                fill=col_for.get(state, CONTROL_BG), outline="")

        # THE SPEEDO'S BOX NOW INCLUDES THIS PANEL, so everything that keeps
        # clear of the speedo keeps clear of the telemetry too. The union of
        # the two, whichever way round they ended up.
        x0, y0 = min(x, sx), min(y, sy)
        self._speedo_box = (x0, y0, max(x + w, sx + sw_) - x0,
                            max(y + h, sy + sh_) - y0)

    def draw_tower(self, s):
        drivers = self._drivers(s)
        if not drivers:
            return
        is_race = (s.session_type == 2)
        # RACE: order by LIVE track position (laps + lap fraction) so an on-track
        # overtake reorders the tower the instant it happens, instead of waiting
        # for RaceRoom's `place` field to catch up (which lags the move). The row
        # NUMBER is the live rank, so order and number always agree. QUALI/
        # PRACTICE keeps RaceRoom's place (already sorted by best time).
        if is_race and self._racing:
            def _prog(d):
                f = d.lap_distance_fraction
                f = 0.0 if f < 0 else (1.0 if f > 1 else f)
                return d.completed_laps + f
            drivers.sort(key=lambda d: -_prog(d))
            for i, d in enumerate(drivers):
                self._tow_rank[d.driver_info.slot_id] = i + 1
        else:
            drivers.sort(key=lambda d: d.place)
            self._tow_rank = {}
        viewed_slot = s.vehicle_info.slot_id

        if self.compact:
            # racing mode: just the cars around you — minimal screen footprint
            vidx = next((i for i, d in enumerate(drivers)
                         if d.driver_info.slot_id == viewed_slot), None)
            rows = drivers[max(0, vidx - 4):vidx + 5] if vidx is not None else drivers[:9]
            w, rh, pos_w, name_len = 284, 22, 28, 12
            font, fontb = self.f_tow, self.f_tow_b
        else:
            rows = drivers[:MAX_ROWS]
            # slim + tall like a broadcast timing tower (was 320 wide = too square)
            w, rh, pos_w, name_len = 274, 21, 26, 12
            font, fontb = self.f_tow, self.f_tow_b

        x, y = 30, 110
        hdr_h = 16
        c2_x = x + w - 8                 # far value column (right edge)
        c1_x = x + w - 58                # near value column
        # the two columns mean different things by session: a RACE shows the gap
        # to the car ahead + the gap to the leader; QUALI/PRACTICE shows each
        # driver's best lap time + the gap to provisional pole (just like F1 TV)
        lbl1, lbl2 = ("INT", "LEAD") if is_race else ("TIME", "GAP")
        pole = None                      # provisional pole time (quali/practice)
        if not is_race:
            bts = [self.best_lap.get(d.driver_info.slot_id) for d in rows]
            bts = [t for t in bts if t]
            pole = min(bts) if bts else None
        # broadcast logo strip sitting on TOP of the tower (like F1 TV)
        strip_h = (self.tower_logo.height() + 10) if self.tower_logo else 0
        self._begin_panel("tower", x, y, w, strip_h + hdr_h + rh * len(rows))
        c = self.canvas

        if strip_h:
            c.create_rectangle(x, y, x + w, y + strip_h, fill="#0a0d12",
                               outline=PANEL_OUTLINE, stipple=PANEL_STIPPLE)
            # image isn't proxied by the translating canvas — draw on the real
            # panel canvas at panel-local coords (like the avatars do)
            self._cv_real.create_image((x + w / 2) - self._ox,
                                       (y + strip_h / 2) - self._oy,
                                       image=self.tower_logo, anchor="center")
        hy = y + strip_h                 # header row sits below the logo strip
        c.create_rectangle(x, hy, x + w, hy + hdr_h, fill="#0a0d12",
                           outline=PANEL_OUTLINE, stipple=PANEL_STIPPLE)
        self.text(x + pos_w + 18, hy + hdr_h / 2, "DRIVER", fill=DIM, font=fontb, anchor="w")
        self.text(c1_x, hy + hdr_h / 2, lbl1, fill=DIM, font=fontb, anchor="e")
        self.text(c2_x, hy + hdr_h / 2, lbl2, fill=DIM, font=fontb, anchor="e")
        ry = hy + hdr_h

        for d in rows:
            di = d.driver_info
            slot = di.slot_id
            pos = self._tow_rank.get(slot, d.place)   # live rank in a race
            is_viewed = (viewed_slot >= 0 and slot == viewed_slot)
            is_leader = (pos == 1)
            holds_fl = (self.fastest["slot"] is not None and slot == self.fastest["slot"])

            # position-change flash: the row glows green (gained) / red (lost)
            # for ~1s after a confirmed place change, then settles back
            fl = getattr(self, "_row_flash", {}).get(slot)
            row_bg = "#1b222b" if is_viewed else "#0e1217"
            if fl and time.time() < fl[1]:
                row_bg = fl[0]
            c.create_rectangle(x, ry, x + w, ry + rh,
                               fill=row_bg,
                               outline=PANEL_OUTLINE, stipple=PANEL_STIPPLE)
            if holds_fl:
                c.create_rectangle(x, ry, x + 5, ry + rh, fill=PURPLE, outline="")

            box = ACCENT if is_viewed else (LEADER if is_leader else "#212a30")
            c.create_rectangle(x, ry, x + pos_w, ry + rh, fill=box, outline="")
            self.text(x + pos_w / 2, ry + rh / 2, str(pos),
                      fill=("#000000" if (is_viewed or is_leader) else TEXT),
                      font=fontb, anchor="center")

            # grid-delta arrow only matters in a race; reclaim the space otherwise
            if is_race:
                # against the LIVE rank too: a gained/lost arrow computed
                # from the lagging field disagreed with the number beside it
                delta = (self.grid_place.get(slot, d.place)
                         - self._tow_rank.get(slot, d.place))
                arr, acol = (("▲", GREEN) if delta > 0
                             else ("▼", "#ff6b6b") if delta < 0 else ("–", DIM))
                self.text(x + pos_w + 7, ry + rh / 2, arr, fill=acol,
                          font=self.f_tow, anchor="center")
                tx = x + pos_w + 17
            else:
                tx = x + pos_w + 9
            c.create_oval(tx - 4, ry + rh / 2 - 4, tx + 4, ry + rh / 2 + 4,
                          fill=self._tyre_color(d), outline="#000000")

            name = (R.u8_to_str(di.name) or "---").upper()
            self.text(tx + 9, ry + rh / 2,
                      f"{di.car_number:>2} {name[:name_len]}",
                      fill=(ACCENT if is_viewed else self._color_for(d)),
                      font=(fontb if is_viewed else font), anchor="w")

            if d.ptp_state == 1:
                self.text(c1_x - 46, ry + rh / 2, "P2P", fill=CYAN,
                          font=fontb, anchor="e")
            elif d.drs_state == 1:
                self.text(c1_x - 46, ry + rh / 2, "DRS", fill=GREEN,
                          font=fontb, anchor="e")

            if is_race:
                if d.in_pitlane == 1:
                    self.text(c2_x, ry + rh / 2, "PIT", fill="#ffa94d",
                              font=fontb, anchor="e")
                elif is_leader:
                    self.text(c2_x, ry + rh / 2, "LDR" if self.compact else "LEADER",
                              fill=LEADER, font=font, anchor="e")
                else:
                    itv = self.interval.get(slot)
                    if holds_fl:
                        # FL sits in the INT column — no name-column overlap
                        self.text(c1_x, ry + rh / 2, "FL",
                                  fill=PURPLE, font=fontb, anchor="e")
                    elif itv is not None and itv > 0.05:
                        close = itv < 1.0
                        self.text(c1_x, ry + rh / 2, f"{itv:.1f}",
                                  fill=("#ffffff" if close else DIM),
                                  font=(fontb if close else font), anchor="e")
                    cg = self.cum_gap.get(slot)
                    if cg is not None and cg > 0.05:
                        self.text(c2_x, ry + rh / 2, f"+{cg:.1f}",
                                  fill=(GREEN if is_viewed else DIM), font=font, anchor="e")
            else:
                # QUALI / PRACTICE: best lap time + gap to provisional pole
                bt = self.best_lap.get(slot)
                if bt:
                    self.text(c1_x, ry + rh / 2, R.fmt_time(bt),
                              fill=("#ffffff" if is_leader else TEXT),
                              font=(fontb if (is_leader or is_viewed) else font),
                              anchor="e")
                    if pole and bt > pole + 0.001:
                        self.text(c2_x, ry + rh / 2, f"+{bt - pole:.3f}",
                                  fill=(GREEN if is_viewed else DIM), font=font,
                                  anchor="e")
                    elif is_leader:
                        self.text(c2_x, ry + rh / 2, "POLE", fill=PURPLE,
                                  font=font, anchor="e")
                else:
                    tag = "PIT" if d.in_pitlane == 1 else "RUN"
                    self.text(c1_x, ry + rh / 2, tag, fill=DIM, font=font, anchor="e")
            ry += rh

    def draw_relative(self, s):
        vslot = s.vehicle_info.slot_id
        if vslot < 0:
            self._rel_box = None                 # tower not drawn — see draw_objective
            return
        # ORDERED BY LIVE TRACK POSITION, like the tower beside it.
        #
        # Reported by a tester: "the position order doesn't update immediately
        # and takes a while to register". The tower stopped trusting
        # RaceRoom's `place` field years ago — its own comment says the field
        # "lags the move" — but the relative panel was still sorted by it and
        # still PRINTED it, and the relative panel is the one you actually
        # watch while racing. So an overtake reordered the tower at once and
        # left the panel under your eyes a beat behind.
        #
        # It is also the more correct sort for this panel: "the cars around
        # me" means around me ON TRACK, which is what lap + lap fraction says
        # and what a `place` waiting to catch up does not.
        if (s.session_type == 2 and getattr(self, "_racing", False)):
            def _rprog(d):
                f = d.lap_distance_fraction
                f = 0.0 if f < 0 else (1.0 if f > 1 else f)
                return d.completed_laps + f
            order = sorted(self._drivers(s), key=lambda d: -_rprog(d))
        else:
            order = sorted(self._drivers(s), key=lambda d: d.place)
        idx = next((i for i, d in enumerate(order)
                    if d.driver_info.slot_id == vslot), None)
        if idx is None or len(order) < 2:
            self._rel_box = None                 # tower not drawn — see draw_objective
            return
        lo = max(0, idx - 3)
        hi = min(len(order), idx + 4)
        window = order[lo:hi]
        focus_cg = self.cum_gap.get(vslot)

        w, rh = 300, 24
        x = self.sw - w - 30
        y = 110
        _h = 22 + rh * len(window)
        # remember the footprint so the objective chip can dock beneath it
        # instead of sitting centre-screen over the sectors and captions
        self._rel_box = (x, y, w, _h)
        self._begin_panel("relative", x, y, w, _h)
        c = self.canvas
        c.create_rectangle(x, y, x + w, y + 22, fill="#0a0d12",
                           outline=PANEL_OUTLINE)
        self.text(x + 10, y + 11, "RELATIVE", fill=DIM, font=self.f_row_b, anchor="w")
        self.text(x + w - 10, y + 11, "GAP", fill=DIM, font=self.f_row_b, anchor="e")
        ry = y + 22
        for d in window:
            di = d.driver_info
            is_focus = (di.slot_id == vslot)
            c.create_rectangle(x, ry, x + w, ry + rh,
                               fill=("#1b222b" if is_focus else "#0e1217"),
                               outline=PANEL_OUTLINE, stipple=PANEL_STIPPLE)
            # the LIVE rank the tower computed this frame, so the two panels
            # can never disagree about who is where
            _pos = self._tow_rank.get(di.slot_id, d.place)
            self.text(x + 10, ry + rh / 2, f"{_pos:>2}", fill=DIM,
                      font=self.f_row, anchor="w")
            c.create_oval(x + 34, ry + rh / 2 - 5, x + 44, ry + rh / 2 + 5,
                          fill=self._tyre_color(d), outline="#000000")
            name = (R.u8_to_str(di.name) or "---").upper()
            self.text(x + 52, ry + rh / 2, f"{di.car_number:>3} {name[:13]}",
                      fill=(ACCENT if is_focus else self._color_for(d)),
                      font=(self.f_row_b if is_focus else self.f_row), anchor="w")
            cg = self.cum_gap.get(di.slot_id)
            if is_focus:
                rel = "◀"  # marker for the followed car
                col = ACCENT
            elif cg is not None and focus_cg is not None:
                diff = cg - focus_cg
                rel = f"{diff:+.1f}"
                col = "#ff8787" if diff < 0 else GREEN
            else:
                rel, col = "", DIM
            self.text(x + w - 10, ry + rh / 2, rel, fill=col,
                      font=self.f_row, anchor="e")
            ry += rh

    def draw_fastest_banner(self, s):
        fl = self.fastest
        if fl["time"] is None:
            return
        age = time.time() - fl["at"]
        if age > 10.0:               # don't leave it on screen forever
            return
        fresh = age < 6.0
        w, h = 360, 28
        x = (self.sw - w) // 2
        y = self.sh - 104
        self._begin_panel("fastest", x, y, w, h)
        self.canvas.create_rectangle(x, y, x + w, y + h,
                                     fill=(PURPLE if fresh else "#1a1326"),
                                     outline=PURPLE)
        fg = "#000000" if fresh else PURPLE
        self.text(x + 12, y + h / 2, "● FASTEST LAP", fill=fg,
                  font=self.f_row_b, anchor="w")
        self.text(x + w - 12, y + h / 2,
                  f"#{fl['car']} {fl['name'][:12]}  {R.fmt_time(fl['time'])}",
                  fill=fg, font=self.f_row_b, anchor="e")

    # Per-KIND accent colour — the whole card (icon, left rail, label, progress)
    # takes its identity from what sort of objective it is, so you read the type
    # by colour before you read a word. Resolved cards stay green/red (universal
    # for done/failed) regardless of kind.
    OBJ_KIND_COL = {
        "position": "#ffcf33", "chase": "#ffcf33", "recover": "#ffcf33",  # gold
        "defend": "#3aa8ff", "damage": "#3aa8ff",                          # blue
        "clean": "#ff5b5b",                                                # red
        "leadhome": "#f4f6f9",                                             # white
        "pole": "#c77dff",                                                 # purple
        "pb": "#69db7c",                                                   # green
        "consistency": "#69db7c",                                          # green
        "tyres": "#ff9f40",                                                # orange
    }

    def _obj_icon(self, obj, res, cx, cy, badge, glyph="#4fd6e0"):
        """Draw the objective's glyph, centred on (cx, cy).

        VECTOR PRIMITIVES, NOT AN SVG FILE. tk has no SVG rasteriser, and
        adding one (cairosvg/PIL) would mean a new dependency inside the
        PyInstaller bundle for something that is a dozen rectangles.

        The glyph is drawn in `glyph` (the card's per-kind colour) on the
        transparent card — no solid block behind it. Each KIND gets its own
        shape; where a position is involved the number sits on the glyph.
        """
        c = self.canvas
        ink = glyph                        # glyph is drawn in the kind colour
        # knock-out colour for a number sitting ON a filled shape (podium step)
        ko = CARD_BG

        def box(x1, y1, x2, y2):
            c.create_rectangle(cx + x1, cy + y1, cx + x2, cy + y2,
                               fill=ink, outline="")

        def num(txt, fill, dx=0, dy=0):
            self.text(cx + dx, cy + dy, str(txt)[:2], fill=fill,
                      font=self.f_small_b, anchor="center")

        # ---- RESOLVED: a tick or a cross
        if res is not None and not obj:
            if res.get("ok"):
                c.create_line(cx - 8, cy, cx - 2, cy + 6, cx + 9, cy - 7,
                              fill=ink, width=4, capstyle="round",
                              joinstyle="round")
            else:
                c.create_line(cx - 7, cy - 7, cx + 7, cy + 7, fill=ink,
                              width=4, capstyle="round")
                c.create_line(cx + 7, cy - 7, cx - 7, cy + 7, fill=ink,
                              width=4, capstyle="round")
            return

        kind = (obj or {}).get("kind", "")
        goal = (obj or {}).get("goal_pos")

        if kind in ("position", "chase", "recover"):
            # PODIUM: three steps, centre tallest, target position on it.
            box(-13, 0, -4, 9)             # left step
            box(-3, -8, 6, 9)              # centre step (tallest)
            box(7, -3, 16, 9)              # right step
            if goal:
                num(goal, ko, dx=1, dy=-1)  # knocked out of the coloured step
        elif kind in ("defend", "damage"):
            # SHIELD: holding what you have. Outlined, so the number sits in the
            # open interior and reads in the glyph colour.
            c.create_polygon(cx - 11, cy - 10, cx + 11, cy - 10, cx + 11, cy - 1,
                             cx, cy + 11, cx - 11, cy - 1,
                             fill="", outline=ink, width=3)
            if goal:
                num(goal, ink, dy=-2)
        elif kind == "clean":
            # TRACK LIMITS: a plain circle with an X through it.
            c.create_oval(cx - 11, cy - 11, cx + 11, cy + 11, outline=ink,
                          width=3)
            c.create_line(cx - 6, cy - 6, cx + 6, cy + 6, fill=ink, width=3,
                          capstyle="round")
            c.create_line(cx + 6, cy - 6, cx - 6, cy + 6, fill=ink, width=3,
                          capstyle="round")
        elif kind == "consistency":
            # EQUAL BARS: four bars of the SAME height read as "steady /
            # repeatable laps" — consistency at a glance.
            for i in range(4):
                box(-13 + i * 7, -8, -9 + i * 7, 9)
        elif kind == "tyres":
            # TYRE: ring with tread ticks
            c.create_oval(cx - 12, cy - 12, cx + 12, cy + 12, outline=ink,
                          width=4)
            for dx, dy in ((0, -12), (0, 12), (-12, 0), (12, 0)):
                box(dx - 2, dy - 2, dx + 2, dy + 2)
        elif kind == "leadhome":
            # CHEQUERED FLAG: the finish, which is the whole job
            box(-13, -12, -10, 12)         # pole
            for r in range(3):
                for q in range(4):
                    if (r + q) % 2 == 0:
                        box(-9 + q * 6, -11 + r * 6, -3 + q * 6, -5 + r * 6)
        elif kind in ("pb", "pole"):
            # STOPWATCH: a lap-time target
            c.create_oval(cx - 11, cy - 8, cx + 11, cy + 12, outline=ink,
                          width=3)
            box(-3, -13, 3, -9)            # crown
            c.create_line(cx, cy + 2, cx, cy - 4, fill=ink, width=3)
            c.create_line(cx, cy + 2, cx + 6, cy + 2, fill=ink, width=3)
        else:
            # fallback: the old text badge, so an unknown kind still shows
            self.text(cx, cy - 1, str(badge)[:3], fill=ink,
                      font=self.f_row_b, anchor="center")

    def draw_objective(self, s):
        """The active race objective as a COMPETITIVE broadcast target chip.

        Built on _card() like every other panel, so it carries the graphics
        package's signature frame: notched corners, the chunky 2px border and
        the stippled glass body. It used to be a hand-rolled skewed
        parallelogram with a plain polygon outline — a different visual
        language from the rest of the HUD, which is exactly why it read as
        flat and unfinished next to the other cards.

        What makes it an OBJECTIVE card rather than a generic one is the
        content, not a different frame: a solid accent block carrying the goal
        position, the target on its own line, a live gap with a trend arrow,
        and a SEGMENTED progress strip that fills like a rev bar and turns
        amber then green as you close it out. Shows the verdict for a few
        seconds when a target resolves, so the screen always agrees with what
        the engineer just said.
        """
        now = time.time()
        res = getattr(self, "_obj_result", None)
        obj = getattr(self, "_obj", None)
        if not obj and not (res and now < res.get("until", 0)):
            self._obj_box = None          # not drawn — see draw_radio
            return
        # DOCKED UNDER THE RELATIVE TOWER. Centre-screen it overlapped the
        # sector-time block and the lower-third caption; here it sits in the
        # right-hand column with the rest of the timing information, and
        # follows the tower as it grows and shrinks with the field.
        # Dock under the relative tower. draw_relative runs right before this
        # every frame and NULLS _rel_box on its early-return paths (tower not
        # drawn), so a non-None box reliably means the tower is on screen this
        # frame — no stale-box docking onto empty space or, worse, the fallback
        # landing on the tower.
        rel = getattr(self, "_rel_box", None)
        if rel:
            rx, ry_, rw, rh_ = rel
            w = rw                               # match the tower's width
            x = rx
            y = ry_ + rh_ + 8
        else:
            # FALLBACK: no tower this frame. Dock where a FULL tower would end
            # (110 + max 7 rows + gap), NOT at y=110 — the old fallback sat
            # exactly on the relative tower's rows and overlapped it whenever
            # the box went momentarily stale.
            w = 300
            x = self.sw - w - 30
            y = 110 + (22 + 24 * 7) + 8
        h = 62
        # remember the footprint so the radio bubble stack (bottom-anchored,
        # same right-hand column) knows not to climb up into this card
        self._obj_box = (x, y, w, h)
        self._begin_panel("objective", x, y, w, h)

        if obj:
            label = "TARGET"
            col = self.OBJ_KIND_COL.get(obj.get("kind", ""), HEADER_ACCENT)
            txt = obj.get("hud", "")
            prog = obj.get("_prog")
            badge = obj.get("_badge") or "GO"
        else:
            ok = res.get("ok")
            label = "TARGET MET" if ok else "TARGET MISSED"
            col = GREEN if ok else "#ff6b6b"
            txt = res.get("hud", "")
            prog = 1.0 if ok else None
            badge = "✓" if ok else "✕"

        # --- the standard pixel card, with the accent rail down the left.
        # _card() owns the notched corners, the chunky border and the glass
        # body, so this panel now matches the tower, the relative and the
        # radio bubbles instead of inventing its own shape.
        self._card(x, y, w, h, accent=col, side="left")
        n = 3                                    # _card's corner notch
        # a slow blink while the target is NEW — two frames a second, no
        # animation machinery, impossible to miss out of the corner of your
        # eye. Drawn as an overlay border so _card keeps ownership of the frame.
        if bool(obj) and now < obj.get("_new_until", 0) and int(now * 2) % 2 == 0:
            c = self.canvas
            c.create_rectangle(x + n, y, x + w - n, y + 2, fill=col, outline="")
            c.create_rectangle(x + n, y + h - 2, x + w - n, y + h,
                               fill=col, outline="")
            c.create_rectangle(x, y + n, x + 2, y + h - n, fill=col, outline="")
            c.create_rectangle(x + w - 2, y + n, x + w, y + h - n,
                               fill=col, outline="")
        # goal badge — the "what am I racing for". The glyph is drawn in the
        # card's kind colour on the transparent card (no block, no glow); the
        # colour alone tells you the objective type at a glance.
        bxw = 44
        self._obj_icon(obj, res, x + 8 + bxw // 2, y + h // 2, badge, glyph=col)

        # --- label + live status on the top line
        tx = x + 8 + bxw + 12
        self.text(tx, y + 15, label, fill=col, font=self.f_small_b, anchor="w")
        status, scol = "", DIM
        if obj:
            left = obj.get("_laps_left")
            if left is not None:
                status = f"{left} LAP{'S' if left != 1 else ''}"
                if left <= 1:
                    scol = "#ff6b6b"             # last chance — make it shout
            g = obj.get("_gap")
            if g is not None:
                trend = obj.get("_trend")        # -1 closing, +1 slipping
                arrow = "▼" if trend == -1 else "▲" if trend == 1 else "•"
                status = (status + "   " if status else "") + f"{arrow} {g:.1f}s"
        # MEASURE, don't guess. The card is only as wide as the relative tower
        # above it, which shrinks with the field — so a fixed character count
        # let "TARGET MISSED" run straight into "4 LAPS  ▼ 1.8s" on a narrow
        # card, and a long target name run past the right edge. Both were
        # visible as overlapping text.
        def _clip(txt_, fnt, avail):
            """Trim to the widest prefix that fits, with an ellipsis."""
            try:
                if fnt.measure(txt_) <= avail:
                    return txt_
                for n in range(len(txt_) - 1, 0, -1):
                    if fnt.measure(txt_[:n] + "…") <= avail:
                        return txt_[:n] + "…"
                return ""
            except Exception:
                return txt_[:34]

        if status:
            try:
                lab_end = tx + self.f_small_b.measure(label) + 12
                room = (x + w - 14) - lab_end
                # the gap+trend is the live part and matters most; the lap
                # count is the first thing to go when there isn't room
                if self.f_small_b.measure(status) > room and "   " in status:
                    status = status.split("   ", 1)[1]
                status = _clip(status, self.f_small_b, max(0, room))
            except Exception:
                pass
        if status:
            self.text(x + w - 14, y + 15, status, fill=scol,
                      font=self.f_small_b, anchor="e")

        # --- the objective itself
        self.text(tx, y + 34, _clip(txt, self.f_row, (x + w - 14) - tx),
                  fill=TEXT, font=self.f_row, anchor="w")

        # --- SEGMENTED progress strip (rev-bar feel), amber then green.
        # Segments are sized to the space AVAILABLE, not fixed, so the bar can
        # always reach 100% however narrow the docked chip is.
        #
        # SMOOTH TRACKING: the displayed fill EASES toward the real progress
        # each frame instead of snapping, and the LEADING segment fills
        # fractionally — so a hold objective (which only gains a lap at the
        # line) still shows the bar creeping the whole way round, and a closing
        # gap glides rather than stepping. A new target resets the fill to empty
        # so it visibly grows; a resolved one eases on up to full. This is the
        # 'track better / more information' the bar was missing.
        target = (prog if prog is not None
                  else 1.0 if (res and res.get("ok")) else 0.0)
        key = obj.get("set_at") if obj else "res"
        if getattr(self, "_obj_prog_key", None) != key:
            self._obj_prog_key = key
            # a brand-new objective starts empty and grows; a resolve keeps the
            # current fill and eases it on to the verdict
            self._obj_prog_shown = 0.0 if obj else getattr(self, "_obj_prog_shown", 0.0)
        shown = getattr(self, "_obj_prog_shown", target)
        shown += (target - shown) * 0.25                 # ease (~0.2s to settle)
        if abs(target - shown) < 0.004:
            shown = target
        shown = max(0.0, min(1.0, shown))
        self._obj_prog_shown = shown

        segs, gap_ = 14, 3
        bx = tx
        bx_end = x + w - 14
        sw_ = max(4, int((bx_end - bx - gap_ * (segs - 1)) / segs))
        by, bh = y + h - 12, 5
        c_lit = (GREEN if shown >= 0.85 else "#ffb000" if shown >= 0.5 else col)
        filled = shown * segs                            # float: sub-segment fill
        for i in range(segs):
            sx = bx + i * (sw_ + gap_)
            if sx + sw_ > bx_end + 1:
                break
            # dark base for every segment...
            self.canvas.create_rectangle(sx, by, sx + sw_, by + bh,
                                         fill=CONTROL_BG, outline="")
            # ...then the lit portion, the leading segment filled fractionally
            frac = max(0.0, min(1.0, filled - i))
            if frac > 0:
                litw = max(1, int(round(sw_ * frac)))
                self.canvas.create_rectangle(sx, by, sx + litw, by + bh,
                                             fill=c_lit, outline="")

        # --- HOLD-STATE GLOW on the border. The resolver already runs every
        # verdict through a debounce (_obj_held: a gained place must stick, a
        # lost one must stay lost) — but that deliberation was invisible, so a
        # rival nosing ahead for two corners LOOKED instantly fatal on the HUD
        # even though the maths was still waiting. The border now shows the
        # deliberation: it warms toward green while a gain is maturing, toward
        # red while a loss is counting down, brightening ring by ring as the
        # hold approaches its verdict (tk has no alpha — the ramp is stacked
        # inset outlines, same trick as the clock glow). A resolved card glows
        # at full strength in its verdict colour for its whole result window.
        # Rings sit INSIDE the card edge: the panel window is exactly card-
        # sized, so anything drawn outside it would simply be clipped away.
        glow = None
        if res is not None and not obj:
            glow = ((GREEN if res.get("ok") else "#ff6b6b"), 1.0)
        elif obj:
            for k, dur, colr in (("lose", OBJ_HOLD_LOSE, "#ff6b6b"),
                                 ("drop", OBJ_HOLD_LOSE, "#ff6b6b"),
                                 ("pass", OBJ_HOLD_GAIN, GREEN),
                                 ("close", OBJ_HOLD_GAIN, GREEN),
                                 ("gain", OBJ_HOLD_GAIN, GREEN),
                                 ("clear", OBJ_DEFEND_CLEAR_HOLD, GREEN)):
                t0 = obj.get("_hold_" + k)
                if t0:
                    glow = (colr, max(0.15, min(1.0, (now - t0) / dur)))
                    break
        if glow is not None:
            gcol, gfrac = glow
            rings = ((("#12331b", "#1e5c30", GREEN) if gcol == GREEN
                      else ("#331212", "#5c1e1e", "#ff6b6b")))
            # 1..3 rings, outside-in: faint outer hint first, the bright inner
            # ring only once the hold is nearly decided (or already resolved)
            nring = 1 + min(2, int(gfrac * 2.999))
            for (off, cring) in tuple(zip((4, 2, 0), rings))[:nring]:
                self.canvas.create_rectangle(x + off, y + off,
                                             x + w - off, y + h - off,
                                             outline=cring, width=2)

    def draw_settings(self):
        """Clickable '≡ SETTINGS' chip pinned to the game's top-left (under
        the clock) + a toggle menu, so testers never need the hotkeys. Clicks
        are POLLED and hit-tested against the rects recorded LAST frame (the
        overlay is click-through, so tk mouse events can't be trusted)."""
        click = getattr(self, "_click", None)
        if click is not None:
            for (rx, ry, rw, rh), action in getattr(self, "_menu_hits", []):
                if rx <= click[0] < rx + rw and ry <= click[1] < ry + rh:
                    action()
                    break
        self._menu_hits = []
        # ICON ONLY. This corner carried "● OVERLAY: waiting for RaceRoom",
        # "≡ SETTINGS" and a bold ticking clock stacked on top of each other —
        # three lines of chrome shouting over the game before a lap is turned.
        # The hamburger already WAS the icon; the word next to it was pure
        # width. A square chip on the clock row: [≡] [14:49:07].
        gear_x, _ = self._corner_layout()
        gx, gy = gear_x, self.CORNER_Y
        gw = gh = self.CORNER_GEAR_W
        self._begin_panel("gear", gx, gy, gw, gh)
        open_ = getattr(self, "_menu_open", False)
        # NO _card() here, deliberately. The standard panel frame — notched
        # corners, chunky border, accent rail down the left — is right for a
        # timing panel and absurd on a 29px button: the rail plus three
        # horizontal strokes read as the spine and lines of a notepad icon
        # rather than a menu. A plain slab matching the clock's panel next to
        # it lets the three strokes be the whole icon.
        c = self.canvas
        c.create_rectangle(gx, gy, gx + gw, gy + gh, fill=CARD_BG2,
                           outline=(HEADER_ACCENT if open_ else PANEL_OUTLINE))
        # DRAWN, not typed. This was "≡" in the mono pixel face: three cramped
        # hairlines at whatever weight and spacing the font chose, sitting on
        # the font's baseline instead of in the middle of the chip. Strokes in
        # the clock's accent tie the two halves of the corner together.
        ink = TEXT if open_ else HEADER_ACCENT
        bx, by = gx + gw // 2, gy + gh // 2
        for dy in (-5, 0, 5):
            c.create_line(bx - 6, by + dy, bx + 6, by + dy,
                          fill=ink, width=2, capstyle="round")
        self._menu_hits.append(((gx, gy, gw, gh), self._menu_flip))
        # the ● OVERLAY chip is its own tk window whose click events don't
        # arrive over the game — give it the same polled treatment
        try:
            bx = self.btn_win.winfo_rootx() - self.game_x
            by = self.btn_win.winfo_rooty() - self.game_y
            bw, bh = self.btn_win.winfo_width(), self.btn_win.winfo_height()
            if bw > 1:
                self._menu_hits.append(((bx, by, bw, bh), self._do_toggle_ui))
        except Exception:
            pass
        if not open_:
            return
        # A SECOND PAGE, not a second window. The overlay is click-through
        # with POLLED clicks, so a modal dialog would have nowhere to live and
        # nothing to receive its events. The designer is the same menu slab
        # with a different row set.
        if getattr(self, "_menu_page", "main") == "helmet":
            self._draw_helmet_page(x=gx, y=gy + gh + 6)
            return
        tts_on = bool(self.tts and getattr(self.tts, "enabled", False))
        rows = [
            ("Overlay UI (audio stays on)",
             "ON" if self.visible else "OFF", self.visible,
             self._do_toggle_ui),
            ("Booth — Miles & Brett",
             "ON" if self.commentary_on else "OFF", self.commentary_on,
             self._do_toggle_booth),
            ("Spectator mode — broadcast only",
             "ON" if self.spectator else "OFF", self.spectator,
             self._do_toggle_spectator),
            # READS `spectating`, NOT `spectator`: in a replay the radio is
            # genuinely off, and a menu still claiming "ON" would be lying
            # about the one thing the row exists to report. The row ABOVE
            # deliberately keeps reading `spectator`, because that is the
            # setting the toggle writes.
            ("Team radio — engineer + drivers",
             "MUTED" if self.spectating else ("ON" if self.radio_on else "MUTED"),
             self.radio_on and not self.spectating,
             self._do_toggle_radio),
            ("All voices (booth + radio)",
             "ON" if tts_on else "MUTED", tts_on,
             self._do_toggle_mute),
            ("Speedometer",
             {"off": "OFF", "kmh": "KM/H", "mph": "MPH"}[
                 getattr(self, "speedo", "kmh")],
             getattr(self, "speedo", "kmh") != "off",
             self._do_cycle_speedo),
            ("Race objectives",
             "ON" if getattr(self, "objectives_on", True) else "OFF",
             getattr(self, "objectives_on", True),
             self._do_toggle_objectives),
            ("Compact timing tower",
             "ON" if self.compact else "OFF", self.compact,
             self._do_toggle_compact),
            ("Debug HUD",
             "ON" if self.debug else "OFF", self.debug,
             self._do_toggle_debug),
            ("My helmet…", self._helmet_words(), True,
             lambda: self._menu_goto("helmet")),
            ("Close RacerTV", "✕", False, self.quit),
        ]
        # sized for the mono pixel font: longest label + state column
        w = max(360, max(self.f_row.measure(r[0]) for r in rows) + 96)
        rh = 28
        h = 14 + rh * (len(rows) + 1)          # +1 for the volume slider
        x, y = gx, gy + gh + 6
        self._begin_panel("menu", x, y, w, h)
        self._card(x, y, w, h, fill=CARD_BG, accent=HEADER_ACCENT, side="left")
        ry = y + 8
        for label, state, ok, action in rows:
            self.text(x + 14, ry + 12, label, fill=TEXT, font=self.f_row,
                      anchor="w")
            self.text(x + w - 14, ry + 12, state,
                      fill=(GREEN if ok else DIM), font=self.f_row_b,
                      anchor="e")
            self._menu_hits.append(((x + 2, ry, w - 4, rh), action))
            ry += rh
        self._draw_volume_row(x, ry, w, rh)

    # ---- the helmet designer page --------------------------------------
    def _helmet_words(self):
        """The design in words, for the row that opens the page."""
        try:
            import helmet as helmet_mod
            spec = getattr(self, "_my_helmet", None)
            if not spec:
                return "FROM MY NAME"
            return helmet_mod.describe(spec).upper()[:22]
        except Exception:
            return ""

    def _colour_name(self, hexc):
        """'#e8202a' -> 'red'. The menu shows words; a hex code is not a
        choice anybody makes with two arrow buttons."""
        try:
            import helmet as helmet_mod
            return {h.lower(): n for n, h in helmet_mod.PALETTE}.get(
                str(hexc or "").lower(), str(hexc or ""))
        except Exception:
            return str(hexc or "")

    def _draw_spin_row(self, x, ry, w, rh, label, field, shown):
        """One field, with an arrow either side of its value.

        The arrows get their OWN hit boxes and the row does not — clicking
        the label must do nothing, because on a click-through overlay a stray
        click near a control should never change a setting silently.
        """
        c = self.canvas
        self.text(x + 14, ry + 12, label, fill=TEXT, font=self.f_row,
                  anchor="w")
        bw = 20
        rx = x + w - 14
        # value sits between the two arrows, right-aligned block
        ax1 = rx - bw
        ax0 = rx - bw - 8 - max(64, self.f_row_b.measure(shown)) - 8 - bw
        for bx, step, glyph in ((ax0, -1, "◀"), (ax1, +1, "▶")):
            c.create_rectangle(bx, ry + 4, bx + bw, ry + rh - 4,
                               fill=CONTROL_BG, outline=PANEL_OUTLINE)
            self.text(bx + bw / 2.0, ry + 12, glyph, fill=TEXT,
                      font=self.f_row, anchor="c")
            self._menu_hits.append(
                ((bx, ry + 2, bw, rh - 4),
                 (lambda f=field, st=step: self._helmet_spin(f, st))))
        self.text((ax0 + bw + ax1) / 2.0 + 4, ry + 12, shown,
                  fill=GREEN, font=self.f_row_b, anchor="c")

    def _draw_helmet_page(self, x, y):
        """The designer: a preview, the fields that build it, and the way out.

        ONLY THE ROWS THAT DO SOMETHING. Trim and line weight apply to a
        minority of the catalogue, and the second layer's colour and weight
        mean nothing while it is off — a control that does nothing on the
        row it is sitting in is a menu that lies, so they appear and disappear
        with the pattern they belong to.
        """
        import helmet as helmet_mod
        # THE HIT LIST MUST EXIST BEFORE ANY ROW REGISTERS INTO IT. In the
        # running app `draw_settings` clears it just above this call, so this
        # looked unnecessary -- but the page is also drawn directly (the shot
        # tool, and drawtest), and an AttributeError inside a draw stage is
        # swallowed into `_stage_err` and shows up as a panel that silently
        # stopped appearing. The same lesson `_dhelmet` taught one commit ago.
        if not hasattr(self, "_menu_hits"):
            self._menu_hits = []
        spec = self._helmet_spec()
        pat = spec.get("pattern") or "solid"
        pat2 = spec.get("pattern2") or "none"
        nm = self._colour_name

        rows = [("Shell", "base", nm(spec.get("base"))),
                ("Pattern", "pattern", pat),
                ("Pattern colour", "accent", nm(spec.get("accent")))]
        if pat in helmet_mod.WEIGHTED:
            rows.append(("Line weight", "weight", spec.get("weight") or "normal"))
        rows.append(("Second layer", "pattern2", pat2))
        if pat2 != "none":
            rows.append(("Layer 2 colour", "accent2", nm(spec.get("accent2"))))
            if pat2 in helmet_mod.WEIGHTED:
                rows.append(("Layer 2 weight", "weight2",
                             spec.get("weight2") or "normal"))
        num = spec.get("number")
        rows.append(("Number", "number", "none" if num is None else str(num)))
        if num is not None:
            rows.append(("Number colour", "ink", nm(spec.get("ink"))))

        acts = [("Mirror", "ON" if spec.get("flip") else "OFF",
                 bool(spec.get("flip")), lambda: self._helmet_toggle("flip")),
                ("Surprise me", "RANDOM", True, self._helmet_random),
                ("Use the one from my name", "RESET", False, self._helmet_reset),
                ("‹ Back", "", False, lambda: self._menu_goto("main"))]

        PREV = 64
        w = max(400, max(self.f_row.measure(r[0]) for r in rows) + 230)
        rh = 28
        h = 14 + PREV + 10 + rh * (len(rows) + len(acts))
        self._begin_panel("menu", x, y, w, h)
        self._card(x, y, w, h, fill=CARD_BG, accent=HEADER_ACCENT, side="left")

        # THE PREVIEW, and the point of the whole page: every row below
        # redraws this, so what he is building is on screen while he builds it.
        ph = None
        try:
            import avatars
            ph = avatars.helmet_icon(spec, PREV)
        except Exception:
            ph = None
        if ph is not None:
            # `_cv_real` WITH THE OFFSET APPLIED, not `self.canvas`. That
            # property returns the translating `_TC` wrapper, which has no
            # `create_image` at all -- the radio cards already draw their
            # avatars this way for the same reason. It raises only at runtime,
            # so it was found by rendering the page rather than by a test.
            self._cv_real.create_image(x + 16 - self._ox, y + 10 - self._oy,
                                       image=ph, anchor="nw")
            self._keep_helmet_ref = ph      # tk drops an unreferenced image
        self.text(x + 16 + PREV + 14, y + 10 + PREV / 2.0 - 8,
                  (self._my_name or "Your helmet")[:18], fill=TEXT,
                  font=self.f_row_b, anchor="w")
        # TRUNCATED AT A COMMA, NOT AT A CHARACTER. A hard slice left
        # "black, neon blade, rose visorband," on screen -- a dangling comma
        # reads as a rendering fault rather than as a shortened list.
        _d = helmet_mod.describe(spec)
        if len(_d) > 34:
            _cut = _d[:34].rsplit(",", 1)[0]
            _d = (_cut if _cut else _d[:33]) + "…"
        self.text(x + 16 + PREV + 14, y + 10 + PREV / 2.0 + 10,
                  _d, fill=DIM, font=self.f_row, anchor="w")

        ry = y + 10 + PREV + 10
        for label, field, shown in rows:
            self._draw_spin_row(x, ry, w, rh, label, field, str(shown))
            ry += rh
        for label, state, ok, action in acts:
            self.text(x + 14, ry + 12, label, fill=TEXT, font=self.f_row,
                      anchor="w")
            if state:
                self.text(x + w - 14, ry + 12, state,
                          fill=(GREEN if ok else DIM), font=self.f_row_b,
                          anchor="e")
            self._menu_hits.append(((x + 2, ry, w - 4, rh), action))
            ry += rh

    def _draw_volume_row(self, x, ry, w, rh):
        """Master VOICE VOLUME slider in the settings menu.

        The overlay is click-through and its mouse events are POLLED, so this
        isn't a drag control: clicking anywhere along the track jumps the level
        to that point, which works fine with a single sampled click per tick.
        """
        vol = getattr(self.tts, "volume", 1.0) if self.tts else 1.0
        vmax = getattr(self.tts, "VOL_MAX", 1.3) if self.tts else 1.3
        self.text(x + 14, ry + 12, "Voice volume", fill=TEXT,
                  font=self.f_row, anchor="w")
        pct = f"{int(round(vol * 100))}%"
        # amber above unity: that range is a real boost, and worth flagging
        pcol = (DIM if vol <= 0 else "#ffb000" if vol > 1.0 else GREEN)
        self.text(x + w - 14, ry + 12, pct, fill=pcol, font=self.f_row_b,
                  anchor="e")
        # track sits between the label and the percentage readout
        tx0 = x + 14 + self.f_row.measure("Voice volume") + 14
        tx1 = x + w - 14 - self.f_row_b.measure("100%") - 12
        ty = ry + 12
        if tx1 - tx0 > 40:
            self.canvas.create_rectangle(tx0, ty - 3, tx1, ty + 3,
                                         fill=CONTROL_BG, outline="")
            span = tx1 - tx0
            fw = span * max(0.0, min(1.0, vol / vmax))
            if fw > 0:
                # the over-unity part is drawn amber, so a boost is obvious
                unity = span * (1.0 / vmax)
                self.canvas.create_rectangle(tx0, ty - 3, tx0 + min(fw, unity),
                                             ty + 3, fill=HEADER_ACCENT,
                                             outline="")
                if fw > unity:
                    self.canvas.create_rectangle(tx0 + unity, ty - 3,
                                                 tx0 + fw, ty + 3,
                                                 fill="#ffb000", outline="")
            # 100% tick, so unity gain is findable by eye
            ux = tx0 + span * (1.0 / vmax)
            self.canvas.create_rectangle(ux - 1, ty - 6, ux + 1, ty + 6,
                                         fill=DIM, outline="")
            # knob
            kx = tx0 + fw
            self.canvas.create_oval(kx - 5, ty - 6, kx + 5, ty + 6,
                                    fill=TEXT, outline="")
            # clicking the track sets the level; a tall hit box so it's easy
            # to hit while the game is moving underneath
            self._menu_hits.append(
                ((tx0 - 6, ry, (tx1 - tx0) + 12, rh),
                 lambda: self._set_volume_from_click(tx0, tx1)))

    def _set_volume_from_click(self, tx0, tx1):
        """Set master volume from where the track was clicked."""
        click = getattr(self, "_click", None)
        if not click or not self.tts or tx1 <= tx0:
            return
        vmax = getattr(self.tts, "VOL_MAX", 1.3)
        v = (click[0] - tx0) / float(tx1 - tx0) * vmax
        v = max(0.0, min(vmax, v))
        # snap to the meaningful stops: silence, unity, and full boost
        if v < 0.04 * vmax:
            v = 0.0
        elif abs(v - 1.0) < 0.05:
            v = 1.0                      # unity is worth landing on exactly
        elif v > vmax - 0.04 * vmax:
            v = vmax
        self.tts.volume = v
        try:
            import tts as _tts
            _tts.save_volume(v)
        except Exception:
            pass
        self._toast(f"VOICE VOLUME {int(round(v * 100))}%")

    def _toast(self, text, hold=3.5):
        """Transient hotkey feedback ('BOOTH OFF', 'UI HIDDEN…'). Drawn every
        tick regardless of UI visibility, so a toggle is never a leap of
        faith when the panels are hidden."""
        self._toast_msg = {"text": text, "until": time.time() + hold}

    def draw_toast(self):
        t = self._toast_msg
        if not t or time.time() >= t["until"]:
            return
        w = 16 + max(280, self.f_row_b.measure(t["text"]) + 32)
        x = (self.sw - w) // 2
        y = 40
        self._begin_panel("toast", x, y, w, 34)
        self._card(x, y, w, 34, fill=CARD_BG2, accent=HEADER_ACCENT, side="left")
        self.text(x + w // 2, y + 17, t["text"], fill=TEXT,
                  font=self.f_row_b, anchor="center")

    def draw_commentary(self, s):
        """Lower-third broadcast caption for the latest commentary line —
        slides up a few pixels as its panel fades in (retro chyron entrance)."""
        cap = self._comm_caption
        now = time.time()
        if not cap or now >= cap["until"]:
            return
        pundit = cap.get("persona") == "PUNDIT"
        who = PUNDIT_NAME.upper() if pundit else COMMENTATOR_NAME.upper()
        label = f"{who} · ANALYSIS" if pundit else f"{who} · COMMENTARY"
        lcol = PUNDIT_COLOR if pundit else COMMENTATOR_COLOR
        w = 780
        x = (self.sw - w) // 2
        # THE CAPTION STEPS ASIDE FOR THE SPEEDO. It was a fixed 780px, always
        # centred, and never looked at the speedometer — the only bottom
        # panel that didn't. Now that the speedo is sized to the screen and
        # carries telemetry above it, a smaller game window put the two on top
        # of each other (measured: 1366x768 and 1280x720 on LARGE). The
        # caption keeps its centre when there is room and slides left, then
        # narrows, only when there is not. The speedo draws first, so its box
        # is this frame's.
        sp = getattr(self, "_speedo_box", None)
        if sp and getattr(self, "speedo", "kmh") != "off":
            right_limit = sp[0] - 16
            if x + w > right_limit:
                x = max(16, right_limit - w)
                w = max(320, right_limit - x)
        lines = self._wrap(cap["text"], width=max(28, int(58 * w / 780.0)),
                           maxlines=2)
        h = 32 + 20 * len(lines)
        # entrance: rise 10px over the first quarter second (with the fade)
        age = now - cap.get("at", now)
        rise = int(max(0.0, 1.0 - age * 4.0) * 10)
        y = self.sh - 118 - h + rise
        self._begin_panel("commentary", x, y, w, h)
        self._card(x, y, w, h, fill=CARD_BG2, accent=lcol, side="left")
        # pixel name chip on the label row
        self.canvas.create_rectangle(x + 12, y + 8, x + 18, y + 14,
                                     fill=lcol, outline="")
        self.text(x + 24, y + 13, label, fill=lcol, font=self.f_small_b,
                  anchor="w")
        ly = y + 33
        for ln in lines:
            self.text(x + 16, ly, ln, fill=TEXT, font=self.f_hdr, anchor="w")
            ly += 20

    def draw_radio(self, s):
        now = time.time()
        with _RADIO_LOCK:
            self.radio_msgs = [m for m in self.radio_msgs if m["until"] > now]
            show = self.radio_msgs[-self.RADIO_MAX_BUBBLES:]  # oldest..newest
        if not show:
            return
        w = 340
        x = self.sw - w - 24
        gap = 10
        # position each bubble by its ACTUAL height (stacked, never overlapping)
        heights = [_BUBBLE_H(len(self._wrap(m["text"], width=30))) for m in show]
        total = sum(heights) + gap * (len(show) - 1)
        bottom = self.sh - 150
        # THE SPEEDO OWNS THE BOTTOM-RIGHT CORNER when it is on, and the
        # bubbles share that column. Without this they stacked straight
        # through the dial. Same treatment the objective card already gets
        # from the other direction — that one is a ceiling, this is a floor.
        sp_box = getattr(self, "_speedo_box", None)
        if sp_box and getattr(self, "speedo", "off") != "off":
            bottom = min(bottom, sp_box[1] - 12)
        top = bottom - total
        # don't climb into the objective card / relative tower above — both
        # live in the same right-hand column and are bottom-unaware, so clamp
        # our ceiling to whichever of them is on screen this frame, dropping
        # the oldest bubbles first if the remaining gap is too tight to fit
        obj_box = getattr(self, "_obj_box", None)
        rel_box = getattr(self, "_rel_box", None)
        ceiling = None
        if obj_box:
            ceiling = obj_box[1] + obj_box[3]
        elif rel_box:
            ceiling = rel_box[1] + rel_box[3]
        if ceiling is not None:
            min_top = ceiling + 12
            while top < min_top and len(show) > 1:
                show = show[1:]
                heights = heights[1:]
                total = sum(heights) + gap * (len(show) - 1)
                top = bottom - total
            top = max(top, min_top)
        self._begin_panel("radio", x, top, w, total)
        y = top
        for m, h in zip(show, heights):    # oldest at top, newest at bottom
            # pop-in: the newest card slides in from the right edge over its
            # first fifth of a second
            age = now - m.get("at", now)
            slide = int(max(0.0, 1.0 - age * 5.0) * 18)
            self._draw_bubble(x + slide, y, w, m)   # clips at the panel edge
            y += h + gap

    def draw_debug(self, s, game_running, in_action):
        """Live diagnostics HUD (Ctrl+Shift+D). Shows why radio/podium/audio
        may not be firing and how fast data is actually updating."""
        # imported here, not at module scope: r3e_overlay imports THIS module
        import r3e_overlay as _RO
        _VERSION = getattr(_RO, "VERSION", "?")
        _BUILD = getattr(_RO, "BUILD", "?")
        if self.tts is None:
            tts_s = "TTS = None  (import/init FAILED -> no audio)"
        else:
            tts_s = (f"TTS engine={self.tts.engine}  "
                     f"{'ENABLED' if self.tts.enabled else 'MUTED (Ctrl+Shift+M)'}")
        drv = self._drivers(s)
        foc = next((d for d in drv
                    if d.driver_info.slot_id == s.vehicle_info.slot_id), None)
        lines = [
            f"RacerTV v{_VERSION} build {_BUILD}",
            f"tick={self._tick_ms:5.1f}ms  ~{1000.0/max(self._tick_ms,1):.0f}fps"
            f"   cars={len(drv)}  moves_seen={self._dbg_moves}",
            # WHERE THE FRAME GOES. A total alone says the overlay is slow;
            # it does not say which panel to look at.
            "slowest: " + ("  ".join(
                "%s %.1f/%.0f" % (n, v, self._stage_peak.get(n, 0.0))
                for n, v in sorted(getattr(self, "_stage_ms", {}).items(),
                                   key=lambda kv: -kv[1])[:4]) or "-"),
            f"replay={s.game_in_replay}  phase={s.session_phase}  "
            f"type={s.session_type}  start_lights={s.start_lights}",
            f"laps_total={s.number_of_laps}  "
            f"t_remain={R.fmt_time(s.session_time_remaining)}  "
            f"checkered={s.flags.checkered}",
            f"you: slot={s.vehicle_info.slot_id} "
            f"place={foc.place if foc else '-'} "
            f"laps={foc.completed_laps if foc else '-'} "
            f"finish={foc.finish_status if foc else '-'}",
            f"podium={'shown' if (self._podium and time.time()<self._podium_until) else ('captured' if self._podium else 'none')}"
            f"   in_action={in_action}",
            tts_s,
        ]
        # corner-learning diagnostics (so you can SEE if overtake-placement works)
        fr = getattr(self, "_corner_fracs", [])
        nm = self._corner_names(R.u8_to_str(s.track_name)) if fr else None
        where = (self._where_on_track(s, foc.lap_distance_fraction)
                 if foc is not None else "")
        lines.append(
            f"corners: learned={len(fr)} laps_seen={getattr(self,'_corner_laps_seen',0)}"
            f"  named_list={len(nm) if nm else 0}"
            f"  -> here='{where}'")
        if self._stage_err:
            lines.append("ERR " + " | ".join(f"{k}:{v}"
                                             for k, v in self._stage_err.items())[:120])
        lines.append("-- recent radio --")
        lines += self._radio_recent or ["(none emitted yet)"]

        w = 640
        x, y = 30, 360
        h = 16 + 16 * len(lines)
        self._begin_panel("debug", x, y, w, h)
        self.panel(x, y, w, h, fill="#05080d")
        self.canvas.create_rectangle(x, y, x + w, y + 18, fill="#ff5a3c", outline="")
        self.text(x + 8, y + 9, "DEBUG  (Ctrl+Shift+D to hide)",
                  fill="#0b0e13", font=self.f_small_b, anchor="w")
        ly = y + 26
        for ln in lines:
            col = "#ff7b7b" if ln.startswith("ERR") else TEXT
            self.text(x + 8, ly, ln, fill=col, font=self.f_small, anchor="w")
            ly += 16

    def draw_podium(self, s):
        """When the race finishes, show a broadcast top-3 podium for a while."""
        now = time.time()
        if getattr(self, "_podium_key", None) != self._sess_key:   # new session
            self._podium_key = self._sess_key
            self._podium = None
            self._podium_until = 0.0
            self._podium_seen_at = 0.0

        # capture the top-3 once the race ends — but only once those three cars
        # have actually CROSSED THE LINE (finish_status == 1), so a fight to the
        # flag is classified correctly. A grace timeout covers odd cases.
        if self._podium is None and s.session_type == 2:           # races only
            finished = (s.session_phase == 6 or s.flags.checkered == 1
                        or (s.number_of_laps > 0
                            and any(d.completed_laps >= s.number_of_laps
                                    for d in self._drivers(s))))
            if finished and not self._podium_seen_at:
                self._podium_seen_at = now
            top = sorted(self._drivers(s), key=lambda d: d.place)[:3]
            top_done = len(top) >= 3 and all(d.finish_status == 1 for d in top)
            if (finished and len(top) >= 3
                    and (top_done or now - self._podium_seen_at > 10.0)):
                self._podium = [{
                    "place": d.place,
                    "name": self._dname(d),
                    "car": d.driver_info.car_number,
                    "color": self._color_for_name(self._dname(d)),
                } for d in top]
                self._podium_at = now
                self._podium_until = now + self.PODIUM_HOLD

        if not self._podium or now >= self._podium_until:
            return

        # --- compact top-3 strip that DROPS DOWN from under the header bar ---
        # (the old version was a 560x330 centre-screen panel that blocked the
        # track). The header is centred at y14 h48 -> bottom at y62; this slides
        # out just below it, top-centre, leaving the racing line clear.
        full_w, full_h = 520, 76
        DROP, FY = 0.45, 64                       # drop duration, final top y
        t = (now - getattr(self, "_podium_at", now)) / DROP
        t = 1.0 if t >= 1.0 else (0.0 if t < 0 else t)
        ease = 1 - (1 - t) * (1 - t)              # ease-out
        h = max(2, int(full_h * ease))            # window grows downward
        x0 = (self.sw - full_w) // 2
        y0 = FY
        self._begin_panel("podium", x0, y0, full_w, h)
        self.panel(x0, y0, full_w, full_h, fill="#0b1019")
        # thin accent header
        self.canvas.create_rectangle(x0, y0, x0 + full_w, y0 + 22,
                                     fill=ACCENT, outline="")
        self.text(x0 + full_w / 2, y0 + 11, "🏁  RACE RESULT",
                  fill="#0b0e13", font=self.f_row_b, anchor="center")

        # three side-by-side entries, gold / silver / bronze
        medal = {1: "#d9b54a", 2: "#c2cad4", 3: "#cd7f32"}
        by_place = {p["place"]: p for p in self._podium}
        cw = full_w / 3
        for i, place in enumerate((1, 2, 3)):
            p = by_place.get(place)
            if p is None:
                continue
            cx = x0 + cw * i + cw / 2
            ry = y0 + 26
            mcol = medal[place]
            # driver colour chip
            self.canvas.create_rectangle(cx - cw / 2 + 8, ry + 4,
                                         cx - cw / 2 + 14, ry + 38,
                                         fill=p["color"], outline="")
            self.text(cx - cw / 2 + 22, ry + 8, f"P{place}", fill=mcol,
                      font=self.f_hdr, anchor="nw")
            self.text(cx - cw / 2 + 22, ry + 30,
                      f"#{p['car']} {p['name'][:13]}", fill=TEXT,
                      font=self.f_sub, anchor="nw")

    def draw_sectors(self, s):
        vslot = s.vehicle_info.slot_id
        drv = None
        for d in self._drivers(s):
            if d.driver_info.slot_id == vslot:
                drv = d
                break
        if drv is None:
            return
        sw_, h = 360, 30
        x = (self.sw - sw_) // 2
        y = self.sh - 64
        self._begin_panel("sectors", x, y, sw_, h)
        self.panel(x, y, sw_, h)
        # running lap time (fall back to last completed lap when not live, e.g.
        # in replays where the current-lap time isn't published)
        lt = drv.lap_time_current_self
        if not (lt and lt > 0):
            st = drv.sector_time_previous_self
            lt = st[2] if all(t > 0 for t in st) else None   # cumulative last = lap
        self.text(x + 12, y + h / 2, R.fmt_time(lt if lt else -1),
                  fill=TEXT, font=self.f_hdr, anchor="w")
        bw = 70
        bx = x + sw_ - bw * 3 - 8
        for i in range(3):
            cur = drv.sector_time_current_self[i]
            prev = drv.sector_time_previous_self[i]
            pbest = drv.sector_time_best_self[i]
            sbest = s.session_best_lap_sector_times[i]
            val = (cur if cur and cur > 0 else
                   prev if prev and prev > 0 else None)
            col = self._sector_color(val, pbest, sbest)
            txt = f"{val:.1f}" if val else "--"
            self.text(bx + i * bw + bw / 2, y + h / 2, txt, fill=col,
                      font=self.f_row_b, anchor="center")

    def draw_map(self, s):
        drivers = self._drivers(s)
        if not drivers:
            return
        # reset the traced outline when the track changes
        tid = (s.track_id, s.layout_id)
        if getattr(self, "_map_tid", None) != tid:
            self._map_tid = tid
            self.track_cells = {}
            self.sf_xy = None

        # sample car positions -> {cell: lap_fraction}; traces shape + sectors
        cell = self.MAP_CELL
        for d in drivers:
            px, pz = d.position.x, d.position.z
            if px == 0 and pz == 0:
                continue
            self.track_cells[(round(px / cell), round(pz / cell))] = \
                d.lap_distance_fraction
            # capture the start/finish line (a car right at fraction ~0)
            if self.sf_xy is None and 0 <= d.lap_distance_fraction < 0.01:
                self.sf_xy = (px, pz)
        if not self.track_cells:
            return
        # bounds from the full sampled outline (stable shape)
        xs = [k[0] * cell for k in self.track_cells]
        zs = [k[1] * cell for k in self.track_cells]
        self.minx, self.maxx = min(xs), max(xs)
        self.minz, self.maxz = min(zs), max(zs)
        if self.maxx <= self.minx or self.maxz <= self.minz:
            return

        size = 240
        pad = 18
        bx = 18
        by = self.sh - size - 60
        self._begin_panel("map", bx, by, size, size)
        self.panel(bx, by, size, size)

        span_x = self.maxx - self.minx
        span_z = self.maxz - self.minz
        span = max(span_x, span_z)
        usable = size - 2 * pad
        scale = usable / span
        # center the shorter axis within the square
        off_x = (usable - span_x * scale) / 2
        off_z = (usable - span_z * scale) / 2

        def to_xy(px, pz):
            mx = off_x + (px - self.minx) * scale
            mz = off_z + (pz - self.minz) * scale
            return bx + pad + mx, by + pad + (usable - mz)

        # which sectors are under yellow -> tint those track cells
        sf = s.sector_start_factors
        bounds = [0.0, sf.sector2, sf.sector3, 1.0]
        if sf.sector2 <= 0 or sf.sector3 <= 0:   # fall back to even thirds
            bounds = [0.0, 1 / 3, 2 / 3, 1.0]
        yellow_sectors = {i + 1 for i in range(3) if s.flags.sector_yellow[i] == 1}

        def sector_of(frac):
            for i in range(3):
                if bounds[i] <= frac < bounds[i + 1]:
                    return i + 1
            return 3

        # draw the track outline (sampled cells) under the cars
        for (qx, qz), frac in self.track_cells.items():
            cx, cy = to_xy(qx * cell, qz * cell)
            col = ("#ffd23f" if (yellow_sectors and frac is not None
                                 and sector_of(frac) in yellow_sectors)
                   else "#5b6470")
            self.canvas.create_rectangle(cx - 1, cy - 1, cx + 1, cy + 1,
                                         fill=col, outline="")

        # start/finish marker
        if self.sf_xy is not None:
            fx, fy = to_xy(*self.sf_xy)
            self.canvas.create_rectangle(fx - 2, fy - 6, fx + 2, fy + 6,
                                         fill="#ffffff", outline="#000000")

        # multiclass colouring (only when >1 class on track)
        classes = {d.driver_info.class_id for d in drivers}
        multiclass = len(classes) > 1
        palette = ["#c9ced6", "#ff922b", "#74c0fc", "#b197fc", "#63e6be"]
        cls_color = {cid: palette[i % len(palette)]
                     for i, cid in enumerate(sorted(classes))}

        viewed_slot = s.vehicle_info.slot_id
        for d in drivers:
            px, pz = d.position.x, d.position.z
            if px == 0 and pz == 0:
                continue
            cx, cy = to_xy(px, pz)
            is_viewed = (viewed_slot >= 0 and d.driver_info.slot_id == viewed_slot)
            is_leader = (d.place == 1)
            r = 6 if is_viewed else 4
            base = cls_color[d.driver_info.class_id] if multiclass else "#c9ced6"
            col = ACCENT if is_viewed else (LEADER if is_leader else base)
            self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                    fill=col, outline="#000000")
            self.canvas.create_text(cx, cy, text=str(d.driver_info.car_number),
                                    fill="#000000", font=("Consolas", 7, "bold"))
