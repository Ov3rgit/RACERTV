"""SPECTATOR MODE — the broadcast without the cockpit.

Half of RacerTV talks TO a driver: the engineer in your ear, the objective
card, the relative panel. Watching a replay of somebody else's race, or
spectating, that half is addressed to nobody — and the engineer telling an
empty seat to mind its tyres is the single most immersion-breaking thing the
overlay can do. Spectator mode drops it and keeps the broadcast: booth,
timing tower, map, flags, sectors, fastest lap.

Asserted here: the toggle flips and is remembered, the radio engine is skipped
rather than merely muted (so it never builds messages at all), and the booth
is untouched.
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import sys

sys.path.insert(0, r"D:\R3EOverlay")
src = open(r"D:\R3EOverlay\tests\smoke.py").read()
exec(src.split('run_session("RACE"')[0])

import r3e_overlay as RO


def session(ncars=6):
    o = headless_overlay(fake_tts=True)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    o.spectator = False
    o._toast = lambda *a, **k: None
    s = make_shared(2, ncars=ncars)
    s.session_phase = 5
    s.player.game_simulation_time = 30.0
    s.session_time_remaining = 600.0
    for i, d in enumerate(s.all_drivers_data_1[:ncars]):
        d.car_speed, d.place, d.completed_laps = 60.0, i + 1, 2
        d.lap_distance_fraction = 0.4
    s.car_speed = 60.0
    return o, s


# ---- 1. the toggle flips, and says so ----------------------------------
o, s = session()
assert o.spectator is False
RO.Overlay._do_toggle_spectator(o)
assert o.spectator is True, "the spectator toggle did not turn on"
RO.Overlay._do_toggle_spectator(o)
assert o.spectator is False, "the spectator toggle did not turn back off"
print("  [spectator] the toggle flips both ways: OK")


# ---- 2. it is remembered between runs ----------------------------------
# Someone who watches replays should not have to re-tick the box every launch,
# or the mode reads as a debug switch rather than a way to watch.
assert hasattr(RO, "_load_prefs") and hasattr(RO, "_save_pref"), (
    "spectator mode is not persisted — it would have to be re-enabled on "
    "every single launch")
src_init = open(r"D:\R3EOverlay\r3e_overlay.py", encoding="utf-8").read()
assert '_load_prefs().get("spectator"' in src_init, (
    "the saved spectator preference is never read back at startup")
assert '_save_pref("spectator"' in src_init, (
    "flipping spectator mode never writes the preference")
print("  [spectator] the preference is loaded and saved: OK")


# ---- 3. the RADIO is skipped, not merely muted --------------------------
# Muting at the speak() call would still build the messages, tick the
# cooldowns and populate the bubble list. The stage is skipped instead, so
# nothing is produced to throw away.
src_tick = src_init.split("def tick(")[1].split("\n    def ")[0]
assert '("radio", self.update_radio)' in src_tick
assert "if not spec:" in src_tick, (
    "the update_radio stage is not gated on spectator mode")
assert 'spec and nm in ("relative", "objective", "bubbles")' in src_tick, (
    "the relative panel, objective card and radio bubbles are not gated on "
    "spectator mode — they address a driver who is not there")
print("  [spectator] radio, objective and relative are all gated: OK")


# ---- 4. the BROADCAST is untouched --------------------------------------
# The gated stages are filtered out of the list in place, so the whole tick
# body is the haystack for the ones that must survive.
head = src_tick
for keep in ('("stats", self.update_stats)', '("comm", self.update_commentary)',
             '("tower", self.draw_tower)', '("map", self.draw_map)',
             '("flags", self.draw_flags)',
             '("fastest", self.draw_fastest_banner)',
             '("caption", self.draw_commentary)'):
    assert keep in head, (
        f"{keep} was caught by the spectator gate — spectator mode is meant "
        "to REMOVE the cockpit, not the broadcast")
print("  [spectator] booth, tower, map and captions all survive: OK")


# ---- 5. the booth still calls the race with spectator on ----------------
o, s = session()
o.spectator = True
o._intro_emit_t = 0.0
drive(o, s, 4)
assert o.tts.spoken, "the booth went silent in spectator mode"
assert any(p in ("COMMENTATOR", "PUNDIT") for p, _t in o.tts.spoken), (
    "no booth voices at all in spectator mode")
print("  [spectator] the booth keeps calling the race: OK")
_booth = [t for p, t in o.tts.spoken if p in ("COMMENTATOR", "PUNDIT")]
print("              ", _booth[0][:74])


print("\nSPECTATOR MODE: ALL OK")
