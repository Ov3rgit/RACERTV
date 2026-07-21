# -*- coding: utf-8 -*-
"""
RACE OBJECTIVES — the engineer sets you a goal, then holds you to it.

The rule this module lives or dies by: an objective that was never achievable
is worse than no objective at all, because it instantly exposes the engineer
as fake. So every candidate is checked against real closing-rate maths before
it is offered, and when nothing passes, HE SAYS NOTHING.

Lifecycle: offer -> track -> resolve (met / missed / withdrawn). Exactly one
objective is ever active, it always resolves out loud, and it is withdrawn
(not left dangling) when the race changes underneath it — damage, the target
retiring, or the race running out of laps.

Mixed into Overlay; see r3e_overlay.py.
"""

import r3e_data as R

# --- tuning ---------------------------------------------------------------
OBJ_MIN_GAP_S = 25.0     # min seconds between one objective resolving and the next
OBJ_SETTLE_LAPS = 1      # objectives can start once lap 1 is complete (lap 2),
                         # early enough to shape the race rather than waiting
OBJ_MARGIN = 0.8         # only offer if it needs <= 80% of the laps available
OBJ_MIN_DELTA = 0.06     # s/lap pace edge below which "catching" is noise
OBJ_MAX_CHASE_GAP = 18.0  # beyond this, a catch is fantasy however good the pace
OBJ_DEFEND_NEAR = 3.5    # a car this close behind is worth defending against
OBJ_NUDGE_CD = 22.0      # min seconds between mid-objective progress lines from
                         # the engineer — encouragement, not a running commentary


