"""
RaceRoom (R3E) shared-memory reader.
Maps the "$R3E" shared memory and parses it into ctypes structs that match
the official sample-c/src/r3e.h (version 3.5).

Run directly to dump live data to the console (requires RaceRoom running):
    python r3e_data.py
"""
import ctypes
import time

R3E_SHARED_MEMORY_NAME = "$R3E"
R3E_NUM_DRIVERS_MAX = 128
R3E_TIRE_INDEX_MAX = 4
R3E_TIRE_TEMP_INDEX_MAX = 3
R3E_PIT_MENU_MAX = 12

F32 = ctypes.c_float
F64 = ctypes.c_double
I32 = ctypes.c_int32
U8 = ctypes.c_uint8


class Base(ctypes.Structure):
    _pack_ = 1  # #pragma pack(push, 1)


class Vec3F32(Base):
    _fields_ = [("x", F32), ("y", F32), ("z", F32)]


class Vec3F64(Base):
    _fields_ = [("x", F64), ("y", F64), ("z", F64)]


class OriF32(Base):
    _fields_ = [("pitch", F32), ("yaw", F32), ("roll", F32)]


class SectorStarts(Base):
    _fields_ = [("sector1", F32), ("sector2", F32), ("sector3", F32)]


class PlayerData(Base):
    _fields_ = [
        ("user_id", I32),
        ("game_simulation_ticks", I32),
        ("game_simulation_time", F64),
        ("position", Vec3F64),
        ("velocity", Vec3F64),
        ("local_velocity", Vec3F64),
        ("acceleration", Vec3F64),
        ("local_acceleration", Vec3F64),
        ("orientation", Vec3F64),
        ("rotation", Vec3F64),
        ("angular_acceleration", Vec3F64),
        ("angular_velocity", Vec3F64),
        ("local_angular_velocity", Vec3F64),
        ("local_g_force", Vec3F64),
        ("steering_force", F64),
        ("steering_force_percentage", F64),
        ("engine_torque", F64),
        ("current_downforce", F64),
        ("voltage", F64),
        ("ers_level", F64),
        ("power_mgu_h", F64),
        ("power_mgu_k", F64),
        ("torque_mgu_k", F64),
        ("suspension_deflection", F64 * R3E_TIRE_INDEX_MAX),
        ("suspension_velocity", F64 * R3E_TIRE_INDEX_MAX),
        ("camber", F64 * R3E_TIRE_INDEX_MAX),
        ("ride_height", F64 * R3E_TIRE_INDEX_MAX),
        ("front_wing_height", F64),
        ("front_roll_angle", F64),
        ("rear_roll_angle", F64),
        ("third_spring_suspension_deflection_front", F64),
        ("third_spring_suspension_velocity_front", F64),
        ("third_spring_suspension_deflection_rear", F64),
        ("third_spring_suspension_velocity_rear", F64),
        ("unused1", F64),
        ("unused2", F64),
        ("unused3", F64),
    ]


class Flags(Base):
    _fields_ = [
        ("yellow", I32),
        ("yellowCausedIt", I32),
        ("yellowOvertake", I32),
        ("yellowPositionsGained", I32),
        ("sector_yellow", I32 * 3),
        ("closest_yellow_distance_into_track", F32),
        ("blue", I32),
        ("black", I32),
        ("green", I32),
        ("checkered", I32),
        ("white", I32),
        ("black_and_white", I32),
    ]


class CarDamage(Base):
    _fields_ = [
        ("engine", F32),
        ("transmission", F32),
        ("aerodynamics", F32),
        ("suspension", F32),
        ("unused1", F32),
        ("unused2", F32),
    ]


class CutTrackPenalties(Base):
    _fields_ = [
        ("drive_through", F32),
        ("stop_and_go", F32),
        ("pit_stop", F32),
        ("time_deduction", F32),
        ("slow_down", F32),
    ]


class Drs(Base):
    _fields_ = [
        ("equipped", I32),
        ("available", I32),
        ("numActivationsLeft", I32),
        ("engaged", I32),
    ]


class PushToPass(Base):
    _fields_ = [
        ("available", I32),
        ("engaged", I32),
        ("amount_left", I32),
        ("engaged_time_left", F32),
        ("wait_time_left", F32),
    ]


class TireTemp(Base):
    _fields_ = [
        ("current_temp", F32 * R3E_TIRE_TEMP_INDEX_MAX),
        ("optimal_temp", F32),
        ("cold_temp", F32),
        ("hot_temp", F32),
    ]


class BrakeTemp(Base):
    _fields_ = [
        ("current_temp", F32),
        ("optimal_temp", F32),
        ("cold_temp", F32),
        ("hot_temp", F32),
    ]


