"""Pure-Python prompt and compact context builders for HVAC Butler AI loops."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .guardrails import GuardrailConfig
from .schedule_utils import ScheduleBlock


@dataclass(slots=True)
class SpaceNightlyContext:
    """Normalized per-space input for the 21:00 Nightly Macro-Planner."""

    space_id: str
    name: str
    default_mode: str
    current_temp: float | None
    active_preset: str | None
    occupied_tonight: list[ScheduleBlock]
    occupied_tomorrow: list[ScheduleBlock]
    unoccupied_tonight: list[ScheduleBlock]
    unoccupied_tomorrow: list[ScheduleBlock]
    supported_hvac_modes: list[str] = field(
        default_factory=lambda: ["heat_cool", "heat", "cool", "off"]
    )
    space_notes: str = ""


@dataclass(slots=True)
class NightlyPlanContext:
    """Full context payload for the Nightly Macro-Planner."""

    timestamp_iso: str
    tonight_day: str
    tomorrow_day: str
    is_weekend_tomorrow: bool
    weather_summary: dict[str, Any]
    spaces: list[SpaceNightlyContext]
    house_notes: str = ""
    # Reserved for future post-MVP day-specific free-form instructions
    day_notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SpaceIntradayContext:
    """Normalized per-space input for the Intraday Plan-Revision Agent."""

    space_id: str
    name: str
    default_mode: str
    current_temp: float | None
    active_preset: str | None
    occupied_remaining: list[ScheduleBlock]
    unoccupied_remaining: list[ScheduleBlock]
    current_butler_remaining: list[ScheduleBlock]
    supported_hvac_modes: list[str] = field(
        default_factory=lambda: ["heat_cool", "heat", "cool", "off"]
    )
    space_notes: str = ""


@dataclass(slots=True)
class IntradayPlanContext:
    """Full context payload for the Intraday Plan-Revision Agent."""

    timestamp_iso: str
    current_day: str
    now_time: str
    trigger_event: dict[str, Any]
    current_weather: dict[str, Any]
    spaces: list[SpaceIntradayContext]
    house_notes: str = ""
    # Reserved for future post-MVP day-specific free-form instructions
    day_notes: list[str] = field(default_factory=list)


def summarize_forecast(
    forecast_entries: list[dict[str, Any]] | None,
    *,
    current_temp: float | None = None,
    current_condition: str | None = None,
    current_wind_speed: float | None = None,
    tomorrow_date_str: str | None = None,
) -> dict[str, Any]:
    """Condense raw HA weather forecast entries into a compact token-friendly summary."""
    summary: dict[str, Any] = {
        "current": {
            "temperature": current_temp,
            "condition": current_condition,
            "wind_speed": current_wind_speed,
        }
    }
    if not forecast_entries:
        return summary

    # Bucket hourly forecasts into overnight / morning / midday / evening when timestamps have hours
    buckets: dict[str, list[dict[str, Any]]] = {
        "overnight": [],
        "morning": [],
        "midday": [],
        "evening": [],
    }
    daily_matches: list[dict[str, Any]] = []

    for entry in forecast_entries[:36]:
        dt_raw = entry.get("datetime")
        if not isinstance(dt_raw, str):
            continue
        try:
            dt = datetime.fromisoformat(dt_raw.replace("Z", "+00:00"))
        except ValueError:
            continue

        # Detect daily forecast entries (no time variance or templow present)
        if entry.get("templow") is not None:
            if tomorrow_date_str is None or dt.date().isoformat() == tomorrow_date_str:
                daily_matches.append(
                    {
                        "date": dt.date().isoformat(),
                        "condition": entry.get("condition"),
                        "temp_high": entry.get("temperature"),
                        "temp_low": entry.get("templow"),
                        "wind_speed": entry.get("wind_speed"),
                        "precipitation_probability": entry.get(
                            "precipitation_probability"
                        ),
                    }
                )
            continue

        hour = dt.hour
        if hour >= 21 or hour < 6:
            buckets["overnight"].append(entry)
        elif 6 <= hour < 11:
            buckets["morning"].append(entry)
        elif 11 <= hour < 17:
            buckets["midday"].append(entry)
        else:
            buckets["evening"].append(entry)

    if daily_matches:
        summary["tomorrow_daily"] = daily_matches[0]

    period_summary: dict[str, Any] = {}
    for name, items in buckets.items():
        if not items:
            continue
        temps = [float(i["temperature"]) for i in items if i.get("temperature") is not None]
        winds = [float(i["wind_speed"]) for i in items if i.get("wind_speed") is not None]
        conditions = [str(i["condition"]) for i in items if i.get("condition")]
        period_summary[name] = {
            "temp_min": round(min(temps), 1) if temps else None,
            "temp_max": round(max(temps), 1) if temps else None,
            "wind_max": round(max(winds), 1) if winds else None,
            "conditions": sorted(set(conditions)),
        }
    if period_summary:
        summary["periods"] = period_summary

    return summary


def build_nightly_prompt(
    context: NightlyPlanContext,
    guardrails: GuardrailConfig,
) -> str:
    """Build the complete Nightly Macro-Planner (21:00) instructions + JSON context."""
    payload: dict[str, Any] = {
        "timestamp": context.timestamp_iso,
        "tonight_day": context.tonight_day,
        "tomorrow_day": context.tomorrow_day,
        "is_weekend_tomorrow": context.is_weekend_tomorrow,
        "guardrails": {
            "min_heat_temp": guardrails.min_heat_temp,
            "max_heat_temp": guardrails.max_heat_temp,
            "min_cool_temp": guardrails.min_cool_temp,
            "max_cool_temp": guardrails.max_cool_temp,
            "min_deadband": guardrails.min_deadband,
            "max_ai_delta_f": guardrails.max_ai_delta_f,
        },
        "house_notes": context.house_notes,
        "weather": context.weather_summary,
        "spaces": {
            s.space_id: {
                "name": s.name,
                "default_mode": s.default_mode,
                "supported_hvac_modes": s.supported_hvac_modes,
                "current_temp": s.current_temp,
                "active_preset": s.active_preset,
                "space_notes": s.space_notes,
                "occupied_schedule": {
                    "tonight_remaining": [b.to_ha_dict() for b in s.occupied_tonight],
                    "tomorrow": [b.to_ha_dict() for b in s.occupied_tomorrow],
                },
                "unoccupied_schedule": {
                    "tonight_remaining": [b.to_ha_dict() for b in s.unoccupied_tonight],
                    "tomorrow": [b.to_ha_dict() for b in s.unoccupied_tomorrow],
                },
            }
            for s in context.spaces
        },
    }
    if context.day_notes:
        payload["day_notes"] = list(context.day_notes)

    day_notes_guideline = (
        "\n6. Day-Specific Instructions:\n"
        "   - Honor any instructions in `day_notes` for tonight/tomorrow while still obeying all Strict Guardrails."
        if context.day_notes
        else ""
    )

    return f"""You are the HVAC Butler, a contextual climate planner for a smart home.
