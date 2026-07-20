"""Lights-out must fire at green and NOT be preempted by a bogus 'gone off' as
the grid sorts out. Also: no DRS in engineer lines."""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"  # tests: no disk deck state

import sys
sys.path.insert(0, r"D:\R3EOverlay")
import r3e_data as R
from r3e_overlay import Overlay
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])

print("===== LIGHTS-OUT vs GRID SORT =====")
o = headless_overlay(fake_tts=True)
o._show_caption = lambda *a, **k: None
o.radio_msgs = []
s = make_shared(2, ncars=8)
# grid build-up tick (stationary) -> pregrid welcome
drive(o, s, 2)
# LIGHTS OUT: cars move, and immediately the grid shuffles hard (slot 5 drops
# 3 places as the standing start sorts out — this used to trigger 'gone off')
for i in range(s.num_cars):
    s.all_drivers_data_1[i].car_speed = 50.0
drive(o, s, 1)
# force a big place shuffle on the next ticks (grid sorting)
order = sorted(s.all_drivers_data_1[:8], key=lambda d: d.place)
order[2].place, order[5].place = order[5].place, order[2].place
order[1].place, order[3].place = order[3].place, order[1].place
for _ in range(4):
    drive(o, s, 1)

spoken = [(p, t) for p, t in o.tts.spoken]
# robust: the start line is the COMMENTATOR line that is NOT a pregrid welcome
# (welcomes all say 'RacerTV') — match distinctive words drawn from the actual
# start pool so every one of its ~35 variants is recognised.
from lines import COMMENTARY_LINES as _CL
_STKW = set()
for _ln in _CL["start"]:
    for _kw in ("lights", "away", "racing", "green", "flag", "off they go",
                "leads", "turn one", "first corner", "getaway", "streaks",
                "charge", "exchanges", "head of", "lap one", "race is on",
                "pour", "stream", "convert", "wheels spinning", "sway",
                "fending", "chaos", "here they come", "initiative", "gone"):
        if _kw in _ln.lower():
            _STKW.add(_kw)
lights = [t for p, t in spoken if p == "COMMENTATOR"
          and "racertv" not in t.lower()
          and any(k in t.lower() for k in _STKW)]
# Match INCIDENT REPORTS by deriving the patterns from the actual line pools,
# rather than guessing keywords.
#
# The old hand-written keyword list was wrong in BOTH directions. Too loose:
# it matched the bare word "trouble", which is all over ordinary colour --
# midpack ("out of trouble"), analysis ("who is in trouble and who has more in
# reserve"), and the crosstalk prediction "someone in the top five hits
# trouble". That made this check fail ~7% of runs on lines that are not
# incident calls at all. Too tight: it had "spun" but not "spin", "gone off"
# but not "went off", so it missed most of the pools it was meant to police --
# 61 of the 91 real incident lines went unmatched.
#
# Building the patterns from the pools themselves means it stays correct when
# lines are added, which a keyword list never does.
import re as _re                                             # noqa: E402
from lines import COMMENTARY_LINES as _CL                    # noqa: E402

_INCIDENT_POOLS = ("offtrack", "offtrack_more", "offtrack_cut",
                   "offtrack_chaos", "offtrack_late", "spin")
_INCIDENT_RE = []
for _pool in _INCIDENT_POOLS:
    for _tmpl in _CL.get(_pool, []):
        # {drv}/{comm} -> wildcard, everything else literal
        _pat = "".join(r".+?" if _p.startswith("{") else _re.escape(_p)
                       for _p in _re.split(r"(\{\w+\})", _tmpl) if _p)
        _INCIDENT_RE.append(_re.compile(_pat, _re.I))
assert len(_INCIDENT_RE) >= 80, (
    f"only {len(_INCIDENT_RE)} incident patterns built — the pools moved, and "
    "this check would silently police nothing")
goneoff = [t for _p, t in spoken if any(r.search(t) for r in _INCIDENT_RE)]
print(f"  lights-out lines: {len(lights)}")
for t in lights[:2]: print(f"    [lights] {t[:60]}")
print(f"  spurious 'gone off' during grid sort: {len(goneoff)}")
for t in goneoff[:3]: print(f"    [oops]   {t[:60]}")
assert lights, "lights-out call did not fire!"
assert not goneoff, f"a bogus incident preempted the start: {goneoff}"
print("  lights-out fired, no bogus incident during grid sort: OK")

# ---- no DRS in any engineer line --------------------------------------------
from lines import ENGINEER_LINES, ENGINEER_QUALI
drs = [l for cat in ENGINEER_LINES.values() for l in cat if "drs" in l.lower()]
drs += [l for cat in ENGINEER_QUALI.values() for l in cat if "drs" in l.lower()]
assert not drs, f"DRS still referenced: {drs}"
print("  no DRS references in engineer lines: OK")

print("\nALL START/DRS CHECKS PASSED")