class AidSettings(Base):
    _fields_ = [
        ("abs", I32),
        ("tc", I32),
        ("esp", I32),
        ("countersteer", I32),
        ("cornering", I32),
    ]


class DriverInfo(Base):
    _fields_ = [
        ("name", U8 * 64),
        ("car_number", I32),
        ("class_id", I32),
        ("model_id", I32),
        ("team_id", I32),
        ("livery_id", I32),
        ("manufacturer_id", I32),
        ("user_id", I32),
        ("slot_id", I32),
        ("class_performance_index", I32),
        ("engine_type", I32),
        ("car_width", F32),
        ("car_length", F32),
        ("rating", F32),
        ("reputation", F32),
        ("unused1", F32),
        ("unused2", F32),
    ]


class DriverData(Base):
    _fields_ = [
        ("driver_info", DriverInfo),
        ("finish_status", I32),
        ("place", I32),
        ("place_class", I32),
        ("lap_distance", F32),
        ("lap_distance_fraction", F32),
        ("position", Vec3F32),
        ("track_sector", I32),
        ("completed_laps", I32),
        ("current_lap_valid", I32),
        ("lap_time_current_self", F32),
        ("sector_time_current_self", F32 * 3),
        ("sector_time_previous_self", F32 * 3),
        ("sector_time_best_self", F32 * 3),
        ("time_delta_front", F32),
        ("time_delta_behind", F32),
        ("pitstop_status", I32),
        ("in_pitlane", I32),
        ("num_pitstops", I32),
        ("penalties", CutTrackPenalties),
        ("car_speed", F32),
        ("tire_type_front", I32),
        ("tire_type_rear", I32),
        ("tire_subtype_front", I32),
        ("tire_subtype_rear", I32),
        ("base_penalty_weight", F32),
        ("aid_penalty_weight", F32),
        ("drs_state", I32),
        ("ptp_state", I32),
        ("virtual_energy", F32),
        ("penaltyType", I32),
        ("penaltyReason", I32),
        ("engineState", I32),
        ("orientation", Vec3F32),
        ("unused1", F32),
        ("unused2", F32),
        ("unused3", F32),
    ]