You run at 21:00 (9:00 PM) to plan the upcoming overnight period (21:00:00-24:00:00 tonight) and the full next day (00:00:00-24:00:00 tomorrow) for each space.

Guidelines:
1. Supported Modes & Deadband:
   - Only emit `hvac_mode` values listed in each space's `supported_hvac_modes` (e.g. a heat-only thermostat must use `"heat"` or `"off"`, never `"heat_cool"` or `"cool"`).
   - Prefer the mode used by the space's baseline schedule (`"heat_cool"` when supported) unless a baseline block uses `"off"`.
   - When using `"heat_cool"`, maintain at least `min_deadband` ({guardrails.min_deadband}°F) between `heat_to` and `cool_to`.
2. Heating Season (Cold Weather):
   - On very cold nights, allow overnight setback blocks to drift slightly lower (within `max_ai_delta_f` and `min_heat_temp`) and start morning warm-up 15-45 minutes earlier by shifting the morning occupied transition earlier (rather than inventing intermediate half-step temperatures).
   - On cold, windy, or stormy days, add +1°F to +2°F to `heat_to` during occupied hours to compensate for lower mean radiant wall temperatures and infiltration.
   - On cold, sunny days, allow a slight midday float (-1°F on `heat_to`) in spaces noted as having strong solar gain.
3. Cooling Season (Hot Weather):
   - On hot or humid days (when cooling is supported), consider starting pre-cooling 15-45 minutes before peak afternoon heat or occupied return, and allow modest unoccupied daytime drift (within `max_ai_delta_f` and `max_cool_temp`).
   - On hot, sunny afternoons, tighten `cool_to` slightly (-1°F) in spaces noted as having strong solar heat gain.
4. Shoulder Seasons & Mild/Unexpected Weather:
   - Balance comfort and efficiency in both directions: on an unexpectedly warm night in an occupied bedroom (when cooling is supported), keep `cool_to` comfortable for sleeping rather than letting the room stay stuffy, unless outdoor temperatures are dropping rapidly overnight.
   - On mild days or nights where outdoor conditions naturally stay comfortable, avoid unnecessary heating or cooling cycles (keep a generous comfortable deadband when using `"heat_cool"`).{day_notes_guideline}

Strict Guardrails:
- Every schedule block must be: {{"from": "HH:MM:SS", "to": "HH:MM:SS", "data": {{"hvac_mode": "heat_cool"|"heat"|"cool"|"off", "heat_to": number, "cool_to": number}}}}.
- Blocks must not overlap, must have from < to, and must cover the full window cleanly (tonight_remaining: 21:00:00 to 24:00:00; tomorrow: 00:00:00 to 24:00:00).
- Never violate `min_heat_temp`, `max_heat_temp`, `min_cool_temp`, `max_cool_temp`, or `min_deadband`.
- Never deviate more than +/- `max_ai_delta_f` from the active baseline schedule's setpoint for that time of day.

