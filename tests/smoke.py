"""Headless smoke test for RacerTV — drives update_stats/update_radio/
update_commentary across race, quali and practice with synthetic shared memory.
No tkinter, no TTS (tts=None). Exercises the new engineer paths (quali off-track,
sector coaching, mandatory pit, intro gate)."""
import os, sys, time, ctypes
sys.path.insert(0, r"D:\R3EOverlay")
import r3e_data as R
from r3e_overlay import Overlay


def set_name(info, name):
    b = name.encode("utf-8")[:63]
    for i, ch in enumerate(b):
        info.name[i] = ch
    info.name[len(b)] = 0


def make_shared(session_type, ncars=6, track="Spa-Francorchamps - Grand Prix"):
    s = R.R3EShared()
    s.version_major = 3
    s.num_cars = ncars
    tb = track.encode("utf-8")[:63]
    for i, ch in enumerate(tb):
        s.track_name[i] = ch
    s.track_id = 1
    s.layout_id = 1
    s.session_type = session_type           # 0 prac, 1 quali, 2 race
    s.session_iteration = 1
    s.session_phase = 3
    s.game_in_menus = 0
    s.game_player_in_garage = 0
    s.game_in_replay = 0
    s.game_paused = 0
    s.number_of_laps = 8 if session_type == 2 else -1
    s.session_time_duration = 600.0
    s.session_time_remaining = 600.0
    s.max_incident_points = 20
    s.incident_points = 0
    s.pit_window_status = 0
    for _f in ("drive_through", "stop_and_go", "pit_stop", "time_deduction",
               "slow_down"):
        setattr(s.penalties, _f, -1.0)     # -1 = no penalty pending (RaceRoom)
    s.lap_valid_state = -1
    s.fuel_use_active = 0
    s.tire_wear_active = 0
    s.current_lap_valid = 1                 # top-level = the player's lap-valid
    s.car_speed = 0.0
    s.in_pitlane = 0
    s.vehicle_info.slot_id = 0              # YOU are slot 0
    set_name(s.vehicle_info, "You Driver")
    for i in range(ncars):
        d = s.all_drivers_data_1[i]
        d.driver_info.slot_id = i
        d.driver_info.car_number = i + 1
        _names = ["You Driver", "Max Hill", "Luca Rossi", "Pierre Dubois",
                  "Hans Gruber", "Sam Stone", "Kenji Tanaka", "Diego Marquez",
                  "Olav Berg", "Tom Clarke", "Rashid Aziz", "Niko Virtanen"]
        set_name(d.driver_info, _names[i % len(_names)] if i else "You Driver")
        d.place = i + 1
        d.completed_laps = 0
        d.current_lap_valid = 1
        d.lap_distance_fraction = 0.0
        d.in_pitlane = 0
        d.car_speed = 0.0
        d.finish_status = 0
        d.pitstop_status = -1
        d.penaltyType = -1
    return s


class FakeTts:
    """Minimal stand-in so the real emit path (speak) and the intro gate run."""
    engine = "fake"
    enabled = True
    def __init__(self):
        self.spoken = []
        self._busy = False
        self._pend = 0
    def speaking(self):
        return self._busy
    def speaking_persona(self):
        return None
    def _pending(self):
        return self._pend
    def native_lang(self, persona, seed):
        return None
    def speak(self, text, persona="ENGINEER", seed="", intensity=0,
              on_play=None, **kw):
        self.spoken.append((persona, text))
        if on_play:
            on_play(text, persona)
    def sting(self, group="alert", persona="PUNDIT", on_play=None):
        return False
    def stop(self): pass
    def flush(self): pass
    def interrupt(self): pass
    def resume(self): pass


def headless_overlay(fake_tts=False):
    o = object.__new__(Overlay)
    # non-tk attributes the three update_* methods (and helpers) need
    o.tts = FakeTts() if fake_tts else None
    o.commentary_on = True
    o._pron = {}
    o._car_names = {}
    o._dcolor = {}
    o._dcolor_n = 0
    o._last_line = {}
    o._radio_recent = []
    o._dbg_moves = 0
    o._stage_err = {}
    o.last_radio_t = 0.0
    o._sess_key = None
    o._comm_key = None
    o._prev_lead_laps = None
    o._sess_gen = 0
    o._racing = False
    o._gone = set()
    o._move_sig = {}
    o._cpend = {}
    o.last_laps = {}
    o.ref_lap = None
    o.fastest = {"time": None, "slot": None, "car": 0, "name": "", "at": 0.0}
    o.cplace = {}
    o.interval = {}
    o.cum_gap = {}
    o.grid_place = {}
    o.best_lap = {}
    o.RADIO_ENG_CD = 14.0
    o.RADIO_GLOBAL_CD = 5.5
    o.RADIO_DRIVER_CD = 25.0
    o.RADIO_HOLD = 6.0
    o.RADIO_NEAR = 4
    o.RADIO_FAR_CHANCE = 0.6
    o.RADIO_MAX_BUBBLES = 3
    o.RADIO_MAX_BURST = 3
    o.COMMENTARY_CD = 5.0
    # init-level new attrs (also set in init, mirror here for the bare object)
    o._sec_laps = {}
    o._eng_sec_cd = 0.0
    o._intro_emit_t = None
    o._intro_aired = False
    o._q_off_lv = 1
    o._q_off_watch = None
    return o


