# -*- coding: utf-8 -*-
"""
Shared foundation for the RacerTV overlay.

Broadcast theme colours, the per-category tuning tables (how hyped the booth
gets per event, how often the pundit chimes in, radio emotion mapping) and
the small pure helpers everything needs.

This module exists so the engine can be split into mixins: overlay_booth,
overlay_radio and overlay_draw all import from HERE, and this imports nothing
of theirs, so there is no cycle. Keep it that way — constants and pure
functions only. Anything that touches win32 handles, tk widgets or Overlay
state belongs in the engine, not here.
"""
import re as _re
import threading



# STRIKING DISTANCE — the gap (seconds) inside which a car behind can genuinely
# make a move stick (a tow onto the straight, then a lunge under braking). Beyond
# it, "he's about to pounce / shut the door" is crying wolf, which the driver
# flagged from a full second back. Shared by the engineer's defend call and the
# objective's threat nudge so both stay honest. Kept deliberately tight.
STRIKE_GAP = 0.8

CHROMA = "#010102"      # fully transparent key color (must be unused elsewhere)
WIN_ALPHA = 0.86        # whole-window opacity: solid SOLID dark panels (no dotty
# TRUE GLASS BACKGROUNDS.
#
# tk has no per-item alpha, and a window's -alpha fades TEXT as much as the
# background, so neither can give "see-through panel, crisp numbers". Stipple
# can, but it dithers and looks cheap.
#
# The trick: alpha is per-WINDOW, so use TWO stacked windows per panel. A
# backing window holds only the panel BODY at GLASS_ALPHA; the content window
# sits exactly on top at full opacity, with the body area left as the chroma
# key so the glass shows through it. Result: smoothly translucent background,
# 100% solid text and borders, no dithering.
# DEFAULT OFF. The two-window glass looks right in isolation, but in the game
# it has caused a run of visual problems: flicker, and panels that RESIZE
# (radio cards appearing, the caption growing with its text) show a one-frame
# mismatch because the content window repaints immediately while its glass
# layer only repaints on flush. Until that is solved properly, the known-good
# single-window rendering is the default. Set True to try it again.
GLASS = False
GLASS_ALPHA = 0.58       # backing-window opacity: lower = more see-through
BG_STIPPLE = ""          # legacy dither fallback; keep empty
PANEL_STIPPLE = ""        # solid panel backgrounds (stipple looked pixelated behind
PANEL_ALPHA = 0.55        # (legacy whole-window alpha; superseded by stipple+CHROMA)
PANEL_BG = "#0c1014"
PANEL_OUTLINE = "#2b313b"
CARD_BG = "#0d1320"
CARD_BG2 = "#0a0d12"
CARD_BORDER = "#2a3440"
HEADER_ACCENT = "#39d0e0"
TEXT = "#f2f4f7"
DIM = "#9aa3ad"
ACCENT = "#ffd23f"      # viewed/focused car
LEADER = "#5cc8ff"
PURPLE = "#c77dff"      # session best (fastest)
GREEN = "#69db7c"       # personal best
ENGINEER_COLOR = "#39d0e0"   # your engineer's radio colour (not a driver)
COMMENTATOR_COLOR = "#ffcf33"  # broadcast booth caption colour
_LEET = {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "8": "b", "9": "g"}
CAT_INTENSITY = {
    "start": 1, "overtake": 2, "overtake_long": 2, "leadchange": 2, "fastlap": 1,
    "overtake_multi": 2,
    "spin": 2, "battle": 2, "battle_mid": 1, "battle_sustained": 2,
    "pit": 0, "lastlap": 2, "win": 2,
    "win_charge": 2, "win_comeback": 2, "win_wire": 2, "win_duel": 2,
    "leadchange_charge": 2, "leadchange_comeback": 2,
    "overtake_charge": 2, "overtake_comeback": 2,
    "second": 1, "third": 1, "summary": 1, "closing": 1, "pulling_away": 0,
    "recovery": 1, "podium_lock": 0, "penalty": 1, "yellow": 1, "analysis": 0,
    "analysis_strategy": 0,
    "lap_milestone": 0, "standings": 0, "praise": 0, "criticism": 0,
    "time_remaining": 1, "race_duration": 1,
    "track_generic": 0, "track_fact": 0, "crosstalk_q": 0, "stat": 0,
    "obj_booth": 0, "obj_booth_close": 1, "obj_booth_done": 1,
    "obj_booth_brief": 1, "obj_booth_met": 1, "obj_booth_miss": 1,
    "car": 0, "pass_clean": 1, "midpack": 0,
    "late": 2, "final_lap": 2,
    "pregrid": 1,
    "quali_start": 1, "practice_start": 0, "quali_fastlap": 1, "quali_pole": 2,
    "quali_improve": 0, "quali_standings": 0, "quali_final": 1, "practice_note": 0,
    "session_colour": 0, "lap_report": 1, "lap_report_slow": 0,
    "insight_lead_slim": 1, "insight_lead_big": 0, "insight_podium_fight": 1,
    "insight_field_spread": 0, "insight_laps_left": 1, "insight_time_left": 1,
    "offtrack": 2, "offtrack_ack": 0, "offtrack_more": 2, "offtrack_chaos": 2,
    "ranwide": 1,
    "offtrack_cut": 2, "offtrack_late": 2, "broadcast": 0, "retake": 2,
    "arc_cost": 1, "arc_recovered": 1, "shuffle": 2, "driverstory_q": 0,
    "lore_q": 0, "lore_a": 0, "lore_q_rally": 0, "lore_a_rally": 0,
    "signoff": 1, "quali_goals": 0, "booth_joke": 0,
}
# What the pit wall has visibly asked for, per objective kind — slotted into
# the booth's obj_booth_brief lines ("{drv} has been asked {brief}"). The booth
# never quotes numbers off a private radio call; it describes what anyone
# watching the driver could infer. {tgt} is the target driver's name.
OBJ_BRIEF = {
    "position": "to find a way past {tgt} for {stake}",
    "chase":    "to close that gap to {tgt} down",
    "defend":   "to defend {stake}",
    "damage":   "to hold on to {stake} with a wounded car",
    "clean":    "to keep it clean and stay out of trouble",
    "recover":  "to fight back to {stake}",
    "tyres":    "to nurse the tyres and hold {stake}",
    "leadhome": "to bring it home for {stake}",
    "consistency": "to string together consistent laps",
}
OBJ_BRIEF_DEFAULT = "for something specific over these next few laps"


