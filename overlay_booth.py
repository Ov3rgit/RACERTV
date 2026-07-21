# -*- coding: utf-8 -*-
"""
The broadcast booth: Miles on
play-by-play and Brett on colour. Owns the race/quali commentary direction
(what is worth saying and when), the crosstalk and lore exchanges, the race
story recaps and the finish sequence.

Mixed into Overlay (see r3e_overlay.py) — these methods take the
same `self` and call the rest of the class freely; only the file
they live in changed.
"""
import r3e_data as R
import random
import re
import time
from types import SimpleNamespace
from overlay_common import (_safe_format, CAT_INTENSITY, PUNDIT_AFTER, RECAP_CATS,
                            OBJ_BRIEF, OBJ_BRIEF_DEFAULT)
from lines import (COMMENTARY_LINES, COMMENTATOR_FULL, COMMENTATOR_NAME,
    CROSSTALK, CROSSTALK_ACK, CROSSTALK_ANSWERS, LORE_COMM_BY_TRACK,
    LORE_PUNDIT_BY_TRACK, LORE_TOPICS, PUNDIT_FULL, PUNDIT_LINES,
    PUNDIT_NAME, PUNDIT_PICK, STORY_REPORT, TRACK_COACH, TRACK_FACTS,
    TRACK_PUNDIT, TRACK_PUNDIT_BY_TRACK, TRACK_TIPS)


