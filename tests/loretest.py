"""Booth LORE: Miles (lead) is an F1 World Champion turned rally man who raced
Schumacher/Barrichello/Häkkinen; Brett (pundit) is a Le Mans/WEC champion who
battled the endurance greats. Lore must be TRACK-FOCUSED (a real memory for
known circuits), drop the right easter-egg names, never sound off-backstory, and
the track keys must match real names (no smushed-key bug)."""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"  # tests: no disk deck state

import sys
sys.path.insert(0, r"D:\R3EOverlay")
from r3e_overlay import Overlay
from lines import (COMMENTARY_LINES, LORE_COMM_BY_TRACK, LORE_PUNDIT_BY_TRACK,
                   TRACK_TIPS, SHORT_TRACK)

o = object.__new__(Overlay)
o._last_line = {}

F1_NAMES = ("schumacher", "barrichello", "häkkinen", "hakkinen", "rubens", "mika",
            "michael")
WEC_NAMES = ("kristensen", "mcnish", "pirro", "lotterer", "capello")

print("===== BOOTH LORE =====")

# A) track keys must be real-name substrings (the brandshatch-bug guard)
valid = set(TRACK_TIPS) | set(SHORT_TRACK)
for name, d in (("LORE_COMM_BY_TRACK", LORE_COMM_BY_TRACK),
                ("LORE_PUNDIT_BY_TRACK", LORE_PUNDIT_BY_TRACK)):
    bad = sorted(set(d) - valid)
    assert not bad, f"{name} has keys matching no real track name: {bad}"
print("  [keys] lore track keys all match real names: OK")

# B) Brett (PUNDIT) on Le Mans -> a track-specific WEC memory appears, and every
#    answer stays within his pool (track memory OR generic endurance lore_a)
allowed_p = set(LORE_PUNDIT_BY_TRACK["le mans"]) | set(COMMENTARY_LINES["lore_a"])
seen = [o._lore_answer("PUNDIT", "Le Mans 24 Hours") for _ in range(80)]
for s in seen:
    assert s in allowed_p, f"off-pool pundit lore: {s!r}"
assert any(s in set(LORE_PUNDIT_BY_TRACK["le mans"]) for s in seen), \
    "no Le Mans-specific pundit memory appeared"
assert any("mulsanne" in s.lower() or "kristensen" in s.lower() for s in seen), \
    "Le Mans lore missing its signature easter eggs"
print("  [pundit] Brett's Le Mans WEC memory + easter eggs: OK")

# C) Miles (COMMENTATOR) on Spa -> an F1-title memory with the right names
allowed_c = set(LORE_COMM_BY_TRACK["spa"]) | set(COMMENTARY_LINES["lore_a_rally"])
seen = [o._lore_answer("COMMENTATOR", "Spa-Francorchamps Grand Prix")
        for _ in range(80)]
for s in seen:
    assert s in allowed_c, f"off-pool lead lore: {s!r}"
assert any(s in set(LORE_COMM_BY_TRACK["spa"]) for s in seen), \
    "no Spa-specific lead memory appeared"
assert any("eau rouge" in s.lower() or "häkkinen" in s.lower()
           or "hakkinen" in s.lower() for s in seen), \
    "Spa lead lore missing its signature easter eggs"
print("  [lead] Miles's Spa F1-title memory + easter eggs: OK")

# D) unknown track -> generic named pools only (still on-backstory)
unk_p = {o._lore_answer("PUNDIT", "Fictional Test Circuit") for _ in range(40)}
unk_c = {o._lore_answer("COMMENTATOR", "Fictional Test Circuit") for _ in range(40)}
assert unk_p <= set(COMMENTARY_LINES["lore_a"]), "pundit unknown-track lore off-pool"
assert unk_c <= set(COMMENTARY_LINES["lore_a_rally"]), "lead unknown-track lore off-pool"
print("  [generic] unknown track -> named generic lore: OK")

# E) BACKSTORY CONSISTENCY: Brett's pools talk endurance; Miles's talk F1/rally.
brett_all = sum(LORE_PUNDIT_BY_TRACK.values(), []) + COMMENTARY_LINES["lore_a"]
miles_all = sum(LORE_COMM_BY_TRACK.values(), []) + COMMENTARY_LINES["lore_a_rally"]
assert sum(any(n in l.lower() for n in WEC_NAMES) for l in brett_all) >= 8, \
    "Brett's lore barely name-drops the endurance greats"
assert sum(any(n in l.lower() for n in F1_NAMES) for l in miles_all) >= 8, \
    "Miles's lore barely name-drops the F1 greats"
# Miles must reference BOTH the F1 title and the later rally chapter somewhere
assert any("champion" in l.lower() or "title" in l.lower() for l in miles_all)
assert any("rally" in l.lower() or "forest" in l.lower() for l in miles_all)
# no crossed wires: Brett never claims an F1 title, Miles never claims Le Mans
assert not any("le mans" in l.lower() and ("i won" in l.lower())
               for l in miles_all), "Miles wrongly claims a Le Mans win"
print("  [backstory] Brett=WEC, Miles=F1-champ-then-rally, no crossed wires: OK")

print("\nALL LORE CHECKS PASSED")
