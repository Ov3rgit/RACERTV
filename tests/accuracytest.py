"""THE BOOTH MAY NOT ASSERT SOMETHING THE TIMING SCREEN DENIES.

Reported after a race, with the transcript to prove it:

  * "It's the best fight on track — three cars covered by a second and none
    giving an inch." Said while the player sat P3 with the leaders four to six
    seconds up the road.
  * "You've been hunted before — what's going through the leading cockpit right
    now?" answered "Not a flicker so far — Pablo Afiq is ice-cool", about the
    driver running FIFTH.

Both came from the same place. The crosstalk exchange picked its topic with
random.choice over every topic there is, and its driver with random.choice over
the top six, independently of each other and of the race. But the answer pools
are not neutral colour -- many state a checkable fact about gaps or positions,
so those claims were true only by luck.

_crosstalk_pick now offers a topic only when the race supports it, and supplies
the driver the topic is ABOUT. Opinion topics (era, racecraft, banter) assert
nothing checkable and stay available, so a strung-out race still has a booth.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import sys

sys.path.insert(0, r"D:\R3EOverlay")
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])
from lines import CROSSTALK                               # noqa: E402
from overlay_booth import TIGHT_TRIO_GAP                  # noqa: E402

# topics whose ANSWERS claim the race is close / that a named driver is in a
# specific situation. These are the ones that must be earned.
GROUNDED = ("podium_fight", "hold_on", "move_on", "pressure", "prediction")


def field(gaps, ncars=8):
    """A race where `gaps[i]` is car i's interval to the car ahead."""
    o = headless_overlay(fake_tts=True)
    s = make_shared(2, ncars=ncars)
    for i, d in enumerate(s.all_drivers_data_1[:ncars]):
        d.car_speed = 60.0
        d.place = i + 1
        d.completed_laps = 5
    order = sorted(s.all_drivers_data_1[:ncars], key=lambda d: d.place)
    for i, d in enumerate(order):
        if i < len(gaps) and gaps[i] is not None:
            o.interval[d.driver_info.slot_id] = gaps[i]
    o._pit_t = {}
    return o, s, order


def picks(o, order, n=400):
    """Sample the selector; returns [(topic, driver_name)]."""
    out = []
    for _ in range(n):
        p = o._crosstalk_pick(order)
        if p is not None:
            t, d = p
            out.append((t, o._dname(d)))
    return out


# ---- 1. STRUNG OUT: the grounded topics must never come up ---------------
# leader clear by 6s, P3 another 5s back -- nothing here is "covered by a
# second" and nobody is "all over the back" of anyone.
o, s, order = field([None, 6.0, 5.0, 7.0, 6.0, 8.0, 9.0, 10.0])
got = picks(o, order)
assert got, "the selector went silent in a normal race -- the booth needs topics"
bad = sorted({t for t, _ in got} & set(GROUNDED))
assert not bad, (
    "in a race with 5-6s between every car the booth still offered %r -- "
    "those answers claim a close fight" % (bad,))
print("  strung-out race offers no close-fight topics: OK (%d topics available)"
      % len({t for t, _ in got}))

# and specifically the reported line's topic
assert "podium_fight" not in {t for t, _ in got}, (
    "podium_fight offered with the podium spread over 11 seconds -- this is "
    "the reported 'three cars covered by a second' line")
print("  podium_fight withheld when the podium is not close: OK")

# ---- 2. GENUINELY CLOSE: now it is allowed --------------------------------
o, s, order = field([None, 0.5, 0.6, 4.0, 5.0, 6.0, 7.0, 8.0])
got = picks(o, order)
assert "podium_fight" in {t for t, _ in got}, (
    "the top three were covered by 1.1s and the booth still would not discuss "
    "the podium fight")
print("  podium_fight offered when the top three ARE covered: OK")

# the claim it makes must match the threshold it was gated on
tri = [d for d in order[:3]]
spread = sum(o.interval.get(d.driver_info.slot_id, 0.0) for d in tri[1:])
assert spread <= TIGHT_TRIO_GAP, (
    "test setup no longer models a tight trio (%.2fs)" % spread)
print("  ...and the gate matches the claim (%.2fs <= %.1fs): OK"
      % (spread, TIGHT_TRIO_GAP))

# ---- 3. THE DRIVER MATCHES THE QUESTION ----------------------------------
# "what's going through the leading cockpit" must be about the LEADER, not
# whoever the dice picked out of the top six.
o, s, order = field([None, 0.5, 0.6, 4.0, 5.0, 6.0, 7.0, 8.0])
leader = o._dname(order[0])
got = picks(o, order)
for topic in ("hold_on",):
    named = {nm for t, nm in got if t == topic}
    assert named, "no %s sample" % topic
    assert named == {leader}, (
        "the '%s' question (about the driver in front) was asked about %r "
        "instead of the leader %r" % (topic, sorted(named), leader))
print("  leader-topics always name the actual leader: OK -> %s" % leader)

# move_on is about someone genuinely chasing -- never the leader, who has
# nobody to move on
chasers = {nm for t, nm in got if t == "move_on"}
if chasers:
    assert leader not in chasers, (
        "'can he find a way past' was asked about the race leader")
    print("  move_on never names the leader: OK -> %s" % sorted(chasers))

# ---- 4. NOBODY CLOSE AT ALL: move_on / pressure stay away ----------------
o, s, order = field([None, 9.0, 9.0, 9.0, 9.0, 9.0, 9.0, 9.0])
got = {t for t, _ in picks(o, order)}
for t in ("move_on", "pressure", "hold_on", "prediction"):
    assert t not in got, (
        "%r offered with nine seconds between every car -- its answers claim "
        "a car in the mirrors" % t)
print("  no close cars -> no pressure/chase/prediction topics: OK")

# the booth must still have SOMETHING to say, or it goes mute in a procession
assert got, "a spread-out race left the booth with no topics at all"
print("  ...but opinion topics still available (%d): OK" % len(got))

# ---- 5. every topic the selector can return actually exists --------------
o, s, order = field([None, 0.4, 0.5, 0.8, 1.0, 1.2, 5.0, 6.0])
for t, _ in picks(o, order):
    assert t in CROSSTALK, "selector returned unknown topic %r" % t
print("  every offered topic exists in CROSSTALK: OK")

# ---- 6. an empty field must not explode ----------------------------------
assert o._crosstalk_pick([]) is None, "empty order should yield no crosstalk"
print("  empty field -> None, no crash: OK")

print("\nBOOTH-ACCURACY CHECKS PASSED")
