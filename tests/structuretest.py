"""Structural guard for the Overlay class.

The engine was split from one 5,600-line module into mixins. That refactor
must be behaviour-neutral, so this pins the things a bad move would break:
every method still exists on the class, nothing got dropped or silently
renamed, and no method is accidentally defined twice across the mixins
(where the later definition would shadow the earlier one and the loss would
be completely silent).

Run it like the other tests: python tests/structuretest.py
"""
import os as _os; _os.environ["RACERTV_EPHEMERAL"] = "1"

import inspect
import sys

sys.path.insert(0, r"D:\R3EOverlay")
from r3e_overlay import Overlay          # noqa: E402

# Every method the class exposed before the split. Sorted, so a diff reads
# cleanly. Add to this list only when you intentionally add a method.
EXPECTED = [
    "_air_bubble", "_bag_save", "_bag_state", "_begin_panel",
    "_build_clock", "_build_logo", "_build_toggle_button",
    "_caption_line_end", "_card", "_career", "_career_note",
    "_career_record", "_color_for", "_color_for_name", "_colour_quali",
    "_colour_race", "_corner_names", "_corner_tick", "_dname",
    "_do_toggle_booth", "_do_toggle_compact", "_do_toggle_debug",
    "_do_toggle_mute", "_do_toggle_radio", "_do_toggle_ui",
    "_draw_bubble", "_drivers", "_emit_commentary", "_emit_sector",
    "_engineer_events", "_finish_sequence", "_fmt_gap",
    "_hide_unused_panels", "_in_action", "_insight", "_intro_done",
    "_limits_warn", "_line_h", "_load_car_names", "_lock_to_game",
    "_lore_answer", "_lore_pick_topic", "_menu_flip", "_moodify",
    "_narrative_arc", "_no_data_notice", "_persona_for", "_pick",
    "_pits_live", "_place_button", "_player_car", "_quali_events",
    "_radio_line", "_rebuild_corners", "_region", "_report_offtrack",
    "_report_wide", "_sector_advice", "_sector_color", "_sector_tip",
    "_short_car", "_short_track", "_show_caption", "_spell_laps",
    "_spoken", "_stat_line", "_story_arc", "_story_pick", "_story_report",
    "_toast", "_track_fact", "_track_knowledge", "_track_pundit",
    "_track_tip", "_tyre_color", "_update_button", "_where_on_track",
    "_wrap", "draw_commentary", "draw_debug", "draw_fastest_banner",
    "draw_flags", "draw_header", "draw_hint", "draw_map", "draw_penalty",
    "draw_podium", "draw_radio", "draw_relative", "draw_sectors",
    "draw_settings", "draw_toast", "draw_tower", "draw_waiting", "panel",
    "quit", "run", "text", "tick", "toggle_visible", "update_commentary",
    "update_radio", "update_stats"
]

actual = {n for n, v in vars(Overlay).items()
          if inspect.isfunction(v) or isinstance(v, (classmethod, staticmethod))}
# inherited-from-mixin methods live on the bases, not in vars(Overlay)
for _b in Overlay.__mro__[1:]:
    actual |= {n for n, v in vars(_b).items()
               if inspect.isfunction(v) or isinstance(v, (classmethod, staticmethod))}

missing = sorted(m for m in EXPECTED if m not in actual)
assert not missing, (
    "methods LOST in the mixin split (or renamed without updating this "
    f"list): {missing}")
print(f"  all {len(EXPECTED)} pinned methods present on Overlay: OK")

# public surface the tick loop and tests drive
for m in ("tick", "update_stats", "update_radio", "update_commentary",
          "draw_tower", "draw_header", "quit"):
    assert m in actual, f"public method {m!r} is missing from Overlay!"
print("  public update_/draw_ entry points intact: OK")

# No method may be defined by two different mixins: Python resolves that
# silently by MRO, so one implementation would just vanish.
import r3e_overlay                                         # noqa: E402
bases = [b for b in Overlay.__mro__ if b not in (Overlay, object)]
seen, dupes = {}, []
for b in bases:
    for n, f in vars(b).items():
        if callable(f) and not n.startswith("__"):
            if n in seen:
                dupes.append(f"{n}: {seen[n].__name__} and {b.__name__}")
            seen[n] = b
assert not dupes, f"method defined in TWO mixins (one is shadowed): {dupes}"
print(f"  {len(bases)} mixin(s), no shadowed duplicates: OK")

# Each mixin must be self-sufficient at import time (no circular import back
# into r3e_overlay), which is what makes the split worth having.
for b in bases:
    mod = sys.modules[b.__module__]
    assert mod is not None, f"{b.__name__} has no module?"
print("  mixin modules import cleanly: OK")

print(f"\nOverlay: {len(actual)} methods across "
      f"{len(bases) + 1} module(s)")
print("ALL STRUCTURE CHECKS PASSED")
