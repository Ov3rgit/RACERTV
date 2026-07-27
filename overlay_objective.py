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
from overlay_common import obj_stake, STRIKE_GAP

# --- tuning ---------------------------------------------------------------
OBJ_MIN_GAP_S = 25.0     # min seconds between one objective resolving and the next
OBJ_SETTLE_LAPS = 1      # objectives can start once lap 1 is complete (lap 2),
                         # early enough to shape the race rather than waiting
OBJ_MARGIN = 0.8         # only offer if it needs <= 80% of the laps available
OBJ_MIN_DELTA = 0.06     # s/lap pace edge below which "catching" is noise
OBJ_MAX_CHASE_GAP = 18.0  # beyond this, a catch is fantasy however good the pace
OBJ_DEFEND_NEAR = 1.5    # a car this close behind is worth defending against —
                         # tightened from 3.5s per driver feedback: a car a
                         # full second-plus back doesn't warrant "hold him off"
OBJ_DEFEND_CLEAR_GAP = 2.2   # beyond this the chaser has plainly lost the pace
                             # to keep up — the defend is as good as won
OBJ_DEFEND_CLEAR_HOLD = 4.0  # ...sustained this long before it resolves MET,
                             # so a car that yo-yos back inside range doesn't
                             # bank the win off one lucky straight
OBJ_NUDGE_CD = 22.0      # min seconds between mid-objective progress lines from
                         # the engineer — encouragement, not a running commentary
OBJ_HOLD_GAIN = 3.0      # a gained/passed place must STICK this long before it
                         # counts as met — a yo-yo battle shouldn't insta-resolve
OBJ_HOLD_LOSE = 8.0      # ...and a lost place must stay lost this long before it
                         # fails. Was 4.0, and a real race proved that too
                         # short: the car behind sent it up the inside, held the
                         # place through the corner sequence for ~7s, overshot
                         # and spun — and the 4s hold had already called
                         # "obj_miss_defend" one second before the player's
                         # regain ack was queued. A miss verdict is a one-shot
                         # with no second chance, so waiting longer costs a late
                         # call at worst; being wrong costs the engineer's
                         # credibility. 8s outlasts a pass that immediately
                         # unravels while still failing a genuine loss well
                         # before the next objective could be offered.
OBJ_MIN_LIFE = 15.0      # an objective may not resolve MET before it has been
                         # live this long. A target set and "achieved" seconds
                         # later was never a target — in the closing laps
                         # `immediate` skips every hysteresis hold, so a defend
                         # could be set and banked within six seconds, twice in
                         # a row. A genuine miss is exempt: losing the place IS
                         # the answer, however fast it happens.
OBJ_REPEAT_CD = 150.0    # ...and the same (kind, driver) can't come back for
                         # this long once resolved, so the engineer finds
                         # something new to ask for instead of looping one job
