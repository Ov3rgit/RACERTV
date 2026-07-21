# -*- coding: utf-8 -*-
"""
Team radio: the player's race
engineer and the rival drivers. Owns the engineer's telemetry watch (fuel,
tyres, damage, penalties, track limits, sector coaching), rival radio
chatter, and the radio card that carries it on screen.

Mixed into Overlay (see r3e_overlay.py) — these methods take the
same `self` and call the rest of the class freely; only the file
they live in changed.
"""
import r3e_data as R
import avatars
import random
import time
from overlay_common import (_BUBBLE_H, _safe_format, ACCENT, CARD_BG, DIM, ENGINEER_COLOR,
    ENG_EMOTION, HEADER_ACCENT, PENALTY_SPOKEN, TEXT, _RADIO_LOCK)
from lines import (COMMENTARY_LINES, COMMENTATOR_FULL, COMMENTATOR_NAME,
    DRIVER_FINISH, EASTER_EGGS, ENGINEER_LINES, ENGINEER_PRACTICE,
    ENGINEER_QUALI, EXTRA_LINES, LEAD, MOOD_FRUSTRATED, MOOD_PUMPED,
    NATIVE_RADIO, NATIVE_RADIO_QUALI, PERSONAS, PUNDIT_FULL, PUNDIT_NAME,
    REVENGE, RIVAL_QUALI, SECTOR_COACH, TRACK_SECTOR_TIPS, TRACK_TIPS)


