"""Track intelligence: EVERY circuit the engine has corner tips for must also
have history (TRACK_FACTS), analysis (TRACK_COACH) and pundit colour
(TRACK_PUNDIT_BY_TRACK). Keys must be substrings of the REAL track names (the
'brandshatch' vs 'brands hatch' bug class), the pundit must be track-specific on
known circuits and varied-generic otherwise, and the generic pool must not be
the old all-'history' set."""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"  # tests: no disk deck state

import sys
sys.path.insert(0, r"D:\R3EOverlay")
from r3e_overlay import Overlay
from lines import (TRACK_TIPS, TRACK_FACTS, TRACK_COACH, TRACK_PUNDIT,
                   TRACK_PUNDIT_BY_TRACK, CORNER_NAMES, SHORT_TRACK)

o = object.__new__(Overlay)
o._last_line = {}

# duplicate aliases that point at the same venue as another key (fine to skip in
# the coverage check — they exist only as extra name-substring matches)
ALIASES = {"panorama"}                      # == bathurst


def pundit(trk):
    return o._track_pundit(trk)


print("===== TRACK INTELLIGENCE COVERAGE =====")
tips = set(TRACK_TIPS) - ALIASES

# A) every track with corner tips also has history, analysis and pundit colour
miss_facts = sorted(tips - set(TRACK_FACTS))
miss_coach = sorted(tips - set(TRACK_COACH))
miss_pun = sorted(tips - set(TRACK_PUNDIT_BY_TRACK))
assert not miss_facts, f"tracks with tips but NO history facts: {miss_facts}"
assert not miss_coach, f"tracks with tips but NO analysis coaching: {miss_coach}"
assert not miss_pun, f"tracks with tips but NO pundit colour: {miss_pun}"
print(f"  [coverage] all {len(tips)} tip'd circuits have facts+coach+pundit: OK")

# B) THE BUG CLASS: every keyed dict's keys must actually MATCH a real track name.
#    TRACK_TIPS and SHORT_TRACK keys are validated against real names in-game, so
#    any track-keyed dict using a key outside that set (e.g. smushed 'brandshatch'
#    instead of 'brands hatch') would never fire.
valid_keys = set(TRACK_TIPS) | set(SHORT_TRACK)
for name, d in (("TRACK_FACTS", TRACK_FACTS), ("TRACK_COACH", TRACK_COACH),
                ("TRACK_PUNDIT_BY_TRACK", TRACK_PUNDIT_BY_TRACK),
                ("CORNER_NAMES", CORNER_NAMES)):
    bad = sorted(set(d) - valid_keys)
    assert not bad, f"{name} has keys that match no real track name: {bad}"
print("  [keys] no smushed/space-mismatch keys in any track dict: OK")

# C) every recognised circuit yields its OWN pundit colour (blended w/ generic)
genset = set(TRACK_PUNDIT)
for key, pool in TRACK_PUNDIT_BY_TRACK.items():
    poolset = set(pool)
    seen = [pundit(f"Circuit {key} layout") for _ in range(60)]
    for line in seen:
        assert line in (poolset | genset), f"{key}: off-list line {line!r}"
    assert any(l in poolset for l in seen), f"{key}: specific colour never shown"
print(f"  [specific] all {len(TRACK_PUNDIT_BY_TRACK)} circuits -> own colour: OK")

# D) the booth's track-fact picker returns real knowledge for every circuit
for key in tips:
    fact = o._track_fact(f"Grand Prix Circuit {key}")
    assert fact, f"_track_fact returned nothing for {key!r}"
print(f"  [facts] _track_fact returns knowledge for all {len(tips)} circuits: OK")

# E) signature colour + generic fallback + de-historified generic pool
spa = {pundit("Spa-Francorchamps Grand Prix") for _ in range(50)}
assert any("eau rouge" in l.lower() or "ardennes" in l.lower() for l in spa)
unknown = {pundit("Some Fictional Kart Circuit") for _ in range(50)}
assert unknown <= genset, f"unknown track non-generic: {unknown - genset}"
hist = sum(1 for l in TRACK_PUNDIT if "history" in l.lower()
           or "hallowed" in l.lower() or "generations" in l.lower())
assert hist == 0, f"generic pool still leans on 'history' ({hist})"
print("  [variety] signature colour + generic fallback + de-historified: OK")

print(f"\nALL TRACK-TALK CHECKS PASSED ({len(TRACK_FACTS)} circuits with history)")