OBJ_SET_STALE_S = 12.0   # a set line still undrained this long after the target
                         # was chosen is announcing a position that has moved on;
                         # withdraw the target rather than say something false


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
        # (kind, target_slot) -> when it last resolved. The repeatable targets
        # (defend / position / chase) are not one-shot like `clean` or `tyres`,
        # so nothing stopped the engineer setting the SAME job against the SAME
        # driver over and over: a race ended with "hold P3 from Pano Papas" set
        # and resolved four times in three minutes, twice inside six seconds.
        self._obj_recent = {}
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

    def _obj_race_ending(self, s, order):
        """True when the race is in its final stretch, so no new multi-lap
        target should be set and any live hold should be banked at the flag.

        LAP race: leader on the last lap. TIMED race: under ~1 lap of time
        left, or the white flag is out. A timed race in RaceRoom runs the
        current lap out after the clock hits zero, so 'time <= one lap' is the
        honest 'this is basically the last lap' signal — which is exactly what
        was missing when the engineer set 'hold for 4 laps' with the flag due."""
        total = s.number_of_laps
        leader = order[0] if order else None
        if total and total > 0 and leader is not None:
            return leader.completed_laps >= total - 1
        rem = getattr(s, "session_time_remaining", 0.0)
        if getattr(getattr(s, "flags", None), "white", 0) == 1:
            return True
        if rem and rem > 0:
            pace = self._obj_pace(s.vehicle_info.slot_id) or 0
            if pace > 0:
                return rem <= pace * 1.1          # ~one lap of time left
        return False

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

    def _obj_held(self, o, key, cond, now, secs, immediate=False):
        """Debounce a resolve condition: return True only once `cond` has stayed
        true continuously for `secs`. The instant `cond` lapses the timer resets,
        so a place that yo-yos with a rival never trips a verdict off one corner.

        CONFIRMED place already rejects a one-TICK flicker (~200ms); this adds the
        SECONDS-long hold the driver asked for, so an overtake that gets repassed
        two corners later resolves nothing either way. `immediate` bypasses the
        wait at the flag, where there is no 'later' to wait for."""
        tkey = "_hold_" + key
        if not cond:
            o[tkey] = None
            return False
        if immediate:
            return True
        t0 = o.get(tkey)
        if t0 is None:
            o[tkey] = now
            return False
        return (now - t0) >= secs

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
            #
            # The target SCALES with the gap now. It was pinned at 1.0s, which
            # is a huge ask from four seconds back and meant _obj_can_close
            # rejected it in exactly the strung-out races that most needed a
            # goal — leaving defend as the only repeatable objective, which is
            # how one race ended up looping "hold P3" four times. From a long
            # way back "get it under three seconds" is a proper stint's work and
            # a target the driver can actually feel progress against; from close
            # range it still asks for the full second.
            if gap and gap > 1.5:
                want = 1.0 if gap <= 2.5 else min(3.0, round(gap * 0.55, 1))
                need = self._obj_can_close(gap, mine, theirs, laps_left,
                                           want_gap=want)
                if need is not None:
                    deadline = max(2, min(laps_left, int(need) + 2))
                    _w = self._obj_gap_text(want)
                    return {
                        "kind": "chase", "target_slot": aslot,
                        "target_name": self._dname(ahead), "goal_pos": None,
                        "gap_target": float(want), "laps": deadline,
                        "hud": f"Within {_w} of {self._dname(ahead)}",
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

        # --- CONSISTENCY: nothing to chase or defend (clean air), so the goal
        # becomes a driving DISCIPLINE — string together laps within a tight
        # window of each other. A real racecraft target, and it means clean air
        # no longer produces silence. Needs a few laps of pace to set a
        # reference off, and enough race left to be worth it.
        recent = getattr(self, "recent_laps", {}).get(vslot) or []
        recent = [l for l in recent if l and l > 0]
        # GENUINE clean air only: no car within 5s ahead or 4s behind. In
        # RaceRoom 5s is already a big gap, and a car behind is the more
        # pressing concern than one the same distance up the road — so the
        # behind threshold is tighter. With a car closer than this you're still
        # in a fight, and "just do consistent laps" would read as the engineer
        # ignoring it.
        agap = self.interval.get(vslot)
        bgap_c = (self.interval.get(behind.driver_info.slot_id)
                  if behind is not None else None)
        clear_ahead = ahead is None or (agap is not None and agap > 5.0)
        clear_behind = behind is None or (bgap_c is not None and bgap_c > 4.0)
        if (len(recent) >= 2 and laps_left >= 4 and clear_ahead and clear_behind
                and not self._obj_seen("consistency")):
            ref = mine                            # median recent pace = the mark
            band = max(0.6, ref * 0.015)          # within ~1.5% (min 0.6s)
            return {
                "kind": "consistency", "target_slot": vslot,
                "target_name": "", "goal_pos": pos, "gap_target": None,
                "laps": min(laps_left, 5), "_ref": ref, "_band": band,
                "_last_lap_n": me.completed_laps, "_ok_laps": 0,
                "hud": f"Consistent laps (±{band:.1f}s)",
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

        # CONSISTENCY: fills with the count of laps kept inside the band.
        if kind == "consistency":
            laps = o.get("laps") or 0
            return (max(0.0, min(1.0, o.get("_ok_laps", 0) / laps))
                    if laps > 0 else None)

        # CLOSING a gap: how much of the gap have you pulled back?
        if kind in ("chase", "position"):
            gap = self.interval.get(vslot)
            start = o.get("gap0")
            if gap is None or not start or start <= o["gap_target"]:
                return None
            span = start - o["gap_target"]
            return max(0.0, min(1.0, (start - gap) / span)) if span > 0 else None

        # HOLDING for N laps (defend / damage / leadhome / clean / tyres): the
        # bar fills with the laps survived toward the flag. Blend in how far
        # through the CURRENT lap the player is, so the bar creeps continuously
        # every frame instead of standing still for a whole lap then jumping a
        # seventh at the line — the 'it's giving too little information' feel.
        if kind in ("defend", "damage", "leadhome", "clean", "tyres"):
            laps = o.get("laps") or 0
            if laps <= 0:
                return None
            done = me.completed_laps - o["lap0"]
            frac = getattr(me, "lap_distance_fraction", 0.0) or 0.0
            frac = max(0.0, min(1.0, frac))
            return max(0.0, min(1.0, (done + frac) / laps))

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

        # RETARGET — the objective is about the POSITION, and the named car is
        # only whoever is in the way of it. When that car leaves the relevant
        # slot (passes someone else, or drops back), the driver you now have to
        # beat is a DIFFERENT person, and the objective must follow the PLACE,
        # not the name. Applied ACROSS every kind that races a specific car:
        #   position -> the car occupying the place you want
        #   chase    -> the car directly ahead you're closing on
        #   defend / -> the car directly behind you're holding off
        #   damage
        #   leadhome -> whoever is now chasing the lead
        # Uses CONFIRMED place so a one-tick side-by-side flicker can't churn the
        # name. (Reported: 'get P5 from X' kept naming X after X moved to P4.)
        def _cpl(d):
            return (self.cplace.get(d.driver_info.slot_id, d.place)
                    if hasattr(self, "cplace") else d.place)
        gp = o.get("goal_pos")
        _cpos = _cpl(me)
        _kind = o["kind"]
        want_place = None
        if _kind == "position" and gp:
            want_place = gp
        elif _kind == "chase":
            want_place = _cpos - 1
        elif _kind in ("defend", "damage") and gp:
            want_place = gp + 1
        elif _kind == "leadhome":
            want_place = 2
        if want_place and want_place >= 1:
            occ = next((d for d in order if _cpl(d) == want_place
                        and d.driver_info.slot_id != vslot), None)
            if occ is not None and occ.driver_info.slot_id != o["target_slot"]:
                o["target_slot"] = occ.driver_info.slot_id
                o["target_name"] = self._dname(occ)
                if _kind == "position":
                    o["hud"] = f"P{gp} — pass {o['target_name']}"
                elif _kind == "chase":
                    _tg = o.get("gap_target") or 1.0
                    o["hud"] = f"Within {_tg:.0f}s of {o['target_name']}"
                elif _kind in ("defend", "damage"):
                    o["hud"] = f"Hold P{gp} from {o['target_name']}"
                # leadhome's HUD is name-free ("Hold the lead to the flag")
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

        # RACE ENDING: bank a live objective at the flag rather than leave it
        # showing "hold for 4 laps" while the timed race runs out under it.
        # Hold-types that reached the flag intact are a WIN; position/chase
        # that didn't get there is a near miss. This is the timed-race fix —
        # the lap deadline no longer outlives the race.
        ending = self._obj_race_ending(s, order)
        if ending:
            kind = o["kind"]
            if kind in ("defend", "damage", "leadhome", "tyres", "clean",
                        "consistency"):
                # you were holding and you made the flag — call it done
                if kind == "leadhome" and me.place > 1:
                    return self._obj_fail(now, "obj_miss_leadhome", {"drv": nm})
                # ...but only if it was ever REALLY a job. At the flag this
                # branch banks any live hold instantly, so a defend handed out
                # seconds earlier was congratulated for surviving a deadline it
                # never had time to face: the transcript shows "1 lap to
                # withstand it" at 09:35:02 and "P3 is yours" at 09:35:08, then
                # the identical pair again half a minute later. Withdraw it
                # quietly instead — no verdict line, no booth reaction, nothing
                # on the HUD. Nothing happened, so nobody says anything.
                #
                # SERVING THE LAPS COUNTS. If the driver actually ran the laps
                # the target asked for, it was a real job however the clock
                # looks — only a target the flag cut short is hollow.
                _served = (me.completed_laps - o["lap0"]) >= o["laps"]
                if not _served and self._obj_too_soon(now):
                    self._obj = None
                    self._obj_last_t = now
                    return None
                met = {"defend": "obj_met_defend", "damage": "obj_met_damage",
                       "leadhome": "obj_met_leadhome", "tyres": "obj_met_tyres",
                       "clean": "obj_met_clean",
                       "consistency": "obj_met_consistency"}[kind]
                return self._obj_done(now, met, {"drv": nm, "pos": me.place})
            # chase/position/recover fall through to their own met/miss below,
            # which the flag will resolve via the normal position checks.

        # ---- STILL-MAKES-SENSE re-evaluation, for EVERY kind ----------------
        # The general principle behind the "hold off Marco after he'd dropped
        # away" bug: an objective must keep asking whether it still describes
        # the race, not only whether it's met/missed. Each kind has its own
        # "this is now moot" condition, checked before the met/miss logic below.

        # DEFEND / DAMAGE: you CLIMBED ABOVE the position you were holding —
        # bank it and let a fresh target come. Fires on ANY place gained (was
        # two places, which meant "hold P6" only released at P4 while you were
        # already in P5 hunting P4). Uses the CONFIRMED place so a one-tick
        # position flicker at the overtake can't supersede prematurely.
        cpos = self.cplace.get(vslot, me.place) if hasattr(self, "cplace") else me.place
        if (o["kind"] in ("defend", "damage")
                and self._obj_held(o, "gain", cpos < o["goal_pos"], now,
                                   OBJ_HOLD_GAIN, immediate=ending)):
            return self._obj_supersede(now, "obj_supersede_gained",
                                       {"drv": nm, "pos": cpos})
        # DEFEND / DAMAGE: the THREAT evaporated — the chaser has plainly lost
        # the pace to keep up. Needs a real, SUSTAINED gap (not one lucky
        # straight): OBJ_DEFEND_CLEAR_GAP held for OBJ_DEFEND_CLEAR_HOLD seconds,
        # via the same hysteresis every other yo-yo-prone transition uses — a
        # gap that yo-yos back inside 3s (traffic, a backmarker tow) doesn't
        # bank the defend as won.
        #
        # PASSIVE resolution, so it also has to have been a REAL job first. The
        # driver did not achieve this one — the chaser simply fell away — and in
        # the closing laps `immediate` skips the hold above entirely, which let
        # a defend be set at 1.5s and banked the moment the gap touched 2.2s.
        # The transcript showed it set and "won" twice inside six seconds each
        # ("Pano Papas's fallen away, no more threat there") and offered again
        # 25s later. Congratulating someone for a threat that never materialised
        # is worse than saying nothing, so it must have stood for a while.
        if o["kind"] in ("defend", "damage") and tgt is not None:
            bgap_now = self.interval.get(o["target_slot"])
            if (self._obj_held(o, "clear",
                               bgap_now is not None and bgap_now > OBJ_DEFEND_CLEAR_GAP,
                               now, OBJ_DEFEND_CLEAR_HOLD, immediate=ending)
                    and not self._obj_too_soon(now)):
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
            dropped = self._obj_held(
                o, "drop",
                o.get("goal_pos") is not None and cpos > o["goal_pos"] + 1,
                now, OBJ_HOLD_LOSE, immediate=ending)
            if (gap is not None and gap > OBJ_MAX_CHASE_GAP * 1.5) or dropped:
                self._obj = None
                self._obj_last_t = now
                return ("obj_withdraw_gone", {"drv": nm})
        # PIT STOP: pitting scrambles your position (you drop through the pit
        # lane) and wrecks a lap time — through no RACING fault. It must
        # WITHDRAW a position/lap objective, never fail it, which is what would
        # otherwise happen (dropped a place -> miss_defend; a garbage in/out lap
        # -> miss_consistency). Only 'clean' (limits) rides through a pit, since
        # you can't earn a limits warning in the pit lane. Tyres keeps its own
        # 'fresh rubber' message; everything else gets the generic pit call.
        if me.in_pitlane == 1 and o["kind"] != "clean":
            self._obj = None
            self._obj_last_t = now
            return (("obj_withdraw_pit" if o["kind"] == "tyres"
                     else "obj_withdraw_pitstop"), {"drv": nm})
        # CONSISTENCY: it was a CLEAN-AIR discipline target. It only withdraws
        # once a car is genuinely ON you — within 2s either side. That is a real
        # fight; 5s isn't, and pulling the rhythm drill that early would make it
        # useless. (The OFFER still needs proper clean air, 5s/4s, to START —
        # you don't get a consistency target while cars are milling nearby, but
        # once you have one it stands until someone actually closes in.)
        if o["kind"] == "consistency":
            ahead_c = next((d for d in order if d.place == me.place - 1), None)
            behind_c = next((d for d in order if d.place == me.place + 1), None)
            ag = self.interval.get(vslot) if ahead_c is not None else None
            bg = (self.interval.get(behind_c.driver_info.slot_id)
                  if behind_c is not None else None)
            if (ag is not None and ag < 2.0) or (bg is not None and bg < 2.0):
                self._obj = None
                self._obj_last_t = now
                return ("obj_withdraw_race", {"drv": nm})

        laps_done = me.completed_laps - o["lap0"]
        # CONFIRMED place for every met/fail comparison below — not live place.
        # An immediate FAIL (lost the place / lost the lead / dropped a place)
        # read off the live place would fire on a one-tick position flicker at
        # a corner or while being lapped. The supersede already uses confirmed
        # place; the fails must too, or they're harsher than the successes.
        pos = cpos

        # POSITION transitions (a pass landing, a place lost) must STICK for a
        # few seconds before they resolve — a wheel-to-wheel fight yo-yos, and
        # neither side should score a met/miss off a place that swaps straight
        # back. `immediate=ending` still resolves instantly at the flag.
        if o["kind"] in ("chase", "position"):
            gap = self.interval.get(vslot)
            if o["goal_pos"] is not None and self._obj_held(
                    o, "pass", pos <= o["goal_pos"], now,
                    OBJ_HOLD_GAIN, immediate=ending):
                return self._obj_done(now, "obj_met_pass",
                                      {"drv": nm, "pos": pos})
            if o["gap_target"] and self._obj_held(
                    o, "close", gap is not None and gap <= o["gap_target"],
                    now, OBJ_HOLD_GAIN, immediate=ending):
                return self._obj_done(now, "obj_met_close",
                                      {"drv": nm, "gap": f"{gap:.1f}s"})
        elif o["kind"] == "defend":
            # (climbed-past, threat-evaporated handled in the re-eval block above)
            if self._obj_held(o, "lose", pos > o["goal_pos"], now,
                              OBJ_HOLD_LOSE, immediate=ending):   # lost the place
                return self._obj_fail(now, "obj_miss_defend", {"drv": nm})
            if laps_done >= o["laps"]:
                return self._obj_done(now, "obj_met_defend",
                                      {"drv": nm, "pos": pos})
        elif o["kind"] == "damage":
            if self._obj_held(o, "lose", pos > o["goal_pos"], now,
                              OBJ_HOLD_LOSE, immediate=ending):
                return self._obj_fail(now, "obj_miss_defend", {"drv": nm})
            if laps_done >= o["laps"]:
                return self._obj_done(now, "obj_met_damage",
                                      {"drv": nm, "pos": pos})

        elif o["kind"] == "leadhome":
            if self._obj_held(o, "lose", pos > 1, now,
                              OBJ_HOLD_LOSE, immediate=ending):   # lost the lead
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
            if self._obj_held(o, "pass", pos <= o["goal_pos"], now,
                              OBJ_HOLD_GAIN, immediate=ending):
                return self._obj_done(now, "obj_met_recover", {"pos": pos})
        elif o["kind"] == "tyres":
            if self._obj_held(o, "lose", pos > o["goal_pos"], now,
                              OBJ_HOLD_LOSE, immediate=ending):   # dropped a place
                return self._obj_fail(now, "obj_miss_tyres", {"pos": pos})
            if laps_done >= o["laps"]:
                return self._obj_done(now, "obj_met_tyres", {"pos": pos})
        elif o["kind"] == "consistency":
            # each completed lap, check the new lap against the reference. One
            # lap outside the band fails it; a full run inside it is met.
            if me.completed_laps > o.get("_last_lap_n", o["lap0"]):
                o["_last_lap_n"] = me.completed_laps
                recent = getattr(self, "recent_laps", {}).get(vslot) or []
                last = recent[-1] if recent else None
                if last and last > 0:
                    if abs(last - o["_ref"]) > o["_band"]:
                        return self._obj_fail(now, "obj_miss_consistency",
                                              {"pos": pos})
                    o["_ok_laps"] = o.get("_ok_laps", 0) + 1
            if o.get("_ok_laps", 0) >= o["laps"]:
                return self._obj_done(now, "obj_met_consistency", {"pos": pos})

        if laps_done >= o["laps"]:                       # ran out of laps
            cat = ("obj_miss_pass" if o["kind"] in ("chase", "position")
                   else "obj_miss_recover" if o["kind"] == "recover"
                   else "obj_miss_consistency" if o["kind"] == "consistency"
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
        """Post the booth's cue: (event, kind, target, when, stake). MUST be
        called while _obj is still set — _obj_done/_obj_fail clear it straight
        after, and the booth needs the KIND and the STAKE to react in the right
        terms ('that's the podium secured') rather than a generic 'job done'."""
        o = self._obj or {}
        self._obj_booth = (event, o.get("kind", ""),
                           o.get("target_name", ""), now,
                           obj_stake(o.get("kind", ""), o.get("goal_pos")))
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
        # THE PRIZE the objective is worth — 'the win', 'the podium', 'P4'. This
        # is what the driver asked for: the engineer naming the STAKE ("you can
        # get this podium, keep pushing") instead of a bare gap/lap readout. Only
        # set when there's a real position prize; None -> no stakes nudge.
        gp = o.get("goal_pos")
        pstake = ("the win" if (gp == 1 or kind == "leadhome")
                  else "the podium" if gp in (2, 3)
                  else "P%d" % gp if gp else None)
        kw = {"drv": o.get("target_name") or "", "pos": me.place,
              "laps": lap_word, "stake": pstake or "the target"}
        advice = {"chase": "obj_advice_chase", "position": "obj_advice_chase",
                  "defend": "obj_advice_defend", "damage": "obj_advice_defend",
                  "tyres": "obj_advice_tyres", "clean": "obj_advice_clean",
                  "leadhome": "obj_advice_leadhome",
                  "consistency": "obj_advice_consistency"}
        attack = ("chase", "position", "recover")
        holdk = ("defend", "damage", "leadhome", "tyres")
        # ROTATE three flavours of check-in so the engineer isn't a one-note
        # "keep it up": real ADVICE (how to do it), the STAKES (what it's worth),
        # and a live TREND read (how it's going). Each nudge advances the dial so
        # all three get an airing over an objective's life.
        self._obj_nudge_i = getattr(self, "_obj_nudge_i", 0) + 1
        slot = self._obj_nudge_i % 3
        # last lap of any objective — always worth a "bring it home", and never
        # buried under coaching or stakes talk
        if laps_left is not None and laps_left <= 1:
            cat = "obj_nudge_nearly"
        elif slot == 0 and kind in advice:
            cat = advice[kind]                   # kind-specific coaching
        elif slot == 1 and pstake and kind in attack:
            cat = "obj_nudge_stakes_go"          # "you can get this podium"
        elif slot == 1 and pstake and kind in holdk:
            cat = "obj_nudge_stakes_hold"        # "the podium's yours to lose"
        elif kind in ("chase", "position"):
            cat = ("obj_nudge_closing" if gtrend == -1
                   else "obj_nudge_slipping" if gtrend == 1
                   else "obj_nudge_holding")     # steady: "keep chipping away"
        elif kind in ("defend", "damage"):
            # "here he comes, defend hard" only when the car behind is ACTUALLY
            # on you — closing AND within striking distance. A gap that's shrinking
            # from 1.9s is not a threat yet (the reported cry-wolf), so that reads
            # as the calmer holding check-in instead.
            _gb = o.get("_gap")
            threatened = (gtrend == -1 and _gb is not None and _gb < STRIKE_GAP)
            cat = "obj_nudge_threat" if threatened else "obj_nudge_holding"
        elif kind in ("leadhome", "clean", "tyres", "recover", "consistency"):
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
        self._obj_mark_resolved(now)
        self._obj_notice("met", now)
        self._obj_result_set(True, now)
        self._obj = None
        self._obj_last_t = now
        self._obj_met += 1
        return (cat, kw)

    def _obj_fail(self, now, cat, kw):
        self._obj_mark_resolved(now)
        self._obj_notice("miss", now)
        self._obj_result_set(False, now)
        self._obj = None
        self._obj_last_t = now
        return (cat, kw)

    def _obj_mark_resolved(self, now):
        """Remember that this exact job against this exact driver has just been
        answered, so _obj_offer doesn't hand it straight back (OBJ_REPEAT_CD)."""
        o = self._obj
        if o:
            self._obj_recent[(o["kind"], o.get("target_slot"))] = now

    def _obj_too_soon(self, now):
        """True while the active objective is too young to be called MET.

        Guards the closing-laps path in particular: `immediate` deliberately
        skips every hysteresis hold at the flag (there is no 'later' to wait
        for), which also meant a defend offered at 1.5s could bank itself the
        moment the gap touched 2.2s — set and won inside six seconds, then
        re-offered and won again. A target has to have been a target for a
        while to be worth congratulating."""
        o = self._obj
        return bool(o) and (now - o.get("set_at", 0.0)) < OBJ_MIN_LIFE

    @staticmethod
    def _obj_gap_text(g):
        """Spoken/HUD form of a gap target: '2s', '2.5s'. One helper so the
        card and the radio call can never disagree about the number."""
        g = float(g)
        return f"{g:.0f}s" if g.is_integer() else f"{g:.1f}s"

    def _obj_repeat_blocked(self, kind, slot, now):
        """True if this (kind, driver) was resolved too recently to re-offer."""
        t = self._obj_recent.get((kind, slot))
        return t is not None and (now - t) < OBJ_REPEAT_CD

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

        # NEVER SHOW A TARGET THE DRIVER WAS NEVER GIVEN. _obj_say is the set
        # line waiting to be drained by the engineer; if it is STILL sitting
        # there long after the objective was set, the radio never even got to
        # queue it (measured: a defend set at 18:31:39 was not queued until
        # 18:31:50 and aired at 18:32:12 — 33s, by which time the player had
        # spun and the numbers were fiction). Announcing it then is worse than
        # not setting it, and leaving the card up is a target nobody was told
        # about, so both go and the next offer comes round with live numbers.
        if (self._obj and getattr(self, "_obj_say", None)
                and now - self._obj.get("set_at", now) > OBJ_SET_STALE_S):
            self._obj = None
            self._obj_say = None
            self._obj_last_t = now
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
                else "LIM" if k == "clean" else "TYR" if k == "tyres"
                else "=" if k == "consistency" else "GO")
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
        # JUST DID THAT ONE. Without this the repeatable kinds (defend, chase,
        # position) loop against the same driver for the rest of the race: the
        # situation that produced the objective is still the situation the
        # moment it resolves, so the very next offer is identical. Staying
        # quiet is better than asking for the same job a fourth time.
        if self._obj_repeat_blocked(o["kind"], o.get("target_slot"), now):
            return None
        # RACE ENDING: don't hand out a fresh multi-lap target with the flag
        # about to fall — "hold P5 for 4 laps" with two laps of time left is the
        # reported bug. A closing-laps push (its own laps already clamped to
        # what's left) is fine; anything asking for 2+ laps is not. Also clamp
        # every deadline to the laps that will actually be run.
        o["laps"] = max(1, min(o.get("laps", 1), laps_left))
        if self._obj_race_ending(s, order) and o["laps"] > 1:
            return None
        o["lap0"] = me.completed_laps
        o["gap0"] = self.interval.get(vslot)
        o["set_at"] = now
        # DIAGNOSTIC. Reported: targets whose deadline outruns the race ("close
        # the gap in 4 laps" with 3 left, "hold to the line" on a 3-lap target
        # with 4 to run). The deadline IS clamped to laps_left just above, so
        # either laps_left is wrong or the phrasing implies the flag when the
        # target ends sooner — and the transcript alone cannot tell those
        # apart. Record what the maths actually saw, so the next race decides
        # it instead of me guessing.
        try:
            from tts import _log as _objlog
            _lead = order[0].completed_laps if order else -1
            _objlog(f"obj SET kind={o['kind']} laps={o['laps']} "
                    f"laps_left={laps_left} total={s.number_of_laps} "
                    f"lead_done={_lead} my_done={me.completed_laps} "
                    f"rem={getattr(s, 'session_time_remaining', 0):.0f}s "
                    f"white={getattr(getattr(s, 'flags', None), 'white', 0)} "
                    f"hud={o.get('hud','')!r}")
        except Exception:
            pass
        o["_new_until"] = now + 6.0      # HUD shows a NEW TARGET flash
        self._obj = o
        self._obj_notice("set", now)
        self._obj_count += 1
        self._obj_kinds = getattr(self, "_obj_kinds", set()) | {o["kind"]}
        kw = {"drv": o["target_name"], "laps": o["laps"],
              "pos": o.get("goal_pos") or me.place,
              # match the HUD exactly: a 2.5s chase target announced as "2s"
              # (%.0f) contradicted the card the driver was looking at
              "gap": (self._obj_gap_text(o["gap_target"])
                      if o.get("gap_target") else "a second")}
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
            o["_badge"] = ("=" if o["kind"] == "consistency"
                           else "PB" if o["kind"] == "pb" else "POLE")
            done = laps - o["lap0"]
            if o["kind"] == "consistency":
                # practice rhythm drill: each new lap checked against the band
                o["_prog"] = max(0.0, min(1.0, o.get("_ok_laps", 0) / o["laps"]))
                if me.completed_laps > o.get("_last_lap_n", o["lap0"]):
                    o["_last_lap_n"] = me.completed_laps
                    rl = getattr(self, "recent_laps", {}).get(vslot) or []
                    last = rl[-1] if rl else None
                    if last and last > 0:
                        if abs(last - o["_ref"]) > o["_band"]:
                            return self._obj_fail(now, "obj_miss_consistency", {})
                        o["_ok_laps"] = o.get("_ok_laps", 0) + 1
                if o.get("_ok_laps", 0) >= o["laps"]:
                    return self._obj_done(now, "obj_met_consistency", {})
                return None
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

        is_quali = (s.session_type == 1)
        # PRACTICE gets its own goals — it is about learning the car, not the
        # grid, so 'close on pole' makes no sense here (that's a QUALI target).
        # A CONSISTENCY drill is the practice staple: string laps together
        # within a tight band. Offered once a reference pace exists.
        if not is_quali:
            recent = getattr(self, "recent_laps", {}).get(vslot) or []
            recent = [l for l in recent if l and l > 0]
            if len(recent) >= 2 and not self._obj_seen("consistency"):
                ref = self._obj_pace(vslot) or recent[-1]
                band = max(0.6, ref * 0.015)
                self._obj = {"kind": "consistency", "target_slot": vslot,
                             "target_name": "", "goal_pos": None,
                             "gap_target": None, "laps": 4, "_ref": ref,
                             "_band": band, "_last_lap_n": laps, "_ok_laps": 0,
                             "lap0": laps, "_new_until": now + 6.0,
                             "_quali": True,     # resolved in _obj_quali, not race
                             "hud": f"Consistent laps (±{band:.1f}s)"}
                self._obj_count += 1
                self._obj_kinds = getattr(self, "_obj_kinds", set()) | {"consistency"}
                return ("obj_set_consistency", {"laps": 4})

        pole_t = self._obj_pole_time(order, vslot) if is_quali else None
        # CLOSE ON POLE — QUALI only, and only when the gap is small enough
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