def cum(d, s1, s2, s3):
    d.sector_time_previous_self[0] = s1
    d.sector_time_previous_self[1] = s1 + s2
    d.sector_time_previous_self[2] = s1 + s2 + s3


def bestcum(d, s1, s2, s3):
    d.sector_time_best_self[0] = s1
    d.sector_time_best_self[1] = s1 + s2
    d.sector_time_best_self[2] = s1 + s2 + s3


def run_session(label, session_type, scenario):
    print(f"\n===== {label} =====")
    o = headless_overlay(fake_tts=True)
    s = make_shared(session_type)
    emitted = o.tts.spoken
    o._show_caption = lambda text, persona="COMMENTATOR": None
    o.radio_msgs = []
    scenario(o, s, emitted)
    eng = [t for p, t in emitted if p == "ENGINEER"]
    booth = [t for p, t in emitted if p != "ENGINEER"]
    print(f"  -> {len(emitted)} lines spoken "
          f"({len(eng)} engineer, {len(booth)} booth/rival), no exceptions")
    for p, tx in emitted:
        tag = "ENG " if p == "ENGINEER" else p[:4].ljust(4)
        print(f"     [{tag}] {tx}")
    return emitted


def age_intro(o):
    """Simulate the booth's intro audio having finished playing (the gate's
    real-time delay can't elapse in a millisecond-fast test)."""
    if o._intro_emit_t is not None:
        o._intro_emit_t -= 15.0


def drive(o, s, ticks=1):
    you = s.all_drivers_data_1[0]
    for _ in range(ticks):
        # the player's top-level shared fields mirror the player driver entry
        s.car_speed = you.car_speed
        s.current_lap_valid = you.current_lap_valid
        s.in_pitlane = you.in_pitlane
        o.last_radio_t = 0.0          # relax global cooldown so every line airs
        o._comm_cd = 0.0
        o.update_stats(s)
        o.update_radio(s)
        o.update_commentary(s)
        time.sleep(0.001)


def eng_count(emitted):
    return sum(1 for p, t in emitted if p == "ENGINEER")


def race_scenario(o, s, emitted):
    # tick 1: on grid (not racing). Then go green, run laps, off-track, finish.
    drive(o, s, 2)
    # go green
    for i in range(s.num_cars):
        s.all_drivers_data_1[i].car_speed = 50.0
    drive(o, s, 3)
    # INTRO GATE: engineer must be silent until the booth intro has aired
    assert eng_count(emitted) == 0, "engineer spoke before intro aired!"
    print("  [gate] engineer silent through booth intro: OK")
    age_intro(o)                    # booth opener has now finished playing
    drive(o, s, 2)                  # engineer's lights-out call can now land
    # complete several laps, you (slot0) set sector times
    you = s.all_drivers_data_1[0]
    for lap in range(1, 6):
        for i in range(s.num_cars):
            s.all_drivers_data_1[i].completed_laps = lap
            s.all_drivers_data_1[i].lap_distance_fraction = 0.1
        # your lap: weak sector 2
        cum(you, 30.0, 45.0 + (0.6 if lap == 3 else 0.0), 28.0)
        bestcum(you, 30.0, 44.0, 28.0)
        you.car_speed = 55.0
        drive(o, s, 1)
        # let cooldowns pass for sector coaching
        o._eng_sec_cd -= 60.0
        o._eng_cd -= 20.0
        drive(o, s, 1)
    # off-track: lap goes invalid + speed collapse (race incident path)
    you.current_lap_valid = 0
    you.car_speed = 8.0
    drive(o, s, 3)
    # mandatory pit test: flag a mandatory unserved + window open
    you.current_lap_valid = 1
    you.car_speed = 55.0
    s.pit_window_status = 2
    you.pitstop_status = 1
    o._eng_cd -= 40.0
    drive(o, s, 2)
    # finish
    s.session_phase = 6
    s.flags.checkered = 1
    for i in range(s.num_cars):
        s.all_drivers_data_1[i].finish_status = 1
    o._eng_cd -= 40.0
    drive(o, s, 2)


