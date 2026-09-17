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
# ---- THE THEME ----------------------------------------------------------
#
# RACERTV IS RED. RaceRoom's own colour is red, and this overlay used to wear
# the same cyan-on-blue-black as FACTORtv — which is a different product for
# a different game, and the two reading as one thing helped neither.
#
# CHROME MOVED; MEANING DID NOT. That split is the whole of this block:
#
#   chrome   the rails, the gear, the borders, the ground. Brand. It is red
#            now, and it could be any colour without anyone misreading a
#            timing screen.
#   meaning  PURPLE is session best and GREEN is personal best in every
#            timing display in motorsport. ACCENT is the car you are watching.
#            Re-colouring these to match a brand would make the overlay
#            prettier and harder to READ, so they are untouched.
#
# THE ONE HONEST COST. Red cannot carry cyan's contrast on a black ground:
# the old #39d0e0 measured 9.97:1 against the card, and the best legible red
# is about 5.4:1 — red is simply darker at full saturation. 5.4 still clears
# WCAG AA for body text (4.5:1) with room, so this is a real trade rather than
# a problem, but it is why the accent is a LIFTED red (#ff3b47) and not
# RaceRoom's own #e2001a, which lands at 3.8:1 and is too dim to line a panel
# with. The true brand red is kept below for FILLS, where white sits on top of
# it and the contrast runs the other way.
def _dim_hex(hexc, f):
    """A colour walked towards black by factor `f`. Used where a second,
    quieter version of an accent is wanted -- the clock's seconds, a glow.

    DERIVED RATHER THAN CHOSEN, deliberately: the clock's seconds were a
    hard-coded teal picked to sit beside a cyan accent, and when the accent
    became red the clock went two-tone. Anything that is "the accent, but
    quieter" should be computed from the accent so it cannot fall out of step.
    """
    h = str(hexc or "").lstrip("#")
    try:
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return hexc
    cl = lambda v: max(0, min(255, int(v * f)))
    return "#%02x%02x%02x" % (cl(r), cl(g), cl(b))


BRAND_RED = "#e2001a"    # RaceRoom's own red: for fills, never for thin lines
PANEL_BG = "#120e0e"
PANEL_OUTLINE = "#3a2b2d"
CARD_BG = "#16100f"
CARD_BG2 = "#0e0a0a"
CARD_BORDER = "#3d2a2c"
# PASTEL, ASKED FOR: "the red on the overlay is too much". Softer AND more
# legible — a pastel red measures 7.0:1 on the card against 5.35:1 for the
# saturated one, because lighter reds carry more luminance.
HEADER_ACCENT = "#e8807f"
CONTROL_BG = "#2a1e20"   # the slab behind sliders, arrows and pills
TEXT = "#f2f4f7"
DIM = "#9aa3ad"
# THE SHIFT LIGHT. Purple, and only for the shift cue — see speedo.py.
SHIFT_PURPLE = "#b36bff"
# A softened on-air/warning red for the LIVE tally, the final-lap and penalty
# chips. Still unmistakably red: these are warnings, not furniture.
TALLY_RED = "#f2575a"
ACCENT = "#ffd23f"      # viewed/focused car — MEANING, left alone
# THE LEADER WAS THE LAST BLUE. It is not a timing convention the way purple
# and green are — nothing is lost by moving it, and a cool blue was the one
# thing still pulling the palette back towards FACTORtv. Platinum reads as
# "first" without competing with the amber of the car you are watching.
LEADER = "#e9ecef"
PURPLE = "#c77dff"      # session best (fastest) — MEANING, left alone
GREEN = "#69db7c"       # personal best — MEANING, left alone
# WARM, BUT NOT THE CHROME RED. The engineer is a person on the radio, not a
# panel edge, and painting him the same red as the furniture would lose him
# against it. Coral keeps him in the warm family and clear of the booth's
# yellow.
# RE-SEPARATED FOR THE PASTEL CHROME. Coral was distinct from a SATURATED
# red; next to a pastel one it measured 1.19:1 — the same colour. The
# warm end of the wheel is crowded (red, orange, yellow sit ~22 degrees
# apart), so the engineer separates by LIGHTNESS instead: a pale apricot,
# unmistakable against both the chrome and the commentator's yellow.
ENGINEER_COLOR = "#ffc9a3"   # your engineer's radio colour (not a driver)
COMMENTATOR_COLOR = "#ffcf33"  # broadcast booth caption colour
# THE ANALYST GETS HIS OWN, AND IT IS WARM. This was a hard-coded
# "#7fd1ff" sitting inside the caption renderer — a light blue chosen
# to pair with the old cyan chrome, and the last obviously-blue thing
# left on screen after the retheme. Named here so the next palette
# change finds it instead of missing it the way this one did.
#
# Three booth-adjacent voices, three separations: the commentator is
# yellow, the analyst rose, the engineer coral. None of them is the
# chrome red, or they would vanish into the furniture.
# Rose sat 1.02:1 from the pastel chrome. Orchid is 50 degrees away.
PUNDIT_COLOR = "#e58fd6"       # the analyst's caption colour
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
    # THE NEW TELEMETRY BEATS. `fuel_burn` is a number with a job attached,
    # so it is WORRIED rather than neutral -- it only ever fires when the
    # sums do not currently work. The two "ok" beats are the only good news
    # the pit wall has, and they are delivered as such.
    "fuel_burn": "worried", "fuel_ok": "happy", "tyres_ok": "happy",
    "held_on": "fired", "retaken": "neutral",
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