def obj_stake(kind, goal_pos):
    """A short noun phrase for what an objective is WORTH, so the booth and the
    engineer can name the prize ('the podium', 'the win', 'P4') instead of a
    generic 'the target'. `goal_pos` is the place being raced for or held.

    Shared by the engineer's mid-objective nudges and the booth's set/met/miss
    reactions so the two always frame the same target the same way."""
    if kind == "leadhome" or goal_pos == 1:
        return "the win"
    if goal_pos in (2, 3):
        return "the podium"
    if kind == "clean":
        return "a clean run"
    if kind == "tyres":
        return "the tyres to the flag"
    if kind == "consistency":
        return "the rhythm"
    if kind == "chase":
        return "that gap"
    if goal_pos:
        return "P%d" % goal_pos
    return "the target"
PENALTY_SPOKEN = {0: "drive-through penalty", 1: "stop-and-go penalty",
                  2: "pit-stop penalty", 3: "time penalty", 4: "slow-down penalty",
                  5: "disqualification"}
RECAP_CATS = {"driverstory_q", "lore_q", "lore_q_rally", "lore_a",
              "lore_a_rally", "storyarc"}
PUNDIT_AFTER = {"overtake": 0.7, "overtake_long": 0.8, "spin": 0.75,
                "overtake_multi": 0.85,   # a double pass always earns a reaction
                "leadchange": 0.7, "win": 0.0, "battle": 0.5, "battle_mid": 0.4,
                "overtake_charge": 0.7, "overtake_comeback": 0.7,
                "leadchange_charge": 0.7, "leadchange_comeback": 0.7,
                "battle_sustained": 0.6,
                "penalty": 0.7, "yellow": 0.6, "closing": 0.3, "recovery": 0.5,
                "fastlap": 0.4, "analysis": 0.45, "standings": 0.3,
                "lap_milestone": 0.3}
