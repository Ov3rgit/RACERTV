"""Career memory: results recorded per track, correct callback category
(win > podium > plain return), persistence across restart, first visit silent,
and every career template formats cleanly with the kwargs the hook provides."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.pop("RACERTV_EPHEMERAL", None)      # this test drives real persistence
from r3e_overlay import Overlay, _safe_format
from lines import COMMENTARY_LINES

TMP = tempfile.mkdtemp()


def fresh(name="c.json"):
    o = object.__new__(Overlay)
    o._CAREER_FILE = os.path.join(TMP, name)
    return o


# 1. first visit: no note
o = fresh()
assert o._career_note("Monza") is None

# 2. plain return (P8): career_back with counts
o._career_record("Monza", 8, 20)
cat, kw = o._career_note("Monza")
assert cat == "career_back" and kw["times"] == "once" and kw["best"] == 8

# 3. podium beats plain; win beats podium
o._career_record("Monza", 3, 20)
assert o._career_note("Monza")[0] == "career_podium_here"
o._career_record("Monza", 1, 20)
cat, kw = o._career_note("Monza")
assert cat == "career_won_here" and kw["wins"] == "once"

# 4. totals + per-track isolation
c = o._career()
assert c["races"] == 3 and c["wins"] == 1 and c["podiums"] == 2
assert o._career_note("Spa") is None

# 5. persistence across a 'restart'
o2 = fresh()
cat, kw = o2._career_note("Monza")
assert cat == "career_won_here" and kw["best"] == 1, "career forgot the win"

# 6. invalid positions ignored
o2._career_record("Spa", 0, 20)
assert o2._career_note("Spa") is None

# 7. every career template formats with the hook's kwargs (no leftover braces)
base = {"trk": "Monza", "drv": "Test Driver", "comm": "Miles", "pundit": "Brett",
        "times": "twice", "best": 2, "last": 4, "wins": "once"}
for cat in ("career_back", "career_podium_here", "career_won_here"):
    for t in COMMENTARY_LINES[cat]:
        out = _safe_format(t, base)
        assert "{" not in out and "}" not in out, f"{cat}: unfilled placeholder in {t!r}"

print("careertest OK")
