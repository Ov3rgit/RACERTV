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

# --- tuning ---------------------------------------------------------------
OBJ_MIN_GAP_S = 25.0     # min seconds between one objective resolving and the next
OBJ_SETTLE_LAPS = 2      # no objectives until the race has settled down
OBJ_MARGIN = 0.8         # only offer if it needs <= 80% of the laps available
OBJ_MIN_DELTA = 0.06     # s/lap pace edge below which "catching" is noise
OBJ_MAX_CHASE_GAP = 18.0  # beyond this, a catch is fantasy however good the pace
OBJ_DEFEND_NEAR = 3.5    # a car this close behind is worth defending against


class ObjectiveMixin:
    """See module docstring."""

    # ---- state ----------------------------------------------------------
    def _obj_reset(self):
        self._obj = None            # the active objective, or None
        self._obj_last_t = 0.0      # when the last one resolved (spacing)
        self._obj_count = 0         # how many set this session
        self._obj_met = 0
        self._obj_result = None     # last outcome, for the HUD chip

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

    # ---- offering -------------------------------------------------------
    def _obj_offer(self, s, order, placemap, now):
        """Pick a credible objective, or None. Ordered by how much it matters
        to the player's race — a podium on the table beats a routine chase."""
        vslot = s.vehicle_info.slot_id
        me = next((d for d in order if d.driver_info.slot_id == vslot), None)
        if me is None or me.in_pitlane == 1:
            return None
        laps_left = self._obj_laps_left(s, order)
        if not laps_left or laps_left < 2:
            return None                       # nothing meaningful left to set
        mine = self._obj_pace(vslot)
        if not mine:
            return None                       # no pace read yet — stay quiet
        pos = me.place

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
                    "goal_pos": pos, "laps": min(laps_left, 5),
                    "hud": f"Stay ahead of {self._dname(behind)} (+{hold}s)",
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
                    "laps": min(laps_left, 6),
                    "hud": f"Hold P{pos} from {self._dname(behind)}",
                }
        return None

    # ---- progress / resolution ------------------------------------------
    def _obj_progress(self, s, order):
        """0.0-1.0 for the HUD, or None when it has no meaningful progress."""
        o = self._obj
        if not o:
            return None
        vslot = s.vehicle_info.slot_id
        me = next((d for d in order if d.driver_info.slot_id == vslot), None)
        if me is None:
            return None
        if o["kind"] in ("chase", "position"):
            gap = self.interval.get(vslot)
            start = o.get("gap0")
            if gap is None or not start or start <= o["gap_target"]:
                return None
            span = start - o["gap_target"]
            return max(0.0, min(1.0, (start - gap) / span)) if span > 0 else None
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
        tgt = next((d for d in order
                    if d.driver_info.slot_id == o["target_slot"]), None)
        if tgt is None:
            self._obj = None                  # withdrawn: no verdict on the HUD
            self._obj_last_t = now
            return ("obj_withdraw_gone", {"drv": nm})
        if o["kind"] != "damage" and getattr(self, "_obj_damaged", False):
            self._obj = None
            self._obj_last_t = now
            return ("obj_withdraw_damage", {"drv": nm})

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

        if laps_done >= o["laps"]:                       # ran out of laps
            cat = ("obj_miss_pass" if o["kind"] in ("chase", "position")
                   else "obj_miss_defend")
            return self._obj_fail(now, cat, {"drv": nm})
        return None

    def _obj_result_set(self, ok, now):
        """Latch the outcome so the HUD can show it briefly — the chip must
        agree with what the engineer just said on the radio."""
        o = self._obj or {}
        self._obj_result = {"ok": ok, "hud": o.get("hud", ""),
                            "until": now + 8.0}

    def _obj_done(self, now, cat, kw):
        self._obj_result_set(True, now)
        self._obj = None
        self._obj_last_t = now
        self._obj_met += 1
        return (cat, kw)

    def _obj_fail(self, now, cat, kw):
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
        if s.session_type != 2 or not getattr(self, "_racing", False):
            return None
        vslot = s.vehicle_info.slot_id
        me = next((d for d in order if d.driver_info.slot_id == vslot), None)
        if me is None:
            return None

        if self._obj:                                 # one active at a time
            self._obj["_prog"] = self._obj_progress(s, order)
            return self._obj_check(s, order, placemap, now)

        if me.completed_laps < OBJ_SETTLE_LAPS:
            return None                               # let the race settle
        if now - self._obj_last_t < OBJ_MIN_GAP_S:
            return None
        laps_left = self._obj_laps_left(s, order)
        if not laps_left or laps_left < 2:
            return None
        o = self._obj_offer(s, order, placemap, now)
        if not o:
            return None                               # nothing credible: silence
        o["lap0"] = me.completed_laps
        o["gap0"] = self.interval.get(vslot)
        o["set_at"] = now
        self._obj = o
        self._obj_count += 1
        kw = {"drv": o["target_name"], "laps": o["laps"],
              "pos": o.get("goal_pos") or me.place,
              "gap": f"{o['gap_target']:.0f}s" if o.get("gap_target") else "a second"}
        return (f"obj_set_{o['kind']}", kw)

    def objective_hud(self):
        """(text, progress) for the on-screen objective, or None."""
        o = getattr(self, "_obj", None)
        if not o:
            return None
        return (o["hud"], o.get("_prog"))