def quali_scenario(o, s, emitted):
    you = s.all_drivers_data_1[0]
    drive(o, s, 2)   # intro
    assert eng_count(emitted) == 0, "engineer spoke before quali intro aired!"
    print("  [gate] engineer silent through quali intro: OK")
    age_intro(o)
    # complete a flying lap (PB / pole) — sets q_events
    for lap in range(1, 4):
        for i in range(s.num_cars):
            s.all_drivers_data_1[i].completed_laps = lap
        cum(you, 30.0, 44.0, 27.5)         # improving
        bestcum(you, 30.5, 44.5, 28.0)
        you.car_speed = 60.0
        drive(o, s, 1)
        o._eng_cd -= 20.0
        drive(o, s, 1)
    # OFF-TRACK in quali on a HOT lap: invalidation edge at speed, THEN the
    # speed collapses (grass/spin) -> the new 'offtrack' engineer warning.
    you.car_speed = 60.0
    you.current_lap_valid = 0      # invalidation edge, ref speed captured ~60
    drive(o, s, 1)
    o._eng_cd -= 20.0
    you.car_speed = 8.0            # pace collapses -> genuine off confirmed
    drive(o, s, 2)
    assert any("offtrack" in t.lower() or "island" in t.lower() or "off the"
               in t.lower() or "excursion" in t.lower() or "lost it" in t.lower()
               or "ran out of road" in t.lower() or "bin it" in t.lower()
               or "off the road" in t.lower() or "off the track" in t.lower()
               for p, t in emitted if p == "ENGINEER"), \
        "no engineer off-track warning fired in quali!"
    print("  [offtrack] engineer warned of quali excursion: OK")


def practice_scenario(o, s, emitted):
    you = s.all_drivers_data_1[0]
    drive(o, s, 2)
    assert eng_count(emitted) == 0, "engineer spoke before practice intro aired!"
    print("  [gate] engineer silent through practice intro: OK")
    age_intro(o)
    for lap in range(1, 4):
        for i in range(s.num_cars):
            s.all_drivers_data_1[i].completed_laps = lap
        cum(you, 31.0, 45.0, 28.0)
        bestcum(you, 30.5, 44.0, 27.5)
        you.car_speed = 58.0
        drive(o, s, 1)
        o._eng_cd -= 30.0
        o._prac_cd -= 30.0
        drive(o, s, 1)
    # off-track (hot lap then collapse)
    you.car_speed = 58.0
    you.current_lap_valid = 0
    drive(o, s, 1)
    o._eng_cd -= 20.0
    you.car_speed = 7.0
    drive(o, s, 2)


run_session("RACE", 2, race_scenario)
run_session("QUALIFYING", 1, quali_scenario)
run_session("PRACTICE", 0, practice_scenario)


def pit_logic_tests():
    print("\n===== PIT-LOGIC (negative) =====")
    PITWORDS = ("box", "pit window", "your stop", "mandatory stop",
                "make your", "need that pit")

    def green_running(o, s):
        for i in range(s.num_cars):
            s.all_drivers_data_1[i].car_speed = 55.0
        you = s.all_drivers_data_1[0]
        you.completed_laps = 3
        for i in range(s.num_cars):
            s.all_drivers_data_1[i].completed_laps = 3
        drive(o, s, 3)
        age_intro(o)

    # A) NO mandatory stop (pitstop_status -1) but window shows OPEN ->
    #    the engineer must NEVER tell you to box.
    o = headless_overlay(fake_tts=True)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    s = make_shared(2)
    s.pit_window_status = 2
    green_running(o, s)
    s.all_drivers_data_1[0].pitstop_status = -1
    for _ in range(6):
        o._eng_cd -= 40.0
        drive(o, s, 2)
    pit_lines = [t for p, t in o.tts.spoken if p == "ENGINEER"
                 and any(w in t.lower() for w in PITWORDS)]
    assert not pit_lines, f"engineer wrongly told you to pit: {pit_lines}"
    print("  [pit] no-mandatory-stop race: engineer never said box: OK")

    # B) tyres CRITICAL, no mandatory stop -> 'manage them home', NOT 'box'
    o = headless_overlay(fake_tts=True)
    o._show_caption = lambda *a, **k: None
    o.radio_msgs = []
    s = make_shared(2)
    s.tire_wear_active = 1
    you = s.all_drivers_data_1[0]
    for i in range(4):
        s.tire_wear[i] = 1.0
    green_running(o, s)                  # green + intro aged (engineer ungated)
    you.pitstop_status = -1
    for _ in range(3):                   # let the engineer log the fresh baseline
        o._eng_cd -= 40.0
        o._eng_tyre_cd -= 60.0
        drive(o, s, 1)
    for i in range(4):
        s.tire_wear[i] = 0.1            # 90% worn -> critical
    fired = None
    for _ in range(8):
        o._eng_cd -= 40.0
        o._eng_tyre_cd -= 60.0
        before = len(o.tts.spoken)
        drive(o, s, 2)
        for p, t in o.tts.spoken[before:]:
            if p == "ENGINEER" and ("tyre" in t.lower() or "rubber" in t.lower()
                                    or "grip" in t.lower()):
                fired = t
    assert fired, "no critical-tyre engineer line fired"
    assert "box" not in fired.lower() and "pit" not in fired.lower(), \
        f"told to box for tyres in a no-stop race: {fired}"
    print(f"  [pit] critical tyres, no stop -> manage (not box): OK")
    print(f"        line: {fired}")


pit_logic_tests()
print("\nALL SMOKE SCENARIOS COMPLETED WITHOUT EXCEPTIONS")