class RadioMixin:
    """See module docstring."""

    def update_radio(self, s):
        now = time.time()
        # reset radio state on a new session
        if getattr(self, "_radio_key", None) != self._sess_key:
            self._radio_key = self._sess_key
            self.prev_places = {}
            self.prev_int_focus = None
            with _RADIO_LOCK:
                self.radio_msgs = []
            self.driver_radio_cd = {}
            self._last_line = {}
            self._chase = {}
            self._eng_cd = 0.0
            self._eng_flags = {}
            self._rivals = {}
            self._mood = {}
            self._prev_gap = None
            self._prev_gapb = None
            self._enc_cd = 0.0
            self._prac_cd = 0.0
            self._finish_q = []          # queued driver finish-position reactions
            self._finish_built = False
            # engineer telemetry trackers (your car's real data)
            self._eng_pen = -1           # last penaltyType seen (rising-edge warn)
            # cut/incident counters seed from the LIVE values — a 0 seed turned
            # any count carried over the session boundary into a false rising
            # edge (phantom "you ran over the track limits" at the green flag)
            self._eng_cuts = max(0, s.cut_track_warnings)
            self._eng_plv = 1            # last player current_lap_valid (off edge)
            self._eng_off_cd = -1e9      # shared off-track warn cooldown
            self._eng_off_watch = None   # [deadline, ref_speed] off-confirm dip
            self._eng_lvs = -1           # last lap_valid_state (next-lap warning)
            self._eng_ip = max(0, s.incident_points)  # last incident-point count
            self._eng_ip_cd = -1e9       # incident-point report cooldown
            # OWN tallies: cut_track_warnings / incident_points are SERVER
            # fields (-1 = N/A per r3e.h), so offline vs AI they never move and
            # the engineer never mentioned limits or incidents at all. We count
            # confirmed mistakes ourselves so he still keeps you honest.
            self._own_cuts = 0           # our confirmed track-limits count
            self._own_inc = 0            # our confirmed incident count
            self._own_inc_cd = -1e9
            self._eng_fuel_cd = 0.0      # fuel-warning cooldown
            self._eng_tyre_cd = 0.0      # tyre-warning cooldown
            self._eng_tyre_base = None   # fresh tyre_wear baseline (4 values)
            self._eng_temp_cd = -1e9     # tyre-temperature warning cooldown
            self._eng_brake_cd = -1e9    # brake-temperature warning cooldown
            self._eng_engtemp_base = None    # warmed-up engine-temp reference
            self._eng_engtemp_hot_since = None  # when the sustained rise began
            self._eng_engtemp_cd = -1e9  # engine-overheat warning cooldown
            self._eng_last_ann_place = None  # last place the engineer announced
            self._eng_place_cd = -1e9    # overtake/position-ack cooldown
            self._eng_sector_prev = 0    # last track_sector (proactive coaching)
            self._eng_section_cd = -1e9  # proactive section-coaching cooldown
            self._eng_dmg = {}           # part -> health reference (re-baselined)
            self._eng_dmg_cd = {}        # part -> last "light damage" report time
            self._eng_dmg_sev = {}       # part -> health at last severe (box) call
            self._eng_laps_cd = 0.0      # periodic laps/time-left update cooldown
            self._eng_sec_cd = 0.0       # sector-coaching cooldown (race)
            self._intro_emit_t = None    # when the booth aired its session opener
            self._intro_aired = False    # engineer gate: intro has finished?
            self._sess_start_t = now     # session start (intro-gate safety release)
            self._signed_off = False     # broadcast over (no more radio either)

        order = sorted(self._drivers(s), key=lambda d: d.place)
        if not order:
            return
        # after the booth's closing sign-off the broadcast is over — no more
        # engineer or driver radio either (the queued wrap still plays out)
        if getattr(self, "_signed_off", False):
            return
        placemap = {d.place: d for d in order}
        # radio reacts to CONFIRMED (debounced) places too, so a flicker never
        # produces a phantom "he passed you / you passed him" call
        cp = lambda d: self.cplace.get(d.driver_info.slot_id, d.place)
        cur = {d.driver_info.slot_id: cp(d) for d in order}
        vslot = s.vehicle_info.slot_id
        focused = next((d for d in order if d.driver_info.slot_id == vslot), None)

        who = self._dname(focused) if focused is not None else ""

        # Rival radio stays quiet only until the LIGHTS-OUT call has aired, so
        # the start itself is clean. It used to be muted for the whole of lap
        # one, which silenced them through turn one — the moment most worth
        # hearing about. The booth latches _comm_flags['start'] when that call
        # goes out; a few seconds past the green covers the case where the
        # booth is disabled entirely.
        # getattr: _comm_flags is created by update_commentary, which runs
        # AFTER update_radio in the tick, so it does not exist on the very
        # first tick of a session (the same ordering trap _green_t hit).
        _started = (getattr(self, "_comm_flags", {}).get("start")
                    or now - getattr(self, "_green_t", 1e18) > 6.0)
        radio_open = self._racing and (s.session_type != 2 or _started)
        # RIVALS ONLY: hold until the end of lap 1. Lap 1 is a scramble of
        # place changes that read as passes and spins but are really just the
        # pack sorting itself out, and the booth is busy calling the start —
        # driver radio on top of it is noise. YOUR ENGINEER is not held here
        # (he's gated at _engineer_events below); he stays free from his
        # opening line, which is wanted.
        if focused is not None and focused.completed_laps < 1:
            radio_open = False

        # update each driver's momentum (decays; +gain / -loss) BEFORE building
        # lines, so _radio_line can flavour them frustrated/pumped
        for d in order:
            sl = d.driver_info.slot_id
            m = self._mood.get(sl, 0.0) * 0.97
            pv = self.prev_places.get(sl)
            if pv is not None:
                if d.place < pv:
                    m += 1.0
                elif d.place > pv:
                    m -= 1.0
            self._mood[sl] = max(-5.0, min(5.0, m))

        events = []  # (priority, slot, name, text, bypass, persona, emotion)
        is_race = (s.session_type == 2)

        # ---- post-race FINISH reactions on the radio (#2) ----------------
        # When the race ends, drivers key the mic reacting to their finishing
        # position. The WINNER's celebration is ALWAYS queued first, then the
        # rest of the podium, the player (if outside the top 3), and a couple of
        # others for colour. Aired one-per-global-cooldown so they don't flood.
        def _fin_tier(place):
            return "podium" if place <= 3 else "points" if place <= 10 else "low"

        if is_race and not self._finish_built:
            leader = order[0]
            done = (s.session_phase == 6 or s.flags.checkered == 1
                    or leader.finish_status == 1
                    or (s.number_of_laps > 0
                        and leader.completed_laps >= s.number_of_laps))
            if done:
                self._finish_built = True
                picks = []
                winner = placemap.get(1)
                if winner is not None:
                    picks.append((winner, "win"))          # ALWAYS first
                for pl in (2, 3):
                    d = placemap.get(pl)
                    if d is not None:
                        picks.append((d, "podium"))
                if focused is not None and focused.place > 3:
                    picks.append((focused, _fin_tier(focused.place)))
                others = [d for d in order if d.place > 3 and d is not focused]
                random.shuffle(others)
                for d in others[:2]:
                    picks.append((d, _fin_tier(d.place)))
                self._finish_q = [(d.driver_info.slot_id, self._dname(d),
                                   d.place, tier) for d, tier in picks]

        # emit one queued finish reaction per global-cooldown window (front =
        # winner), forced past the per-driver cooldown so the order is preserved
        if self._finish_q and (now - self.last_radio_t) >= self.RADIO_GLOBAL_CD:
            sl, nm, place, tier = self._finish_q.pop(0)
            d = placemap.get(place)
            line = self._pick(DRIVER_FINISH[tier], ("FIN", tier)).format(pos=place)
            emo = ("happy" if tier in ("win", "podium")
                   else "neutral" if tier == "points" else "sad")
            persona = self._persona_for(d) if d is not None else "VETERAN"
            events.append((-9, sl, nm, line, True, persona, emo))

        # a rival takes the lead (you taking it is handled by your engineer).
        # Position-battle radio only makes sense in a RACE that's actually GREEN
        # — in practice/qualy or on the grid, cars aren't racing for position.
        if is_race and radio_open:
            for d in order:
                sl = d.driver_info.slot_id
                pv = self.prev_places.get(sl)
                if cp(d) == 1 and sl != vslot and pv is not None and pv > 1:
                    events.append((0, sl, self._dname(d),
                                   self._pick(LEAD, ("LEAD",)), False,
                                   self._persona_for(d), "smug"))

        if focused is not None and is_race and radio_open:
            fp = focused.place          # LIVE place for neighbours / the chase
            fpc = cp(focused)           # CONFIRMED place for detecting a pass
            pvf = self.prev_places.get(vslot)
            if pvf is not None and fpc == pvf - 1:              # you overtook 1 car
                passed = placemap.get(fpc + 1)
                if (passed is not None
                        and self.prev_places.get(passed.driver_info.slot_id) == fpc):
                    psl = passed.driver_info.slot_id
                    self._rivals[psl] = now              # remember for revenge
                    events.append((1, psl, self._dname(passed),
                                   self._radio_line(passed, "overtaken", who), False,
                                   self._persona_for(passed), "angry"))
            elif pvf is not None and fpc == pvf + 1:            # someone passed YOU
                over = placemap.get(fpc - 1)
                if (over is not None
                        and self.prev_places.get(over.driver_info.slot_id) == fpc):
                    osl = over.driver_info.slot_id
                    # if you passed THEM in the last 90s, this is a revenge re-pass
                    # (bypass cooldown so the grudge actually lands)
                    if now - self._rivals.get(osl, -1e9) < 90:
                        line = self._pick(REVENGE, ("REVENGE",)).format(who=who or "you")
                        revenge = True
                    else:
                        line = self._radio_line(over, "taunt", who)
                        revenge = False
                    events.append((1, osl, self._dname(over), line, revenge,
                                   self._persona_for(over), "smug"))
            elif pvf is not None and fpc >= pvf + 2:            # you spun / lost places
                events.append((0, vslot, self._dname(focused),
                               self._radio_line(focused, "crash"), False,
                               self._persona_for(focused), "shock"))

            # closing on the car ahead -> ESCALATING chase radio: distinct lines
            # at each tier (1.5s / 0.8s / 0.3s), each aired once per chase, so a
            # long chase tells a story instead of repeating one line. Resets when
            # the gap opens back up (a new chase later sounds fresh).
            if fp > 1:
                ahead = placemap.get(fp - 1)
                itv = self.interval.get(vslot)
                if ahead is not None and itv is not None and itv > 0:
                    tslot = ahead.driver_info.slot_id
                    fired = self._chase.get(tslot, set())
                    if itv > 2.5:
                        fired = set()
                    tier = ("attack" if itv < 0.3 and "attack" not in fired else
                            "near" if itv < 0.8 and "near" not in fired else
                            "far" if itv < 1.5 and "far" not in fired else None)
                    if tier is not None:
                        fired = set(fired) | {tier}
                        events.append((2, tslot, self._dname(ahead),
                                       self._radio_line(ahead, "caught", who), True,
                                       self._persona_for(ahead), "worried"))
                    self._chase[tslot] = fired

        # your race engineer talking to YOU
        if focused is not None:
            self._engineer_events(s, focused, placemap, events, now)

        # any driver losing 2+ places at once = spin/crash. RACE only — in
        # quali/practice a place change is just the timesheet reshuffling as
        # others set times, NOT an on-track incident.
        for d in (order if (is_race and radio_open) else []):
            sl = d.driver_info.slot_id
            if sl == vslot:
                continue
            pv = self.prev_places.get(sl)
            if pv is None or cp(d) < pv + 2:            # confirmed place drop = real
                continue
            txt = self._radio_line(d, "crash")
            if focused is not None and (abs(pv - cp(focused)) <= self.RADIO_NEAR
                                        or abs(cp(d) - cp(focused)) <= self.RADIO_NEAR):
                events.append((0, sl, self._dname(d), txt, False,
                               self._persona_for(d), "shock"))
            elif random.random() < self.RADIO_FAR_CHANCE:
                events.append((3, sl, self._dname(d), txt, False,
                               self._persona_for(d), "shock"))

        # FIELD radio: occasionally a driver scrapping elsewhere on track keys the
        # mic, so you still hear the odd bit of team radio even when leading in
        # clean air. RARE — its own ~18s cooldown so it's flavour, not a flood.
        if is_race and radio_open and now - getattr(self, "_field_cd", 0.0) > 18.0:
            fighters = [d for d in order
                        if d.driver_info.slot_id != vslot and d.place > 1
                        and 0.1 < (self.interval.get(d.driver_info.slot_id) or 9) < 0.8]
            if fighters and random.random() < 0.5:
                # a 'fighter' is within 0.8s of the car AHEAD of it, i.e. it's the
                # CHASER. The natural radio is the car being HUNTED keying the mic
                # about the chaser right behind — get the perspective right so we
                # never say "X is on my tail" about a car that's actually ahead.
                chaser = random.choice(fighters)
                chased = placemap.get(chaser.place - 1)     # the car in front
                if chased is not None and chased.driver_info.slot_id != vslot:
                    self._field_cd = now
                    events.append((3, chased.driver_info.slot_id,
                                   self._dname(chased),
                                   self._radio_line(chased, "caught",
                                                    self._dname(chaser)),
                                   False, self._persona_for(chased), "worried"))

        # QUALI / PRACTICE rival radio: EVENT-DRIVEN. Drivers react to their OWN
        # actual laps this tick — provisional pole, a good lap (PB), a deleted lap
        # — and occasionally one reacts to SOMEONE ELSE going fastest. No random
        # filler; every line is tied to a real event.
        if not is_race:
            is_quali_sess = (s.session_type == 1)
            by_slot = {d.driver_info.slot_id: d for d in order}
            for sl, kind, val in getattr(self, "_q_events", []):
                if sl == vslot or sl not in by_slot:
                    continue
                d = by_slot[sl]
                if kind == "pole":
                    # only QUALIFYING has a 'pole'; in practice it's just a good
                    # (fastest) lap, so the rival doesn't shout 'pole!' in practice
                    if is_quali_sess:
                        cat, emo, pr = "pole", "happy", 1
                    else:
                        cat, emo, pr = "good", "smug", 3
                elif kind == "pb":
                    cat, emo, pr = "good", "smug", 3
                elif kind == "deleted":
                    cat, emo, pr = "scrappy", "worried", 3
                else:
                    continue                         # lap_slow / first: no radio
                events.append((pr, sl, self._dname(d),
                               self._pick(RIVAL_QUALI[cat], ("RQ", cat)),
                               False, self._persona_for(d), emo))
            # a rival reacting to SOMEONE ELSE setting the fastest lap
            pole_evt = next((e for e in getattr(self, "_q_events", [])
                             if e[1] == "pole" and e[0] != vslot), None)
            if (pole_evt and now - getattr(self, "_qreact_cd", 0.0) > 20.0
                    and random.random() < 0.4):
                others = [d for d in order
                          if d.driver_info.slot_id not in (vslot, pole_evt[0])]
                if others:
                    self._qreact_cd = now
                    d = random.choice(others)
                    events.append((3, d.driver_info.slot_id, self._dname(d),
                                   self._pick(RIVAL_QUALI["chasing"], ("RQ", "chasing")),
                                   False, self._persona_for(d), "fired"))

        if self.prev_places:
            self._dbg_moves += sum(1 for sl, p in cur.items()
                                   if self.prev_places.get(sl) not in (None, p))
        self.prev_places = cur

        if not events or (now - self.last_radio_t) < self.RADIO_GLOBAL_CD:
            return
        # ENGINEER FIRST at equal priority. He talks to YOU; a rival's chatter
        # is colour. With ~15 rivals each on a 25s cooldown the field
        # collectively out-talked him many times over, which is why the radio
        # sounded like drivers with an occasional engineer.
        events.sort(key=lambda e: (e[0], 0 if e[5] == "ENGINEER" else 1))
        emitted = 0
        for _evt in events:
            # optional 8th element = an explicit TTL (seconds) for lines that
            # skip the spacing (bypass) but MUST still go stale — a position
            # ack like "P13 now" is wrong once you've climbed to P10, so it
            # can't inherit bypass's no-expiry. Most events are 7-tuples.
            _prio, sl, nm, txt, bypass, persona, emotion = _evt[:7]
            ttl_override = _evt[7] if len(_evt) > 7 else "default"
            if emitted >= self.RADIO_MAX_BURST:
                break
            # BALANCE: radio no longer yields to a booth backlog here — dropping
            # the event killed the bubble too, which is why radio "vanished" in
            # busy races. Voiced-vs-ticker is decided at the speak site below;
            # a backlogged queue just means the line airs as a silent ticker.
            # PIPELINE GATE — deliberately gentle. Its job is to stop a deep
            # backlog forming (a queued line that outlives its TTL is dropped
            # while its card still airs). At >=2 pending it was far too tight:
            # the booth sits at 2 for most of a race, so every non-bypass
            # engineer and driver line was starved and the radio cards stopped
            # appearing altogether. Only a genuinely deep queue blocks now, and
            # the ENGINEER is never gated — he is talking to YOU, and rival
            # chatter is the thing worth thinning out.
            if (not bypass and persona != "ENGINEER" and self.tts is not None
                    and self.tts._pending() >= 4):
                continue
            if persona == "ENGINEER":
                # bypass lines (overtake acks, severe damage, incident points,
                # session intro) skip the 14s spacing — they're one-shot, must
                # land while they still mean something, and carry their OWN
                # cooldowns so they can't machine-gun.
                if not bypass and now - self._eng_cd < self.RADIO_ENG_CD:
                    continue
            elif not bypass:
                if (now - self.driver_radio_cd.get(sl, 0)
                        < self.RADIO_DRIVER_CD):
                    continue
                # RELEVANCE: the drivers worth hearing are the ones you are
                # actually racing — the car you're chasing and the car hunting
                # you. Everyone else is background noise, so most of their
                # chatter is dropped rather than queued. This is what stops
                # the radio being every driver's reaction to every moment.
                _me = next((d for d in placemap.values()
                            if d.driver_info.slot_id == s.vehicle_info.slot_id),
                           None)
                if _me is not None:
                    _them = next((d for d in placemap.values()
                                  if d.driver_info.slot_id == sl), None)
                    if _them is not None:
                        _near = abs(_them.place - _me.place)
                        if _near > 1 and random.random() > (
                                0.45 if _near <= 3 else 0.15):
                            continue
            # TIER-C rival drivers radio in their NATIVE language; the bubble then
            # shows the English translation. Use SESSION-APPROPRIATE chatter — the
            # race set is full of battle lines ("he's right behind me!"), which is
            # nonsense in practice/qualifying, so non-race sessions use the
            # lap/pace-flavoured set instead.
            spoken_text, disp_text = None, txt
            if persona != "ENGINEER" and self.tts:
                lang = self.tts.native_lang(persona, nm)
                pool = NATIVE_RADIO if is_race else NATIVE_RADIO_QUALI
                if lang and pool.get(lang):
                    spoken_text, disp_text = random.choice(pool[lang])
            color = (ENGINEER_COLOR if persona == "ENGINEER"
                     else self._color_for_name(nm))
            msg = {"name": nm, "text": disp_text, "color": color,
                   "emotion": emotion, "engineer": persona == "ENGINEER"}
            if persona == "ENGINEER":
                self._eng_cd = now
            else:
                self.driver_radio_cd[sl] = now
            # CARD/AUDIO SYNC: when the voice is going to play, the card airs
            # from the audio's on_play — the moment the line actually STARTS —
            # so bubble and voice land together (queueing the card immediately
            # put it seconds ahead of its audio: render + queue latency).
            # GUARANTEE: every card still reaches the screen. It's parked in
            # _pending_bubbles with a deadline; if the audio never starts
            # (TTL-dropped, purged, render error), tick() airs it silently at
            # the deadline — so cards can never vanish like the old on_play-
            # only code allowed.
            spoke = "card"
            muted = not getattr(self, "radio_on", True)
            if self.tts and self.tts.enabled and not muted:
                say_text = (spoken_text if spoken_text is not None
                            else self._spoken(txt))
                # TTL matched to how long the card stays up, so the voice plays
                # WHILE its card is visible or drops cleanly (no orphan audio
                # over a card that's already gone). The engineer keeps the
                # longer radio TTL — he's talking to YOU and must be heard.
                if ttl_override != "default":
                    # a bypass line that opted into a real TTL — position acks,
                    # which must drop if they can't play while still true
                    _ttl = ttl_override
                elif bypass:
                    # ONE-SHOT lines (lights-out start call, severe damage,
                    # incident points, objective set/met) must not carry the
                    # short "numbers go stale" TTL. The start call says "P5",
                    # so it got a 9s deadline — and lights-out is the single
                    # busiest moment for the booth queue, so it routinely
                    # expired before it could play and the card aired silently.
                    # For these, being heard matters more than the number
                    # being seconds fresh.
                    _ttl = None
                elif persona == "ENGINEER":
                    _ttl = 9.0 if any(c.isdigit() for c in say_text) else None
                else:
                    _ttl = self.RADIO_HOLD + 2.0
                st = {"aired": False}

                def _air(_m=msg, _st=st):
                    with self._bubble_lock:
                        if _st["aired"]:
                            return
                        _st["aired"] = True
                    self._air_bubble(_m)

                def _onp(_t, _p):
                    _air()                     # audio STARTED — card lands with it

                def _ondrop(_st=st):
                    # THE LINE WILL NEVER SOUND (queue full, TTL expired,
                    # interrupted, render failed) — so DON'T put the card up.
                    #
                    # This used to air the bubble anyway, reasoning that a card
                    # beat leaving the driver staring at nothing. In practice
                    # it produced the opposite of a broadcast: a team-radio
                    # message from your engineer appearing on screen while the
                    # commentators are still mid-sentence, with no voice behind
                    # it, ever. Reported as "I see a message from the race
                    # engineer but no audio plays".
                    #
                    # A radio bubble IS the visual of a transmission. If the
                    # transmission never happened, the honest thing is silence:
                    # nothing was said, so nothing is shown. Mark it consumed
                    # so the safety net below doesn't resurrect it.
                    with self._bubble_lock:
                        _st["aired"] = True
                self.tts.speak(say_text, persona, seed=nm, ttl=_ttl,
                               on_play=_onp, on_drop=_ondrop)
                if not st["aired"]:
                    # SAFETY NET ONLY. The card's fate is now decided by the
                    # cue — on_play when the audio starts, on_drop the moment
                    # it can't. This timer only covers a path that somehow
                    # reports neither, so it is long and should never fire.
                    # (The old 3s timer was the primary mechanism, which is
                    # why cards led their audio: it guessed instead of being
                    # told.)
                    self._pending_bubbles.append((msg, now + 20.0, st))
                spoke = "spoke"
            else:
                self._air_bubble(msg)    # no audio coming — show it right away
            self._radio_recent.append(f"{time.strftime('%H:%M:%S')} {persona[:4]}"
                                      f"/{emotion[:4]} [{spoke}] {txt[:40]}")
            self._radio_recent = self._radio_recent[-7:]
            emitted += 1
        if emitted:
            self.last_radio_t = now

    def _engineer_events(self, s, focused, placemap, events, now):
        """Your engineer reacts to YOUR race. At most one candidate per tick;
        the emit loop throttles them with RADIO_ENG_CD."""
        vslot = focused.driver_info.slot_id
        # LIVE place for 'who is around me' (neighbours/gaps must match reality);
        # CONFIRMED place only for detecting a CHANGE (gained/lost/took the lead)
        fp = focused.place
        fpc = self.cplace.get(vslot, fp)
        ahead = placemap.get(fp - 1)
        behind = placemap.get(fp + 1)
        gap = self.interval.get(vslot)
        gapb = self.interval.get(behind.driver_info.slot_id) if behind else None
        pgap, pgapb = self._prev_gap, self._prev_gapb
        self._prev_gap, self._prev_gapb = gap, gapb
        grid = self.grid_place.get(vslot, fp)
        gained = grid - fp                       # +climbed / -dropped vs start

        def add(cat, prio, bypass=False, ttl="default", **extra):
            fmt = dict(
                pos=fp,
                ahead=self._dname(ahead) if ahead else "the car ahead",
                behind=self._dname(behind) if behind else "the car behind",
                gap=f"{gap:.1f}s" if gap else "a bit",
                gapb=f"{gapb:.1f}s" if gapb else "a bit",
                grid=grid, gain=abs(gained))
            fmt.update(extra)
            line = _safe_format(self._pick(ENGINEER_LINES[cat], ("ENGINEER", cat)),
                                fmt)
            evt = (prio, -1, "RACE ENGINEER", line, bypass, "ENGINEER",
                   ENG_EMOTION.get(cat, "neutral"))
            if ttl != "default":
                evt = evt + (ttl,)
            events.append(evt)

        # GATE: stay silent until the booth has finished its session intro
        # (pregrid / lights-out, or the quali / practice opener). The engineer
        # must never talk over the commentators setting the scene.
        if not self._intro_done(now):
            return

        # ---- RACE OBJECTIVE: DRAIN FIRST, ALWAYS ----------------------------
        # The engineer setting you a target, tracking it, and RESOLVING IT OUT
        # LOUD ("well done mate" / "just didn't have it, unlucky"). This used
        # to sit ~400 lines further down, below the gained/lost place calls —
        # and a verdict fires at exactly the moment you complete a pass or drop
        # a place, so those branches returned first and ate the tick, over and
        # over. Net effect: targets were set and resolved in silence.
        #
        # It belongs at the TOP. objective_event() has ALREADY mutated state by
        # the time it parks something here (the target is set, or met, or
        # withdrawn), so a dropped line is a verdict the driver never hears —
        # there is no second chance at it. Nothing below outranks that.
        #
        # bypass=True is essential for the same reason: the RADIO_ENG_CD
        # spacing must not swallow it. These are rare and carry their own
        # spacing in overlay_objective.py, so they cannot machine-gun.
        # Covers race AND quali/practice targets — same drain, same rules.
        obj = getattr(self, "_obj_say", None)
        if obj:
            self._obj_say = None
            ocat, okw = obj
            if ocat in ENGINEER_LINES:
                # a NUDGE is mid-objective colour — it must respect the normal
                # engineer spacing and yield to anything real, so it does NOT
                # bypass. set/met/miss/supersede DO bypass: they've already
                # mutated the objective state, so dropping them would leave the
                # target set or resolved silently (the whole system's failure
                # mode). See the _obj_notice contract in overlay_objective.py.
                is_nudge = ocat.startswith("obj_nudge_")
                return add(ocat, 2 if is_nudge else 1, bypass=not is_nudge,
                           **okw)

        # PRACTICE / QUALIFY / WARMUP: EVENT-DRIVEN. The engineer reacts to YOUR
        # actual laps — a lap completed (with gap to pole), a personal best,
        # provisional pole, a slow lap, a deleted lap — plus a real track tip to
        # help you find time. No more random filler.
        if s.session_type != 2:
            # (session objectives are drained at the top of this function,
            # above the lap-report ladder below — which returns on almost every
            # completed lap and would otherwise bury them)
            is_quali = (s.session_type == 1)
            trk = self._short_track(R.u8_to_str(s.track_name))
            pb = self.best_lap.get(vslot)
            pole_d = placemap.get(1)
            pole_t = (self.best_lap.get(pole_d.driver_info.slot_id)
                      if pole_d else None)
            gtp = (pb - pole_t) if (pb and pole_t and pole_t < pb) else None
            gtp_s = f"{gtp:.3f}s" if gtp else "a couple of tenths"

            def qadd(cat, prio):
                pool = ENGINEER_QUALI.get(cat)
                if not pool:
                    return
                line = _safe_format(self._pick(pool, ("ENGQ", cat)),
                                    dict(pos=fp, gap=gtp_s))
                emo = {"pole": "happy", "pb": "smug", "improve": "happy",
                       "hold": "neutral", "push": "fired", "traffic": "worried",
                       "deleted": "worried", "offbest": "neutral",
                       "offtrack": "shock", "nextlap": "worried",
                       "limits": "worried"}.get(cat, "neutral")
                events.append((prio, -1, "RACE ENGINEER", line, False,
                               "ENGINEER", emo))

            # ENGINEER SESSION INTRO — once, after the booth opener: greet you,
            # drop a bit of track knowledge and a warm-up plan, like a real race
            # engineer would on the way out of the garage.
            if not self._eng_flags.get("qintro"):
                self._eng_flags["qintro"] = True
                greet = _safe_format(self._pick(
                    ENGINEER_PRACTICE["intro_quali" if is_quali
                                      else "intro_practice"], ("ENGINEER", "qintro")),
                    {"trk": trk})
                # a real PACE tip (where to find time), not a history fun-fact
                know = self._track_tip(trk) or ""
                tail = self._pick(ENGINEER_PRACTICE["intro_tail"], ("ENGINEER", "qtail"))
                line = " ".join(p for p in (greet, know, tail) if p).strip()
                # bypass=True so the intro is never dropped if the booth queue is
                # busy at session start (that's why it wasn't firing)
                events.append((1, -1, "RACE ENGINEER", line, True,
                               "ENGINEER", "neutral"))
                return

            # react to MY lap events THIS tick (highest priority, immediate).
            # A completed lap (pole/pb/lap_slow) is also a chance for SPECIFIC
            # sector coaching rather than a generic verdict.
            for sl, kind, val in getattr(self, "_q_events", []):
                if sl != vslot:
                    continue
                if kind == "offtrack":
                    return qadd("offtrack", 0)  # genuine off — warn immediately
                if kind == "limits":
                    return qadd("limits", 0)    # ran off the track limits
                if kind == "nextlap_invalid":
                    return qadd("nextlap", 0)   # this AND next lap won't count
                if kind == "deleted":
                    return qadd("deleted", 1)
                if kind == "pole":
                    return qadd("pole", 0)
                if kind == "pb":
                    adv = self._sector_advice(s, focused)
                    if adv and random.random() < 0.45:
                        return self._emit_sector(adv, events, 1, s=s)
                    return qadd("improve", 1)   # PB: reports position + gap to pole
                if kind == "lap_slow":
                    adv = self._sector_advice(s, focused)
                    if adv:                      # name the weak sector, not just "slow"
                        return self._emit_sector(adv, events, 2, s=s)
                    return qadd("offbest", 2)
            # otherwise, periodic help — but keep it LIGHT. The real coaching is
            # the SECTOR advice above (only when you're actually slow somewhere);
            # a generic full-corner TRACK TIP is now a rare extra, and never in
            # your opening laps (you're still finding your feet). Mostly the
            # engineer just gives a push/hold nudge or a practice run note.
            if now - getattr(self, "_prac_cd", 0.0) > 50.0:
                self._prac_cd = now
                laps_done = focused.completed_laps
                tip = self._track_tip(trk) if laps_done >= 4 else None
                if tip and random.random() < 0.12:
                    events.append((3, -1, "RACE ENGINEER", tip, False,
                                   "ENGINEER", "neutral"))
                    return
                if is_quali:
                    return qadd("push" if fp == 1 or not gtp else "hold", 3)
                line = self._pick(ENGINEER_PRACTICE["practice"], ("ENGINEER", "prac"))
                events.append((3, -1, "RACE ENGINEER", line, False, "ENGINEER",
                               "neutral"))
            return

        # Seed the car-damage HEALTH baseline as early as possible — from the
        # green flag, at full health — so it's captured BEFORE any contact. The
        # report ladder further down sits behind higher-priority returns, so if
        # it owned the baseline it would only snapshot AFTER damage was already
        # taken (baselining at the damaged value) and never see the drop.
        if self._racing:
            cd0 = s.car_damage
            for _p, _v in (("engine", cd0.engine),
                           ("transmission", cd0.transmission),
                           ("aero", cd0.aerodynamics),
                           ("suspension", cd0.suspension)):
                if _v >= 0 and _p not in self._eng_dmg:
                    self._eng_dmg[_p] = _v
            # Engine-temp baseline: capture at the first WARMED-UP tick (lap >= 2),
            # unconditionally here rather than down in the return-heavy ladder —
            # otherwise it would only snapshot after a rise had already begun
            # (baselining the hot value as "normal"), and seeding at the green
            # flag would baseline a COLD engine so the normal warm-up looks like
            # an overheat. Player-only field; -1/0 = N/A.
            if (self._eng_engtemp_base is None and focused.completed_laps >= 2):
                _et = max(s.engine_temp, s.engine_oil_temp)
                if _et > 0:
                    self._eng_engtemp_base = _et

        # RACE START (once) — held until the launch has actually PLAYED OUT,
        # not fired on the green itself. Two reasons it must wait:
        #   * `gained` is the delta vs the grid slot, and at lights-out that is
        #     still 0 — so the call could never say "good start, up to P5",
        #     which is the whole point of it
        #   * at t=0 it collided with the booth's lights-out call (a signature
        #     line that interrupts), so it was fighting for the busiest audio
        #     moment of the race and losing
        # 9s clears the booth's own 8s grid-sort window, i.e. roughly turn one.
        # _green_t (not the booth's _green_at): stamped in update_stats at the
        # same moment _racing latches, so it is already set when the radio runs.
        # Default +inf, so a missing stamp holds the call rather than releasing
        # it — the failure mode we want is "late", never "on the green".
        if (not self._eng_flags.get("start") and self._racing
                and now - getattr(self, "_green_t", float("inf")) >= 9.0):
            self._eng_flags["start"] = True
            if gained >= 1 and "start_gain" in ENGINEER_LINES:
                return add("start_gain", 0, bypass=True)
            if gained <= -2 and "start_loss" in ENGINEER_LINES:
                return add("start_loss", 0, bypass=True)
            return add("start", 0, bypass=True)
        # race finish (once) -> win / podium / finish. Wait until the PLAYER has
        # actually CROSSED the line (finish_status == 1) so their position is FINAL
        # — otherwise a last-corner pass for your place gets the verdict wrong
        # ("P3, podium!" when you were pipped to P4 at the flag). A grace timeout
        # covers a DNF where you never take the flag.
        if not self._eng_flags.get("finish"):
            ldr = placemap.get(1)
            race_over = (s.session_phase == 6 or s.flags.checkered == 1
                         or (ldr is not None and ldr.finish_status == 1)
                         or (s.number_of_laps > 0 and ldr is not None
                             and ldr.completed_laps >= s.number_of_laps))
            if race_over and not self._eng_flags.get("finseen"):
                self._eng_flags["finseen"] = True
                self._eng_flags["finat"] = now
            player_done = (focused.finish_status == 1)
            done = (self._eng_flags.get("finseen")
                    and (player_done
                         or now - self._eng_flags.get("finat", now) > 8.0))
            if done:
                self._eng_flags["finish"] = True
                if fp == 1:
                    cat = "win"
                elif fp <= 3:
                    cat = "podium"
                elif gained >= 6:
                    cat = "recovery"          # big climb from the grid
                elif gained <= -6:
                    cat = "slip"              # big drop from the grid
                elif fp <= 6:
                    cat = "finish_strong"     # just off the podium
                elif fp <= 10:
                    cat = "finish_points"     # decent points
                else:
                    cat = "finish_low"        # tough day
                self._eng_obj_wrap_due = now + 6.0   # objective verdict after
                return add(cat, 0)

        # PHASE 3 — OBJECTIVE WRAP: a few seconds after the finish verdict, how
        # the targets went today, with recent form when there's enough history.
        # Sits here (before the post-flag gate below) because it is the one
        # thing still worth saying once the race is over.
        _wrap_due = getattr(self, "_eng_obj_wrap_due", None)
        if (_wrap_due and now >= _wrap_due
                and not self._eng_flags.get("objwrap")):
            self._eng_flags["objwrap"] = True
            summ = self.objective_summary()
            if summ and summ[0] in ENGINEER_LINES:
                return add(summ[0], 1, bypass=True, **summ[1])

        # the flag is out: nothing below is news any more. The cool-down lap
        # naturally slows, cuts corners and invalidates — without this gate the
        # engineer scolded "you ran over the track limits" AFTER the race.
        if self._eng_flags.get("finseen"):
            return

        # INCIDENT POINTS — report EVERY point you pick up and escalate hard as
        # you near the disqualification limit. Checked from the GREEN flag (they
        # count from lap one) and BYPASSES the chatter-drop so you never miss one
        # — the whole point is you should never get DQ'd by surprise.
        ip, mip = s.incident_points, s.max_incident_points
        if ip >= 0 and ip < getattr(self, "_eng_ip", 0):
            self._eng_ip = ip                  # game reset the counter — re-seed
        if (self._racing and mip > 0 and ip > getattr(self, "_eng_ip", 0)
                and now - getattr(self, "_eng_ip_cd", -1e9) > 5.0):
            self._eng_ip = ip
            self._eng_ip_cd = now
            left = mip - ip
            cat = ("points_critical" if left <= max(2, int(mip * 0.15))
                   else "points_high" if ip >= mip * 0.5
                   else "warn_points")
            line = _safe_format(self._pick(ENGINEER_LINES[cat], ("ENGINEER", cat)),
                                dict(pos=fp, pts=ip, maxpts=mip, left=left))
            events.append((0, -1, "RACE ENGINEER", line, True,  # bypass: never drop
                           "ENGINEER", "worried"))
            return

        # Silent until the race is GREEN — no "he's catching you" on the grid.
        # After that he is free the moment his own opening line has aired: the
        # old rule held him until lap 2, which left the most eventful minute
        # of the race (the lap-one scramble) with no engineer at all.
        if not self._racing:
            return
        if not self._eng_flags.get("start") and focused.completed_laps < 1:
            return          # opening line hasn't gone out yet — let it lead
        if (self.fastest.get("slot") == vslot and self.fastest.get("time")
                and not self._eng_flags.get("fastest")):
            self._eng_flags["fastest"] = True
            return add("fastest", 0)
        if (s.number_of_laps > 0 and focused.completed_laps == s.number_of_laps - 1
                and not self._eng_flags.get("lastlap")):
            self._eng_flags["lastlap"] = True
            return add("lastlap", 0)
        # closing-laps COUNTDOWN — once each at 5 / 3 / 2 to go (lap races)
        if s.number_of_laps > 0 and self._racing:
            cd_togo = s.number_of_laps - focused.completed_laps
            if cd_togo in (5, 3, 2) and self._eng_flags.get("cd") != cd_togo:
                self._eng_flags["cd"] = cd_togo
                return add("laps_countdown", 1, togo=cd_togo)
        # closing-MINUTES countdown — once each at 10 / 5 / 2 / 1 min (TIMED races)
        if s.number_of_laps <= 0 and self._racing and s.session_time_remaining > 0:
            secs = s.session_time_remaining
            mmk = (1 if secs <= 60 else 2 if secs <= 120 else 5 if secs <= 300
                   else 10 if secs <= 600 else 0)
            if mmk and self._eng_flags.get("mcd", 99) > mmk:
                self._eng_flags["mcd"] = mmk
                return add("mins_countdown", 1,
                           mins=("1 minute" if mmk == 1 else f"{mmk} minutes"))
        if focused.in_pitlane == 1:
            if not self._eng_flags.get("inpit"):
                self._eng_flags["inpit"] = True
                return add("pit", 0)
            return
        self._eng_flags["inpit"] = False

        # ---- TELEMETRY WARNINGS (your car's real data) — high priority ----
        # a penalty was just issued (rising edge on penaltyType)
        pen = getattr(focused, "penaltyType", -1)
        if pen >= 0 and self._eng_pen != pen:
            self._eng_pen = pen
            return add("warn_penalty", 0,
                       pen=PENALTY_SPOKEN.get(pen, "penalty"))
        if pen < 0:
            self._eng_pen = -1
        # (incident-point reporting moved above the lap-1 gate so it fires from
        # the green flag — every point, escalating toward the DQ limit)
        # NEXT LAP WON'T COUNT — lap_valid_state == 2 (this AND next lap invalid).
        # Rising edge -> warn every time it happens.
        lvs = getattr(s, "lap_valid_state", -1)
        if lvs == 2 and getattr(self, "_eng_lvs", -1) != 2:
            self._eng_lvs = lvs
            return add("nextlap", 1)
        self._eng_lvs = lvs
        # OFF-TRACK / TRACK LIMITS — warn EVERY time you leave the track, from
        # TWO signals: cut_track_warnings (RaceRoom's official limits counter) AND
        # the lap going invalid (current_lap_valid 1->0), which also catches the
        # grass/gravel excursions that DON'T trip the limits counter (the offs the
        # engineer used to miss). One shared cooldown so a single off that fires
        # both signals doesn't double-call; the emit loop's RADIO_ENG_CD throttles
        # it further so it never becomes chatter.
        plv = s.current_lap_valid
        cuts_now = s.cut_track_warnings
        cut_edge = cuts_now > self._eng_cuts
        lap_edge = (getattr(self, "_eng_plv", 1) == 1 and plv == 0
                    and self._racing and focused.in_pitlane != 1)
        # clamp at 0 so an N/A (-1) reading can never manufacture a rising
        # edge when the counter comes back; a decrease = reset, no edge
        self._eng_cuts = max(0, cuts_now)
        self._eng_plv = plv
        if cut_edge and now - getattr(self, "_eng_off_cd", -1e9) > 5.0:
            # RaceRoom's official limits counter ticked — always a real cut
            self._eng_off_cd = now
            self._eng_off_watch = None
            return self._limits_warn(add, cuts_now)
        # The lap-invalid edge alone is NOT proof of an off — it also fires for
        # a harmless kerb/paint clip at full speed (same reasoning as the booth's
        # off grading), which had the engineer scolding "you ran over the track
        # limits" when the player never left the road. Treat it as a CANDIDATE
        # and only call it if the speed genuinely collapses during the window.
        spd = abs(s.car_speed)
        if (lap_edge and spd > 3.0
                and getattr(self, "_eng_off_watch", None) is None):
            self._eng_off_watch = [now + 1.8, spd]
        watch = getattr(self, "_eng_off_watch", None)
        if watch is not None:
            deadline, ref = watch
            if (spd < ref * 0.62
                    and now - getattr(self, "_eng_off_cd", -1e9) > 5.0):
                self._eng_off_watch = None       # confirmed: real excursion
                self._eng_off_cd = now
                return self._limits_warn(add, cuts_now)
            if now > deadline:
                self._eng_off_watch = None       # clean clip — say nothing
        # OFFLINE INCIDENT TALLY. incident_points/max_incident_points are SERVER
        # fields (-1 = N/A per r3e.h), so vs AI the official block above never
        # runs and the engineer never mentioned incidents at all. With no server
        # limit there's no DQ threshold to quote, so report our own running
        # count of confirmed moments — every 3rd, never the first.
        # Placed AFTER the off-track handling deliberately: it must never
        # preempt (and swallow) the immediate limits warning for a live off.
        # Spaced well clear of the off itself so it lands as a reflective
        # "let's reset" later in the lap, not as an echo of that same call.
        if (self._racing and mip <= 0
                and getattr(self, "_own_inc", 0) >= 3
                and self._own_inc % 3 == 0
                and self._own_inc != getattr(self, "_own_inc_said", 0)
                and now - getattr(self, "_eng_off_cd", -1e9) > 25.0
                and now - getattr(self, "_own_inc_cd", -1e9) > 20.0):
            self._own_inc_said = self._own_inc
            self._own_inc_cd = now
            return add("incident_tally", 1, count=self._own_inc)
        # a serveable penalty (drive-through / stop-go) sitting unserved — remind
        if pen in (0, 1) and now - getattr(self, "_eng_pen_remind", 0.0) > 22.0:
            self._eng_pen_remind = now
            return add("penalty_serve", 1)
        # MANDATORY pit stop only. RaceRoom's pitstop_status is the authoritative
        # signal: -1 = no mandatory stop this session, 0/1 = a mandatory stop is
        # required and NOT yet served (two/four tyres), 2 = already served. Only
        # nag when a stop is genuinely required, unserved, AND the window's open
        # (pit_window_status 2 = OPEN) — never on a no-stop race.
        pstat = getattr(focused, "pitstop_status", -1)
        mandatory_unserved = pstat in (0, 1)
        window_open = getattr(s, "pit_window_status", 0) == 2
        if (mandatory_unserved and window_open
                and now - getattr(self, "_eng_pit_remind", 0.0) > 30.0):
            self._eng_pit_remind = now
            return add("pit_needed", 1)

        # OVERTAKE / position-change acknowledgement. Compare CONFIRMED place to
        # the place we LAST ANNOUNCED — not just last tick — so the call survives
        # even if the exact overtaking tick is busy with another message; it then
        # lands at the next opening instead of being lost forever (the old
        # last-tick compare gave a one-tick window that the 14s spacing routinely
        # swallowed, which is why overtakes went unacknowledged). bypass=True so
        # it skips that spacing; its own short cooldown stops a multi-place
        # shuffle from machine-gunning.
        # These acks carry a SHORT TTL (not bypass's usual no-expiry): "P13
        # now" is wrong once you've climbed to P10, so if it can't play while
        # still true it must drop rather than air late. This is the fix for
        # the start-of-race drip — a burst of stale per-place calls queued
        # behind the lights-out booth chatter and played back to back while the
        # driver was already several places higher.
        _ACK_TTL = 7.0
        # opening laps are a scramble, so wait LONGER between acks early on and
        # coalesce a fast multi-car climb into one line instead of a per-place
        # roll-call ("P14 up to P10, four places!" not P13, P12, P11...).
        early = focused.completed_laps < 2
        ack_cd = 12.0 if early else 8.0
        if self._eng_last_ann_place is None:
            self._eng_last_ann_place = fpc
        elif fpc != self._eng_last_ann_place and now - self._eng_place_cd > ack_cd:
            njump = self._eng_last_ann_place - fpc      # +climbed / -dropped
            gained_now = njump > 0
            led = (fpc == 1 and self._eng_last_ann_place > 1)
            prev_ann = self._eng_last_ann_place
            self._eng_last_ann_place = fpc
            self._eng_place_cd = now
            if led:
                return add("lead", 0, bypass=True, ttl=_ACK_TTL)
            if not gained_now:
                return add("lost", 1, bypass=True, ttl=_ACK_TTL)
            # MULTI-CLIMB: three or more places since the last ack is one big
            # move, not three small ones. Report the net jump in a single line
            # (grid/prev -> now), which is what the driver actually feels.
            if njump >= 3:
                return add("gained_multi", 1, bypass=True, ttl=_ACK_TTL,
                           gain=njump, frm=prev_ann)
            # name WHERE the pass happened when we can place it at a corner
            # (named or 'Turn N'); a vague sector phrase isn't worth it for an
            # overtake, so only upgrade on a real corner, else the plain pool.
            where = self._where_on_track(s, focused.lap_distance_fraction)
            if where.startswith("into ") and random.random() < 0.7:
                return add("gained_where", 1, bypass=True, ttl=_ACK_TTL,
                           where=where)
            return add("gained", 1, bypass=True, ttl=_ACK_TTL)
        # (the race objective is drained at the TOP of this function — it used
        # to live here, where the place-change calls above buried it)

        # directional gap calls (only when the gap is actually moving)
        if ahead and gap and pgap is not None:
            if gap < 2.0 and gap < pgap - 0.05:        # you're closing on car ahead
                return add("catching", 2)
            if gap < 4.0 and gap > pgap + 0.10:        # car ahead pulling away
                return add("dropping", 2)
        if behind and gapb and pgapb is not None:
            if gapb < 1.5 and gapb < pgapb - 0.05:      # car behind closing on you
                return add("defending", 2)
            if gapb < 3.0 and gapb > pgapb + 0.10:      # you're pulling clear
                return add("clear", 2)
        # ---- TELEMETRY STATUS (fuel / tyres / damage) — lower priority, on
        # their own long cooldowns so they're useful, not naggy ----
        if s.fuel_use_active and s.fuel_per_lap > 0 and now - self._eng_fuel_cd > 40.0:
            laps_fuel = s.fuel_left / s.fuel_per_lap
            laps_left = (s.number_of_laps - focused.completed_laps
                         if s.number_of_laps > 0 else None)
            if laps_left is not None and 0 < laps_fuel < laps_left - 0.5:
                self._eng_fuel_cd = now
                return add("fuel_save", 2, laps=max(1, int(laps_fuel)))
            if laps_fuel < 3.0:
                self._eng_fuel_cd = now
                return add("fuel_low", 2)
        if s.tire_wear_active and now - self._eng_tyre_cd > 45.0:
            tw = list(s.tire_wear)
            if len(tw) == 4:
                if self._eng_tyre_base is None:
                    self._eng_tyre_base = tw          # fresh-tyre reference
                else:
                    worn = max(abs(self._eng_tyre_base[i] - tw[i]) for i in range(4))
                    if worn > 0.75 and not self._eng_flags.get("tyrecrit"):
                        self._eng_flags["tyrecrit"] = True
                        self._eng_tyre_cd = now
                        # only tell him to BOX if a mandatory stop is still coming
                        # (pstat 0/1 unserved); otherwise it's a no-stop race —
                        # manage the worn tyres to the flag, don't nag to pit.
                        return add("pit_tyres" if pstat in (0, 1)
                                   else "tyres_gone", 1)
                    if worn > 0.45:                   # well into the wear range
                        self._eng_tyre_cd = now
                        return add("tyres_worn", 2)
        # CAR DAMAGE — car_damage fields are a HEALTH fraction (1.0 = pristine,
        # 0.0 = hurt; -1.0 = N/A when the damage model is off). RaceRoom's note:
        # aero damage is "a bit arbitrary", so real contact often moves health
        # only a few percent — the old >0.12 gate meant most damage was never
        # called. Report meaningful drops sensitively, re-baseline so a SEPARATE
        # later contact reports again, and escalate to a box call when a part is
        # badly hurt (big single hit OR low absolute health).
        dmg = s.car_damage
        for part, val in (("engine", dmg.engine), ("transmission", dmg.transmission),
                          ("aero", dmg.aerodynamics), ("suspension", dmg.suspension)):
            if val < 0:                       # -1 = N/A (damage model disabled)
                continue
            base = self._eng_dmg.get(part)
            if base is None:
                self._eng_dmg[part] = val
                continue
            if val > base:                    # part repaired (pit) -> track recovery
                self._eng_dmg[part] = val
                continue
            drop = base - val                 # health lost since the reference
            if drop < 0.03:                   # noise / nothing meaningful
                continue
            # SEVERE -> box to repair. Latched per part, but re-arms if it gets
            # materially worse so a second big hit still gets a fresh call.
            sev = self._eng_dmg_sev.get(part)
            if (drop > 0.22 or val < 0.55) and (sev is None or sev - val > 0.10):
                # flag SEVERE damage for the objective system: it withdraws any
                # attacking target and switches to damage limitation
                self._obj_damaged = True
                self._eng_dmg_sev[part] = val
                self._eng_dmg[part] = val
                self._eng_dmg_cd[part] = now
                self._eng_flags[f"dmg_{part}"] = True
                # bypass the engineer throttle: a box-to-repair call is one-shot
                # (the baseline resets after it, so it never regenerates) and must
                # never be swallowed by the 14s spacing — like the DQ warnings.
                return add("pit_damage", 1, bypass=True, part=part)
            # LIGHT/MODERATE -> report it, re-baseline, and cool down so a single
            # scrape doesn't chatter but a fresh contact later still gets called.
            if now - self._eng_dmg_cd.get(part, -1e9) > 25.0:
                self._eng_dmg[part] = val
                self._eng_dmg_cd[part] = now
                self._eng_flags[f"dmg_{part}"] = True
                # bypass=True, like the box call above. THIS BLOCK HAS ALREADY
                # RE-BASELINED by the time the line is emitted, so if the
                # RADIO_ENG_CD spacing drops it (a silent `continue` in the
                # emit loop) the damage counts as reported and can NEVER fire
                # again — the car is visibly broken and the engineer never
                # mentions it for the rest of the race. Any state mutated
                # before an add() must not depend on that add() surviving.
                # Its own 25s per-part cooldown above stops it machine-gunning.
                return add("damage", 1, bypass=True, part=part)

        # ---- TYRE & BRAKE TEMPERATURES — read the live tread/brake telemetry
        # against the car's OWN optimal/cold/hot references. Centre-tread (index
        # 1) is the core temperature; -1 / non-positive refs mean N/A (no temp
        # model) and are skipped. Not for the pit-lane or the opening crawl.
        if (self._racing and focused.in_pitlane != 1
                and focused.completed_laps >= 1):
            def _axle_temp(i0, i1):
                cs, opt, cold, hot = [], [], [], []
                for i in (i0, i1):
                    t = s.tire_temp[i]
                    c = t.current_temp[1]               # CENTER tread = core
                    if c > 0 and t.hot_temp > 0 and t.optimal_temp > 0:
                        cs.append(c)
                        opt.append(t.optimal_temp)
                        cold.append(t.cold_temp)
                        hot.append(t.hot_temp)
                if not cs:
                    return None
                n = len(cs)
                return (sum(cs) / n, sum(cold) / n, sum(hot) / n)
            front = _axle_temp(0, 1)
            rear = _axle_temp(2, 3)
            # OVERHEAT / COLD — a centre temp past the hot or cold reference.
            if (front or rear) and now - getattr(self, "_eng_temp_cd", -1e9) > 50.0:
                hot_ax = [nm for nm, ax in (("fronts", front), ("rears", rear))
                          if ax and ax[0] > ax[2]]
                cold_ax = [nm for nm, ax in (("fronts", front), ("rears", rear))
                           if ax and ax[0] < ax[1]]
                if hot_ax:
                    self._eng_temp_cd = now
                    ax = "tyres" if len(hot_ax) == 2 else hot_ax[0]
                    # sitting in another car's wake is a classic overheat cause
                    if ahead and gap and gap < 1.5:
                        return add("tyre_hot_traffic", 2, ax=ax)
                    return add("tyre_hot", 2, ax=ax)
                if cold_ax:
                    self._eng_temp_cd = now
                    ax = "tyres" if len(cold_ax) == 2 else cold_ax[0]
                    return add("tyre_cold", 2, ax=ax)
            # BRAKES — a brake over its hot reference risks fade.
            if now - getattr(self, "_eng_brake_cd", -1e9) > 60.0:
                def _brake_hot(i0, i1):
                    cs, hot = [], []
                    for i in (i0, i1):
                        b = s.brake_temp[i]
                        if b.current_temp > 0 and b.hot_temp > 0:
                            cs.append(b.current_temp)
                            hot.append(b.hot_temp)
                    return bool(cs) and (sum(cs) / len(cs) > sum(hot) / len(hot))
                fb, rb = _brake_hot(0, 1), _brake_hot(2, 3)
                if fb or rb:
                    self._eng_brake_cd = now
                    ax = ("front and rear" if fb and rb
                          else "front" if fb else "rear")
                    return add("brake_hot", 2, ax=ax)

        # ---- ENGINE TEMPERATURE (mechanical sympathy). The API gives a bare
        # Celsius value with NO optimal/max reference (and it's player-only), so
        # an absolute threshold would be wrong from car to car. Instead learn
        # THIS car's warmed-up running temp (after a couple of green laps) and
        # warn only on a large, SUSTAINED rise above it — a genuine cooling
        # problem (damage, or a blocked radiator sat in traffic), not the normal
        # rise-and-fall of a stint.
        if (self._racing and focused.in_pitlane != 1
                and focused.completed_laps >= 2):
            et = max(s.engine_temp, s.engine_oil_temp)   # whichever runs hotter
            base = self._eng_engtemp_base                # seeded early (lap >= 2)
            if et > 0 and base is not None:
                if et < base:                            # track the steady-state
                    self._eng_engtemp_base = base + (et - base) * 0.05
                if et - self._eng_engtemp_base > 20.0:
                    if self._eng_engtemp_hot_since is None:
                        self._eng_engtemp_hot_since = now
                    elif (now - self._eng_engtemp_hot_since > 4.0
                          and now - self._eng_engtemp_cd > 60.0):
                        self._eng_engtemp_cd = now
                        dmg_now = any(
                            self._eng_flags.get(f"dmg_{p}") for p in
                            ("engine", "aero", "suspension", "transmission"))
                        return add("engine_hot_dmg" if dmg_now
                                   else "engine_hot", 2)
                else:
                    self._eng_engtemp_hot_since = None

        # SECTOR COACHING (race) — occasional, specific feedback on where your
        # last lap gained or lost time. Own slow cooldown so it stays useful, not
        # constant; the in-race battle/telemetry calls above always take priority.
        if (self._racing and focused.in_pitlane != 1
                and now - getattr(self, "_eng_sec_cd", 0.0) > 55.0):
            adv = self._sector_advice(s, focused)
            if adv and adv[0] != "solid":     # don't interrupt with "nothing to fix"
                self._eng_sec_cd = now
                return self._emit_sector(adv, events, 3)

        # periodic "where are we in the race" update so you always know how far is
        # left (laps or, in a timed race, minutes) — on its own slow cooldown
        if self._racing and now - getattr(self, "_eng_laps_cd", 0.0) > 70.0:
            if s.number_of_laps > 0:
                done = focused.completed_laps
                lt = s.number_of_laps - done
                if lt >= 4:                       # last few handled by the countdown
                    self._eng_laps_cd = now
                    return add("laps_update", 2, togo=lt, done=done,
                               total=s.number_of_laps)
            elif s.session_time_remaining > 90:
                self._eng_laps_cd = now
                return add("time_update", 2,
                           mins=int(s.session_time_remaining // 60))

        # PROACTIVE per-section coaching — as you cross into a new sector, an
        # occasional track-aware heads-up for the part of the lap coming up. Rare
        # in the race (long cooldown + low chance) so it's the engineer being
        # alive to where you are on the lap, never nagging you about a track you
        # already know. track_sector is 1/2/3 (0 = N/A); fire on the rising edge.
        cur_sec = getattr(focused, "track_sector", 0)
        prev_sec = self._eng_sector_prev
        self._eng_sector_prev = cur_sec
        if (self._racing and prev_sec in (1, 2, 3) and cur_sec in (1, 2, 3)
                and cur_sec != prev_sec and focused.in_pitlane != 1
                and now - self._eng_section_cd > 80.0
                and random.random() < 0.2):
            # prefer the tip for THE SECTOR you just entered (curated tracks);
            # otherwise fall back to the general track tip
            tip = (self._sector_tip(s, cur_sec)
                   or self._track_tip(self._short_track(R.u8_to_str(s.track_name))))
            if tip:
                self._eng_section_cd = now
                return add("section_ahead", 3, sec=cur_sec, tip=tip)

        # LAP-SPLIT coaching (race) — on a completed lap, compare your sector
        # splits to your own best and point at where the time is going, with
        # that sector's track-specific tip where we have one. This is the
        # 'you're struggling in sector two, here's what to do about it' layer;
        # long cooldown so racing information always comes first.
        if self._racing and now - self._eng_sec_cd > 75.0:
            adv = self._sector_advice(s, focused)
            if adv and adv[0] in ("slow", "mixed"):
                self._eng_sec_cd = now
                return self._emit_sector(adv, events, 3, s=s)

        # nothing dynamic happening -> stay INVOLVED with a proactive report:
        # a gap to the car ahead/behind, or POSITION-AWARE encouragement (never
        # "you're perfect" when you're dead last). When the car's healthy, an
        # occasional "gap's good, no damage, keep pushing" status.
        if now - self._enc_cd > 15.0:
            self._enc_cd = now
            # occasionally drop a real track tip to help find pace (across all
            # sessions) instead of generic encouragement
            if now - getattr(self, "_eng_tip_cd", 0.0) > 150.0:
                tip = self._track_tip(self._short_track(R.u8_to_str(s.track_name)))
                if tip and random.random() < 0.25:
                    self._eng_tip_cd = now
                    events.append((3, -1, "RACE ENGINEER", tip, False,
                                   "ENGINEER", "neutral"))
                    return
            opts = []
            if ahead and gap:
                opts.append("info_ahead")
            if behind and gapb:
                opts.append("info_behind")
            healthy = not any(self._eng_flags.get(f"dmg_{p}") for p in
                              ("engine", "transmission", "aero", "suspension"))
            if healthy and fp <= 12:
                opts.append("status_good")
            opts.append("enc_top" if fp <= 3 else "enc_mid" if fp <= 10
                        else "enc_back")
            return add(random.choice(opts), 3)

    def _radio_line(self, d, category, who=""):
        persona = self._persona_for(d)
        # ~10% of the time, drop in a famous real motorsport quote as an easter
        # egg (kept rare so it stays a treat, not a gimmick).
        eggs = EASTER_EGGS.get(category)
        if eggs and random.random() < 0.10:
            line = self._pick(eggs, ("EGG", category))
            line = line.format(pos=d.place, who=who or "the guy behind")
            return self._moodify(d.driver_info.slot_id, line)
        pools = PERSONAS[persona]
        pool = pools.get(category) or pools.get("taunt") or next(iter(pools.values()))
        pool = pool + EXTRA_LINES.get(category, [])   # +generic lines for variety
        line = self._pick(pool, (persona, category))
        line = line.format(pos=d.place, who=who or "the guy behind")
        return self._moodify(d.driver_info.slot_id, line)

    def _limits_warn(self, add, cuts_now):
        """A confirmed track-limits / off-track moment. Keeps a RUNNING count
        and escalates, so repeated offs stop sounding like the first one.

        cut_track_warnings is a SERVER field (-1 = N/A offline per r3e.h), so
        offline it never moves — we count confirmed moments ourselves and use
        the server's figure only when it's actually being published."""
        self._own_cuts = getattr(self, "_own_cuts", 0) + 1
        self._own_inc = getattr(self, "_own_inc", 0) + 1
        n = cuts_now if cuts_now > 0 else self._own_cuts
        cat = ("warn_limits_serious" if n >= 5
               else "warn_limits_repeat" if n >= 2
               else "warn_offtrack")
        return add(cat, 1, cuts=n)

    def _sector_advice(self, s, focused):
        """On a completed-lap edge, read your last lap's three sector splits
        against your OWN best (and the session best) and return (category, fmt)
        for a specific coaching line — or None. Consumes the lap edge per call.

        RaceRoom sector times are CUMULATIVE ([s1, s1+s2, s1+s2+s3]), so each
        sector is the difference between consecutive entries."""
        sl = focused.driver_info.slot_id
        cl = focused.completed_laps
        prevc = self._sec_laps.get(sl)
        self._sec_laps[sl] = cl
        if prevc is None or cl <= prevc or cl < 2:
            return None                      # need a prior lap to compare against
        prev = list(focused.sector_time_previous_self)
        best = list(focused.sector_time_best_self)
        if not (prev[0] > 0 and prev[1] > 0 and prev[2] > 0):
            return None
        if not (best[0] > 0 and best[1] > 0 and best[2] > 0):
            return None
        lap = [prev[0], prev[1] - prev[0], prev[2] - prev[1]]
        bst = [best[0], best[1] - best[0], best[2] - best[1]]
        if min(lap) <= 0 or min(bst) <= 0:
            return None                      # garbage split — skip
        deltas = [lap[i] - bst[i] for i in range(3)]      # +ve = slower than best
        worst = max(range(3), key=lambda i: deltas[i])
        bests = min(range(3), key=lambda i: deltas[i])
        # was a sector right on the SESSION best (purple)?
        sess = list(getattr(s, "session_best_lap_sector_times", [0, 0, 0]))
        purple = None
        if len(sess) == 3 and sess[0] > 0 and sess[1] > 0 and sess[2] > 0:
            ss = [sess[0], sess[1] - sess[0], sess[2] - sess[1]]
            for i in range(3):
                if ss[i] > 0 and lap[i] <= ss[i] + 0.03:
                    purple = i
        d_txt = f"{deltas[worst]:.2f}s"
        # all three near your best -> a clean, consistent lap
        if deltas[worst] < 0.12:
            if deltas[bests] < -0.03 or purple is not None:
                return ("strong", {"sec": (purple if purple is not None
                                           else bests) + 1})
            return ("solid", {})
        # one strong AND one weak -> the classic "great here, costing there"
        if deltas[bests] < -0.04 and deltas[worst] > 0.15:
            return ("mixed", {"one": bests + 1, "two": worst + 1, "d": d_txt})
        # otherwise: name the weakest sector and how much it's costing
        return ("slow", {"sec": worst + 1, "d": d_txt})

    def _sector_tip(self, s, sec):
        """A per-track coaching tip for a SPECIFIC timing sector (1-3), or None.
        Curated tracks only, and only on their full/GP layouts — a short layout
        splits the sectors elsewhere, and a wrong 'sector two is the hairpin'
        breaks immersion far worse than a generic tip."""
        full = (R.u8_to_str(s.track_name) or "").lower()
        if any(w in full for w in ("indy", "national", "club", "short",
                                   "sprint", "moto", "classic", "junior")):
            return None
        for key, secs in TRACK_SECTOR_TIPS.items():
            if key in full:
                pool = secs.get(str(sec))
                if pool:
                    return self._pick(pool, ("SECTIP", f"{key}#{sec}"))
        return None

    def _emit_sector(self, adv, events, prio, s=None):
        """Append a sector-coaching engineer line for a (category, fmt) advice.
        When the advice names a WEAK sector and we have curated notes for this
        track, the engineer follows the split with THAT sector's actual tip —
        'sector two is costing you… here's where the time is'."""
        cat, fmt = adv
        line = _safe_format(self._pick(SECTOR_COACH[cat], ("SEC", cat)), fmt)
        if s is not None and cat in ("slow", "mixed"):
            weak = fmt.get("sec") or fmt.get("two")
            tip = self._sector_tip(s, weak) if weak else None
            if tip:
                line = f"{line} {tip}"
        emo = {"strong": "smug", "solid": "smug"}.get(cat, "neutral")
        events.append((prio, -1, "RACE ENGINEER", line, False, "ENGINEER", emo))

    def _air_bubble(self, msg):
        """Put a team-radio bubble on screen the instant its audio starts, so
        the bubble matches what's heard. Called from the TTS worker thread."""
        # hold at least as long as the audio runs (estimated from length) — a
        # fixed hold dropped the bubble mid-sentence on longer radio calls,
        # which read as the captions being out of sync with the voice
        hold = max(self.RADIO_HOLD, min(14.0, len(msg["text"]) * 0.055 + 2.5))
        msg["until"] = time.time() + hold
        msg["at"] = time.time()               # entrance animation reference
        with _RADIO_LOCK:
            self.radio_msgs.append(msg)
            self.radio_msgs = self.radio_msgs[-6:]

    def _wrap(self, text, width=34, maxlines=2):
        words, lines, cur = text.split(), [], ""
        for wd in words:
            if len(cur) + len(wd) + 1 > width:
                lines.append(cur); cur = wd
            else:
                cur = (cur + " " + wd).strip()
        if cur:
            lines.append(cur)
        return lines[:maxlines]

    def _draw_bubble(self, x, y, w, m):
        col = m.get("color", ACCENT)
        is_eng = bool(m.get("engineer"))
        accent = HEADER_ACCENT if is_eng else col
        lines = self._wrap(m["text"], width=30)
        h = _BUBBLE_H(len(lines))
        # broadcast card: dark rounded box, thin border, accent strip in the
        # driver's colour (cyan for the engineer)
        # SOLID (glass=False) on purpose. The icons are PNGs flattened onto
        # CARD_BG to kill their colour-key fringe, so each carries an opaque
        # CARD_BG square. Against a TRANSLUCENT glass body that square read as
        # a darker rectangle — the visible "image border". Drawing the radio
        # card solid in the SAME colour makes icon background and card
        # identical, so the artwork reads as fully transparent again.
        self._card(x, y, w, h, fill=CARD_BG, accent=accent, side="top",
                   glass=False)
        # avatar in a SQUARE region (so it's never stretched), vertically centred.
        # Drawn on the panel's real canvas — avatars use polygon/arc, which the
        # translating canvas wrapper doesn't proxy — at panel-local coords.
        # CAPPED at 36px: the old h-18 grew the icon to ~58px on two-line
        # cards, dwarfing the text — the icon is a badge, not the content.
        av = min(h - 22, 36)
        ax = x + 11
        ay = y + (h - av) // 2
        # user-drawn PNG icon takes priority when present. Drivers: the
        # PRE-COLOURED variant assigned to them (icon_helmet_*.png, used as
        # drawn); else the single tintable icon_helmet.png; else vectors.
        ph = None
        if not is_eng:
            vi = self._dvariant.get(m["name"])
            if vi is None:                     # colour not assigned yet
                self._color_for_name(m["name"])
                vi = self._dvariant.get(m["name"])
            if vi is not None:
                ph = avatars.variant_icon(vi, av)
        if ph is None:
            ph = avatars.custom_icon("engineer" if is_eng else "helmet", av,
                                     None if is_eng else col)
        if ph is not None:
            self._cv_real.create_image(ax - self._ox, ay - self._oy,
                                       image=ph, anchor="nw")
        elif is_eng:
            avatars.draw_headset(self._cv_real, ax - self._ox, ay - self._oy, av)
        else:
            avatars.draw_helmet(self._cv_real, ax - self._ox, ay - self._oy,
                                av, col, seed=m["name"])
        tx = ax + av + 12                     # text zone starts after the avatar
        name = m["name"][:14]
        self.text(tx, y + 17, name, fill=accent, font=self.f_row_b, anchor="w")
        if not is_eng:                        # small "RADIO" tag pill (drivers)
            px = tx + self.f_row_b.measure(name) + 8
            self.canvas.create_rectangle(px, y + 10, px + 42, y + 23,
                                         fill="#1c2530", outline="")
            self.text(px + 21, y + 16, "RADIO", fill=DIM,
                      font=self.f_small_b, anchor="center")
        ly = y + 36
        for ln in lines:
            self.text(tx, ly, ln, fill=TEXT, font=self.f_row, anchor="w")
            ly += 18
        return h

    def _report_offtrack(self, name, now, primary=False):
        """Single entry point for EVERY off-track call (your car and rivals), so
        multiple incidents are handled coherently instead of interrupting one
        another mid-sentence. The model:

          • FRESH report — the pundit names the car (after an instant bridging
            sting) and the lead hands back ('hope they're okay'). Opens a ~7s
            'incident window'.
          • A car going off DURING that window is folded in as a follow-up queued
            BEHIND (never cuts the first call): the 1st extra -> 'and {drv} is off
            too!', a 2nd+ -> one 'chaos, multiple cars off!' line, then we go
            quiet so it can't become a spammy roll-call.

        primary=True (YOUR car) ALWAYS gets the full named report + ack — it is
        never downgraded to a follow-up. This matters because going off often
        brings out a yellow a beat earlier, which would otherwise 'open' the
        window and swallow your own off into a terse 'and X is off too'.

        Rivals are detected via position loss (the only signal we get for other
        cars, so slightly delayed); your own car is caught instantly upstream."""
        if not self.tts:
            return

        def say(cat, persona, cutoff=False, **kw):
            pool = COMMENTARY_LINES.get(cat)
            if not pool:
                return
            kw.setdefault("comm", COMMENTATOR_NAME)
            kw.setdefault("pundit", PUNDIT_NAME)
            kw.setdefault("comm_full", COMMENTATOR_FULL)
            kw.setdefault("pundit_full", PUNDIT_FULL)
            text = _safe_format(self._pick(pool, ("COMM", cat)), kw)
            if cutoff:
                self.tts.interrupt()
            self.tts.speak(self._spoken(text), persona,
                           seed=("PUNDIT" if persona == "PUNDIT" else "COMM"),
                           intensity=(2 if persona == "PUNDIT" else 0),
                           on_play=self._show_caption, force=True)

        active = now < getattr(self, "_incident_until", 0.0)
        # ONE INCIDENT PER DRIVER. The window above coalesces by TIME but never
        # asked WHO, so the same car could be reported over and over: a real log
        # had Marco Wittmann called three times in ten seconds — a full report,
        # then a second full report once the 7s window lapsed, then folded in as
        # "Make that two — Marco Wittmann has gone off", which names him as his
        # own second car. Rivals are detected by position loss, and one spin
        # sheds places over several seconds, so a single incident readily
        # triggers the detector more than once.
        #
        # Anyone already named in this incident is done: a driver going off does
        # not go off again a heartbeat later, and saying so is worse than
        # silence because it invents cars that never crashed.
        seen = getattr(self, "_incident_names", None)
        if seen is None or not active:
            seen = self._incident_names = set()
        if name in seen and active:
            return
        seen.add(name)
        if primary or not active:                            # FULL named report
            cutting_lead = self.tts.speaking_persona() == "COMMENTATOR"
            # INSTANT bridging sting ("Oh, trouble — looks like someone's gone
            # off!") + subtitle, filling the ~1s while the NAMED line renders. But
            # don't sting if something incident-ish is ALREADY playing (e.g. a
            # yellow just stung) — a second sting would purge that audio; instead
            # the named line cuts in itself. The sting does its own interrupt, so
            # when it fires the named line must NOT interrupt again.
            stung = (not active) and self.tts.sting(
                "alert", "PUNDIT", on_play=self._show_caption)
            cat = ("offtrack" if (stung or not cutting_lead) else "offtrack_cut")
            say(cat, "PUNDIT", cutoff=not stung, drv=name)
            say("offtrack_ack", "COMMENTATOR")
            self._incident_until = now + 7.0
            self._incident_extra = 0
        else:                                                # during a report
            self._incident_extra = getattr(self, "_incident_extra", 0) + 1
            if self._incident_extra == 1:
                say("offtrack_more", "PUNDIT", drv=name)     # queued behind
                self._incident_until = max(self._incident_until, now + 4.0)
            elif self._incident_extra == 2:
                say("offtrack_chaos", "PUNDIT")
                self._incident_until = max(self._incident_until, now + 4.0)

    def _moodify(self, slot, line):
        """Prepend a frustrated/pumped interjection when a driver is on a
        losing/winning streak — makes them feel human over a stint."""
        m = self._mood.get(slot, 0.0)
        if m <= -2.5 and random.random() < 0.5:
            return self._pick(MOOD_FRUSTRATED, ("moodf",)) + " " + line
        if m >= 2.5 and random.random() < 0.5:
            return self._pick(MOOD_PUMPED, ("moodp",)) + " " + line
        return line

    def _intro_done(self, now):
        """True once the booth's session intro has AIRED, so the engineer can
        start talking. Latches True for the session. If there's no booth to wait
        for (commentary off / TTS muted or absent) it's immediately True; the
        booth records _intro_emit_t when it emits the opener (set in
        update_commentary), and we release once the audio queue has drained or a
        safety timeout passes so the engineer can never be starved into silence."""
        if getattr(self, "_intro_aired", False):
            return True
        # RACE: the gate ends the moment the lights go out. Holding the
        # engineer through the booth's opening spiel meant he was mute for most
        # of lap one — no launch call, and a lap-1 off got reported a lap late
        # (the edge trackers below the gate never ran). He talks to YOU from
        # the green; the pipeline's radio priority handles booth overlap.
        # (NB _racing latches True for ALL non-race sessions, so check the
        # session type — quali/practice keep waiting for the booth opener.)
        sk = getattr(self, "_sess_key", None)
        if (getattr(self, "_racing", False)
                and sk is not None and sk[2] == 2):
            self._intro_aired = True
            return True
        if (not self.commentary_on or self.tts is None
                or not getattr(self.tts, "enabled", False)):
            self._intro_aired = True
            return True
        et = getattr(self, "_intro_emit_t", None)
        if et is None:
            # SAFETY: if the booth never sets a scene (mid-session join, or a
            # replay where the opener doesn't trigger), don't gag the engineer
            # forever — release a few seconds into the session.
            if now - getattr(self, "_sess_start_t", now) > 8.0:
                self._intro_aired = True
                return True
            return False                       # booth hasn't set the scene yet
        drained = (not self.tts.speaking() and self.tts._pending() == 0)
        if (now - et > 12.0) or (now - et > 1.0 and drained):
            self._intro_aired = True
            return True
        return False

    def _track_tip(self, trk):
        """A real 'find more time here' coaching tip the engineer can relay, or
        None if we don't have tips for this track."""
        low = (trk or "").lower()
        for key, tips in TRACK_TIPS.items():
            if key in low:
                return self._pick(tips, ("TIP", key))
        return None
