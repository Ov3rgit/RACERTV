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
    COMMENTATOR_COLOR, CYAN, DIM, GREEN, HEADER_ACCENT, LEADER, MAX_ROWS,
    PANEL_BG, PANEL_OUTLINE, PANEL_STIPPLE, PURPLE, TEXT, _RADIO_LOCK)
from lines import (COMMENTATOR_NAME, PUNDIT_NAME)


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

    def _card(self, x, y, w, h, fill=CARD_BG, accent=None, side="top", r=7):
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
        bg = getattr(self, "_bg_real", None)
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
            self._card(x, cy, w, rh, fill="#2a0d0d", accent="#ff3b3b", side="left")
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

    def draw_header(self, s):
        track = R.u8_to_str(s.track_name)
        if not track:
            return
        stype = {0: "PRACTICE", 1: "QUALIFY", 2: "RACE", 3: "WARMUP"}.get(
            s.session_type, "")

        # progress: prefer lap counter; in replays/time sessions fall back to
        # the leader's actual lap (RaceRoom's time-remaining is unreliable here)
        lead_laps = max((d.completed_laps for d in self._drivers(s)), default=0)
        total = s.number_of_laps
        if total and total > 0:
            prog = f"LAP {min(lead_laps + 1, total)}/{total}"
        elif (s.game_in_replay != 1 and s.session_time_remaining
                and s.session_time_remaining > 0):
            prog = R.fmt_time(s.session_time_remaining)
        else:
            prog = f"LAP {lead_laps + 1}"

        # bottom-row status: a blinking LIVE (red) / REPLAY (cyan) dot + tag,
        # then the session type. Kept on the LEFT row so it can never collide
        # with the track name (top-left) or the lap counter (top-right).
        is_rep = (s.game_in_replay == 1)
        tag = "REPLAY" if is_rep else "LIVE"
        tcol = HEADER_ACCENT if is_rep else "#ff3b3b"
        bottom = tag + (("   " + stype) if stype else "")

        # size the panel to fit BOTH rows: top (title + gap + lap) and the
        # bottom status row (dot + tag + session), so nothing overlaps
        title = track[:30]
        tw = self.f_hdr.measure(title)
        pw = self.f_hdr.measure(prog)
        bw = 14 + self.f_sub.measure(bottom)
        w = max(420, 16 + max(tw, bw) + 40 + pw + 16)
        x = (self.sw - w) // 2
        self._begin_panel("header", x, 14, w, 50)
        self._card(x, 14, w, 50, fill=CARD_BG2, accent=HEADER_ACCENT, side="top")
        # CRT scanlines over the chyron (every 3rd row, barely-there dark line)
        for sy in range(14 + 8, 14 + 50 - 4, 3):
            self.canvas.create_line(x + 4, sy, x + w - 4, sy, fill="#070b10")
        self.text(x + 16, 29, title, fill=TEXT, font=self.f_hdr, anchor="w")
        self.text(x + w - 16, 31, prog, fill=HEADER_ACCENT, font=self.f_hdr,
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
                delta = self.grid_place.get(slot, d.place) - d.place
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
            return
        order = sorted(self._drivers(s), key=lambda d: d.place)
        idx = next((i for i, d in enumerate(order)
                    if d.driver_info.slot_id == vslot), None)
        if idx is None or len(order) < 2:
            return
        lo = max(0, idx - 3)
        hi = min(len(order), idx + 4)
        window = order[lo:hi]
        focus_cg = self.cum_gap.get(vslot)

        w, rh = 300, 24
        x = self.sw - w - 30
        y = 110
        self._begin_panel("relative", x, y, w, 22 + rh * len(window))
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
            self.text(x + 10, ry + rh / 2, f"{d.place:>2}", fill=DIM,
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

    def draw_objective(self, s):
        """The active race objective as a COMPETITIVE broadcast target chip.

        Deliberately not a plain box: a skewed motorsport chip with a solid
        accent flash carrying the goal position, the target on its own line,
        a live gap with a trend arrow, and a SEGMENTED progress strip that
        fills like a rev bar and turns amber then green as you close it out.
        Shows the verdict for a few seconds when a target resolves, so the
        screen always agrees with what the engineer just said.
        """
        now = time.time()
        res = getattr(self, "_obj_result", None)
        obj = getattr(self, "_obj", None)
        if not obj and not (res and now < res.get("until", 0)):
            return
        w, h = 348, 52
        sk = 10                                  # skew: the motorsport slant
        x = (self.sw - w) // 2
        y = self.sh - 162
        self._begin_panel("objective", x, y, w + sk, h)

        if obj:
            label, col = "TARGET", HEADER_ACCENT
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

        # --- skewed body (parallelogram) + hard accent edge down the left
        body = [x + sk, y, x + w + sk, y, x + w, y + h, x, y + h]
        self.canvas.create_polygon(*body, fill=CARD_BG, outline=CARD_BORDER,
                                   width=2)
        flash = [x + sk, y, x + sk + 58, y, x + 58, y + h, x, y + h]
        self.canvas.create_polygon(*flash, fill=col, outline="")
        # goal badge sits in the accent flash — the "what am I racing for"
        self.text(x + sk + 22, y + h // 2 - 1, str(badge)[:3], fill="#080c11",
                  font=self.f_row_b, anchor="center")

        # --- label + live status on the top line
        tx = x + sk + 68
        self.text(tx, y + 14, label, fill=col, font=self.f_small_b, anchor="w")
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
        if status:
            self.text(x + w - 14, y + 14, status, fill=scol,
                      font=self.f_small_b, anchor="e")

        # --- the objective itself
        self.text(tx, y + 32, txt[:34], fill=TEXT, font=self.f_row, anchor="w")

        # --- SEGMENTED progress strip (rev-bar feel), amber then green
        segs, sw_, gap_ = 14, 16, 3
        bx = tx
        by, bh = y + h - 12, 5
        lit = int(round((prog or 0.0) * segs))
        for i in range(segs):
            sx = bx + i * (sw_ + gap_)
            if sx + sw_ > x + w - 14:
                break
            if i < lit:
                c2 = (GREEN if prog and prog >= 0.85
                      else "#ffb000" if prog and prog >= 0.5 else col)
            else:
                c2 = "#1c2530"
            self.canvas.create_rectangle(sx, by, sx + sw_, by + bh,
                                         fill=c2, outline="")

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
        # chip sits on the clock row: [≡ SETTINGS] [11:25:49], under ● OVERLAY
        gx, gy, gw, gh = 12, 40, 126, 28
        self._begin_panel("gear", gx, gy, gw, gh)
        open_ = getattr(self, "_menu_open", False)
        self._card(gx, gy, gw, gh, fill=CARD_BG2,
                   accent=HEADER_ACCENT if open_ else DIM, side="left")
        self.text(gx + 12, gy + gh // 2, "≡ SETTINGS",
                  fill=(HEADER_ACCENT if open_ else TEXT),
                  font=self.f_row_b, anchor="w")
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
        tts_on = bool(self.tts and getattr(self.tts, "enabled", False))
        rows = [
            ("Overlay UI (audio stays on)",
             "ON" if self.visible else "OFF", self.visible,
             self._do_toggle_ui),
            ("Booth — Miles & Brett",
             "ON" if self.commentary_on else "OFF", self.commentary_on,
             self._do_toggle_booth),
            ("Team radio — engineer + drivers",
             "ON" if self.radio_on else "MUTED", self.radio_on,
             self._do_toggle_radio),
            ("All voices (booth + radio)",
             "ON" if tts_on else "MUTED", tts_on,
             self._do_toggle_mute),
            ("Compact timing tower",
             "ON" if self.compact else "OFF", self.compact,
             self._do_toggle_compact),
            ("Debug HUD",
             "ON" if self.debug else "OFF", self.debug,
             self._do_toggle_debug),
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

    def _draw_volume_row(self, x, ry, w, rh):
        """Master VOICE VOLUME slider in the settings menu.

        The overlay is click-through and its mouse events are POLLED, so this
        isn't a drag control: clicking anywhere along the track jumps the level
        to that point, which works fine with a single sampled click per tick.
        """
        vol = getattr(self.tts, "volume", 1.0) if self.tts else 1.0
        self.text(x + 14, ry + 12, "Voice volume", fill=TEXT,
                  font=self.f_row, anchor="w")
        pct = f"{int(round(vol * 100))}%"
        self.text(x + w - 14, ry + 12, pct,
                  fill=(GREEN if vol > 0 else DIM), font=self.f_row_b,
                  anchor="e")
        # track sits between the label and the percentage readout
        tx0 = x + 14 + self.f_row.measure("Voice volume") + 14
        tx1 = x + w - 14 - self.f_row_b.measure("100%") - 12
        ty = ry + 12
        if tx1 - tx0 > 40:
            self.canvas.create_rectangle(tx0, ty - 3, tx1, ty + 3,
                                         fill="#1c2530", outline="")
            fw = (tx1 - tx0) * max(0.0, min(1.0, vol))
            if fw > 0:
                self.canvas.create_rectangle(tx0, ty - 3, tx0 + fw, ty + 3,
                                             fill=HEADER_ACCENT, outline="")
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
        v = (click[0] - tx0) / float(tx1 - tx0)
        v = max(0.0, min(1.0, v))
        # snap the ends so full-off and full-on are easy to actually hit
        if v < 0.04:
            v = 0.0
        elif v > 0.96:
            v = 1.0
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
        lines = self._wrap(cap["text"], width=58, maxlines=2)
        pundit = cap.get("persona") == "PUNDIT"
        who = PUNDIT_NAME.upper() if pundit else COMMENTATOR_NAME.upper()
        label = f"{who} · ANALYSIS" if pundit else f"{who} · COMMENTARY"
        lcol = "#7fd1ff" if pundit else COMMENTATOR_COLOR
        w = 780
        x = (self.sw - w) // 2
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
        top = bottom - total
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
        if self.tts is None:
            tts_s = "TTS = None  (import/init FAILED -> no audio)"
        else:
            tts_s = (f"TTS engine={self.tts.engine}  "
                     f"{'ENABLED' if self.tts.enabled else 'MUTED (Ctrl+Shift+M)'}")
        drv = self._drivers(s)
        foc = next((d for d in drv
                    if d.driver_info.slot_id == s.vehicle_info.slot_id), None)
        lines = [
            f"tick={self._tick_ms:5.1f}ms  ~{1000.0/max(self._tick_ms,1):.0f}fps"
            f"   cars={len(drv)}  moves_seen={self._dbg_moves}",
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