ENG_EMOTION = {
    "start": "fired", "start_gain": "happy", "start_loss": "worried",
    "win": "happy", "podium": "happy", "recovery": "fired",
    "slip": "sad", "finish_strong": "happy", "finish_points": "neutral",
    "finish_low": "sad", "fastest": "smug", "lastlap": "fired", "pit": "neutral",
    "lead": "smug", "gained": "happy", "lost": "sad", "catching": "fired",
    "dropping": "worried", "defending": "worried", "clear": "smug",
    "encourage": "neutral", "enc_top": "smug", "enc_mid": "neutral",
    "enc_back": "worried", "info_ahead": "neutral", "info_behind": "neutral",
    "nextlap": "worried", "tyres_gone": "worried",
    "tyre_cold": "neutral", "tyre_hot": "worried",
    "tyre_hot_traffic": "worried", "brake_hot": "worried",
    "engine_hot": "worried", "engine_hot_dmg": "worried",
    "gained_where": "happy", "gained_multi": "happy",
    "section_ahead": "neutral",
    "warn_offtrack": "worried", "warn_limits_repeat": "worried",
    "warn_limits_serious": "angry", "incident_tally": "worried",
    "warn_points": "worried", "points_high": "worried",
    "points_critical": "angry",
    # mid-objective progress nudges + the supersede line
    "obj_nudge_closing": "fired", "obj_nudge_slipping": "worried",
    "obj_nudge_threat": "worried", "obj_nudge_nearly": "fired",
    "obj_supersede_gained": "happy", "obj_nudge_holding": "neutral",
    "obj_nudge_stakes_go": "fired", "obj_nudge_stakes_hold": "worried",
    "obj_met_defend_clear": "happy",
    "obj_withdraw_pit": "neutral",
    "obj_advice_chase": "fired", "obj_advice_defend": "worried",
    "obj_advice_tyres": "neutral", "obj_advice_clean": "worried",
    "obj_advice_leadhome": "neutral",
    "obj_set_consistency": "neutral", "obj_met_consistency": "happy",
    "obj_miss_consistency": "sad", "obj_advice_consistency": "neutral",
    "obj_withdraw_race": "fired", "obj_withdraw_pitstop": "neutral",
}
DRIVER_COLORS = [
    "#ff3b3b", "#ff7a1a", "#ffb000", "#ffe24d", "#b6e02e",
    "#4fd13a", "#16c98a", "#00c2c7", "#29a8ff", "#4f7bff",
    "#8a6dff", "#b964ff", "#e85aff", "#ff5db4", "#ff6f61",
    "#c98a3c", "#88c057", "#5ad1b0", "#c3a6ff", "#9fd8ff",
]
YELLOWT = "#e6c84a"     # slower than best
CYAN = "#4dd6e0"        # push-to-pass
TYRE_COLORS = {2: "#e03131", 3: "#f1c40f", 4: "#e9ecef",
               0: "#4dabf7", 1: "#69db7c"}
ROW_H = 22
MAX_ROWS = 24
CORNER_NBINS = 180      # lap-fraction bins for learning corner positions (2°)
UPDATE_MS = 50          # 20 Hz — snappier event detection + tower updates
_RADIO_LOCK = threading.Lock()
PLACE_CONFIRM_TICKS = 6  # a position must hold this many ticks (~300ms) before
VK_CONTROL, VK_SHIFT, VK_Q, VK_O, VK_E, VK_M = 0x11, 0x10, 0x51, 0x4F, 0x45, 0x4D
VK_D = 0x44
VK_C = 0x43
VK_R = 0x52
VK_LBUTTON = 0x01


_ONE_PLURAL = _re.compile(
    r"(?<!\d)1 (lap|minute|second|corner|tenth|place|position|car|warning|point|degree)s\b")


def _fix_plural(text):
    """Collapse '1 laps'/'1 minutes' -> '1 lap'/'1 minute'. Templates hardcode the
    plural noun (they read right for n>=2), but a race-ending target always clamps
    to a single lap, so the count of 1 was the only ungrammatical case left. The
    lookbehind keeps '11 laps'/'21 laps' untouched; the noun whitelist keeps it
    from mangling anything that legitimately reads '1 ...s'."""
    return _ONE_PLURAL.sub(r"1 \1", text)


def _safe_format(tmpl, kw):
    """str.format that never raises on a missing/extra key (blanks missing)."""
    class _D(dict):
        def __missing__(self, k):
            return ""
    try:
        return _fix_plural(tmpl.format_map(_D(kw)))
    except Exception:
        return tmpl


def _BUBBLE_H(n_lines):
    """Radio bubble height for n message lines (shared by draw_radio + _draw_bubble
    so the stacking maths and the drawn box always agree)."""
    return 40 + 18 * n_lines