class ObjectiveMixin:
    """See module docstring."""

    # ---- state ----------------------------------------------------------
    def _obj_reset(self):
        self._obj = None            # the active objective, or None
        self._obj_last_t = 0.0      # when the last one resolved (spacing)
        self._obj_count = 0         # how many set this session
        self._obj_met = 0
        self._obj_result = None     # last outcome, for the HUD chip
        self._obj_kinds = set()     # kinds used this race (one-shot ones)
        self._obj_nudge_t = 0.0     # last mid-objective progress line
        # BOOTH NOTICE: ("set"|"met"|"miss", kind, target_name, when). The booth
        # can't see a private radio call, but it CAN see a driver visibly
        # working to one — so it nods at the pit wall in the right terms at
        # the moment it happens, instead of at random. Drained by the booth.
        self._obj_booth = None

    # ---- helpers --------------------------------------------------------
    def _obj_pace(self, slot):
        """A driver's CURRENT pace in seconds/lap, from their recent laps —
        not their best, which is a one-off and would promise catches that
        today's pace cannot deliver. None until they have run a clean lap."""
        laps = getattr(self, "recent_laps", {}).get(slot) or []
        laps = [l for l in laps if l and l > 0]
        if not laps:
            return None
        if len(laps) >= 3:
            return sorted(laps)[len(laps) // 2]       # median: ignores one-offs
        return sum(laps) / len(laps)

    def _obj_laps_left(self, s, order):
        """Laps remaining for the PLAYER, for lap races and timed races alike.
        None when it cannot be known (no pace yet in a timed race)."""
        total = s.number_of_laps
        leader = order[0] if order else None
        if total and total > 0 and leader is not None:
            return max(0, total - leader.completed_laps)
        rem = getattr(s, "session_time_remaining", 0.0)
        if rem and rem > 0:
            vslot = s.vehicle_info.slot_id
            pace = self._obj_pace(vslot)
            if pace and pace > 0:
                return max(0, int(rem / pace))
        return None

    def _obj_can_close(self, gap, mine, theirs, laps_left, want_gap=0.0):
        """Core feasibility test. Returns the laps needed to pull `gap` down to
        `want_gap`, or None when it is not realistically on.

        This is the guard that keeps the engineer credible: no pace edge, a
        gap too large to matter, or not enough laps -> no objective."""
        if not (gap and mine and theirs and laps_left):
            return None
        if gap > OBJ_MAX_CHASE_GAP:
            return None
        delta = theirs - mine                 # +ve = you are the faster car
        if delta < OBJ_MIN_DELTA:
            return None
        need = (gap - want_gap) / delta
        if need <= 0:
            return None                       # already there
        if need > laps_left * OBJ_MARGIN:
            return None                       # not enough race left
        return need

    def _obj_driver(self, order, place):
        return next((d for d in order if d.place == place), None)

    def _obj_seen(self, kind):
        """True once this KIND has already been set this race. The one-shot
        objectives (clean running, recovery, tyre management) describe a
        situation rather than a moment, so re-offering them would nag."""
        return kind in getattr(self, "_obj_kinds", set())

    def _obj_tyre_worn(self, s):
        """Worst tyre wear as 0.0 (fresh) - 1.0 (gone), or None when the game
        isn't publishing wear (tire_wear_active off = -1 = N/A)."""
        if not getattr(s, "tire_wear_active", 0):
            return None
        tw = [t for t in list(s.tire_wear)[:4] if t is not None and t >= 0]
        if len(tw) != 4:
            return None
        base = getattr(self, "_eng_tyre_base", None)
        if not base:
            return None
        return max(abs(base[i] - tw[i]) for i in range(4))

    # ---- offering -------------------------------------------------------
    def _obj_offer(self, s, order, placemap, now):
        """Pick a credible objective, or None. Ordered by how much it matters
        to the player's race — a podium on the table beats a routine chase."""
        vslot = s.vehicle_info.slot_id
        me = next((d for d in order if d.driver_info.slot_id == vslot), None)
        if me is None or me.in_pitlane == 1:
            return None
        laps_left = self._obj_laps_left(s, order)
        if not laps_left or laps_left < 1:
            return None                       # nothing meaningful left to set
        mine = self._obj_pace(vslot)
        if not mine:
            return None                       # no pace read yet — stay quiet
        pos = me.place

        # --- CLEAN RUNNING: you're close to a limits penalty. This one matters
        # more than any position target, because it is the one that can take
        # the whole result away. Uses the engineer's own limits tally.
        cuts = getattr(self, "_own_cuts", 0)
        if cuts >= 3 and not self._obj_seen("clean"):
            return {
                "kind": "clean", "target_slot": vslot,
                "target_name": "", "goal_pos": None, "gap_target": None,
                "cuts0": cuts, "laps": min(laps_left, 3),
                "hud": f"No more limits warnings ({cuts})",
            }

        # --- RECOVERY: you lost real ground after an incident. Gives a bad
        # race a purpose instead of leaving it flat.
        grid = self.grid_place.get(vslot)
        st = getattr(self, "_race_story", {}).get(vslot)
        if (grid and st and pos > grid + 2 and st.get("worst", pos) >= pos
                and not self._obj_seen("recover") and laps_left >= 4):
            goal = max(1, min(grid, pos - 2))
            return {
                "kind": "recover", "target_slot": vslot, "target_name": "",
                "goal_pos": goal, "gap_target": None,
                "laps": min(laps_left, 6), "_from_pos": pos,
                "hud": f"Recover to P{goal} (from P{pos})",
            }

        # --- TYRE MANAGEMENT: worn rubber and a stint still to run. Not a
        # position goal at all — the target is arriving at the flag with
        # something left, which is a real racing skill.
        tw = self._obj_tyre_worn(s)
        if tw is not None and tw > 0.55 and laps_left >= 4 and not self._obj_seen("tyres"):
            return {
                "kind": "tyres", "target_slot": vslot, "target_name": "",
                "goal_pos": pos, "gap_target": None,
                "laps": min(laps_left, 5),
                "hud": f"Nurse the tyres, hold P{pos}",
            }

        # --- DAMAGE LIMITATION: the race changed, so the goal changes.
        # Offered regardless of pace edge — this is about salvage, and it is
        # what stops a broken car from having no objective at all.
        dmg = getattr(self, "_obj_damaged", False)
        behind = self._obj_driver(order, pos + 1)
        if dmg and behind is not None:
            bgap = self.interval.get(behind.driver_info.slot_id)
            if bgap and bgap < 12.0:
                hold = round(max(3.0, bgap + 2.0))
                return {
                    "kind": "damage", "target_slot": behind.driver_info.slot_id,
                    "target_name": self._dname(behind), "gap_target": float(hold),
                    "goal_pos": pos, "laps": min(laps_left, 4),
                    "hud": f"Stay ahead of {self._dname(behind)} (+{hold}s)",
                }

        # --- HOLD THE LEAD HOME: you are winning, and the race is nearly done.
        # Without this the leader gets NOTHING: chase/position needs a car
        # ahead (there isn't one) and defend needs someone inside
        # OBJ_DEFEND_NEAR, so a comfortable lead produced silence at exactly
        # the moment the race should feel like it is being closed out. The
        # driver's own report: "the only objective I was hoping for at the end
        # was 'hold the lead to the finish' — that way the whole race would
        # have felt complete."
        #
        # No feasibility maths needed, and that is not a loophole: you are
        # already in front, so the target is to not lose it. Held back to the
        # closing laps so it reads as the final job of the day rather than a
        # 20-lap instruction to keep doing what you're doing.
        if pos == 1 and not self._obj_seen("leadhome") and laps_left <= 5:
            behind_ldr = self._obj_driver(order, 2)
            return {
                "kind": "leadhome",
                "target_slot": (behind_ldr.driver_info.slot_id
                                if behind_ldr is not None else vslot),
                "target_name": (self._dname(behind_ldr)
                                if behind_ldr is not None else "the field"),
                "goal_pos": 1, "gap_target": None,
                "laps": laps_left,
                "hud": "Hold the lead to the flag",
            }

        # --- CLOSING LAPS: the flag itself is the deadline, so drop the
        # pace-edge maths. A car close ahead in the last few laps is a "go get
        # them, this is your chance" whether or not your median lap is quicker
        # — following at 0.3s for three corners IS the opportunity. This is the
        # "I was right behind P3 in the last laps and got NO objective to
        # secure the podium" gap. Mirror for a close car behind: "secure P{n}
        # to the flag". Ahead takes priority — attacking beats defending.
        ahead0 = self._obj_driver(order, pos - 1)
        behind0 = self._obj_driver(order, pos + 1)
        if laps_left <= 3:
            if ahead0 is not None:
                agap = self.interval.get(vslot)
                if agap is not None and agap < 2.5:
                    return {
                        "kind": "position", "target_slot": ahead0.driver_info.slot_id,
                        "target_name": self._dname(ahead0),
                        "goal_pos": pos - 1, "gap_target": 0.0,
                        "laps": laps_left,
                        "hud": f"P{pos - 1} — last chance, pass {self._dname(ahead0)}",
                    }
            if behind0 is not None:
                bg = self.interval.get(behind0.driver_info.slot_id)
                if bg is not None and bg < 2.5:
                    return {
                        "kind": "defend", "target_slot": behind0.driver_info.slot_id,
                        "target_name": self._dname(behind0),
                        "gap_target": float(round(max(1.0, bg))), "goal_pos": pos,
                        "laps": laps_left,
                        "hud": f"Secure P{pos} to the flag",
                    }

        # --- CHASE / POSITION: the car directly ahead.
        ahead = self._obj_driver(order, pos - 1)
        if ahead is not None:
            aslot = ahead.driver_info.slot_id
            gap = self.interval.get(vslot)     # our gap to the car ahead
            theirs = self._obj_pace(aslot)
            need = self._obj_can_close(gap, mine, theirs, laps_left)
            if need is not None:
                deadline = max(2, min(laps_left, int(need) + 2))
                # kind "position" whenever the goal is to TAKE the place —
                # its lines talk about passing, which is what the HUD shows.
                # (Keying this off podium-or-not made a pass objective speak
                # the gap-closing line: "get within a second" under a HUD
                # reading "pass Dubois".)
                return {
                    "kind": "position",
                    "target_slot": aslot, "target_name": self._dname(ahead),
                    "goal_pos": pos - 1, "gap_target": 0.0,
                    "laps": deadline,
                    "hud": f"P{pos - 1} — pass {self._dname(ahead)}",
                }
            # can't pass, but can we at least CLOSE onto them? (a real, honest
            # smaller goal — and the one the tester described)
            if gap and gap > 1.5:
                need = self._obj_can_close(gap, mine, theirs, laps_left,
                                           want_gap=1.0)
                if need is not None:
                    deadline = max(2, min(laps_left, int(need) + 2))
                    return {
                        "kind": "chase", "target_slot": aslot,
                        "target_name": self._dname(ahead), "goal_pos": None,
                        "gap_target": 1.0, "laps": deadline,
                        "hud": f"Within 1s of {self._dname(ahead)}",
                    }

        # --- DEFEND: someone quicker is closing on you.
        if behind is not None:
            bslot = behind.driver_info.slot_id
            bgap = self.interval.get(bslot)
            theirs = self._obj_pace(bslot)
            if (bgap and bgap < OBJ_DEFEND_NEAR and theirs and mine
                    and mine - theirs > OBJ_MIN_DELTA):
                hold = round(max(1.0, bgap))
                return {
                    "kind": "defend", "target_slot": bslot,
                    "target_name": self._dname(behind),
                    "gap_target": float(hold), "goal_pos": pos,
                    "laps": min(laps_left, 4),
                    "hud": f"Hold P{pos} from {self._dname(behind)}",
                }
        return None

    # ---- progress / resolution ------------------------------------------
    def _obj_progress(self, s, order):
        """0.0-1.0 for the HUD, or None when it has no meaningful progress.

        EVERY position/time-bounded kind reports progress now. It used to only
        cover chase/position, so a 'defend P4' or 'nurse the tyres' objective
        showed a frozen empty bar for its whole life — reported as "the
        progress bar did not track it properly"."""
        o = self._obj
        if not o:
            return None
        vslot = s.vehicle_info.slot_id
        me = next((d for d in order if d.driver_info.slot_id == vslot), None)
        if me is None:
            return None
        kind = o["kind"]

        # CLOSING a gap: how much of the gap have you pulled back?
        if kind in ("chase", "position"):
            gap = self.interval.get(vslot)
            start = o.get("gap0")
            if gap is None or not start or start <= o["gap_target"]:
                return None
            span = start - o["gap_target"]
            return max(0.0, min(1.0, (start - gap) / span)) if span > 0 else None

        # HOLDING for N laps (defend / damage / leadhome / clean / tyres): the
        # bar fills with the laps survived. This is the honest read of "how
        # close am I to the flag on this", which is what these are really about.
        if kind in ("defend", "damage", "leadhome", "clean", "tyres"):
            laps = o.get("laps") or 0
            if laps <= 0:
                return None
            done = me.completed_laps - o["lap0"]
            return max(0.0, min(1.0, done / laps))

        # RECOVER: progress along the places climbed back toward the goal.
        if kind == "recover":
            frm = o.get("_from_pos")
            goal = o.get("goal_pos")
            if not frm or not goal or frm <= goal:
                return None
            return max(0.0, min(1.0, (frm - me.place) / (frm - goal)))
        return None

    def _obj_check(self, s, order, placemap, now):
        """Resolve the active objective. Returns (category, kwargs) for the
        engineer, or None if it is still running."""
        o = self._obj
        if not o:
            return None
        vslot = s.vehicle_info.slot_id
        me = next((d for d in order if d.driver_info.slot_id == vslot), None)
        if me is None:
            return None
        nm = o["target_name"]

        # WITHDRAW: the objective stopped making sense. Always spoken — a
        # silently vanishing target is worse than one that was never set.
        self_kinds = ("clean", "recover", "tyres")
        tgt = next((d for d in order
                    if d.driver_info.slot_id == o["target_slot"]), None)
        if tgt is None and o["kind"] not in self_kinds:
            self._obj = None                  # withdrawn: no verdict on the HUD
            self._obj_last_t = now
            return ("obj_withdraw_gone", {"drv": nm})
        if (o["kind"] not in ("damage",) + self_kinds
                and getattr(self, "_obj_damaged", False)):
            self._obj = None
            self._obj_last_t = now
            return ("obj_withdraw_damage", {"drv": nm})

        # ---- STILL-MAKES-SENSE re-evaluation, for EVERY kind ----------------
        # The general principle behind the "hold off Marco after he'd dropped
        # away" bug: an objective must keep asking whether it still describes
        # the race, not only whether it's met/missed. Each kind has its own
        # "this is now moot" condition, checked before the met/miss logic below.

        # DEFEND / DAMAGE: you comfortably CLIMBED PAST the position you were
        # holding — bank it and let a fresh target come.
        if o["kind"] in ("defend", "damage") and me.place <= o["goal_pos"] - 2:
            return self._obj_supersede(now, "obj_supersede_gained",
                                       {"drv": nm, "pos": me.place})
        # DEFEND / DAMAGE: the THREAT evaporated — the car you were told to hold
        # off dropped well out of range, so the target is meaningless.
        if o["kind"] in ("defend", "damage") and tgt is not None:
            bgap_now = self.interval.get(o["target_slot"])
            if bgap_now is not None and bgap_now > OBJ_DEFEND_NEAR * 2.5:
                return self._obj_done(now, "obj_met_defend_clear",
                                      {"drv": nm, "pos": me.place})
        # CHASE / POSITION: target retired or fell unreachably far ahead, OR you
        # DROPPED a place so the position you were racing for is behind you now.
        if o["kind"] in ("chase", "position"):
            gap = self.interval.get(vslot)
            # you set out to pass the car AHEAD, i.e. from position goal_pos+1.
            # "dropped a place" means you fell BELOW that start slot — the
            # position you were racing for is two or more places up now, a
            # different fight. (Not just me.place > goal_pos: that is true the
            # instant you set a pass objective, since you start one place back.)
            dropped = (o.get("goal_pos") is not None
                       and me.place > o["goal_pos"] + 1)
            if (gap is not None and gap > OBJ_MAX_CHASE_GAP * 1.5) or dropped:
                self._obj = None
                self._obj_last_t = now
                return ("obj_withdraw_gone", {"drv": nm})
        # TYRES: you PITTED — fresh rubber, so "nurse the tyres home" is done.
        if o["kind"] == "tyres" and me.in_pitlane == 1:
            self._obj = None
            self._obj_last_t = now
            return ("obj_withdraw_pit", {"drv": nm})

        laps_done = me.completed_laps - o["lap0"]
        pos = me.place

        if o["kind"] in ("chase", "position"):
            gap = self.interval.get(vslot)
            if o["goal_pos"] is not None and pos <= o["goal_pos"]:
                return self._obj_done(now, "obj_met_pass",
                                      {"drv": nm, "pos": pos})
            if (o["gap_target"] and gap is not None
                    and gap <= o["gap_target"]):
                return self._obj_done(now, "obj_met_close",
                                      {"drv": nm, "gap": f"{gap:.1f}s"})
        elif o["kind"] == "defend":
            # (climbed-past, threat-evaporated handled in the re-eval block above)
            if pos > o["goal_pos"]:                      # lost the place
                return self._obj_fail(now, "obj_miss_defend", {"drv": nm})
            if laps_done >= o["laps"]:
                return self._obj_done(now, "obj_met_defend",
                                      {"drv": nm, "pos": pos})
        elif o["kind"] == "damage":
            if pos > o["goal_pos"]:
                return self._obj_fail(now, "obj_miss_defend", {"drv": nm})
            if laps_done >= o["laps"]:
                return self._obj_done(now, "obj_met_damage",
                                      {"drv": nm, "pos": pos})

        elif o["kind"] == "leadhome":
            if pos > 1:                                  # lost the lead
                return self._obj_fail(now, "obj_miss_leadhome", {"drv": nm})
            if laps_done >= o["laps"]:
                return self._obj_done(now, "obj_met_leadhome",
                                      {"drv": nm, "pos": pos})
        elif o["kind"] == "clean":
            # failed the moment another limits warning lands
            if getattr(self, "_own_cuts", 0) > o["cuts0"]:
                return self._obj_fail(now, "obj_miss_clean", {"drv": nm})
            if laps_done >= o["laps"]:
                return self._obj_done(now, "obj_met_clean", {"pos": pos})
        elif o["kind"] == "recover":
            if pos <= o["goal_pos"]:
                return self._obj_done(now, "obj_met_recover", {"pos": pos})
        elif o["kind"] == "tyres":
            if pos > o["goal_pos"]:                      # dropped a place
                return self._obj_fail(now, "obj_miss_tyres", {"pos": pos})
            if laps_done >= o["laps"]:
                return self._obj_done(now, "obj_met_tyres", {"pos": pos})

        if laps_done >= o["laps"]:                       # ran out of laps
            cat = ("obj_miss_pass" if o["kind"] in ("chase", "position")
                   else "obj_miss_recover" if o["kind"] == "recover"
                   else "obj_miss_defend")
            return self._obj_fail(now, cat, {"drv": nm, "pos": pos})
        return None

    def _obj_result_set(self, ok, now):
        """Latch the outcome so the HUD can show it briefly — the chip must
        agree with what the engineer just said on the radio."""
        o = self._obj or {}
        self._obj_result = {"ok": ok, "hud": o.get("hud", ""),
                            "until": now + 8.0}

    def _obj_notice(self, event, now):
        """Post the booth's cue: (event, kind, target, when). MUST be called
        while _obj is still set — _obj_done/_obj_fail clear it straight after,
        and the booth needs the KIND to say what was actually asked for."""
        o = self._obj or {}
        self._obj_booth = (event, o.get("kind", ""),
                           o.get("target_name", ""), now)
        # UI chime for the objective card: given / met / missed, each a
        # distinct motif. Queued ahead of the engineer's line, so you hear the
        # chime and then what it means. Never let audio trouble break the
        # objective itself — this is decoration, the target is the feature.
        tts = getattr(self, "tts", None)
        if tts is not None:
            try:
                tts.chime(event)
            except Exception:
                pass

    def _obj_nudge(self, s, me, now):
        """A mid-objective progress line, or None. Keyed off the live trend so
        it MEANS something — the engineer reacting to how the target is going,
        not filler. On a long cooldown (OBJ_NUDGE_CD) so it encourages rather
        than nags, and only when there's something worth saying."""
        o = self._obj
        if now - getattr(self, "_obj_nudge_t", 0.0) < OBJ_NUDGE_CD:
            return None
        kind = o["kind"]
        gtrend = o.get("_trend")            # -1 closing gap, +1 gap slipping
        laps_left = o.get("_laps_left")
        cat = None
        lap_word = ("1 more lap" if laps_left == 1
                    else f"{laps_left} more laps" if laps_left else "a few laps")
        kw = {"drv": o.get("target_name") or "", "pos": me.place,
              "laps": lap_word}
        # ALTERNATE between a PROGRESS read (how it's going) and real ADVICE
        # (how to do it), so the engineer isn't only saying "keep it up" — the
        # driver asked for relevant coaching per objective. Which one this time
        # flips each nudge so both get an airing.
        want_advice = not getattr(self, "_obj_nudge_advice", False)
        self._obj_nudge_advice = want_advice
        advice = {"chase": "obj_advice_chase", "position": "obj_advice_chase",
                  "defend": "obj_advice_defend", "damage": "obj_advice_defend",
                  "tyres": "obj_advice_tyres", "clean": "obj_advice_clean",
                  "leadhome": "obj_advice_leadhome"}
        # last lap of any objective — always worth a "bring it home", and never
        # buried under coaching
        if laps_left is not None and laps_left <= 1:
            cat = "obj_nudge_nearly"
        elif want_advice and kind in advice:
            cat = advice[kind]                   # kind-specific coaching
        elif kind in ("chase", "position"):
            cat = ("obj_nudge_closing" if gtrend == -1
                   else "obj_nudge_slipping" if gtrend == 1
                   else "obj_nudge_holding")     # steady: "keep chipping away"
        elif kind in ("defend", "damage"):
            cat = ("obj_nudge_threat" if gtrend == -1
                   else "obj_nudge_holding")     # steady: "looking comfortable"
        elif kind in ("leadhome", "clean", "tyres", "recover"):
            cat = "obj_nudge_holding"            # a steady check-in on progress
        if cat is None:
            return None
        self._obj_nudge_t = now
        return (cat, kw)

    def _obj_supersede(self, now, cat, kw):
        """Like _obj_done (it IS an achievement — you climbed past the target),
        but shortens the spacing so the fresh, relevant objective can land
        promptly instead of leaving a gap where the driver has clearly earned a
        new goal."""
        self._obj_notice("met", now)
        self._obj_result_set(True, now)
        self._obj = None
        self._obj_last_t = now - (OBJ_MIN_GAP_S * 0.5)   # offer the next sooner
        self._obj_met += 1
        return (cat, kw)

    def _obj_done(self, now, cat, kw):
        self._obj_notice("met", now)
        self._obj_result_set(True, now)
        self._obj = None
        self._obj_last_t = now
        self._obj_met += 1
        return (cat, kw)

    def _obj_fail(self, now, cat, kw):
        self._obj_notice("miss", now)
        self._obj_result_set(False, now)
        self._obj = None
        self._obj_last_t = now
        return (cat, kw)

    # ---- entry point ----------------------------------------------------
    def objective_event(self, s, order, placemap, now):
        """Called from the engineer each tick. Returns (category, kwargs) for
        a line to speak, or None. Races only, and never on the last lap —
        setting a target you cannot resolve is the thing we are avoiding."""
        if getattr(self, "_obj", "missing") == "missing":
            self._obj_reset()
        if s.session_type != 2:
            return self._obj_quali(s, order, now)
        if not getattr(self, "_racing", False):
            return None
        vslot = s.vehicle_info.slot_id
        me = next((d for d in order if d.driver_info.slot_id == vslot), None)
        if me is None:
            return None

        if self._obj:                                 # one active at a time
            # live HUD fields: progress, laps remaining on the target and the
            # current gap, so the chip answers "how am I doing?" on its own
            self._obj["_prog"] = self._obj_progress(s, order)
            self._obj["_laps_left"] = max(
                0, self._obj["laps"] - (me.completed_laps - self._obj["lap0"]))
            _gap = (self.interval.get(vslot)
                    if self._obj["kind"] in
                    ("chase", "position", "defend", "damage") else None)
            # trend for the HUD arrow: is the gap actually coming down?
            _prev = self._obj.get("_gap")
            if _gap is not None and _prev is not None:
                if _gap < _prev - 0.05:
                    self._obj["_trend"] = -1        # closing
                elif _gap > _prev + 0.05:
                    self._obj["_trend"] = 1         # slipping away
            self._obj["_gap"] = _gap
            # badge shown in the chip's accent flash: the position being raced
            # for, or a short tag for the situational targets
            k = self._obj["kind"]
            gp = self._obj.get("goal_pos")
            self._obj["_badge"] = (
                f"P{gp}" if gp and k in ("position", "chase", "defend",
                                         "damage", "recover")
                else "LIM" if k == "clean" else "TYR" if k == "tyres" else "GO")
            resolved = self._obj_check(s, order, placemap, now)
            if resolved is not None:
                return resolved
            # STILL RUNNING — the engineer stays with you on it. This is the
            # difference between a target that is set once and forgotten, and
            # an engineer who is actually racing it with you: an occasional
            # progress read keyed off the live trend ("that's the gap coming
            # down, keep it up" / "he's got a run, defend hard"). Spaced on its
            # own long cooldown so it's encouragement, not nagging.
            return self._obj_nudge(s, me, now)

        if me.completed_laps < OBJ_SETTLE_LAPS:
            return None                               # let the race settle
        if now - self._obj_last_t < OBJ_MIN_GAP_S:
            return None
        laps_left = self._obj_laps_left(s, order)
        # allow a 1-lap objective now: the closing-laps push ("last chance, go
        # get P3") is exactly a final-lap goal, and blocking at <2 was why the
        # end-of-race podium chase never got a target.
        if not laps_left or laps_left < 1:
            return None
        o = self._obj_offer(s, order, placemap, now)
        if not o:
            return None                               # nothing credible: silence
        o["lap0"] = me.completed_laps
        o["gap0"] = self.interval.get(vslot)
        o["set_at"] = now
        o["_new_until"] = now + 6.0      # HUD shows a NEW TARGET flash
        self._obj = o
        self._obj_notice("set", now)
        self._obj_count += 1
        self._obj_kinds = getattr(self, "_obj_kinds", set()) | {o["kind"]}
        kw = {"drv": o["target_name"], "laps": o["laps"],
              "pos": o.get("goal_pos") or me.place,
              "gap": f"{o['gap_target']:.0f}s" if o.get("gap_target") else "a second"}
        return (f"obj_set_{o['kind']}", kw)

    # ---- practice / qualifying -----------------------------------------
    def _obj_quali(self, s, order, now):
        """Objectives for a session against the clock rather than the field:
        beat your own best, or close on pole. Same contract as the race
        version — offered only when the numbers say it is realistic, always
        resolved, exactly one at a time."""
        vslot = s.vehicle_info.slot_id
        me = next((d for d in order if d.driver_info.slot_id == vslot), None)
        if me is None:
            return None
        pb = self.best_lap.get(vslot)
        laps = me.completed_laps

        if self._obj:                              # resolve the live one
            o = self._obj
            o["_laps_left"] = max(0, o["laps"] - (laps - o["lap0"]))
            o["_gap"] = None
            o["_badge"] = "PB" if o["kind"] == "pb" else "POLE"
            done = laps - o["lap0"]
            if o["kind"] == "pb":
                if pb and pb <= o["target_t"]:
                    return self._obj_done(now, "obj_met_pb",
                                          {"t": R.fmt_time(pb)})
                if done >= o["laps"]:
                    return self._obj_fail(now, "obj_miss_pb", {})
            elif o["kind"] == "pole":
                pt = self._obj_pole_time(order, vslot)
                if pb and pt and (pb - pt) <= o["gap_target"]:
                    return self._obj_done(now, "obj_met_pole",
                                          {"gap": f"{max(0.0, pb - pt):.2f}s"})
                if done >= o["laps"]:
                    return self._obj_fail(now, "obj_miss_pole", {})
            return None

        # need a couple of laps banked before a target means anything
        if not pb or laps < 2 or now - self._obj_last_t < OBJ_MIN_GAP_S:
            return None
        # a clock session can run out too — don't set what can't be resolved
        rem = getattr(s, "session_time_remaining", 0.0)
        if 0 < rem < 180:
            return None

        pole_t = self._obj_pole_time(order, vslot)
        # CLOSE ON POLE — only when the gap is small enough to be real
        if (pole_t and pb - pole_t > 0.05 and pb - pole_t < 1.5
                and not self._obj_seen("pole")):
            want = round(max(0.15, (pb - pole_t) * 0.5), 2)
            self._obj = {"kind": "pole", "target_slot": vslot,
                         "target_name": "", "goal_pos": None,
                         "gap_target": want, "laps": 3, "lap0": laps,
                         "_new_until": now + 6.0,
                         "hud": f"Within {want:.2f}s of pole"}
            self._obj_count += 1
            self._obj_kinds = getattr(self, "_obj_kinds", set()) | {"pole"}
            return ("obj_set_pole", {"gap": f"{want:.2f}s", "laps": 3})

        # BEAT YOUR BEST — a couple of tenths is a real but fair ask
        if not self._obj_seen("pb"):
            want = round(pb - 0.20, 3)
            self._obj = {"kind": "pb", "target_slot": vslot,
                         "target_name": "", "goal_pos": None,
                         "gap_target": None, "target_t": want, "laps": 3,
                         "lap0": laps, "_new_until": now + 6.0,
                         "hud": "Beat your best by 0.2s"}
            self._obj_count += 1
            self._obj_kinds = getattr(self, "_obj_kinds", set()) | {"pb"}
            return ("obj_set_pb", {"t": R.fmt_time(want), "laps": 3})
        return None

    def _obj_pole_time(self, order, vslot):
        """Best lap set by anyone other than the player, or None."""
        ts = [self.best_lap.get(d.driver_info.slot_id) for d in order
              if d.driver_info.slot_id != vslot]
        ts = [t for t in ts if t and t > 0]
        return min(ts) if ts else None

    def objective_form(self):
        """PHASE 3: the player's recent objective form from the career file, as
        (met, set) over the last few races — or None when there isn't enough
        history to be worth mentioning. Lets the engineer refer to how you've
        been going lately instead of treating every race as the first."""
        try:
            hist = (self._career().get("obj_races") or [])[-5:]
        except Exception:
            return None
        if len(hist) < 3:                  # too little history to mean anything
            return None
        met = sum(h[0] for h in hist)
        setn = sum(h[1] for h in hist)
        if setn < 3:
            return None
        return (met, setn, len(hist))

    def objective_summary(self):
        """PHASE 3: end-of-race verdict on the targets set today, as
        (category, kwargs) — spoken by the engineer in the finish wrap."""
        n = getattr(self, "_obj_count", 0)
        if not n:
            return None
        met = getattr(self, "_obj_met", 0)
        kw = {"met": met, "total": n}
        form = self.objective_form()
        if form:
            kw["fmet"], kw["fset"], kw["fraces"] = form
        if met == n:
            return ("obj_wrap_all", kw)
        if met == 0:
            return ("obj_wrap_none", kw)
        return ("obj_wrap_some", kw)

    def objective_hud(self):
        """(text, progress) for the on-screen objective, or None."""
        o = getattr(self, "_obj", None)
        if not o:
            return None
        return (o["hud"], o.get("_prog"))
