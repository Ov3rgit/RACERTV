"""The RACE engineer is track-aware THROUGH the lap: as the player crosses into
a new sector he occasionally gives a track-specific heads-up ('Into sector 2 now
— <tip>'). It must name a real sector, carry a real track tip, only fire on the
sector rising edge, and stay quiet on an unknown track / in the pits."""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"  # tests: no disk deck state

import sys
sys.path.insert(0, r"D:\R3EOverlay")
import r3e_data as R
from r3e_overlay import Overlay
from lines import TRACK_TIPS, TRACK_SECTOR_TIPS
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])

# a section tip may come from the per-SECTOR curated notes (preferred) or the
# generic track-tip pool (fallback)
LAGUNA_TIPS = set(TRACK_TIPS["laguna"])
for _pool in TRACK_SECTOR_TIPS["laguna"].values():
    LAGUNA_TIPS |= set(_pool)


def setup(track="Laguna Seca"):
    o = headless_overlay(fake_tts=True)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    s = make_shared(2, ncars=4, track=track)
    for i in range(s.num_cars):
        s.all_drivers_data_1[i].car_speed = 55.0
        s.all_drivers_data_1[i].completed_laps = 3
    drive(o, s, 3)
    age_intro(o)
    drive(o, s, 1)
    return o, s


def cycle_sectors(o, s, laps=12):
    """Drive the player repeatedly around sectors 1->2->3, relaxing cooldowns so
    the (rare) proactive section call has chances to land."""
    me = s.all_drivers_data_1[0]
    for _ in range(laps):
        for sec in (1, 2, 3):
            me.track_sector = sec
            o._eng_cd -= 40.0
            o._eng_section_cd -= 200.0
            drive(o, s, 1)


def section_lines(o):
    return [t for p, t in o.tts.spoken if p == "ENGINEER"
            and "sector" in t.lower()
            and any(tip in t for tip in LAGUNA_TIPS)]


print("===== PROACTIVE SECTION COACHING =====")

# A) on a known track, the engineer gives sector-tagged track tips
o, s = setup("Laguna Seca")
cycle_sectors(o, s, 16)
sec = section_lines(o)
assert sec, "engineer never gave a proactive section tip on a known track"
# it must name a sector number that exists and carry a real Laguna tip
assert any(("sector 1" in t.lower() or "sector 2" in t.lower()
            or "sector 3" in t.lower()) for t in sec), \
    f"section line didn't name a sector: {sec[0]}"
print(f"  [known] sector-tagged track tip fired: OK -> {sec[0][:70]}")

# B) it only fires on a sector CHANGE, not while parked in one sector
o, s = setup("Laguna Seca")
me = s.all_drivers_data_1[0]
me.track_sector = 2
before = len(o.tts.spoken)
for _ in range(20):
    o._eng_cd -= 40.0
    o._eng_section_cd -= 200.0
    drive(o, s, 1)               # sector never changes -> no rising edge
assert not section_lines(o), "section tip fired without a sector change"
print("  [edge] no sector change -> no section tip: OK")

# C) unknown track -> no track tip to give -> silent
o, s = setup("Fictional Test Circuit")
cycle_sectors(o, s, 16)
assert not [t for p, t in o.tts.spoken if p == "ENGINEER"
            and t.lower().startswith(("sector", "into sector", "heads up for sector",
                                      "coming into sector", "through sector"))], \
    "section coaching fired on a track with no tips"
print("  [unknown] no tips for track -> silent: OK")

print("\nALL SECTION-COACHING CHECKS PASSED")