Output ONLY valid JSON matching this exact structure:
{{
  "spaces": {{
    "<space_id>": {{
      "tonight_remaining": [ ...blocks... ],
      "tomorrow": [ ...blocks... ],
      "daily_plan_summary": "1-3 sentence freeform summary of tweaks made and why."
    }}
  }}
}}

Context:
{json.dumps(payload, indent=2)}
"""


def build_intraday_prompt(
    context: IntradayPlanContext,
    guardrails: GuardrailConfig,
) -> str:
    """Build the complete Intraday Plan-Revision Agent instructions + JSON context."""
    payload: dict[str, Any] = {
        "timestamp": context.timestamp_iso,
        "current_day": context.current_day,
        "now_time": context.now_time,
        "trigger_event": context.trigger_event,
        "guardrails": {
            "min_heat_temp": guardrails.min_heat_temp,
            "max_heat_temp": guardrails.max_heat_temp,
            "min_cool_temp": guardrails.min_cool_temp,
            "max_cool_temp": guardrails.max_cool_temp,
            "min_deadband": guardrails.min_deadband,
            "max_ai_delta_f": guardrails.max_ai_delta_f,
        },
        "house_notes": context.house_notes,
        "current_weather": context.current_weather,
        "spaces": {
            s.space_id: {
                "name": s.name,
                "default_mode": s.default_mode,
                "supported_hvac_modes": s.supported_hvac_modes,
                "current_temp": s.current_temp,
                "active_preset": s.active_preset,
                "space_notes": s.space_notes,
                "occupied_schedule_remaining": [
                    b.to_ha_dict() for b in s.occupied_remaining
                ],
                "unoccupied_schedule_remaining": [
                    b.to_ha_dict() for b in s.unoccupied_remaining
                ],
                "current_butler_schedule_remaining": [
                    b.to_ha_dict() for b in s.current_butler_remaining
                ],
            }
            for s in context.spaces
        },
    }
    if context.day_notes:
        payload["day_notes"] = list(context.day_notes)

    return f"""You are the HVAC Butler Intraday Reviser.
You wake up when an intraday event occurs (alarm state change or debounced space presence/vacancy) and decide how to adjust the remaining schedule for today (from `{context.now_time}` to `24:00:00`) and whether to trigger an immediate `comfort_boost`.

Available Actions per Space:
1. `schedule_updates`: Replacement blocks covering `{context.now_time}` through `24:00:00` for that space's butler schedule, or `null` if no change is needed. Only emit `hvac_mode` values listed in each space's `supported_hvac_modes` (preferring the baseline schedule's mode).
2. `comfort_boost` (optional, `null` if not needed): {{"feeling": "too_cold"|"too_hot", "delta_f": number, "duration_minutes": number}}. Use when an occupant arrives or enters a room that is noticeably below/above target, as an immediate comfort bridge. Note: `comfort_boost` only takes physical effect if `active_preset` is `"Butler"`, though you should still update `schedule_updates` for all affected spaces.
3. `intraday_explanation`: A concise 1-2 sentence freeform explanation of what changed and why (or why no change was needed).

Guidelines:
- On `armed_away`: transition spaces toward `unoccupied_schedule_remaining`, except where `house_notes` or `space_notes` indicate a reason to keep a room conditioned (e.g., pets, sensitive plants, or a housesitter).
- On `disarmed`: occupants are home (or just arrived) — restore normally-occupied spaces toward `occupied_schedule_remaining`; if a room is currently noticeably cold/warm, consider a `comfort_boost`.
- On `armed_home` (perimeter alarm armed while occupants are home and staying in): confirms normally-occupied spaces are occupied — ensure they follow `occupied_schedule_remaining` rather than an away setback.
- On sustained presence `on` in a normally unoccupied space: if `current_temp` is noticeably below `occupied_schedule_remaining`'s current `heat_to` (e.g. >1.5°F), issue a `comfort_boost` AND switch upcoming blocks to `occupied_schedule_remaining` for a reasonable window before returning to `unoccupied_schedule_remaining`.
- On sustained vacancy `off` during an occupied window: gently shift toward `unoccupied_schedule_remaining` (respecting `space_notes` about stationary occupants or sensor quirks).
- Strict Guardrails: Every block must have `from < to`, no overlaps, cover `{context.now_time}` to `24:00:00`, and respect `min_heat_temp`, `max_heat_temp`, `min_cool_temp`, `max_cool_temp`, and `min_deadband`.

Output ONLY valid JSON matching this exact structure:
{{
  "spaces": {{
    "<space_id>": {{
      "schedule_updates": [ ...blocks... ] | null,
      "comfort_boost": {{ "feeling": "too_cold", "delta_f": 2.0, "duration_minutes": 60 }} | null,
      "intraday_explanation": "1-2 sentence freeform explanation."
    }}
  }}
}}

Context:
{json.dumps(payload, indent=2)}
"""