class BoothMixin:
    """See module docstring."""

    def update_commentary(self, s):
        """Third-person play-by-play over the WHOLE field. Reuses the per-tick
        stats (places, intervals, fastest lap) the overlay already computes."""
        now = time.time()
        if self._comm_key != self._sess_key:           # reset on new session
            self._comm_key = self._sess_key
            self._comm_prev = {}
            self._comm_cd = 0.0
            self._comm_flags = {}
            self._comm_lead = None
            self._comm_fastest_at = 0.0
            self._comm_pit = {}
            self._pit_t = {}          # slot -> last time seen in pitlane
            self._comm_prev_int = {}
            self._comm_pen = {}
            self._battle = {}
            self._battle_called = {}  # (chaser,target) -> last sustained-battle call
            self._battle_said = {}    # (pair) -> last close-fight colour call, so
                                      # one long scrap can't monopolise the booth
            self._battle_cd = 0.0     # global cooldown for sustained-battle calls
            self._last_pass = None    # (winner_slot, loser_slot, pos, t) re-pass detect
            self._race_story = {}     # slot -> {best,worst,now}: each driver's arc
            self._story_told = set()  # slots whose race-story recap has been aired
            self._wrap_until = 0.0    # clear stale post-race wrap protection
            self._last_off = None     # (name, t) most recent off — for naming yellows
            self._filler_cd = {}
            self._story = {}          # slot -> list of notable tags ("spun","led","recovered")
            self._comm_lap_cd = 0.0   # throttle for lap-report events
            self._crosstalk_t = 0.0   # last commentator->pundit question
            self._crosstalk_topic = None  # paired Q/A topic for the current crosstalk
            self._crosstalk_pos = 0   # the questioned driver's place
            self._comm_close_t = 0.0  # last closing-phase 'win fight' emphasis
            self._offtrack_cd = {}    # slot -> last off-track call (anti-double)
            self._player_lap_valid = 1  # player's prev current_lap_valid (edge)
            self._off_watch = None     # (deadline, ref_speed) while confirming an off
            self._incident_until = 0.0  # an incident is being reported until this
            self._incident_extra = 0    # extra cars off during the current window
            self._signed_off = False    # booth has aired its closing sign-off?
            self._filler_until = 0.0    # est. time a colour/filler line finishes
            self._comm_qpole = None     # slot on provisional pole (time-true)

        # booth muted (Ctrl+Shift+C) — AFTER the session reset above, so flags
        # can't go stale across a session change while the booth is off (the
        # old early-return woke the booth up still "signed off" from the
        # previous race). Engineer/driver radio are unaffected.
        if not self.commentary_on:
            return
        # once the booth has signed off (after the post-race wrap), the broadcast
        # is OVER — produce no further commentary. The queued wrap still plays out.
        if getattr(self, "_signed_off", False):
            return

        order = sorted(self._drivers(s), key=lambda d: d.place)
        if len(order) < 1:
            return
        placemap = {d.place: d for d in order}
        # change detection runs on CONFIRMED (debounced) places so the booth
        # never reacts to a flicker; display/naming still uses the live placemap
        cp = lambda d: self.cplace.get(d.driver_info.slot_id, d.place)
        cur = {d.driver_info.slot_id: cp(d) for d in order}
        # RACE STORY: keep every driver's arc (best/worst/current place) so the
        # booth can talk about anyone's race with real context ("started P3,
        # dropped to P12, recovered to P7"). Cheap per-tick bookkeeping.
        if s.session_type == 2 and self._racing:
            for d in order:
                sl, p = d.driver_info.slot_id, d.place
                st = self._race_story.get(sl)
                if st is None:
                    self._race_story[sl] = {"best": p, "worst": p, "now": p}
                else:
                    st["now"] = p
                    st["best"] = min(st["best"], p)
                    st["worst"] = max(st["worst"], p)
        trk = self._short_track(R.u8_to_str(s.track_name))
        is_race = (s.session_type == 2)
        n1 = self._dname(placemap[1]) if 1 in placemap else ""
        n2 = self._dname(placemap[2]) if 2 in placemap else ""
        n3 = self._dname(placemap[3]) if 3 in placemap else ""
        # QUALI/PRACTICE: the timing-tower 'place' is just registration order
        # until laps are actually set, so a name being 'P1' does NOT mean they're
        # on provisional pole. Build the REAL provisional order from drivers who
        # have banked a lap (best_lap among _q_set), sorted by time. n1/n2/n3 stay
        # place-based for race use; q_n1/q_n2/q_n3 are the time-true quali order.
        field_n = len(order)
        # an OPEN/registered qualifying or practice has NO clock (you can stay out
        # as long as you like with just your ghost); a pre-race quali is timed.
        open_sess = (getattr(s, "session_time_duration", 0.0) or 0.0) <= 0.0
        # SOLO = effectively on your own: one car, OR an open/registered session
        # with just you and your ghost (which can show as two entries). A timed
        # session with 2+ real cars is NOT solo.
        solo = (not is_race) and (field_n <= 1 or (open_sess and field_n <= 2))
        q_n1 = q_n2 = q_n3 = ""
        q_set_t = []
        if not is_race:
            q_set_t = [d for d in order
                       if d.driver_info.slot_id in getattr(self, "_q_set", set())
                       and self.best_lap.get(d.driver_info.slot_id)]
            q_set_t.sort(key=lambda d: self.best_lap[d.driver_info.slot_id])
            q_n1 = self._dname(q_set_t[0]) if len(q_set_t) > 0 else ""
            q_n2 = self._dname(q_set_t[1]) if len(q_set_t) > 1 else ""
            q_n3 = self._dname(q_set_t[2]) if len(q_set_t) > 2 else ""
        cands = []   # (priority, text, cat, intensity, persona)

        def L(cat, prio, persona="COMMENTATOR", line=None, **kw):
            pool = COMMENTARY_LINES.get(cat)
            if pool or line is not None:
                kw.setdefault("trk", trk)
                kw.setdefault("comm", COMMENTATOR_NAME)
                kw.setdefault("pundit", PUNDIT_NAME)
                kw.setdefault("comm_full", COMMENTATOR_FULL)
                kw.setdefault("pundit_full", PUNDIT_FULL)
                # `line` lets the caller supply the exact text (e.g. a crosstalk
                # question drawn from a PAIRED topic) while still flowing through
                # the normal formatting / intensity / queueing path.
                text = line if line is not None else self._pick(pool, ("COMM", cat))
                cands.append((prio, _safe_format(text, kw),
                              cat, CAT_INTENSITY.get(cat, 1), persona))

        total = s.number_of_laps
        # CONFIRMED leader (debounced) so a flicker at the front never triggers a
        # false "new race leader" call
        leader = next((d for d in order if cp(d) == 1), placemap.get(1))
        is_quali = (s.session_type == 1)

        # ---- RACE PHASE: a real broadcast follows the STORY of the race, not the
        # whole field equally. Opening laps -> lock onto the leaders/front; the
        # mid race -> open it up to battles, track facts, the wider field; the
        # closing laps -> swing back to the fight for the win. `_focus(place)`
        # gates the chatter so we don't narrate a P12 scrap while the front is
        # the story (and so big stuff lands on time, not buried under midfield).
        ll = leader.completed_laps if leader is not None else 0
        # RaceRoom's white flag means SLOW CAR ON TRACK (European rules), NOT
        # final lap — a lap-3 tow-in was making the booth scream "LAST LAP".
        # So: in LAP races, "final lap" comes from counting laps only; in TIMED
        # races the white flag is only trusted once the clock has expired
        # (that's the one case where it does accompany the last lap).
        wf = (s.flags.white == 1)
        timed = not (total and total > 0)       # RaceRoom online sprints are timed
        self._timed = timed
        if not timed:                           # LAP race: phase by laps to go
            togo = total - ll
            white = (ll >= 1 and togo == 1)     # leader has started the last lap
            if ll < 1:
                phase = "opening"
            elif white or togo <= 1:
                phase = "closing"
            elif togo <= 4:
                phase = "late"
            else:
                phase = "mid"
        else:                                   # TIMED race: phase by the clock
            togo = 999
            dur, rem = s.session_time_duration, s.session_time_remaining
            white = (wf and not (rem and rem > 0))   # white only after time-up
            if ll < 1:
                phase = "opening"
            elif white:
                phase = "closing"               # on the final lap after time-up
            elif dur and dur > 0 and rem > 0 and rem / dur < 0.18:
                phase = "late"                  # final ~fifth of the clock
            else:
                phase = "mid"
        flimit = {"opening": 5, "late": 8, "closing": 5, "mid": 99}[phase]

        def _focus(place):
            """Is this place worth commentating in the current phase?"""
            return place <= flimit

        def _INC(cat, persona="PUNDIT", intensity=2, cutoff=False, **kw):
            """Incident line (yellow / penalty) — bypasses cands + COMMENTARY_CD,
            always force-queued. cutoff=True interrupts current audio, BUT never
            while an off-track report is mid-flight (it queues behind instead) so
            incidents don't sever one another — e.g. a yellow caused by a spin
            now FOLLOWS the spin call rather than cutting it off."""
            pool = COMMENTARY_LINES.get(cat)
            if not pool:
                return
            kw.setdefault("trk", trk)
            kw.setdefault("comm", COMMENTATOR_NAME)
            kw.setdefault("pundit", PUNDIT_NAME)
            kw.setdefault("comm_full", COMMENTATOR_FULL)
            kw.setdefault("pundit_full", PUNDIT_FULL)
            text = _safe_format(self._pick(pool, ("COMM", cat)), kw)
            spoken = self._spoken(text)
            seed = "PUNDIT" if persona == "PUNDIT" else "COMM"
            if self.tts:
                if cutoff and now >= getattr(self, "_incident_until", 0.0):
                    self.tts.interrupt()   # cut current dialogue, drain queue
                    self._incident_until = now + 5.0
                self.tts.speak(spoken, persona, seed=seed, intensity=intensity,
                               on_play=self._show_caption, force=True)
        # race START — works in REPLAYS too: don't rely on start_lights/phase
        # (often unset in replay), just catch the leader still on the opening lap
        # grid build-up (once, while still on the standing grid) so the booth is
        # AWARE of the start instead of dead silent, then the punchy lights-out
        # call lands at green
        if (is_race and not self._racing and leader is not None
                and not self._comm_flags.get("pregrid")):
            self._comm_flags["pregrid"] = True
            self._intro_emit_t = now            # engineer gate: scene being set
            L("pregrid", 2, drv=self._dname(leader))
        # START call fires the instant the race goes green (the _racing edge),
        # naming the leader — "Lights out and {leader} leads them away!" Fired
        # DIRECTLY with force (like the finish wrap) so this signature moment can
        # NEVER be dropped or buried behind the pregrid welcome — it interrupts
        # whatever's playing and lands right on the lights going out.
        if (is_race and self._racing and not self._comm_flags.get("start")
                and leader is not None):
            self._comm_flags["start"] = True
            self._intro_emit_t = now            # latest opener -> hold engineer
            self._green_at = now                # start of the grid-sort window
            if self.tts:
                # INSTANT pre-rendered lights-out sting fires on the green edge
                # with zero render latency; the named "…and {leader} leads them
                # away!" line is queued straight after WITHOUT its own interrupt
                # (the sting already purged), so it lands as the bridge finishes.
                # If no sting is ready yet, fall back to the old interrupt+render.
                stung = self.tts.sting("lightsout", "COMMENTATOR",
                                       on_play=self._show_caption)
                if not stung:
                    self.tts.interrupt()        # cut the welcome, land on the moment
                # the sting already SAID "lights out and away we go" — the named
                # follow-up must not repeat it, so filter the pool to the lines
                # that don't open with a lights/getaway call
                pool = COMMENTARY_LINES["start"]
                if stung:
                    _lo = re.compile(r"lights|five red|away we go", re.I)
                    pool = [t for t in pool if not _lo.search(t)] or pool
                stxt = _safe_format(self._pick(pool, ("COMM", "start")),
                                    {"drv": self._dname(leader), "trk": trk})
                self.tts.speak(self._spoken(stxt), "COMMENTATOR", seed="COMM",
                               intensity=2, on_play=self._show_caption, force=True)
                self._incident_until = now + 3.0  # protect it from being cut
            else:
                self._show_caption(_safe_format(
                    self._pick(COMMENTARY_LINES["start"], ("COMM", "start")),
                    {"drv": self._dname(leader), "trk": trk}), "COMMENTATOR")
        # QUALI/PRACTICE session intro (once) — so the booth names the session
        # correctly instead of calling everything "the race"
        if not is_race and not self._comm_flags.get("qstart"):
            self._comm_flags["qstart"] = True
            self._intro_emit_t = now            # engineer gate: opener airing
            L("quali_start" if is_quali else "practice_start", 1)
        # race FINISH — TWO PHASES so the result is accurate even in a drag race
        # to the line. PHASE A: the instant the LEADER crosses, call the win (the
        # winner is final the moment they take the flag). PHASE B: once the PLAYER
        # has also crossed (finish_status == 1) or a short grace window, fire the
        # rest of the wrap with FINAL positions — otherwise a last-corner pass for
        # the player's place gets mis-reported (the bug: "you finished P3" when
        # you were actually pipped to the line for P4).
        if (is_race and leader is not None
                and not self._comm_flags.get("winannounced")):
            done_race = (s.session_phase == 6 or s.flags.checkered == 1
                         or order[0].finish_status == 1
                         or leader.finish_status == 1
                         or (total and total > 0 and leader.completed_laps >= total))
            if done_race:
                self._comm_flags["winannounced"] = True
                self._finish_at = now
                # NARRATIVE win call: tie the flag to the winner's race story
                # (comeback / charge from deep / flag-to-flag) when there is one
                # — 'It is redemption day!' beats 'X wins' every single time.
                arc, akw = self._narrative_arc(leader.driver_info.slot_id,
                                               place=1)
                wcat = {"comeback": "win_comeback", "charge": "win_charge",
                        "wire": "win_wire"}.get(arc, "win")
                wtxt = _safe_format(
                    self._pick(COMMENTARY_LINES[wcat], ("FIN", wcat)),
                    {"drv": self._dname(leader), "trk": trk,
                     "comm": COMMENTATOR_NAME, "pundit": PUNDIT_NAME,
                     "comm_full": COMMENTATOR_FULL, "pundit_full": PUNDIT_FULL,
                     **akw})
                if self.tts:
                    # INSTANT pre-rendered VICTORY sting on the flag (zero render
                    # latency on the signature moment); the named win call is
                    # queued straight after WITHOUT its own interrupt (the sting
                    # already purged), so it lands as the bridge finishes.
                    stung = self.tts.sting("victory", "COMMENTATOR",
                                           on_play=self._show_caption)
                    if not stung:
                        self.tts.interrupt()
                    self.tts.speak(self._spoken(wtxt), "COMMENTATOR", seed="COMM",
                                   intensity=2, on_play=self._show_caption,
                                   force=True)
                    self._incident_until = now + 3.0   # protect it from being cut
                else:
                    self._show_caption(wtxt, "COMMENTATOR")
        if (is_race and self._comm_flags.get("winannounced")
                and not self._comm_flags.get("finish")):
            pfin = next((d for d in order if d.driver_info.slot_id
                         == s.vehicle_info.slot_id), None)
            if ((pfin is not None and pfin.finish_status == 1)
                    or now - getattr(self, "_finish_at", now) > 8.0):
                self._comm_flags["finish"] = True
                # FINAL order now (cars have crossed) -> accurate podium/player pos
                fn1 = self._dname(order[0]) if order else n1
                fn2 = self._dname(order[1]) if len(order) > 1 else ""
                fn3 = self._dname(order[2]) if len(order) > 2 else ""
                chasers = [self._dname(d) for d in order[1:5]]
                if pfin is not None:
                    self._career_record(trk, next(
                        (i + 1 for i, d in enumerate(order)
                         if d.driver_info.slot_id == s.vehicle_info.slot_id),
                        0), len(order))
                self._finish_sequence(fn1, fn2, fn3, trk, chasers, include_win=False)
                self._signed_off = True
                self._comm_prev = cur
                return

        if leader is not None:
            lslot = leader.driver_info.slot_id
            if is_race and self._comm_lead is not None and lslot != self._comm_lead:
                # narrative lead call: name the arc when the new leader climbed
                # from deep or fought back from a disaster
                arc, akw = self._narrative_arc(lslot, place=1)
                lcat = {"comeback": "leadchange_comeback",
                        "charge": "leadchange_charge"}.get(arc, "leadchange")
                L(lcat, 0, drv=self._dname(leader), **akw)
                self._story.setdefault(lslot, [])
                if "led" not in self._story[lslot]:
                    self._story[lslot].append("led")
            # QUALI: provisional pole is the fastest TIME set — NOT the
            # timing-tower position (which is just registration order until laps
            # go in). Only announce a change of pole among drivers who've banked a
            # lap; the very first time set is announced by the fastlap event.
            elif not is_race and q_set_t:
                pole_slot = q_set_t[0].driver_info.slot_id
                prev_pole = getattr(self, "_comm_qpole", None)
                if prev_pole is not None and pole_slot != prev_pole:
                    L("quali_pole", 1, drv=self._dname(q_set_t[0]))
                self._comm_qpole = pole_slot
            self._comm_lead = lslot
            # lap milestones (half distance, closing laps) — keep the story going
            if is_race and total and total > 0:
                done = leader.completed_laps
                togo = max(0, total - done)
                lap = min(total, done + 1)
                for key, cond in (("half", done >= total * 0.5),
                                  ("final5", 0 < togo <= 5),
                                  ("final3", 0 < togo <= 3)):
                    if cond and not self._comm_flags.get(key):
                        self._comm_flags[key] = True
                        L("lap_milestone", 4, lap=lap, total=total, togo=togo)
                        break
            # TIMED race: announce the CLOCK winding down — once each as it drops
            # below 10 / 5 / 2 / 1 minute(s) to go, so the booth is aware the race
            # is nearing its end just like a lap race.
            elif is_race and self._racing and s.session_time_remaining > 0:
                secs = s.session_time_remaining
                mk = (1 if secs <= 60 else 2 if secs <= 120 else 5 if secs <= 300
                      else 10 if secs <= 600 else 0)
                if mk and self._comm_flags.get("mins", 99) > mk:
                    self._comm_flags["mins"] = mk
                    L("time_remaining", 3,
                      mins=("1 minute" if mk == 1 else f"{mk} minutes"))
            if (is_race and s.number_of_laps > 0 and not self._comm_flags.get("lastlap")
                    and leader.completed_laps >= s.number_of_laps - 1):
                self._comm_flags["lastlap"] = True
                L("lastlap", 1, drv=self._dname(leader))

        ft = self.fastest.get("at", 0.0)
        if self.fastest.get("time") and ft > self._comm_fastest_at:
            self._comm_fastest_at = ft
            if self.fastest.get("name"):
                # in quali/practice the fastest lap is the session benchmark, not
                # "the fastest lap of the race" — use the right wording
                L("fastlap" if is_race else "quali_fastlap", 1,
                  drv=self.fastest["name"], gap=R.fmt_time(self.fastest["time"]))

        # periodic CONVERSATION: every ~35s the lead asks the pundit about a
        # specific driver and the pundit answers (the exchange is force-queued in
        # the emit so it always completes). This is the back-and-forth the user
        # wants, so it fires RELIABLY on a fixed cadence — when a driver's had an
        # eventful race we ask for the full story recap, otherwise a general
        # 'how's their race going'. Gated only on a little queue headroom.
        if (is_race and self._racing and order
                and now - self._crosstalk_t > 35.0
                # NOT on the final lap. The win is the only story then, and a
                # "talk us through P6's afternoon" recap while the flag is
                # about to fall is the most jarring thing the booth can do.
                and phase != "closing"
                # in the closing laps, only when nothing close is happening —
                # a live fight outranks conversation
                and not (phase == "late" and self._tight_battle(order))
                and (self.tts is None or self.tts._pending() < 2)):
            self._crosstalk_t = now
            # A "how has his race gone" recap on lap one is nonsense — nothing
            # has happened yet. Stories need a race behind them: four laps, or
            # a quarter of the distance, whichever comes first.
            _story_ok = (ll >= 4 or (total and total > 0 and ll >= total * 0.25))
            story_d = self._story_pick(order) if _story_ok else None
            if story_d is None and _story_ok and random.random() < 0.3:
                # quiet race, nobody's swung much — a "steady afternoon" recap
                # of a front-runner still beats never mentioning anyone's race.
                told = getattr(self, "_story_told", set())
                cand = [d for d in order[:8]
                        if d.driver_info.slot_id not in told
                        and d.driver_info.slot_id in self._race_story
                        and self.grid_place.get(d.driver_info.slot_id) is not None]
                if cand:
                    story_d = random.choice(cand)
            if story_d is not None and random.random() < 0.6:
                # data-driven recap of THIS driver's race so far (grid -> now)
                self._storyq_d = story_d
                self._crosstalk_drv = self._dname(story_d)
                L("driverstory_q", 1, persona="COMMENTATOR",
                  drv=self._crosstalk_drv)
            else:
                d = random.choice(order[:min(6, len(order))])
                topic = random.choice([t for t in CROSSTALK
                                       if self._pits_live(order)
                                       or t not in self._PIT_TOPICS])
                self._crosstalk_topic = topic
                self._crosstalk_drv = self._dname(d)
                self._crosstalk_pos = d.place
                L("crosstalk_q", 1, persona="COMMENTATOR",
                  line=self._pick(CROSSTALK[topic]["q"], ("XQ", topic)),
                  drv=self._crosstalk_drv, pos=d.place)

        # GRID-SORT window: for the first ~8s after lights-out the field is still
        # sorting from the standing grid, so big position swaps are NOT incidents.
        # Suppress incident/yellow calls so they can't preempt the lights-out call
        # with a bogus "someone's gone off".
        grid_sort = (is_race and now - getattr(self, "_green_at", -1e9) < 8.0)

        # yellow flag on track (rising edge) — incident, always immediate
        yellow = (s.flags.yellow == 1
                  or any(s.flags.sector_yellow[i] == 1 for i in range(3)))
        if yellow and not self._comm_flags.get("yellow") and not grid_sort:
            self._comm_flags["yellow"] = True
            # Only act if NO incident is already being reported (a player off that
            # caused this yellow already named the culprit). If it IS fresh: instant
            # sting, then NAME whoever most recently went off (past tense, so a
            # slightly late report still fits) — that's the missing follow-up. If
            # we don't know who, fall back to the generic yellow call.
            if now >= getattr(self, "_incident_until", 0.0):
                lo = self._last_off
                name = lo[0] if (lo and now - lo[1] < 8.0) else None
                stung = (self.tts.sting("alert", "PUNDIT",
                                        on_play=self._show_caption)
                         if self.tts else False)
                if name:
                    _INC("offtrack_late", persona="PUNDIT", intensity=2,
                         cutoff=not stung, drv=name)
                    _INC("offtrack_ack", persona="COMMENTATOR", intensity=0)
                else:
                    _INC("yellow", persona="PUNDIT", intensity=2, cutoff=not stung)
                self._incident_until = now + 6.0
        elif not yellow:
            self._comm_flags["yellow"] = False

        # BIG SHUFFLE — many positions changing within ~2s (a pile-up / multi-car
        # melee, common online). Compare to a snapshot taken ~2s ago; if 5+ cars
        # have changed place, the pundit flags the chaos. Skipped in the opening
        # phase (lap one always shuffles) and rate-limited.
        if not hasattr(self, "_shuf_snap") or now - self._shuf_snap_t > 2.0:
            prev_snap = getattr(self, "_shuf_snap", None)
            if (prev_snap and is_race and self._racing and phase != "opening"
                    and now - getattr(self, "_shuffle_cd", 0.0) > 25.0):
                changed = sum(1 for sl, p in cur.items()
                              if prev_snap.get(sl) not in (None, p))
                if changed >= 5:
                    self._shuffle_cd = now
                    L("shuffle", 2, persona="PUNDIT")
            self._shuf_snap = dict(cur)
            self._shuf_snap_t = now

        # PLAYER off-track — report only a GENUINE off, never a harmless run-wide.
        # A lap going invalid (current_lap_valid 1->0) only means you crossed a
        # track limit — which INCLUDES clipping a painted kerb/runoff at full
        # speed (the photo case): not news. So the invalidation is just a
        # CANDIDATE; we confirm it by what actually matters — did you lose real
        # speed? Grass, gravel and spins scrub a big chunk of pace; a clean clip
        # over the line does not. Only when the speed COLLAPSES during the off do
        # we call it — exactly the worth-reporting cases (and the ones that tend to
        # bring out a yellow). Gated to GREEN-flag, on-circuit, moving.
        vslot = s.vehicle_info.slot_id
        pdrv = next((d for d in order if d.driver_info.slot_id == vslot), None)
        in_pits = (pdrv is not None and pdrv.in_pitlane == 1) or s.in_pitlane == 1
        plv = s.current_lap_valid
        spd = abs(s.car_speed)
        racing_clean = (is_race and self._racing and not in_pits and spd > 3.0
                        and not grid_sort)

        if racing_clean:
            lap_edge = (getattr(self, "_player_lap_valid", 1) == 1 and plv == 0)
            if lap_edge and self._off_watch is None:
                # [deadline, ref_speed, min_speed] — min_speed tracks the dip so we
                # can grade the off at the end of the window (collapse / run-wide /
                # clean clip).
                self._off_watch = [now + 1.8, spd, spd]
                if pdrv is not None:                       # candidate culprit for a
                    self._last_off = (self._dname(pdrv), now)  # yellow to name
        else:
            self._off_watch = None
        if self._off_watch is not None and pdrv is not None:
            deadline, ref, mins = self._off_watch
            if spd < mins:
                self._off_watch[2] = mins = spd            # track the lowest dip
            if spd < ref * 0.58 and now - self._offtrack_cd.get(vslot, -1e9) > 5.0:
                # confirmed: lost 40%+ of pace mid-excursion -> a real off (spin)
                self._offtrack_cd[vslot] = now
                self._off_watch = None
                self._last_off = (self._dname(pdrv), now)
                self._report_offtrack(self._dname(pdrv), now, primary=True)
                self._story.setdefault(vslot, [])
                if "spun" not in self._story[vslot]:
                    self._story[vslot].append("spun")
            elif now >= deadline:
                self._off_watch = None
                # window elapsed with no collapse. A MODERATE loss of pace means
                # you ran wide / had a moment off the track -> a lighter booth note
                # (longer cooldown). A clean flat-out kerb clip (no real loss) stays
                # silent so the booth never spams painted-kerb touches.
                if (mins < ref * 0.85
                        and now - self._offtrack_cd.get(vslot, -1e9) > 12.0):
                    self._offtrack_cd[vslot] = now
                    self._report_wide(self._dname(pdrv), now)
        # keep the lap-valid tracker current (even while gated off) so a 1->0 that
        # happened on the grid / in the pits can't 'save up' and fire later
        self._player_lap_valid = plv

        # leader stretching clear out front (milestones at 3/6/10s)
        second = placemap.get(2)
        if is_race and leader is not None and second is not None:
            g2 = self.interval.get(second.driver_info.slot_id)
            if g2:
                mile = 10 if g2 >= 10 else 6 if g2 >= 6 else 3 if g2 >= 3 else 0
                if mile and self._comm_flags.get("pull") != mile:
                    self._comm_flags["pull"] = mile
                    L("pulling_away", 3, drv=self._dname(leader),
                      gap=f"{g2:.1f} seconds")

        prev_int = getattr(self, "_comm_prev_int", {})
        for d in order:
            sl = d.driver_info.slot_id
            if is_race and d.in_pitlane == 1:
                self._pit_t[sl] = now            # mark recently-in-pits (for the
                if not self._comm_pit.get(sl):   # off-track false-positive guard)
                    self._comm_pit[sl] = True
                    L("pit", 3, drv=self._dname(d))
            elif d.in_pitlane != 1:
                self._comm_pit[sl] = False
            # penalty handed out (rising edge per driver)
            pen = getattr(d, "penaltyType", -1)
            if is_race and pen >= 0 and self._comm_pen.get(sl) != pen:
                self._comm_pen[sl] = pen
                _INC("penalty", persona="PUNDIT", intensity=2, drv=self._dname(d))
            elif pen < 0:
                self._comm_pen[sl] = -1
            # a strong recovery drive (climbing well clear of the grid slot)
            gain = self.grid_place.get(sl, d.place) - d.place
            if is_race and gain >= 4:
                mk = gain // 3
                if self._comm_flags.get(f"rec{sl}") != mk:
                    self._comm_flags[f"rec{sl}"] = mk
                    L("recovery", 3, drv=self._dname(d), pos=d.place)
                    self._story.setdefault(sl, [])
                    if "recovered" not in self._story[sl]:
                        self._story[sl].append("recovered")
            pv = self._comm_prev.get(sl)
            cpd = cp(d)                                 # this driver's CONFIRMED place
            if pv is None:
                continue
            if (is_race and self._racing and cpd >= pv + 2   # off-track / big loss
                    and not grid_sort                        # not the grid sorting out
                    and d.in_pitlane != 1                    # not a car in the pits
                    and now - self._pit_t.get(sl, -1e9) > 12.0   # nor a pit rejoin
                    # 6s was shorter than the 7s incident window, so ONE spin
                    # could be re-detected and reported as a second incident
                    # the moment the window lapsed. A car losing places after
                    # an off keeps tripping this detector while it recovers, so
                    # the gap has to outlast the recovery, not just the call.
                    and now - self._offtrack_cd.get(sl, -1e9) > 20.0):
                # Routed through _report_offtrack so it can't cut off another
                # incident mid-call and multi-car pile-ups are coalesced. _focus()
                # intentionally NOT applied — an incident matters regardless of
                # position. Gated on the race being GREEN and the car not pitting,
                # so a standing-start shuffle or a pit stop isn't called an "off".
                # The per-slot cooldown also stops a double-call when the player's
                # instant lap-invalid path already fired above.
                self._offtrack_cd[sl] = now
                self._last_off = (self._dname(d), now)    # culprit for a yellow
                self._report_offtrack(self._dname(d), now)
                self._story.setdefault(sl, [])
                if "spun" not in self._story[sl]:
                    self._story[sl].append("spun")
            # MULTIPLE PLACES IN ONE MOVE — a driver who takes two or more cars
            # at once is one of the biggest things that can happen, and it used
            # to hit NO branch at all: the loss branch wants cpd >= pv+2 and the
            # gain branch wants exactly cpd == pv-1, so a double pass fell
            # straight through in silence.
            #
            # The catch is that most big jumps are NOT heroics — they're the
            # cars ahead peeling into the pits. So every car we supposedly
            # passed must still be on track and not fresh out of a stop; if any
            # of them is pit-related this is a cycle, not a move, and we say
            # nothing. Front-of-field moves ignore the phase focus limit.
            elif (is_race and self._racing and cpd <= pv - 2
                  and not grid_sort and d.in_pitlane != 1
                  and now - self._pit_t.get(sl, -1e9) > 12.0
                  and (_focus(cpd) or cpd <= 3)):
                passed = [placemap.get(p) for p in range(cpd + 1, pv + 1)]
                real = [v for v in passed if v is not None]
                pitting = any(v.in_pitlane == 1
                              or now - self._pit_t.get(v.driver_info.slot_id,
                                                       -1e9) < 12.0
                              for v in real)
                if real and not pitting:
                    n = pv - cpd
                    # top-3 moves outrank everything bar a retake
                    L("overtake_multi", 1 if cpd <= 3 else 2,
                      drv=self._dname(d), n=n, pos=cpd,
                      oth=self._dname(real[0]))
                    self._story.setdefault(sl, [])
                    if "charging" not in self._story[sl]:
                        self._story[sl].append("charging")
                self._battle.pop(sl, None)
            # a pass for P1/P2/P3 is the story of the race — it must not be
            # gated out by the phase focus limit, and it outranks midfield
            # chatter in the candidate sort below.
            elif is_race and cpd == pv - 1 and (_focus(cpd) or cpd <= 3):
                victim = placemap.get(cpd + 1)
                if (victim is not None
                        and self._comm_prev.get(victim.driver_info.slot_id) == cpd):
                    # how close were they? the victim is now directly behind, so
                    # its interval IS the gap to our overtaker. Only call it a
                    # dramatic "dive up the inside" pass when they're genuinely
                    # wheel-to-wheel (<0.45s); a wider gap gets a neutral line,
                    # and a big gap (>1.6s) is almost always a pit cycle or an
                    # off, not real on-track combat, so don't commentate a duel.
                    vgap = self.interval.get(victim.driver_info.slot_id)
                    b = self._battle.get(sl)
                    longfight = (b and b[0] == victim.driver_info.slot_id
                                 and now - b[1] > 8.0)
                    if longfight:
                        cat = "overtake_long"
                    elif vgap is not None and vgap < 0.45:
                        cat = "overtake"            # close, on-track pass
                    elif vgap is None or vgap < 1.6:
                        cat = "pass_clean"          # a pass, but not a knife-fight
                    else:
                        cat = None                  # likely pit/off, stay quiet
                    # a routine (non-wheel-to-wheel) pass deep in the field is the
                    # "X passes Y for P12" spam the tester flagged — mostly skip it
                    if cat == "pass_clean" and cpd > 8 and random.random() > 0.35:
                        cat = None
                    # RE-PASS / REVERSAL: if this exact pair just swapped this
                    # position the other way moments ago, it's a fight-back. Say so
                    # AND interrupt the now-stale "X takes P{pos}" that's likely
                    # still rendering/playing, so the booth isn't a swap behind the
                    # live action (the P3-then-not confusion).
                    vsl = victim.driver_info.slot_id
                    lp = self._last_pass
                    if (cat and lp and lp[0] == vsl and lp[1] == sl
                            and lp[2] == cpd and now - lp[3] < 6.0):
                        cat = "retake"
                        if self.tts:
                            self.tts.interrupt()
                    if cat:
                        akw = {}
                        if cat in ("overtake", "overtake_long", "pass_clean"):
                            # narrative pass call: a driver on a charge or a
                            # comeback gets the story woven into the call —
                            # but only ~half the time, so a recovery drive
                            # isn't narrated identically pass after pass
                            arc, akw2 = self._narrative_arc(sl, place=cpd)
                            ncat = {"comeback": "overtake_comeback",
                                    "charge": "overtake_charge"}.get(arc)
                            if ncat and random.random() < 0.5:
                                cat, akw = ncat, akw2
                        # PRIORITY BY POSITION: a pass for the lead or the
                        # podium is the story; a P9 swap is texture. Without
                        # this they were all prio 2 and the sort picked
                        # whichever happened to land first in the tick.
                        L(cat, 1 if (cat == "retake" or cpd <= 3) else 2,
                          drv=self._dname(d), oth=self._dname(victim), pos=cpd,
                          **akw)
                        self._last_pass = (sl, vsl, cpd, now)
                    self._battle.pop(sl, None)

        if is_race and self._racing:
            for d in order[:8]:                         # close fight near the front
                sl = d.driver_info.slot_id
                itv = self.interval.get(sl)
                if itv is None or d.place <= 1:
                    continue
                ahead = placemap.get(d.place - 1)
                if ahead is None or not _focus(ahead.place):
                    continue
                # A BATTLE IS A STATE, NOT A MOMENT. It was briefly promoted to
                # prio 2 for podium fights, which was wrong twice over: prio<=2
                # is "urgent", so it skipped COMMENTARY_CD and re-rolled at
                # 20Hz, and two cars stay within 0.5s for many seconds at a
                # time. The booth ended up narrating the same fight over and
                # over ("millimetres between them" three times in one race)
                # AND holding the audio queue at pending>=2, which is the very
                # gate that blocks crosstalk, lore and race stories — so the
                # conversation between the two commentators dried up entirely.
                #
                # Battles stay prio 3: real colour, subject to the normal
                # cooldown. A podium fight gets a better chance of being the
                # colour that airs, not permission to air constantly.
                podium_fight = (ahead.place <= 3 and itv < 0.5)
                # ...and don't re-narrate the SAME pair for a while. Without
                # this the closest fight monopolises the broadcast simply by
                # staying close.
                pair = tuple(sorted((sl, ahead.driver_info.slot_id)))
                if now - self._battle_said.get(pair, -1e9) < 25.0:
                    continue
                if 0.05 < itv < 0.6 and random.random() < (0.22 if podium_fight
                                                           else 0.10):
                    self._battle_said[pair] = now
                    L("battle", 3, drv=self._dname(d),
                      oth=self._dname(ahead), pos=ahead.place)   # contested place
                    break
                pvi = prev_int.get(sl)                  # closing the gap down quickly
                if (pvi is not None and 0.6 < itv < 2.0 and pvi - itv > 0.2
                        and random.random() < 0.18):
                    L("closing", 3, drv=self._dname(d),
                      oth=self._dname(ahead), pos=ahead.place)
                    break
            # midfield scraps ONLY in the mid race (the opening + closing belong
            # to the leaders) and at a lower rate so it's not "X passes Y for P12"
            # every few seconds — the tester's main complaint
            if phase == "mid":
                for d in order[8:18]:
                    sl = d.driver_info.slot_id
                    itv = self.interval.get(sl)
                    if (itv is not None and 0.05 < itv < 0.5 and d.place > 1
                            and random.random() < 0.035):
                        ahead = placemap.get(d.place - 1)
                        if ahead is not None:
                            L("battle_mid", 4, drv=self._dname(d),
                              oth=self._dname(ahead), pos=ahead.place)
                            break
        self._comm_prev_int = {d.driver_info.slot_id:
                               self.interval.get(d.driver_info.slot_id) for d in order}

        # battle memory: track how long each car has been hounding the one ahead.
        # Tuple is (target_slot, start_time, start_lap) — start_lap lets the
        # sustained-battle callout report the fight's length in laps.
        for d in order:
            sl = d.driver_info.slot_id
            itv = self.interval.get(sl)
            ahead = placemap.get(d.place - 1)
            if ahead is not None and itv is not None and itv < 0.9 and d.place > 1:
                tslot = ahead.driver_info.slot_id
                b = self._battle.get(sl)
                if not b or b[0] != tslot:
                    self._battle[sl] = (tslot, now, d.completed_laps)  # new fight
            elif itv is None or itv > 1.4:
                self._battle.pop(sl, None)                 # gap opened, fight over

        # SUSTAINED BATTLE — a fight that's gone the distance WITHOUT resolving
        # into a pass yet ("nose-to-tail for three laps now"). The staple of real
        # colour commentary. Front-focused, gated on `not cands` so live events
        # always win, and rate-limited globally + per pair so it never nags. Picks
        # the longest-running, most forward unresolved fight on track.
        if (is_race and self._racing and not cands
                and now - getattr(self, "_battle_cd", 0.0) > 18.0):
            best = None
            for d in order:
                sl = d.driver_info.slot_id
                b = self._battle.get(sl)
                if not b:
                    continue
                tslot, t0, lap0 = b
                ahead = placemap.get(d.place - 1)
                if (ahead is None
                        or ahead.driver_info.slot_id != tslot
                        or not _focus(ahead.place)):
                    continue
                itv = self.interval.get(sl)
                if itv is None or itv > 1.0 or now - t0 < 14.0:
                    continue
                if now - self._battle_called.get((sl, tslot), -1e9) < 30.0:
                    continue
                score = (now - t0) - ahead.place      # longer + more forward wins
                if best is None or score > best[0]:
                    best = (score, d, ahead, sl, tslot, now - t0, lap0)
            if best is not None:
                _, d, ahead, sl, tslot, dur, lap0 = best
                laps = max(0, d.completed_laps - lap0)
                if laps >= 2:
                    dur_txt = self._spell_laps(laps)
                elif dur >= 45.0:
                    dur_txt = "the best part of a minute"
                else:
                    dur_txt = "several corners now"
                self._battle_cd = now
                self._battle_called[(sl, tslot)] = now
                L("battle_sustained", 3, drv=self._dname(d),
                  oth=self._dname(ahead), pos=ahead.place, dur=dur_txt)

        # OPENING, LATE & CLOSING keep FOCUS ON THE FRONT — the start/early
        # leaders and the fight for the win down the stretch. Mid race gets the
        # wider-field colour below.
        if (phase in ("opening", "late", "closing") and is_race and self._racing
                and leader is not None and not cands
                and now - self._comm_close_t > 15.0):
            self._comm_close_t = now
            sec = placemap.get(2)
            g2 = self.interval.get(sec.driver_info.slot_id) if sec is not None else None
            # FINAL LAP: the win is the only story. Either it's a fight, or the
            # leader is cruising it home — say which, and say nothing else.
            if phase == "closing":
                if sec is not None and g2 is not None and g2 < 2.0:
                    L("battle", 2, drv=self._dname(sec),
                      oth=self._dname(leader), pos=1)
                elif not self._comm_flags.get("runaway"):
                    # A RUNAWAY WIN IS ONE LINE, NOT A THEME. Said once, "he's
                    # got this in hand" is the right call; said every fifteen
                    # seconds it becomes the entire final phase of the
                    # broadcast, which is what a real log showed — six
                    # different ways of saying "the leader is clear", back to
                    # back, while the actual racing behind went uncovered.
                    self._comm_flags["runaway"] = True
                    L("pulling_away", 2, drv=self._dname(leader),
                      oth=self._dname(sec) if sec is not None else n2, pos=1)
                else:
                    # ...then follow the best fight still live behind him. If
                    # the win is settled, the race is P2 and back.
                    fight = None
                    for d in order[1:10]:
                        g = self.interval.get(d.driver_info.slot_id)
                        if g is not None and 0.05 < g < 2.0:
                            fight = d
                            break
                    if fight is not None:
                        aho = placemap.get(fight.place - 1)
                        if aho is not None:
                            L("battle", 2, drv=self._dname(fight),
                              oth=self._dname(aho), pos=aho.place)
            # LATE: follow the closest fight that actually matters — the
            # HIGHEST-PLACED close battle, not automatically P1/P2. If the
            # leaders are strung out and P4/P5 are scrapping, that scrap is
            # the race, and the booth should be on it.
            elif phase == "late":
                best = None
                for d in order[:10]:
                    if d.place <= 1:
                        continue
                    g = self.interval.get(d.driver_info.slot_id)
                    if g is not None and 0.05 < g < 1.5:
                        best = d          # first match = highest placed
                        break
                if best is not None:
                    ahead = placemap.get(best.place - 1)
                    if ahead is not None:
                        L("battle", 2, drv=self._dname(best),
                          oth=self._dname(ahead), pos=ahead.place)
                elif n3:
                    L("standings", 3, p1=n1, p2=n2, p3=n3)
            elif sec is not None and g2 is not None and 0.05 < g2 < 1.5:
                L("battle", 2, drv=self._dname(sec), oth=self._dname(leader), pos=1)
            elif n3:
                L("standings", 3, p1=n1, p2=n2, p3=n3)

        # OBJECTIVE AWARENESS — the booth reacts to the player's target being
        # set, hit or missed. The engineer's radio is a private conversation;
        # having the commentators pick up on it is what makes the objective
        # feel like part of the broadcast rather than a HUD widget.
        # PRIO 2 (urgent), NOT 3 — this is the fix for "the commentators still
        # don't commentate on objectives". At prio 3 it was added as a single
        # candidate and _obj_booth cleared the same tick, so if it lost that
        # one arbitration (and an objective resolves at exactly the moment of
        # an overtake/lead-change call, so it almost always did) the line was
        # gone for good. As urgent it rides the arbitration HOLD BUFFER, which
        # keeps retrying it until it airs or goes stale — a whole race went by
        # with zero booth objective lines before this.
        _ob = getattr(self, "_obj_booth", None)
        if is_race and _ob and now - _ob[3] < 12.0:
            _ev, _kind, _tgt, _t = _ob
            self._obj_booth = None
            # noticing EVERY target would be as tiresome as noticing none, but
            # a RESOLVED target is a payoff and is always worth calling
            if random.random() < (0.6 if _ev == "set" else 1.0):
                pdrv = next((d for d in order if d.driver_info.slot_id
                             == s.vehicle_info.slot_id), None)
                if pdrv is not None and _ev == "set":
                    # say WHAT was asked for, in terms the broadcast could
                    # legitimately infer from watching — "asked to put the
                    # pressure on", "told to defend" — not numbers off a
                    # private radio call
                    _brief = _safe_format(OBJ_BRIEF.get(_kind,
                                                        OBJ_BRIEF_DEFAULT),
                                          {"tgt": _tgt or "the car ahead"})
                    L("obj_booth_brief", 2, persona="PUNDIT",
                      drv=self._dname(pdrv), brief=_brief)
                elif pdrv is not None:
                    L("obj_booth_met" if _ev == "met" else "obj_booth_miss",
                      2, persona="PUNDIT", drv=self._dname(pdrv))

        # LATE phase — one-time urgency call (LAP races only; the {togo} wording
        # needs a lap count). Timed races get their late nudge via the time-aware
        # insight layer instead.
        if (is_race and phase == "late" and self._racing and not timed
                and not self._comm_flags.get("late_entry") and leader is not None):
            self._comm_flags["late_entry"] = True
            L("late", 2, persona="COMMENTATOR", togo=togo)

        # FINAL LAP — fire on the WHITE FLAG (works for BOTH lap and timed races;
        # in a timed race the last lap only begins once the clock hits zero).
        if (is_race and self._racing and leader is not None
                and (white or (total and total > 0 and togo <= 0))
                and not self._comm_flags.get("final_lap")):
            self._comm_flags["final_lap"] = True
            L("final_lap", 0, persona="COMMENTATOR")

        # CAREER CALLBACK (once, early-mid race): the booth remembers the
        # player's past results at this circuit across sessions — the thing
        # that makes RacerTV feel like it's been covering YOUR career.
        if (is_race and phase != "opening" and not self._comm_flags.get("career")
                and leader is not None and leader.completed_laps >= 1):
            self._comm_flags["career"] = True
            note = self._career_note(trk)
            pd = next((d for d in order if d.driver_info.slot_id
                       == s.vehicle_info.slot_id), None)
            if note and pd is not None:
                ccat, ckw = note
                cpool = COMMENTARY_LINES.get(ccat)
                if cpool:
                    cands.append((4, _safe_format(
                        self._pick(cpool, ("COMM", ccat)),
                        dict(ckw, trk=trk, drv=self._dname(pd),
                             comm=COMMENTATOR_NAME, pundit=PUNDIT_NAME)),
                        ccat, 0,
                        "PUNDIT" if random.random() < 0.5 else "COMMENTATOR"))

        # a circuit-trivia drop early on (once, around lap 2) — name & history.
        # Hold it back until the MID race — the opening belongs to the leaders.
        # (the flag is latched in _emit_commentary when the line actually AIRS —
        # latching here lost the track intro for the whole race whenever the
        # queue happened to be busy at this instant; retry every 20s instead)
        if (is_race and phase != "opening" and not self._comm_flags.get("trackintro")
                and leader is not None and leader.completed_laps >= 1
                and now - getattr(self, "_trackintro_try", -1e9) > 20.0):
            self._trackintro_try = now
            fact = self._track_fact(trk)
            cands.append((4, _safe_format(fact or self._pick(
                COMMENTARY_LINES["track_generic"], ("COMM", "trk")), {"trk": trk}),
                "track_fact", 0, "COMMENTATOR"))

        ctx = SimpleNamespace(
            s=s, now=now, order=order, placemap=placemap, cur=cur, leader=leader,
            phase=phase, total=total, togo=togo, timed=timed, is_race=is_race,
            is_quali=is_quali, solo=solo, open_sess=open_sess, field_n=field_n,
            trk=trk, n1=n1, n2=n2, n3=n3, q_n1=q_n1, q_n2=q_n2, q_n3=q_n3,
            q_set_t=q_set_t, cands=cands, L=L)
        self._colour_race(ctx)        # MID-RACE colour rotation
        self._quali_events(ctx)       # quali/practice event-driven booth
        self._colour_quali(ctx)       # quali/practice filler
        self._emit_commentary(ctx)    # arbitrate cands -> speak

    def _emit_commentary(self, c):
        """Arbitrate the candidate lines and speak the winner (from update_commentary)."""
        cands, cur, is_race, now = c.cands, c.cur, c.is_race, c.now
        trk = c.trk
        self._comm_prev = cur
        # ---- ARBITRATION BUFFER -------------------------------------------
        # A booth line exists only on the tick the moment happens. If the queue
        # is full right then, the old code threw it away — so under saturation
        # WHICH call aired was decided by timing, not importance: a midfield
        # scrap could take the slot a beat before a lead change, and the lead
        # change was simply lost.
        #
        # So a blocked call is now HELD and re-entered as a candidate on the
        # following ticks, competing on priority like anything else. Exactly
        # one is held: a better call replaces it (the worse one is genuinely
        # gone, which is correct — the booth can't say everything), an equal or
        # worse call leaves it alone.
        #
        # It EXPIRES. Play-by-play rots: "takes P3" is wrong a few seconds
        # later once they've lost it again, and airing a stale call is worse
        # than silence. HOLD_TTL is deliberately short for that reason. This is
        # the one thing the buffer must not get wrong.
        held = getattr(self, "_comm_hold", None)
        if held is not None and now >= held[5]:
            held = self._comm_hold = None          # went stale — let it go
        if held is not None:
            cands = list(cands) + [held[:5]]
        if not cands:
            return
        cands.sort(key=lambda c: c[0])
        _prio, text, cat, inten, persona = cands[0]
        # big live moments (overtakes/spins/lead changes/start/finish = prio <=2)
        # jump the cooldown so the booth reacts right away. Everything else only
        # starts when the audio queue has ROOM, so the booth never lags the race
        # by a long backlog. Urgent events are NOT force-queued — they're capped
        # too (just with a touch more headroom), so a busy race can't bury the
        # booth seconds behind the action with stale "takes the lead" calls.
        urgent = _prio <= 2
        # RECAP categories bypass the busy gate too: they're already rare
        # (their own 30s+ selection cooldown was spent the moment they were
        # PICKED, win or lose) — without this exemption a recap chosen while
        # the queue had any backlog at all was silently discarded, and the
        # next attempt was 30+ seconds away, making them air far less often
        # than the cooldown alone would suggest.
        busy = (self.tts is not None and self.tts._pending() >= 2
                and cat not in RECAP_CATS)
        # the booth is RELAXED in practice/qualifying — a much longer gap between
        # colour lines, so it isn't chattering away over a quiet session
        cd = self.COMMENTARY_CD if is_race else self.COMMENTARY_CD * 4.0
        if not urgent and (busy or (now - self._comm_cd) < cd):
            return
        signature = cat in ("start", "final_lap", "pregrid")
        if urgent and not signature and cat not in RECAP_CATS:
            # DON'T HAND A LINE TO A QUEUE THAT IS ALREADY FULL. speak() would
            # discard it on arrival (`DROP-busy`), so returning here loses
            # nothing — but it stops the booth churning through candidates and
            # synthesising audio that is certain to be binned. A real debug log
            # showed 200+ consecutive `DROP-busy urgent=True` with the queue
            # pegged at its cap: urgent lines skip COMMENTARY_CD, and the tick
            # loop runs at 20Hz, so it attempted a call every 50ms.
            #
            # The line is not lost: it goes into the hold above and comes back
            # as a candidate next tick. An earlier attempt here BLOCKED urgent
            # calls behind a minimum spacing instead, which silently destroyed
            # real overtake and crosstalk lines. Defer, never discard.
            if self.tts is not None and self.tts._pending() >= 4:
                cur_hold = getattr(self, "_comm_hold", None)
                # keep the MORE important of the two (lower prio wins). On a
                # tie the incumbent stays, so the older call — already waiting,
                # already closer to expiry — gets its chance first.
                if cur_hold is None or _prio < cur_hold[0]:
                    self._comm_hold = (_prio, text, cat, inten, persona,
                                       now + self.COMMENTARY_HOLD_TTL)
                return
        # this line is airing — release the hold. If the winner WAS the held
        # call it has now had its turn; if it was beaten by something live,
        # the hold is stale by definition (the booth has moved on).
        self._comm_hold = None
        self._comm_cd = now
        if is_race and cat == "track_fact":
            # the one-shot race track intro made it to air — latch it now
            self._comm_flags["trackintro"] = True
        spoken = self._spoken(text)
        seed = "PUNDIT" if persona == "PUNDIT" else "COMM"
        nmkw = {"comm": COMMENTATOR_NAME, "pundit": PUNDIT_NAME,
                "comm_full": COMMENTATOR_FULL, "pundit_full": PUNDIT_FULL,
                "trk": trk}
        if self.tts:
            # BOOTH PRIORITY over team radio: if a big live call (overtake / lead
            # change / incident, prio<=2) needs to land and a driver's radio
            # message is mid-playback, cut the radio off — the broadcast booth
            # talks over the radio, never the other way round. (Only urgent calls
            # do this; routine colour still waits its turn politely.)
            # SIGNATURE moments that must NEVER be dropped or buried, even if the
            # queue is busy — the pregrid welcome ("Race day on RacerTV..."),
            # the lights-out start and the final-lap call. These interrupt
            # whatever's playing (e.g. leftover quali chatter before the grid
            # forms) so the call lands ON the moment, and force=True so they're
            # exempt from the TTL/busy-drop. The welcome can still be cut by the
            # lights-out sting if the race goes green mid-sentence — that's the
            # one thing allowed to talk over it.
            if urgent:
                sp = self.tts.speaking_persona()
                if signature:
                    self.tts.interrupt()                  # land it on the moment
                elif sp is not None and sp not in ("COMMENTATOR", "PUNDIT",
                                                   "ENGINEER"):
                    # cut a RIVAL's radio for a live call — but never your own
                    # engineer. He is talking to you and is the one voice
                    # actually worth protecting; the booth waits its turn.
                    self.tts.interrupt()
                elif (sp in ("COMMENTATOR", "PUNDIT")
                      and now < getattr(self, "_filler_until", 0.0)):
                    # a LIVE moment (overtake / lead change / spin) trumps the
                    # low-value colour the booth is mid-way through — cut it so
                    # the call lands NOW instead of queuing behind the filler
                    self.tts.interrupt()
            # CONVERSATION follow-ups (the pundit's answer, the lead's ack, the
            # banter chime-back) are built NOW but queued only from the lead
            # line's on_play — i.e. the moment the QUESTION actually airs. They
            # used to be force-queued immediately, so a question that TTL-dropped
            # in a backlog left its orphaned answer to play with no question
            # ("answer to nothing" / non-sequitur replies). Chaining makes the
            # exchange atomic: no question aired, no answer queued.
            followups = []                     # (text, persona, intensity, force)
            if cat == "crosstalk_q":
                # full exchange: lead asks -> pundit answers -> lead hands back.
                # The answer is drawn from the SAME topic as the question (paired
                # in CROSSTALK) so it actually responds to what was asked, not a
                # random non-sequitur. CROSSTALK_ANSWERS is the safe fallback.
                topic = getattr(self, "_crosstalk_topic", None)
                apool = (CROSSTALK[topic]["a"] if topic in CROSSTALK
                         else CROSSTALK_ANSWERS)
                ans = _safe_format(self._pick(apool, ("XANS", topic or "")),
                                   {"drv": getattr(self, "_crosstalk_drv", ""),
                                    "pos": getattr(self, "_crosstalk_pos", 0),
                                    **nmkw})
                followups.append((self._spoken(ans), "PUNDIT", 0, True))
                if random.random() < 0.7:
                    followups.append((_safe_format(
                        self._pick(CROSSTALK_ACK, ("XACK",)), nmkw),
                        "COMMENTATOR", 0, True))
            elif cat == "driverstory_q":
                # the pundit recaps that driver's race from the RACE STORY data
                d = getattr(self, "_storyq_d", None)
                report = self._story_report(d) if d is not None else None
                if report:
                    self._story_told.add(d.driver_info.slot_id)   # don't repeat it
                    followups.append((self._spoken(report), "PUNDIT", 0, True))
            elif cat in ("lore_q", "lore_q_rally"):
                # the OTHER voice answers from their racing past — track-specific
                # where we have a memory, else a named generic
                ans_persona = "PUNDIT" if cat == "lore_q" else "COMMENTATOR"
                followups.append((self._spoken(_safe_format(
                    self._lore_answer(ans_persona, trk), nmkw)),
                    ans_persona, 0, True))
            elif cat in ("track_fact", "track_generic") and random.random() < 0.8:
                # keep the booth conversational — whoever gave the track
                # knowledge, the OTHER voice responds, so it feels like the two of
                # them are watching together. Pundit-led coaching earns a "great
                # analysis" from the lead; a lead-told fact gets the pundit's take.
                if persona == "PUNDIT":
                    followups.append((_safe_format(
                        self._pick(CROSSTALK_ACK, ("XACK",)), nmkw),
                        "COMMENTATOR", 0, True))
                else:
                    followups.append((self._spoken(_safe_format(
                        self._track_pundit(trk), nmkw)), "PUNDIT", 0, True))
            # the OTHER voice in the booth chimes back on the big moments (banter)
            elif persona == "COMMENTATOR" and random.random() < PUNDIT_AFTER.get(cat, 0.0):
                pool = PUNDIT_LINES.get(cat, PUNDIT_LINES["generic"])
                followups.append((self._spoken(self._pick(pool, ("PUNDIT", cat))),
                                  "PUNDIT", 1, False))

            # caption is shown by the on_play callback the moment audio STARTS,
            # so the subtitle matches what you actually hear (no desync).
            if followups:
                def _onp(t, p, _f=tuple(followups)):
                    self._show_caption(t, p)     # runs on the TTS play thread
                    # hold the play stage for the reply that's about to render:
                    # priority alone couldn't stop an already-rendered engineer
                    # line airing in the gap between question and answer.
                    # (getattr: the headless test harness's FakeTts predates it)
                    getattr(self.tts, "expect_answer", lambda: None)()
                    for ftxt, fper, finten, ffor in _f:
                        # exchange=True: the reply outranks even the engineer in
                        # the pipeline, so nothing can wedge between a question
                        # and its answer ("What do you think, Brett?" ->
                        # engineer gap call -> answer broke the whole flow)
                        # exchange=True for EVERY followup, not just the forced
                        # ones. expect_answer() holds all prio>=0 jobs, and a
                        # non-exchange reply is prio 1 — so the pundit's
                        # chime-back was being blocked by the very hold its own
                        # question set, sat out the whole 8s window, and the
                        # engineer (prio 0) then beat it to the queue. That is
                        # the "engineer talks in the middle of the booth's
                        # conversation" the tester heard. force stays as-is, so
                        # banter is still droppable — it just can't be gazumped.
                        self.tts.speak(ftxt, fper,
                                       seed=("PUNDIT" if fper == "PUNDIT"
                                             else "COMM"),
                                       intensity=finten, force=ffor,
                                       on_play=self._show_caption,
                                       exchange=True)
            else:
                _onp = self._show_caption
            # booth lines quoting a LIVE figure (gap/lap/standing) date fastest
            # of all — tighten their TTL so "gap is 1.0 seconds" can never air
            # half a race late. RECAPS (driver-story arc, lore anecdotes) also
            # contain numbers (grid/finish positions) but describe something
            # still true 15s later — TTL-dropping those is why driverstory
            # recaps had gone quiet: they're rare (own 30s+ gate) AND
            # number-heavy, so the tight TTL was killing almost every one
            # that got picked while the queue had any backlog at all.
            _ttl = (8.0 if (not signature and cat not in RECAP_CATS
                            and any(c.isdigit() for c in spoken))
                    else None)
            self.tts.speak(spoken, persona, seed=seed, intensity=inten,
                           on_play=_onp, urgent=urgent, force=signature,
                           ttl=_ttl)
            # remember roughly when a colour/filler line will finish, so a live
            # call arriving during it can interrupt (above)
            if not urgent:
                self._filler_until = now + min(7.0, len(spoken) * 0.055 + 1.5)
            else:
                self._filler_until = 0.0
        else:
            self._show_caption(spoken, persona)
        self._radio_recent.append(
            f"{time.strftime('%H:%M:%S')} {persona[:4]}[{inten}] {text[:40]}")
        self._radio_recent = self._radio_recent[-7:]

    def _tight_battle(self, order, within=1.5, top=10):
        """True when a genuinely close fight is running near the front.

        Used to keep the booth ON the racing in the closing laps: while cars
        are that close, conversation and recaps wait."""
        for d in order[:top]:
            if d.place <= 1:
                continue
            g = self.interval.get(d.driver_info.slot_id)
            if g is not None and 0.05 < g < within:
                return True
        return False

    def _colour_race(self, c):
        """MID-RACE colour rotation (extracted verbatim from update_commentary)."""
        # once the win is announced the race is OVER for the booth: no more
        # "X minutes remaining" / stakes / analysis colour — those lines queue
        # behind the finish wrap and air stale after the flag, which is the
        # single most immersion-breaking thing the booth can do
        if self._comm_flags.get("winannounced"):
            return
        is_race, phase, cands, now = c.is_race, c.phase, c.cands, c.now
        order, placemap, leader = c.order, c.placemap, c.leader
        total, togo, timed = c.total, c.togo, c.timed
        n1, n2, n3, s, trk, L = c.n1, c.n2, c.n3, c.s, c.trk, c.L
        # MID-RACE colour (no dead air): driver assessments, track trivia,
        # standings, analysis. Mid + late phases — opening belongs to leaders,
        # closing to the win fight. Late phase gets a narrower subset (no random
        # criticism/midpack — keep urgency, not colour).
        if is_race and phase in ("mid", "late") and not cands:
            # the LEAD commentator is the primary voice — weight filler toward him
            # (~65%) so the pundit complements rather than dominates the booth
            who2 = lambda: "COMMENTATOR" if random.random() < 0.65 else "PUNDIT"
            pits = self._pits_live(order)
            # strategy-flavoured analysis only when pitting is really in play
            ana = lambda: ("analysis_strategy"
                           if pits and random.random() < 0.3 else "analysis")
            fcd = self._filler_cd
            rdy = lambda t, g: now - fcd.get(t, -1e9) >= g
            pcar = self._player_car(s)
            types = ["analysis"]
            # INSIGHT — the pundit framing the live race state (gaps, laps,
            # stakes). The core "help the viewer understand the race" layer, so
            # it's offered often (short gate) in BOTH mid and late phases.
            mins_left = (int(s.session_time_remaining // 60)
                         if timed and s.session_time_remaining > 0 else None)
            ins = self._insight(placemap, n1, n2, n3, total, togo, mins_left)
            if ins and rdy("insight", 9):
                types.append("insight")
            if rdy("stat", 12):
                types.append("stat")
            if n3 and rdy("standings", 12):
                types.append("standings")
            if rdy("crosstalk", 14):
                types.append("crosstalk")
            # BOOTH AWARENESS of the player's race objective. The broadcast
            # can't see a private radio target, but it CAN see a driver
            # visibly working to one — so the booth nods at the pit wall
            # rather than quoting numbers it shouldn't know.
            if getattr(self, "_obj", None) and rdy("objective", 40):
                types.append("objective")
            if rdy("lore", 70):                 # the booth's racing-past banter
                types.append("lore")
            # RACE ARC — call back to a driver's earlier incident (did it cost
            # them, or did they recover?). Available mid AND late, since the
            # closing-stages payoff ("that earlier incident cost them") is the
            # whole point.
            arc = self._story_arc(order)
            if arc and rdy("storyarc", 18):
                types.append("storyarc")
            # RACE STORY conversation — the lead asks the pundit to recap an
            # eventful driver's whole race (grid -> now), pundit answers from the
            # recorded data. Rare-ish; it's a proper bit of analysis.
            # only once there IS a story to tell (same gate as the cadence
            # block above) — otherwise the booth recaps a race that hasn't
            # happened yet
            _ll = leader.completed_laps if leader is not None else 0
            _sok = (_ll >= 4 or (total and total > 0 and _ll >= total * 0.25))
            story_d = self._story_pick(order) if _sok else None
            if story_d is not None and rdy("driverstory", 30):
                types.append("driverstory")
            # colour-padding types only in mid (not late — urgency wins)
            if phase == "mid":
                if rdy("praise", 14):
                    types.append("praise")
                if len(order) >= 5 and rdy("midpack", 16):
                    types.append("midpack")
                if len(order) > 10 and rdy("criticism", 18):
                    types.append("criticism")
                if rdy("track", 22):
                    types.append("track")
                if rdy("broadcast", 40):      # RacerTV channel ID — a rare treat
                    types.append("broadcast")
                if total and total > 0 and leader is not None and rdy("lap", 24):
                    types.append("lap")
                if pcar and rdy("car", 45):
                    types.append("car")
            # ROTATION (#3): bias toward the category used LONGEST ago so every
            # type cycles in and no two races sound the same — round-robin-ish,
            # with a little random jitter so the order still varies. (Plain
            # random.choice clustered the same few fillers.)
            pick = min(types, key=lambda t: fcd.get(t, -1e9) + random.uniform(0, 5))
            fcd[pick] = now
            if pick == "insight":
                cat, ikw = ins
                # the lead frames the race state too (not just the pundit), so the
                # play-by-play voice stays prominent
                L(cat, 6, persona=who2(), **ikw)
            elif pick == "storyarc":
                acat, adrv = arc
                L(acat, 6, persona="PUNDIT", drv=adrv)
            elif pick == "driverstory":
                # lead asks; pundit answers dynamically at emission (below)
                self._storyq_d = story_d
                self._crosstalk_drv = self._dname(story_d)
                L("driverstory_q", 6, persona="COMMENTATOR",
                  drv=self._crosstalk_drv)
            elif pick == "lap":
                done = leader.completed_laps
                L("lap_milestone", 6, lap=min(total, done + 1), total=total,
                  togo=max(0, total - done))
            elif pick == "standings":
                L("standings", 6, p1=n1, p2=n2, p3=n3)
            elif pick == "car":                          # name the player's car
                pdrv = next((d for d in order
                             if d.driver_info.slot_id == s.vehicle_info.slot_id),
                            None)
                L("car", 6, persona=who2(),
                  drv=self._dname(pdrv) if pdrv else "our driver", car=pcar)
            elif pick == "praise":                       # TOP 3 — driving brilliantly
                dd = random.choice(order[:3])
                dsl = dd.driver_info.slot_id
                tags = self._story.get(dsl, [])
                cat = ("praise_recovery" if "recovered" in tags and
                       COMMENTARY_LINES.get("praise_recovery")
                       else "praise_led" if "led" in tags and
                       COMMENTARY_LINES.get("praise_led")
                       else "praise")
                L(cat, 6, persona=who2(), drv=self._dname(dd))
            elif pick == "midpack":                      # P4-P10 — solid/average race
                cand = order[3:10]
                if cand:
                    dd = random.choice(cand)
                    dsl = dd.driver_info.slot_id
                    tags = self._story.get(dsl, [])
                    cat = ("midpack_recovery" if "recovered" in tags and
                           COMMENTARY_LINES.get("midpack_recovery")
                           else "midpack_spun" if "spun" in tags and
                           COMMENTARY_LINES.get("midpack_spun")
                           else "midpack")
                    L(cat, 6, persona=who2(), drv=self._dname(dd), pos=dd.place)
            elif pick == "criticism":                    # P11+ — having a rough one
                cand = order[10:]
                if cand:
                    dd = random.choice(cand)
                    dsl = dd.driver_info.slot_id
                    tags = self._story.get(dsl, [])
                    cat = ("criticism_spun" if "spun" in tags and
                           COMMENTARY_LINES.get("criticism_spun")
                           else "criticism")
                    L(cat, 6, persona=who2(), drv=self._dname(dd))
            elif pick == "crosstalk":                    # lead asks the pundit
                d = random.choice(order[:5])
                topic = random.choice([t for t in CROSSTALK
                                       if pits or t not in self._PIT_TOPICS])
                self._crosstalk_topic = topic
                self._crosstalk_drv = self._dname(d)
                self._crosstalk_pos = d.place
                L("crosstalk_q", 6, persona="COMMENTATOR",
                  line=self._pick(CROSSTALK[topic]["q"], ("XQ", topic)),
                  drv=self._crosstalk_drv, pos=d.place)
            elif pick == "objective":
                pdrv = next((d for d in order
                             if d.driver_info.slot_id == s.vehicle_info.slot_id),
                            None)
                if pdrv is not None:
                    o = getattr(self, "_obj", None) or {}
                    prog = o.get("_prog")
                    cat = ("obj_booth_close" if prog and prog > 0.55
                           else "obj_booth")
                    L(cat, 6, persona=who2(), drv=self._dname(pdrv))
            elif pick == "lore":                         # racing-past banter
                if random.random() < 0.6:                # Miles asks Brett
                    L("lore_q", 6, persona="COMMENTATOR",
                      line=self._lore_pick_topic("pundit"))
                else:                                    # Brett asks Miles
                    L("lore_q_rally", 6, persona="PUNDIT",
                      line=self._lore_pick_topic("comm"))
            elif pick == "stat":                         # fill space with real numbers
                txt = self._stat_line(placemap, n1, n2)
                if txt:
                    cands.append((6, txt, "stat", 0, who2()))
                else:
                    L(ana(), 6, persona=who2())
            elif pick == "track":
                # the PUNDIT owns circuit knowledge (history + where-to-find-time
                # coaching) — it's his analytical role, and what the player loved
                fact = self._track_fact(trk)
                if fact:
                    cands.append((6, _safe_format(fact, {"trk": trk}),
                                  "track_fact", 0, "PUNDIT"))
                else:
                    L("track_generic", 6, persona="PUNDIT")
            else:
                L(ana(), 6, persona=who2())

    def _colour_quali(self, c):
        """Quali/practice filler (extracted verbatim from update_commentary)."""
        is_race, cands, now, order = c.is_race, c.cands, c.now, c.order
        q_n1, q_n2, q_n3, q_set_t = c.q_n1, c.q_n2, c.q_n3, c.q_set_t
        field_n, solo, open_sess, is_quali = c.field_n, c.solo, c.open_sess, c.is_quali
        s, trk, L, n1 = c.s, c.trk, c.L, c.n1
        # QUALI / PRACTICE filler — keep the booth talking but ONLY with
        # session-safe pools (no race wording). The provisional grid, the venue,
        # the player's car, and in practice a run note.
        if not is_race and not cands:
            # in the calmer practice/qualifying booth keep a genuine 50/50 between
            # the two voices — they're chatting, not calling a race — so it always
            # sounds like TWO people, not one voice droning on
            who2 = lambda: "COMMENTATOR" if random.random() < 0.5 else "PUNDIT"
            fcd = self._filler_cd
            rdy = lambda t, g: now - fcd.get(t, -1e9) >= g
            pcar = self._player_car(s)
            # bread-and-butter "colour" is the default; track facts are an
            # occasional TREAT on a long cooldown (there are only ~4-6 per
            # circuit, so firing them often = an obvious repeating loop)
            nset = len(q_set_t)                          # how many have a TIME
            npits = sum(1 for d in order if d.in_pitlane == 1)
            pdrv = next((d for d in order
                         if d.driver_info.slot_id == s.vehicle_info.slot_id), None)
            pname = self._dname(pdrv) if pdrv is not None else (q_n1 or n1)
            types = []
            if solo:
                # PRIVATE session (just you, maybe a ghost) — talk about YOUR
                # running and GOALS, the venue, the booth's racing past and the
                # odd joke; never a 'field' or 'provisional grid'. Spread across
                # many types on long cooldowns so it never loops the same line.
                if (open_sess and pdrv is not None and pdrv.completed_laps >= 2
                        and rdy("qopen", 28)):
                    types.append("qopen")
                if rdy("qsolo", 45):              # 'only you out there' — sparingly
                    types.append("qsolo")
                if rdy("qgoals", 26):             # what you're working on
                    types.append("qgoals")
                if pcar and rdy("qcar", 40):
                    types.append("qcar")
                if not is_quali and rdy("pnote", 22):
                    types.append("pnote")
                if rdy("scolour", 24):
                    types.append("scolour")
                if rdy("joke", 70):               # a light joke now and then
                    types.append("joke")
                if rdy("qtrack", 50):
                    types.append("qtrack")
            else:
                if rdy("scolour", 9):
                    types.append("scolour")
                # nobody's set a lap yet -> DON'T read the registration order as a
                # grid; say so plainly instead
                if nset == 0 and rdy("qnobody", 16):
                    types.append("qnobody")
                # SESSION STATE — who's set a time, who's still in the pits
                if 0 < nset < field_n and rdy("qcount", 18):
                    types.append("qcount")
                if npits >= max(3, field_n // 2) and rdy("qpits", 22):
                    types.append("qpits")
                # only a 'provisional grid' once THREE have actually set times
                if nset >= 3 and rdy("qstand", 14):
                    types.append("qstand")
                if pcar and rdy("qcar", 34):
                    types.append("qcar")
                if not is_quali and rdy("pnote", 12):
                    types.append("pnote")
                if nset >= 4 and rdy("sslow", 24):
                    types.append("sslow")
                if (open_sess and pdrv is not None and pdrv.completed_laps >= 3
                        and rdy("qopen", 34)):
                    types.append("qopen")
                if pcar and rdy("qgoals", 26):      # what the player's working on
                    types.append("qgoals")
                if rdy("joke", 80):
                    types.append("joke")
                if rdy("qtrack", 40):               # track facts: rare, a treat
                    types.append("qtrack")
            if rdy("lore", 55):                     # racing-past banter (any session)
                types.append("lore")
            # if EVERYTHING is on cooldown, just stay quiet — a practice/quali
            # booth doesn't need to fill every gap, and forcing a repeat was
            # exactly what made the track facts loop.
            if types:
                pick = min(types,
                           key=lambda t: fcd.get(t, -1e9) + random.uniform(0, 4))
                fcd[pick] = now
                if pick == "scolour":
                    L("session_colour", 6, persona=who2())
                elif pick == "qgoals":
                    L("quali_goals", 6, persona=who2(), drv=pname)
                elif pick == "joke":
                    L("booth_joke", 6, persona=who2())
                elif pick == "lore":
                    if random.random() < 0.6:
                        L("lore_q", 6, persona="COMMENTATOR",
                          line=self._lore_pick_topic("pundit"))
                    else:
                        L("lore_q_rally", 6, persona="PUNDIT",
                          line=self._lore_pick_topic("comm"))
                elif pick == "qsolo":
                    L("quali_solo", 6, persona=who2(), drv=pname)
                elif pick == "qopen":
                    L("quali_open_laps", 6, persona=who2(), drv=pname,
                      laps=pdrv.completed_laps if pdrv is not None else 0)
                elif pick == "qnobody":
                    L("quali_nobody", 6, persona=who2())
                elif pick == "qstand":
                    L("quali_standings", 6, p1=q_n1, p2=q_n2, p3=q_n3)
                elif pick == "qcount":
                    if nset == 1:                    # only one driver has a time
                        L("quali_onlyone", 6, persona=who2(),
                          drv=q_n1 or pname)
                    else:
                        L("quali_count", 6, persona=who2(),
                          set=nset, total=field_n)
                elif pick == "qpits":
                    L("quali_pits", 6, persona=who2())
                elif pick == "qcar":
                    L("car", 6, persona=who2(),
                      drv=pname if pdrv is not None else "our driver", car=pcar)
                elif pick == "pnote":
                    L("practice_note", 6, persona=who2(),
                      drv=self._dname(random.choice(order[:10] or order)))
                elif pick == "sslow":
                    dd = q_set_t[-1]                 # the slowest car WITH a time
                    L("lap_report_slow", 6, persona=who2(),
                      drv=self._dname(dd), pos=len(q_set_t))
                else:
                    # quali/practice booth: pull the RICH track-knowledge pool
                    # (history + analysis + deep per-corner tips) so a solo
                    # session is genuinely track-focused and never loops.
                    fact = self._track_knowledge(trk)
                    cands.append((6, _safe_format(
                        fact or self._pick(COMMENTARY_LINES["track_generic"],
                                           ("COMM", "trk")), {"trk": trk}),
                        "track_fact", 0, "COMMENTATOR"))

    def _finish_sequence(self, n1, n2, n3, trk, chasers=None, include_win=True):
        """Scripted post-race wrap, played as a CONVERSATION between the lead and
        the pundit — queued in order with synced captions (force=True so the
        chatter-drop never eats the wrap-up). The lead calls the win as P1 crosses
        the line; the pundit then singles out a standout drive from P2-P5 (his
        'man of the race'); then they round off the podium and sign off.

        include_win=False skips the win call (used when the win was already
        announced at the leader's crossing and this is the FINAL-positions wrap)."""
        n = 0

        def say(cat, persona, inten, pool=None, **kw):
            nonlocal n
            kw.setdefault("trk", trk)
            kw.setdefault("comm", COMMENTATOR_NAME)
            kw.setdefault("pundit", PUNDIT_NAME)
            kw.setdefault("comm_full", COMMENTATOR_FULL)
            kw.setdefault("pundit_full", PUNDIT_FULL)
            src = pool if pool is not None else COMMENTARY_LINES.get(cat)
            if not src:
                return
            text = _safe_format(self._pick(src, ("FIN", cat)), kw)
            spoken = self._spoken(text)
            if self.tts:
                self.tts.speak(spoken, persona,
                               seed=("PUNDIT" if persona == "PUNDIT" else "COMM"),
                               intensity=inten, on_play=self._show_caption, force=True)
            else:
                self._show_caption(spoken, persona)
            n += 1

        # KEEP IT SHORT — a tight wrap, then sign off. The pundit picks his
        # standout drive; the lead rounds off the podium; then the closing
        # sign-off. (The win call is fired separately at the leader's crossing.)
        if include_win:
            say("win", "COMMENTATOR", 2, drv=n1)                          # lead
        pick = random.choice(chasers) if chasers else (n2 or n1)
        say("ppick", "PUNDIT", 1, pool=PUNDIT_PICK, p1=n1, pick=pick)     # pundit
        say("summary", "COMMENTATOR", 1, p1=n1, p2=n2, p3=n3)            # lead
        # CLIMACTIC close: the winner crosses the line to take victory at the
        # venue, then the RacerTV sign-off — the signature send-off.
        say("victory_signoff", "COMMENTATOR", 2, p1=n1)                  # sign off

        # protect the whole wrap from the leave-session flush. The window must
        # cover not just the wrap's own lines (~8s each) but whatever is ALREADY
        # queued ahead of them — at the flag the queue is full of driver
        # celebrations, and the sign-off was getting flushed when the player
        # dropped to the results screen before the wrap had even started.
        ahead = self.tts._pending() if self.tts else 0
        self._wrap_until = time.time() + max(30.0, (n + ahead) * 8.0)

    def _insight(self, placemap, n1, n2, n3, total, togo, mins_left=None):
        """The pundit's 'meaning' line — framed from the LIVE race state so the
        viewer understands the race as a whole: what the front gap is worth,
        what's at stake in the podium fight, how the time/laps remaining change
        the picture. Returns (category, kwargs) or None (caller falls back)."""
        def gap_to(place):
            d = placemap.get(place)
            return self.interval.get(d.driver_info.slot_id) if d is not None else None

        timed = not (total and total > 0)
        cands = []
        front = gap_to(2)            # leader -> P2
        p4 = gap_to(4)              # P3 -> P4 (is the podium under threat?)

        if front is not None and n1 and n2:
            if front < 2.5 and not timed:
                cands.append(("insight_lead_slim",
                              {"p1": n1, "p2": n2, "gap": self._fmt_gap(front),
                               "togo": togo}))
            elif front > 6.0:
                cands.append(("insight_lead_big",
                              {"p1": n1, "gap": self._fmt_gap(front)}))
                cands.append(("insight_field_spread", {}))
        if p4 is not None and p4 < 1.3 and n3:
            cands.append(("insight_podium_fight",
                          {"p3": n3, "gap": self._fmt_gap(p4)}))
        if not timed and 1 <= togo <= 12:
            cands.append(("insight_laps_left", {"togo": togo, "total": total}))
        # TIMED race: frame the clock instead of laps
        if timed and mins_left is not None and 1 <= mins_left <= 12:
            cands.append(("insight_time_left", {"mins": mins_left}))

        return random.choice(cands) if cands else None

    def _story_report(self, d):
        """A spoken summary of a driver's race so far, built from their RACE
        STORY (grid -> best/worst -> now). Returns text or None."""
        sl = d.driver_info.slot_id
        st = self._race_story.get(sl)
        grid = self.grid_place.get(sl)
        if not st or grid is None:
            return None
        nm, now, best, worst = self._dname(d), st["now"], st["best"], st["worst"]
        net = grid - now
        dip = worst - grid
        if net >= 2:                        # net climber
            arc = "comeback" if dip >= 3 else "climber"
        elif net <= -2:                     # net loser
            if worst > now + 2:             # fell further, then clawed some back
                arc = "faller_clawing"
            elif best <= grid - 1:          # ran higher than the grid, then sank
                arc = "peaked_slipped"
            else:
                arc = "faller"
        elif dip >= 3:                      # steady net, but a mid-race scare
            arc = "scare_held"
        else:
            arc = "steady"
        return _safe_format(
            self._pick(STORY_REPORT[arc], ("STORY", arc)),
            {"nm": nm, "grid": grid, "best": best, "worst": worst, "now": now,
             "comm": COMMENTATOR_NAME, "pundit": PUNDIT_NAME})

    def _story_pick(self, order):
        """Pick a driver whose race has an INTERESTING arc worth discussing
        (climbed a lot, fell a lot, or fell-then-recovered). Returns a driver or
        None. Prefers bigger swings; the player is eligible too."""
        told = getattr(self, "_story_told", set())
        elig = []
        for d in order:
            sl = d.driver_info.slot_id
            if sl in told:                  # already recapped this driver — skip
                continue
            st = self._race_story.get(sl)
            grid = self.grid_place.get(sl)
            if not st or grid is None:
                continue
            net = grid - st["now"]          # + climbed / - dropped
            dip = st["worst"] - grid        # how far below the start they fell
            # a 2-place net swing or a 3-place dip is already a story worth
            # telling (the old >=3/>=4 bar meant a normal race produced NO
            # eligible drivers and the recap never aired at all)
            if abs(net) >= 2 or dip >= 3:
                elig.append((d, abs(net) + dip))
        if not elig:
            return None
        elig.sort(key=lambda e: -e[1])
        return random.choice(elig[:4])[0]   # one of the most eventful

    def _story_arc(self, order):
        """For a driver who had an early incident (a 'spun' story tag), judge how
        their race played out vs where they STARTED: did it cost them (still well
        down on the grid slot) or did they bounce back (recovered to/above it)?
        Returns (category, driver_name) or None."""
        picks = []
        for d in order:
            sl = d.driver_info.slot_id
            if "spun" not in self._story.get(sl, []):
                continue
            grid = self.grid_place.get(sl)
            if grid is None:
                continue
            if d.place <= grid:
                picks.append(("arc_recovered", self._dname(d)))
            elif d.place > grid + 2:
                picks.append(("arc_cost", self._dname(d)))
        return random.choice(picks) if picks else None

    def _narrative_arc(self, sl, place=None):
        """Classify a driver's race-so-far for the BIG-moment calls, so the
        booth ties the call to the story ('wins from P14 on the grid!') instead
        of just stating the event. Returns (tag, kwargs):
          'comeback' — fell way below the grid slot and has climbed right back
          'charge'   — started deep and has carved up through the field
          'wire'     — front all the way (only meaningful for the leader)
          None       — no special arc; use the generic call."""
        st = self._race_story.get(sl)
        grid = self.grid_place.get(sl)
        if not st or grid is None:
            return None, {}
        now_p = place if place is not None else st["now"]
        if st["worst"] >= grid + 3 and st["worst"] - now_p >= 4:
            return "comeback", {"worst": st["worst"], "grid": grid}
        if grid - now_p >= 4:
            return "charge", {"grid": grid}
        if grid == 1 and st["worst"] <= 2 and now_p == 1:
            return "wire", {"grid": grid}
        return None, {}

    def _lore_answer(self, persona, trk):
        """The booth lore answer, PAIRED to the topic of the question that was
        just asked. Track-flavoured topics may substitute a track-SPECIFIC
        memory (Miles' F1-title battles / Brett's WEC easter eggs) when we have
        one for this circuit — those are still on-topic, since the question was
        about the track."""
        who = "PUNDIT" if persona == "PUNDIT" else "COMM"
        low = (trk or "").lower()
        twho, topic = getattr(self, "_lore_topic", (None, None))
        tdef = LORE_TOPICS.get(twho, {}).get(topic) if topic else None
        # a track-specific war story only replaces the answer when the QUESTION
        # was about the track (topic marked "track") — never on personal topics
        if tdef is None or tdef.get("track"):
            by_track = (LORE_PUNDIT_BY_TRACK if who == "PUNDIT"
                        else LORE_COMM_BY_TRACK)
            for key, pool in by_track.items():
                if key in low and random.random() < 0.7:
                    return self._pick(pool, ("LOREPK", who, key))
        if tdef is not None:
            return self._pick(tdef["a"], ("LOREA", twho, topic))
        # no stored topic (shouldn't happen) — fall back to the generic pools
        cat = "lore_a" if who == "PUNDIT" else "lore_a_rally"
        return self._pick(COMMENTARY_LINES[cat], ("COMM", cat))

    def _lore_pick_topic(self, who):
        """Choose a lore TOPIC for the given answerer ('pundit' = Brett is
        asked, 'comm' = Miles is asked) and remember it, so the answer that
        airs actually responds to the question that was asked — the same
        Q/A pairing crosstalk uses. Returns the question text."""
        topics = LORE_TOPICS[who]
        topic = random.choice(list(topics))
        self._lore_topic = (who, topic)
        return self._pick(topics[topic]["q"], ("LOREQ", who, topic))

    def _track_pundit(self, trk):
        """The pundit's follow-up after a track fact. Track-SPECIFIC colour if we
        recognise the circuit, else a VARIED generic line — never the same 'so
        much history' every race, which is what made the booth sound repetitive."""
        low = (trk or "").lower()
        for key, pool in TRACK_PUNDIT_BY_TRACK.items():
            if key in low:
                # blend the track-specific colour with the varied generic pool so
                # a long (especially solo) session doesn't loop the same couple of
                # specific lines — a real pundit talks racing, not just the one
                # famous corner over and over.
                if random.random() < 0.5:
                    return self._pick(pool, ("TPUNK", key))
                return self._pick(TRACK_PUNDIT, ("TPUN",))
        return self._pick(TRACK_PUNDIT, ("TPUN",))

    def _track_knowledge(self, trk):
        """A BIG track-specific pool for the quali/practice booth's 'track
        knowledge' colour — history + analysis + the deep per-corner tips — so a
        long solo session stays richly track-focused (history, the works) without
        looping the same handful of lines."""
        low = (trk or "").lower()
        pool = []
        for key, facts in TRACK_FACTS.items():
            if key in low:
                pool += facts + TRACK_COACH.get(key, [])
                break
        for key, tips in TRACK_TIPS.items():
            if key in low:
                pool += tips
                break
        if pool:
            return self._pick(pool, ("TRACKKNOW", low[:12]))
        return None

    def _track_fact(self, trk):
        """Circuit knowledge if we recognise the track, else None — a mix of
        history (TRACK_FACTS) and 'where to find time / how to attack' coaching
        (TRACK_COACH), so the booth is both colourful AND genuinely useful."""
        low = (trk or "").lower()
        for key, facts in TRACK_FACTS.items():
            if key in low:
                pool = facts + TRACK_COACH.get(key, [])
                return self._pick(pool, ("TRACKFACT", key))
        return None

    def _stat_line(self, placemap, n1, n2):
        """A factual filler built from real numbers (gaps / fastest lap)."""
        opts = []
        p2 = placemap.get(2)
        if p2 is not None:
            g = self.interval.get(p2.driver_info.slot_id)
            if g and g > 0.1:
                opts.append(f"{n1} leads {n2} by {g:.1f} seconds at the front.")
        if self.fastest.get("time") and self.fastest.get("name"):
            opts.append(f"The fastest lap of the race belongs to "
                        f"{self.fastest['name']}, a {R.fmt_time(self.fastest['time'])}.")
        return random.choice(opts) if opts else None

    def _fmt_gap(self, g):
        """Speak a gap naturally: 'under a second' / '1.8 seconds'."""
        if g is None:
            return "moments"
        if g < 1.0:
            return "under a second"
        return f"{g:.1f} seconds"

    def _spell_laps(self, n):
        """'three laps', 'ten laps', else 'N laps' — reads better than digits."""
        return f"{self._LAP_WORDS.get(n, n)} laps"

    def _pits_live(self, order):
        """True when pit strategy is actually part of THIS race: a mandatory
        stop is configured (pitstop_status != -1 for the field) or somebody has
        genuinely visited the pit lane. Gates the booth's undercut / pit-wall /
        strategy chatter out of no-stop sprints, where 'pitting now would throw
        the strategy into question' is immersion-breaking nonsense."""
        if getattr(self, "_pit_t", None):
            return True
        d = order[0] if order else None
        return d is not None and getattr(d, "pitstop_status", -1) in (0, 1, 2)

    def _report_wide(self, name, now):
        """Lighter booth note for a MODERATE off — you ran wide / had a moment but
        didn't spin. The pundit flags it; no dramatic sting, short window so it
        never escalates the way a real incident does. Skipped if a bigger incident
        is already mid-report."""
        if now < getattr(self, "_incident_until", 0.0):
            return
        txt = _safe_format(
            self._pick(COMMENTARY_LINES["ranwide"], ("COMM", "ranwide")),
            {"drv": name, "comm": COMMENTATOR_NAME, "pundit": PUNDIT_NAME})
        if self.tts:
            self.tts.speak(self._spoken(txt), "PUNDIT", seed="PUNDIT",
                           intensity=1, on_play=self._show_caption, force=True)
            self._incident_until = now + 4.0
        else:
            self._show_caption(txt, "PUNDIT")
