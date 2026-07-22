"""COHESION: a hard-fought win is called a DUEL, not a flawless cruise.

Even when the leader is never headed (a true 'wire' win), if a rival hounded them
within ~1.5s for a real cumulative stretch of the race, the finish should read
'held off X to the flag', not 'lights to flag, flawless'. The booth accumulates
lead-pressure seconds and _lead_challenger reads them at the flag.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import os
import sys

sys.path.insert(0, r"D:\R3EOverlay")
import r3e_data as R                                        # noqa: E402
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "smoke.py")).read()
exec(_src.split('run_session("RACE"')[0])
from lines import COMMENTARY_LINES                          # noqa: E402
from overlay_common import _safe_format                     # noqa: E402


# ---- 1. _lead_challenger reads the accumulated pressure -------------------
o = headless_overlay(fake_tts=True)
s = make_shared(2, ncars=6)
order = sorted((d for d in s.all_drivers_data_1[:6]), key=lambda d: d.place)
win = order[0]
chal = order[1]
wsl, csl = win.driver_info.slot_id, chal.driver_info.slot_id

o._lead_press = {(wsl, csl): 12.0}         # only a brief scrap
assert o._lead_challenger(wsl, order) is None, (
    "a brief 12s scrap was wrongly called a race-long duel")
print("  a brief scrap is NOT a duel: OK")

o._lead_press = {(wsl, csl): 70.0}         # hounded for over a minute
assert o._lead_challenger(wsl, order) == o._dname(chal), (
    "a genuine race-long challenger was not identified")
print(f"  a sustained challenger IS a duel: OK -> {o._dname(chal)}")

# a duplicate-named challenger is not named against themselves
_orig = o._dname
o._dname = lambda d, _o=_orig: ("SAME" if d.driver_info.slot_id in (wsl, csl)
                                else _o(d))
assert o._lead_challenger(wsl, order) is None, (
    "named a same-named challenger — 'held off X to beat X'")
o._dname = _orig
print("  a same-named challenger is skipped: OK")


# ---- 2. end to end: a hounded 'wire' winner gets win_duel, not win_wire ---
def build_finish(pressure_secs):
    o = headless_overlay(fake_tts=True)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    s = make_shared(2, ncars=6)
    s.number_of_laps = 3
    for i, d in enumerate(s.all_drivers_data_1[:6]):
        d.car_speed = 55.0
        d.place = i + 1
        d.completed_laps = 2
    ldr = s.all_drivers_data_1[0]             # P1, our winner
    ch = s.all_drivers_data_1[1]              # P2, the challenger
    drive(o, s, 3); age_intro(o)
    # winner led every lap (wire-eligible) and was hounded by P2
    wsl = ldr.driver_info.slot_id
    o.grid_place[wsl] = 1
    o._race_story[wsl] = {"best": 1, "worst": 1, "now": 1}
    o._lead_press = {(wsl, ch.driver_info.slot_id): pressure_secs}
    # take the flag
    for i in range(6):
        s.all_drivers_data_1[i].completed_laps = 3
    ldr.finish_status = 1
    s.flags.checkered = 1
    o._comm_cd = 0.0
    before = len(o.tts.spoken)
    drive(o, s, 2)
    return " || ".join(t for _p, t in o.tts.spoken[before:]), o._dname(ch)


duel_words = ("EARNED it", "duel", "fight for every", "no cruise", "at bay",
              "does NOT crack", "glued to the leader", "made them fight")
# phrases UNIQUE to the flawless-cruise framing (note: 'lights to flag' also
# appears in a duel line — 'glued to the leader from lights to flag' — so it is
# not a marker of the flawless framing on its own)
wire_words = ("flawless", "never headed", "never threatened", "domination",
              "total control", "wire to wire", "gave the rest a sniff")

said, chname = build_finish(80.0)            # hounded all race
assert any(w.lower() in said.lower() for w in duel_words), (
    "a hard-fought win was not framed as a duel:\n" + said)
assert not any(w.lower() in said.lower() for w in wire_words), (
    "a hard-fought win was STILL called flawless/lights-to-flag:\n" + said)
print("  a hounded winner -> win_duel (names the challenger): OK")

said2, _ = build_finish(5.0)                 # led untroubled
assert any(w.lower() in said2.lower() for w in wire_words), (
    "an untroubled wire win lost its 'lights to flag' framing:\n" + said2)
print("  an untroubled winner -> still 'lights to flag': OK")

# every win_duel line formats cleanly
for tpl in COMMENTARY_LINES["win_duel"]:
    out = _safe_format(tpl, {"drv": "Alonso", "oth": "Hamilton"})
    assert "{" not in out, f"win_duel line failed to format: {out}"
print("  all win_duel lines format cleanly: OK")

print("\nDUEL-WIN COHESION CHECKS PASSED")