class R3EShared(Base):
    _fields_ = [
        ("version_major", I32),
        ("version_minor", I32),
        ("all_drivers_offset", I32),
        ("driver_data_size", I32),
        ("game_mode", I32),
        ("game_paused", I32),
        ("game_in_menus", I32),
        ("game_in_replay", I32),
        ("game_using_vr", I32),
        ("game_player_in_garage", I32),
        ("player", PlayerData),
        ("track_name", U8 * 64),
        ("layout_name", U8 * 64),
        ("track_id", I32),
        ("layout_id", I32),
        ("layout_length", F32),
        ("sector_start_factors", SectorStarts),
        ("race_session_laps", I32 * 3),
        ("race_session_minutes", I32 * 3),
        ("event_index", I32),
        ("session_type", I32),
        ("session_iteration", I32),
        ("session_length_format", I32),
        ("session_pit_speed_limit", F32),
        ("session_phase", I32),
        ("start_lights", I32),
        ("tire_wear_active", I32),
        ("fuel_use_active", I32),
        ("number_of_laps", I32),
        ("session_time_duration", F32),
        ("session_time_remaining", F32),
        ("max_incident_points", I32),
        ("event_unused1", F32),
        ("event_unused2", F32),
        ("pit_window_status", I32),
        ("pit_window_start", I32),
        ("pit_window_end", I32),
        ("in_pitlane", I32),
        ("pit_menu_selection", I32),
        ("pit_menu_state", I32 * R3E_PIT_MENU_MAX),
        ("pit_state", I32),
        ("pit_total_duration", F32),
        ("pit_elapsed_time", F32),
        ("pit_action", I32),
        ("num_pitstops", I32),
        ("pit_min_duration_total", F32),
        ("pit_min_duration_left", F32),
        ("flags", Flags),
        ("position", I32),
        ("position_class", I32),
        ("finish_status", I32),
        ("cut_track_warnings", I32),
        ("penalties", CutTrackPenalties),
        ("num_penalties", I32),
        ("completed_laps", I32),
        ("current_lap_valid", I32),
        ("track_sector", I32),
        ("lap_distance", F32),
        ("lap_distance_fraction", F32),
        ("lap_time_best_leader", F32),
        ("lap_time_best_leader_class", F32),
        ("session_best_lap_sector_times", F32 * 3),
        ("lap_time_best_self", F32),
        ("sector_time_best_self", F32 * 3),
        ("lap_time_previous_self", F32),
        ("sector_time_previous_self", F32 * 3),
        ("lap_time_current_self", F32),
        ("sector_time_current_self", F32 * 3),
        ("lap_time_delta_leader", F32),
        ("lap_time_delta_leader_class", F32),
        ("time_delta_front", F32),
        ("time_delta_behind", F32),
        ("time_delta_best_self", F32),
        ("best_individual_sector_time_self", F32 * 3),
        ("best_individual_sector_time_leader", F32 * 3),
        ("best_individual_sector_time_leader_class", F32 * 3),
        ("incident_points", I32),
        ("lap_valid_state", I32),
        ("prev_lap_valid", I32),
        ("discharge_rate", F32),
        ("brake_regen", F32),
        ("unused1", F32),
        ("vehicle_info", DriverInfo),
        ("player_name", U8 * 64),
        ("control_type", I32),
        ("car_speed", F32),
        ("engine_rps", F32),
        ("max_engine_rps", F32),
        ("upshift_rps", F32),
        ("gear", I32),
        ("num_gears", I32),
        ("car_cg_location", Vec3F32),
        ("car_orientation", OriF32),
        ("local_acceleration", Vec3F32),
        ("total_mass", F32),
        ("fuel_left", F32),
        ("fuel_capacity", F32),
        ("fuel_per_lap", F32),
        ("virtual_energy_left", F32),
        ("virtual_energy_capacity", F32),
        ("virtual_energy_per_lap", F32),
        ("engine_temp", F32),
        ("engine_oil_temp", F32),
        ("fuel_pressure", F32),
        ("engine_oil_pressure", F32),
        ("turbo_pressure", F32),
        ("throttle", F32),
        ("throttle_raw", F32),
        ("brake", F32),
        ("brake_raw", F32),
        ("clutch", F32),
        ("clutch_raw", F32),
        ("steer_input_raw", F32),
        ("steer_lock_degrees", I32),
        ("steer_wheel_range_degrees", I32),
        ("aid_settings", AidSettings),
        ("drs", Drs),
        ("pit_limiter", I32),
        ("push_to_pass", PushToPass),
        ("brake_bias", F32),
        ("drs_numActivationsTotal", I32),
        ("ptp_numActivationsTotal", I32),
        ("battery_soc", F32),
        ("water_left", F32),
        ("abs_setting", I32),
        ("headlights", I32),
        ("steer_wheel_max_rotation", I32),
        ("tire_type", I32),
        ("tire_rps", F32 * R3E_TIRE_INDEX_MAX),
        ("tire_speed", F32 * R3E_TIRE_INDEX_MAX),
        ("tire_grip", F32 * R3E_TIRE_INDEX_MAX),
        ("tire_wear", F32 * R3E_TIRE_INDEX_MAX),
        ("tire_flatspot", I32 * R3E_TIRE_INDEX_MAX),
        ("tire_pressure", F32 * R3E_TIRE_INDEX_MAX),
        ("tire_dirt", F32 * R3E_TIRE_INDEX_MAX),
        ("tire_temp", TireTemp * R3E_TIRE_INDEX_MAX),
        ("tire_type_front", I32),
        ("tire_type_rear", I32),
        ("tire_subtype_front", I32),
        ("tire_subtype_rear", I32),
        ("brake_temp", BrakeTemp * R3E_TIRE_INDEX_MAX),
        ("brake_pressure", F32 * R3E_TIRE_INDEX_MAX),
        ("traction_control_setting", I32),
        ("engine_map_setting", I32),
        ("engine_brake_setting", I32),
        ("traction_control_percent", F32),
        ("tire_on_mtrl", I32 * R3E_TIRE_INDEX_MAX),
        ("tire_load", F32 * R3E_TIRE_INDEX_MAX),
        ("car_damage", CarDamage),
        ("num_cars", I32),
        ("all_drivers_data_1", DriverData * R3E_NUM_DRIVERS_MAX),
    ]


SHARED_SIZE = ctypes.sizeof(R3EShared)


def u8_to_str(arr):
    raw = bytes(arr)
    nul = raw.find(b"\x00")
    if nul >= 0:
        raw = raw[:nul]
    try:
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return ""


import ctypes as _ct
from ctypes import wintypes as _wt

_k32 = _ct.windll.kernel32
_FILE_MAP_READ = 0x0004
_k32.OpenFileMappingW.restype = _wt.HANDLE
_k32.OpenFileMappingW.argtypes = [_wt.DWORD, _wt.BOOL, _wt.LPCWSTR]
_k32.MapViewOfFile.restype = _ct.c_void_p
_k32.MapViewOfFile.argtypes = [_wt.HANDLE, _wt.DWORD, _wt.DWORD, _wt.DWORD, _ct.c_size_t]
_k32.UnmapViewOfFile.argtypes = [_ct.c_void_p]
_k32.CloseHandle.argtypes = [_wt.HANDLE]


