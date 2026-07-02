"""Shuffle-bag line selection: no repeats until a pool is exhausted, the deck
survives a restart (persisted to _heard.json), and a reshuffle never deals the
same line twice in a row across the boundary."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from r3e_overlay import Overlay

TMP = tempfile.mkdtemp()
BAG = os.path.join(TMP, "_heard.json")


def fresh(bag_file=BAG):
    o = object.__new__(Overlay)
    o._BAG_FILE = bag_file
    return o


POOL = [f"line {i}" for i in range(12)]

# 1. full coverage before any repeat, twice over
o = fresh()
for cycle in range(2):
    seen = [o._pick(POOL, ("T", "cat")) for _ in range(len(POOL))]
    assert sorted(seen) == sorted(POOL), f"cycle {cycle}: repeats before exhaustion: {seen}"

# 2. no immediate repeat across the reshuffle boundary (1000 draws, never twice in a row)
o2 = fresh(os.path.join(TMP, "b2.json"))
prev = None
for _ in range(1000):
    cur = o2._pick(POOL, ("T", "x"))
    assert cur != prev, "same line dealt twice in a row at a reshuffle"
    prev = cur

# 3. persistence: deal half the deck, force-save, 'restart', deal the rest —
#    the second half must be exactly the lines not heard before the restart
o3 = fresh(os.path.join(TMP, "b3.json"))
first_half = [o3._pick(POOL, ("T", "p")) for _ in range(6)]
o3._bag_save(force=True)
o4 = fresh(os.path.join(TMP, "b3.json"))          # simulated new session
second_half = [o4._pick(POOL, ("T", "p")) for _ in range(6)]
assert not set(first_half) & set(second_half), (
    f"restart forgot the deck: {set(first_half) & set(second_half)} repeated")
assert sorted(first_half + second_half) == sorted(POOL)

# 4. pool edits between versions don't break the deck (hash-keyed, not index)
o5 = fresh(os.path.join(TMP, "b4.json"))
for _ in range(4):
    o5._pick(POOL, ("T", "e"))
o5._bag_save(force=True)
o6 = fresh(os.path.join(TMP, "b4.json"))
grown = POOL + ["brand new line"]
got = {o6._pick(grown, ("T", "e")) for _ in range(30)}
assert "brand new line" in got                     # new lines join the deck

# 5. corrupt state file -> fresh decks, no crash
bad = os.path.join(TMP, "bad.json")
open(bad, "w").write("{not json")
o7 = fresh(bad)
assert o7._pick(POOL, ("T", "c")) in POOL

# 6. degenerate pools
o8 = fresh(os.path.join(TMP, "b5.json"))
assert o8._pick([], ("T", "z")) == ""
assert o8._pick(["only"], ("T", "z")) == "only"

print("bagtest OK")
