"""COHESION: 'lights to flag' must mean the winner was NEVER HEADED.

A real Portimao finish called 'Lights to flag — a flawless victory, pole, lead,
win' for a leader after the booth had spent the whole race narrating a fight for
P1. The 'wire' arc allowed worst confirmed place == 2, i.e. the leader HAD lost
the lead — so the flawless-lights-to-flag call flatly contradicted the race. It
now requires worst == 1 (never headed); a leader who dropped and won it back gets
the generic win call instead.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import os
import sys

sys.path.insert(0, r"D:\R3EOverlay")
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "smoke.py")).read()
exec(_src.split('run_session("RACE"')[0])

o = headless_overlay(fake_tts=True)
sl = 7
o.grid_place = {sl: 1}                 # started on pole

# led every lap -> 'wire' is honest
o._race_story = {sl: {"best": 1, "worst": 1, "now": 1}}
arc, _ = o._narrative_arc(sl, place=1)
assert arc == "wire", f"a never-headed pole winner should be 'wire': {arc}"
print("  never headed (worst P1) -> 'lights to flag': OK")

# lost the lead at some point (worst P2), won it back -> NOT 'wire'
o._race_story = {sl: {"best": 1, "worst": 2, "now": 1}}
arc, _ = o._narrative_arc(sl, place=1)
assert arc != "wire", (
    f"a leader who was headed (dropped to P2) was still called 'lights to flag': {arc}")
print("  dropped to P2 then won -> NOT 'lights to flag': OK")

print("\nWIRE-NARRATIVE COHESION CHECK PASSED")
