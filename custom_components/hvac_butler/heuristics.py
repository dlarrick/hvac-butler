"""Pure-Python deterministic heuristic fallback planners for HVAC Butler.

Used automatically when the cloud/local AI task is unavailable, rate-limited,
or unconfigured so core MVP climate behaviors continue operating reliably.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from .const import MODE_OCCUPIED
from .guardrails import GuardrailConfig
from .prompts import IntradayPlanContext, NightlyPlanContext
from .schedule_utils import ScheduleBlock

_STORM_CONDITIONS = frozenset(
    {
        "snowy",
        "snowy-rainy",
        "hail",
        "lightning-rainy",
        "pouring",
        "windy",
        "windy-variant",
    }
)
_SEVERE_WINTRY_CONDITIONS = frozenset({"snowy", "snowy-rainy", "hail"})


def _extract_weather_metrics(
    weather_summary: dict[str, Any],
) -> tuple[float | None, float | None, float | None, float | None, set[str]]:
    """Extract (overnight_min, day_min, day_max, wind_max, conditions) from weather_summary."""
    periods = weather_summary.get("periods") or {}
    daily = weather_summary.get("tomorrow_daily") or {}
    current = weather_summary.get("current") or {}

    overnight = periods.get("overnight") or {}
    overnight_min: float | None = overnight.get("temp_min")
    if overnight_min is None and daily.get("temp_low") is not None:
        overnight_min = float(daily["temp_low"])

    day_mins: list[float] = []
    day_maxs: list[float] = []
    winds: list[float] = []
    conditions: set[str] = set()

    for period_name in ("morning", "midday", "evening"):
        p = periods.get(period_name) or {}
        if p.get("temp_min") is not None:
            day_mins.append(float(p["temp_min"]))
        if p.get("temp_max") is not None:
            day_maxs.append(float(p["temp_max"]))
        if p.get("wind_max") is not None:
            winds.append(float(p["wind_max"]))
        for cond in p.get("conditions") or []:
            conditions.add(str(cond).lower())

    if overnight.get("wind_max") is not None:
        winds.append(float(overnight["wind_max"]))
    for cond in overnight.get("conditions") or []:
        conditions.add(str(cond).lower())

    if daily.get("temp_low") is not None and not day_mins:
        day_mins.append(float(daily["temp_low"]))
    if daily.get("temp_high") is not None and not day_maxs:
        day_maxs.append(float(daily["temp_high"]))
    if daily.get("wind_speed") is not None:
        winds.append(float(daily["wind_speed"]))
    if daily.get("condition"):
        conditions.add(str(daily["condition"]).lower())

    if current.get("temperature") is not None:
        if not day_mins:
            day_mins.append(float(current["temperature"]))
        if not day_maxs:
            day_maxs.append(float(current["temperature"]))
    if current.get("wind_speed") is not None:
        winds.append(float(current["wind_speed"]))
    if current.get("condition"):
        conditions.add(str(current["condition"]).lower())

    day_min = min(day_mins) if day_mins else None
    day_max = max(day_maxs) if day_maxs else None
    wind_max = max(winds) if winds else None
    return overnight_min, day_min, day_max, wind_max, conditions


def _shift_morning_warmup_earlier(
    blocks: list[ScheduleBlock], shift_min: int
) -> tuple[list[ScheduleBlock], int]:
    """Shift the first morning warm-up boundary (04:00–10:00) earlier by up to `shift_min`."""
    out = [replace(b) for b in blocks]
    for idx in range(1, len(out)):
        prev = out[idx - 1]
        curr = out[idx]
        if not (240 <= curr.start_min <= 600):
            continue
        if (
            prev.heat_to is not None
            and curr.heat_to is not None
            and curr.heat_to - prev.heat_to >= 2.0
        ):
            new_start = max(prev.start_min + 15, curr.start_min - shift_min)
            actual_shift = curr.start_min - new_start
            if actual_shift > 0:
                prev.end_min = new_start
                curr.start_min = new_start
                return out, actual_shift
            break
    return out, 0


def _shift_precool_earlier(
    blocks: list[ScheduleBlock], shift_min: int
) -> tuple[list[ScheduleBlock], int]:
    """Shift the first daytime cooling step-down (06:00–18:00) earlier by up to `shift_min`."""
    out = [replace(b) for b in blocks]
    for idx in range(1, len(out)):
        prev = out[idx - 1]
        curr = out[idx]
        if not (360 <= curr.start_min <= 1080):
            continue
        if (
            prev.cool_to is not None
            and curr.cool_to is not None
            and prev.cool_to - curr.cool_to >= 2.0
        ):
            new_start = max(prev.start_min + 15, curr.start_min - shift_min)
            actual_shift = curr.start_min - new_start
            if actual_shift > 0:
                prev.end_min = new_start
                curr.start_min = new_start
                return out, actual_shift
            break
    return out, 0


def _apply_occupied_heat_offset(
    blocks: list[ScheduleBlock], delta_f: float
) -> tuple[list[ScheduleBlock], bool]:
    """Add `+delta_f` to occupied (highest-tier) heating blocks without raising sleep setbacks."""
    heat_vals = [
        b.heat_to for b in blocks if b.hvac_mode != "off" and b.heat_to is not None
    ]
    if not heat_vals:
        return [replace(b) for b in blocks], False
    occupied_floor = max(heat_vals) - 1.0
    changed = False
    out: list[ScheduleBlock] = []
    for blk in blocks:
        copy = replace(blk)
        if (
            copy.hvac_mode in ("heat_cool", "heat")
            and copy.heat_to is not None
            and copy.heat_to >= occupied_floor
        ):
            copy.heat_to = round(copy.heat_to + delta_f, 1)
            changed = True
        out.append(copy)
    return out, changed


def build_heuristic_nightly_plan(
    context: NightlyPlanContext,
    guardrails: GuardrailConfig,
) -> dict[str, Any]:
    """Build a deterministic nightly plan matching the AI JSON contract."""
    overnight_min, day_min, day_max, wind_max, conditions = _extract_weather_metrics(
        context.weather_summary
    )
    current = context.weather_summary.get("current") or {}
    curr_temp = (
        float(current["temperature"])
        if current.get("temperature") is not None
        else None
    )
    curr_wind = (
        float(current["wind_speed"]) if current.get("wind_speed") is not None else None
    )
    curr_cond = str(current.get("condition") or "").lower()

    cold_and_windy_tomorrow = (
        day_min is not None
        and day_min <= 35.0
        and (
            (wind_max is not None and wind_max >= 20.0)
            or bool(conditions & _STORM_CONDITIONS)
        )
    )
    chill_delta_f = 0.0
    if cold_and_windy_tomorrow:
        severe = (wind_max is not None and wind_max >= 28.0) or (
            day_min is not None
            and day_min <= 25.0
            and bool(conditions & _SEVERE_WINTRY_CONDITIONS)
        )
        chill_delta_f = min(guardrails.max_ai_delta_f, 2.0 if severe else 1.0)

    cold_and_windy_tonight = (
        curr_temp is not None
        and curr_temp <= 35.0
        and (
            (curr_wind is not None and curr_wind >= 20.0)
            or curr_cond in _STORM_CONDITIONS
        )
    )

    spaces_out: dict[str, Any] = {}
    for space in context.spaces:
        use_unocc = space.default_mode != MODE_OCCUPIED and bool(
            space.unoccupied_tonight or space.unoccupied_tomorrow
        )
        tonight_base = space.unoccupied_tonight if use_unocc else space.occupied_tonight
        tomorrow_base = (
            space.unoccupied_tomorrow if use_unocc else space.occupied_tomorrow
        )

        if use_unocc:
            spaces_out[space.space_id] = {
                "tonight_remaining": [b.to_ha_dict() for b in tonight_base],
                "tomorrow": [b.to_ha_dict() for b in tomorrow_base],
                "daily_plan_summary": "Maintained unoccupied baseline (heuristic fallback).",
            }
            continue

        modes = set(space.supported_hvac_modes)
        can_heat = bool(modes & {"heat", "heat_cool"})
        can_cool = bool(modes & {"cool", "heat_cool"})

        tonight_blocks = [replace(b) for b in tonight_base]
        tomorrow_blocks = [replace(b) for b in tomorrow_base]
        reasons: list[str] = []

        # 1. Early morning recovery shift on frigid overnight lows
        if can_heat and overnight_min is not None and overnight_min <= 20.0:
            shift_target = 45 if overnight_min <= 5.0 else 30
            tomorrow_blocks, shifted = _shift_morning_warmup_earlier(
                tomorrow_blocks, shift_target
            )
            if shifted > 0:
                reasons.append(
                    f"shifted morning warm-up {shifted}m earlier for {overnight_min:.0f}°F overnight low"
                )

        # 2. Wind / storm operative chill offset on occupied blocks
        if can_heat and chill_delta_f > 0.0:
            tomorrow_blocks, boosted_tom = _apply_occupied_heat_offset(
                tomorrow_blocks, chill_delta_f
            )
            if cold_and_windy_tonight:
                tonight_blocks, _ = _apply_occupied_heat_offset(
                    tonight_blocks, min(chill_delta_f, 1.0)
                )
            if boosted_tom:
                reasons.append(
                    f"added +{chill_delta_f:.0f}°F operative heat offset for cold/windy weather"
                )

        # 3. Hot-weather pre-cooling shift
        if can_cool and day_max is not None and day_max >= 90.0:
            tomorrow_blocks, shifted_cool = _shift_precool_earlier(tomorrow_blocks, 30)
            if shifted_cool > 0:
                reasons.append(
                    f"started pre-cooling {shifted_cool}m earlier for {day_max:.0f}°F high"
                )

        if reasons:
            summary = f"Heuristic fallback: {'; '.join(reasons)}."
        else:
            summary = "Maintained baseline schedule (heuristic fallback)."

        spaces_out[space.space_id] = {
            "tonight_remaining": [b.to_ha_dict() for b in tonight_blocks],
            "tomorrow": [b.to_ha_dict() for b in tomorrow_blocks],
            "daily_plan_summary": summary,
        }

    return {"spaces": spaces_out}


def _needs_unoccupied_shift(
    current_blocks: list[ScheduleBlock],
    unoccupied_blocks: list[ScheduleBlock],
) -> bool:
    """Return True if current_blocks is more conditioned than unoccupied_blocks."""
    if not unoccupied_blocks or current_blocks == unoccupied_blocks:
        return False
    unocc_max_heat = max(
        (b.heat_to for b in unoccupied_blocks if b.heat_to is not None),
        default=None,
    )
    unocc_min_cool = min(
        (b.cool_to for b in unoccupied_blocks if b.cool_to is not None),
        default=None,
    )
    for blk in current_blocks:
        if blk.hvac_mode == "off":
            continue
        if (
            blk.heat_to is not None
            and unocc_max_heat is not None
            and blk.heat_to > unocc_max_heat + 0.5
        ):
            return True
        if (
            blk.cool_to is not None
            and unocc_min_cool is not None
            and blk.cool_to < unocc_min_cool - 0.5
        ):
            return True
    return False


def build_heuristic_intraday_revision(
    context: IntradayPlanContext,
    guardrails: GuardrailConfig,
) -> dict[str, Any]:
    """Build a deterministic intraday revision matching the AI JSON contract."""
    del guardrails  # Clamping and deadband enforcement are handled by guardrails.py
    trig = context.trigger_event or {}
    trig_type = str(trig.get("type", "")).lower()
    trig_from = str(trig.get("from", "")).lower()
    trig_to = str(trig.get("to", trig.get("state", ""))).lower()
    alarm = str(context.current_alarm_state or "").lower()

    spaces_out: dict[str, Any] = {}
    for space in context.spaces:
        has_unocc = bool(space.unoccupied_remaining)
        curr = space.current_butler_remaining
        occ = space.occupied_remaining
        unocc = space.unoccupied_remaining

        has_sensors = bool(space.presence_sensors)
        any_on = any(
            str(v.get("state", "")).lower() == "on"
            for v in space.presence_sensors.values()
        )
        all_off = has_sensors and not any_on

        updates: list[dict[str, Any]] | None = None
        explanation = "Maintained current schedule (heuristic fallback)."

        # 1. Alarm armed_away (transition or steady state) -> unoccupied
        if alarm == "armed_away" or (
            trig_type == "alarm_change" and trig_to == "armed_away"
        ):
            if has_unocc and curr != unocc:
                updates = [b.to_ha_dict() for b in unocc]
                explanation = (
                    "Alarm armed away; shifted to unoccupied schedule "
                    "(heuristic fallback)."
                )
            else:
                explanation = (
                    "Already on unoccupied schedule while armed away "
                    "(heuristic fallback)."
                )

        # 2. Alarm armed_away -> disarmed -> restore default_mode baseline
        elif (
            trig_type == "alarm_change"
            and trig_from == "armed_away"
            and trig_to == "disarmed"
        ):
            target = (
                occ if (space.default_mode == MODE_OCCUPIED or not has_unocc) else unocc
            )
            if curr != target:
                updates = [b.to_ha_dict() for b in target]
                explanation = (
                    f"Alarm disarmed from away; restored {space.default_mode} "
                    "schedule (heuristic fallback)."
                )
            else:
                explanation = (
                    f"Alarm disarmed; already on {space.default_mode} schedule "
                    "(heuristic fallback)."
                )

        # 3. Presence on (debounced transition or manual check with live occupancy)
        elif (trig_type == "presence_change" and trig_to == "on") or (
            trig_type == "manual_intraday" and any_on
        ):
            if (has_unocc and curr == unocc) or not curr:
                updates = [b.to_ha_dict() for b in occ]
                explanation = (
                    "Sustained presence detected; switched to occupied schedule "
                    "(heuristic fallback)."
                )
            else:
                explanation = (
                    "Presence active; preserved current occupied/planned schedule "
                    "(heuristic fallback)."
                )

        # 4. Presence off (debounced transition or manual check with all sensors off)
        elif (trig_type == "presence_change" and trig_to == "off") or (
            trig_type == "manual_intraday" and all_off
        ):
            if has_unocc and _needs_unoccupied_shift(curr, unocc):
                updates = [b.to_ha_dict() for b in unocc]
                explanation = (
                    "Sustained vacancy detected; shifted to unoccupied schedule "
                    "(heuristic fallback)."
                )
            else:
                explanation = (
                    "Space vacant; already at setback/unoccupied level "
                    "(heuristic fallback)."
                )

        spaces_out[space.space_id] = {
            "schedule_updates": updates,
            "comfort_boost": None,
            "intraday_explanation": explanation,
        }

    return {"spaces": spaces_out}