class R3EReader:
    """Reads the $R3E shared memory.

    IMPORTANT: only ever *opens* the mapping (OpenFileMapping) - it never
    creates it. Creating it (e.g. mmap(-1, ...)) can prevent RaceRoom from
    writing telemetry, because the game thinks another instance owns it.
    """

    def __init__(self):
        self._h = None       # mapping handle, held open persistently
        self._view = None    # mapped view, held open persistently

    def _open(self):
        """Open the mapping ONCE and keep it open. RaceRoom (like CrewChief /
        SimHub) only streams telemetry while a consumer holds the shared-memory
        handle open — opening/closing per read meant no consumer was present
        between reads, so the game wouldn't keep writing. Holding it open fixes
        data not appearing in races/replays."""
        h = _k32.OpenFileMappingW(_FILE_MAP_READ, False, R3E_SHARED_MEMORY_NAME)
        if not h:
            return False
        view = _k32.MapViewOfFile(h, _FILE_MAP_READ, 0, 0, SHARED_SIZE)
        if not view:
            _k32.CloseHandle(h)
            return False
        self._h, self._view = h, view
        return True

    def open(self):
        return self._view is not None or self._open()

    def read(self):
        """Return an R3EShared snapshot from the persistently-held view, or
        None if unavailable. Reopens automatically if the game restarts."""
        if self._view is None and not self._open():
            return None
        try:
            raw = _ct.string_at(self._view, SHARED_SIZE)
            s = R3EShared.from_buffer_copy(raw)
            # version 0 => our handle is stale (game closed/relaunched a new
            # mapping). Drop it and try a fresh open so we re-attach.
            if s.version_major != 3:
                self.close()
                if self._open():
                    raw = _ct.string_at(self._view, SHARED_SIZE)
                    s = R3EShared.from_buffer_copy(raw)
            return s
        except Exception:
            self.close()
            return None

    def close(self):
        if self._view:
            _k32.UnmapViewOfFile(self._view)
            self._view = None
        if self._h:
            _k32.CloseHandle(self._h)
            self._h = None


def fmt_time(t):
    if t is None or t < 0:
        return "--:--.---"
    m = int(t // 60)
    s = t - m * 60
    return f"{m}:{s:06.3f}" if m else f"{s:.3f}"


def _dump():
    print(f"struct size = {SHARED_SIZE} bytes")
    r = R3EReader()
    if not r.open():
        print("Could not open '$R3E' shared memory. Is RaceRoom running?")
        return
    while True:
        s = r.read()
        if s is None:
            print("read failed; retrying...")
            time.sleep(1)
            continue
        print("\x1b[2J\x1b[H", end="")  # clear screen
        print(f"version {s.version_major}.{s.version_minor}   "
              f"driver_data_size={s.driver_data_size} (ours={ctypes.sizeof(DriverData)})")
        print(f"track: {u8_to_str(s.track_name)} / {u8_to_str(s.layout_name)}  "
              f"len={s.layout_length:.0f}m")
        print(f"in_replay={s.game_in_replay} paused={s.game_paused} "
              f"in_menus={s.game_in_menus} session_type={s.session_type} "
              f"phase={s.session_phase}")
        print(f"laps_total={s.number_of_laps} time_remaining={fmt_time(s.session_time_remaining)} "
              f"num_cars={s.num_cars}")
        print(f"viewed slot_id={s.vehicle_info.slot_id} name={u8_to_str(s.vehicle_info.name)}")
        print("-" * 78)
        print(f"{'P':>2} {'#':>3} {'NAME':<22} {'LAP':>3} {'INT':>9} {'LAST':>9} {'BEST':>9} PIT")
        drivers = list(s.all_drivers_data_1)[:max(0, s.num_cars)]
        drivers.sort(key=lambda d: d.place if d.place > 0 else 9999)
        for d in drivers:
            di = d.driver_info
            print(f"{d.place:>2} {di.car_number:>3} {u8_to_str(di.name):<22.22} "
                  f"{d.completed_laps:>3} "
                  f"{fmt_time(d.time_delta_front):>9} "
                  f"{fmt_time(d.lap_time_previous_self):>9} "
                  f"{fmt_time(d.lap_time_best_self if hasattr(d,'lap_time_best_self') else -1):>9} "
                  f"{'Y' if d.in_pitlane==1 else ''}")
        time.sleep(0.5)


if __name__ == "__main__":
    _dump()
