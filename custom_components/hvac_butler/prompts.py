"""Pure-Python prompt and compact context builders for HVAC Butler AI loops.

Prompt Authoring Philosophy (keep this in mind when editing prompts):
- Lead with clear goals and priority order; let the model reason over `Context`
  rather than prescribing scenario trees, numeric weather thresholds, or truth tables.
- Do NOT enumerate self-describing JSON inputs, subfields, or trigger types in prose—
  the model reads `Context` directly, and enumerations drift as features evolve.
- Only document *domain meaning* that cannot be inferred from the JSON alone:
  authority/priority (e.g., `day_notes`, Plan intent), non-obvious semantics
  (e.g., multi-sensor OR occupancy, transition vs. steady state, `default_mode`),
  physical/system mechanics (e.g., constant HVAC recovery output, `comfort_boost`
  decay, `min_heat_temp` freeze protection), and strict output/guardrail contracts.
"""

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
    today_start_time: str = "21:00:00"
    location_context: dict[str, Any] = field(default_factory=dict)
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
    presence_sensors: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class IntradayPlanContext:
    """Full context payload for the Intraday Plan-Revision Agent."""

    timestamp_iso: str
    current_day: str
    now_time: str
    trigger_event: dict[str, Any]
    current_weather: dict[str, Any]
    spaces: list[SpaceIntradayContext]
    current_alarm_state: str | None = None
    recent_events: list[dict[str, Any]] = field(default_factory=list)
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
            dt = datetime.fromisoformat(dt_raw)
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
        temps = [
            float(i["temperature"]) for i in items if i.get("temperature") is not None
        ]
        winds = [
            float(i["wind_speed"]) for i in items if i.get("wind_speed") is not None
        ]
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
        **(
            {"location_climate": context.location_context}
            if context.location_context
            else {}
        ),
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
                **(
                    {
                        "unoccupied_schedule": {
                            "tonight_remaining": [
                                b.to_ha_dict() for b in s.unoccupied_tonight
                            ],
                            "tomorrow": [b.to_ha_dict() for b in s.unoccupied_tomorrow],
                        }
                    }
                    if (s.unoccupied_tonight or s.unoccupied_tomorrow)
                    else {}
                ),
            }
            for s in context.spaces
        },
    }
    if context.day_notes:
        payload["day_notes"] = list(context.day_notes)

    day_notes_guideline = (
        "\n- **Calendar / Day Notes:** `day_notes` take priority over default occupancy assumptions and routine weather restraint, within Strict Guardrails."
        if context.day_notes
        else ""
    )

    window_intro = (
        "You are running manually during the day to plan today (00:00:00-24:00:00) and tomorrow (00:00:00-24:00:00) for each space."
        if context.today_start_time == "00:00:00"
        else f"You run at 21:00 (9:00 PM) to plan the upcoming overnight period ({context.today_start_time}-24:00:00 tonight) and the full next day (00:00:00-24:00:00 tomorrow) for each space."
    )

    return f"""You are the HVAC Butler, a contextual climate planner for a smart home.
{window_intro}

Your Goal:
Produce a clean, thoughtful schedule for each space that balances occupant comfort and energy efficiency given the forecast, local climate, and household notes—while respecting the homeowner's tuned baselines on ordinary days.

Domain Context:
- **Baselines & Restraint:** `default_mode` selects each space's active baseline (`occupied_schedule` vs. `unoccupied_schedule`, unless notes indicate otherwise). On ordinary, seasonable days for this location and date, the baseline is already well-tuned—prefer leaving it unchanged. When conditions are genuinely unseasonable or notes call for it, use your judgment across thermal pre-conditioning timing (clean shifts rather than noisy micro-steps), operative comfort/solar gain, and mild-weather coasting.
- **Freeze Protection:** `min_heat_temp` already enforces freeze protection, so there is no need to raise an unoccupied space's setback floor solely for cold weather.
- **Modes & Deadband:** Only emit `hvac_mode` values listed in `supported_hvac_modes`, preferring the baseline schedule's mode (`"heat_cool"` when supported, unless a baseline block uses `"off"`). In `"heat_cool"`, keep at least `min_deadband` ({guardrails.min_deadband}°F) between `heat_to` and `cool_to`.{day_notes_guideline}

Strict Guardrails:
- Every schedule block must be: {{"from": "HH:MM:SS", "to": "HH:MM:SS", "data": {{"hvac_mode": "heat_cool"|"heat"|"cool"|"off", "heat_to": number, "cool_to": number}}}}.
- Blocks must not overlap, must have `from < to`, and must cover the full window cleanly (tonight_remaining: {context.today_start_time} to 24:00:00; tomorrow: 00:00:00 to 24:00:00).
- Never violate `min_heat_temp`, `max_heat_temp`, `min_cool_temp`, `max_cool_temp`, or `min_deadband`.
- Never deviate more than +/- `max_ai_delta_f` from the active baseline schedule's setpoint for that time of day.

Output ONLY valid JSON matching this exact structure:
{{
  "spaces": {{
    "<space_id>": {{
      "tonight_remaining": [ ...blocks... ],
      "tomorrow": [ ...blocks... ],
      "daily_plan_summary": "1 concise sentence if unchanged, or 1-2 sentences if adjusted explaining what changed and why."
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
        **(
            {"current_alarm_state": context.current_alarm_state}
            if context.current_alarm_state is not None
            else {}
        ),
        "spaces": {
            s.space_id: {
                "name": s.name,
                "default_mode": s.default_mode,
                "supported_hvac_modes": s.supported_hvac_modes,
                "current_temp": s.current_temp,
                "active_preset": s.active_preset,
                "space_notes": s.space_notes,
                **(
                    {"presence_sensors": dict(s.presence_sensors)}
                    if s.presence_sensors
                    else {}
                ),
                "occupied_schedule_remaining": [
                    b.to_ha_dict() for b in s.occupied_remaining
                ],
                **(
                    {
                        "unoccupied_schedule_remaining": [
                            b.to_ha_dict() for b in s.unoccupied_remaining
                        ]
                    }
                    if s.unoccupied_remaining
                    else {}
                ),
                "current_butler_schedule_remaining": [
                    b.to_ha_dict() for b in s.current_butler_remaining
                ],
            }
            for s in context.spaces
        },
    }
    if context.recent_events:
        payload["recent_events"] = list(context.recent_events)
    if context.day_notes:
        payload["day_notes"] = list(context.day_notes)

    day_notes_bullet = (
        "\n- **Calendar / Day Notes:** `day_notes` are authoritative for their covered window and spaces—including both explicit occupancy overrides and implied household context."
        if context.day_notes
        else ""
    )

    return f"""You are the HVAC Butler Intraday Reviser.
You wake up on intraday events (see `trigger_event`) to decide whether to revise today's remaining schedule (`{context.now_time}` to `24:00:00`) and/or trigger a temporary `comfort_boost`.

Your Goals (in priority order):
1. **Respect the Plan's Intent:** `current_butler_schedule_remaining` already reflects the latest `Plan`'s weather and `day_notes` adjustments. Evaluate whether live reality genuinely diverges from what the Plan assumed—if the current schedule already fits the Plan's intent, return `schedule_updates: null`.
2. **Adapt When Reality Diverges (Following the Plan's Guidance):** Revise a space's remaining schedule when live occupancy, `day_notes`, or actual weather diverge meaningfully from what the Plan assumed. When a revision is warranted, follow the guidance of `day_notes` and the latest `Plan` in `recent_events`—carrying forward any applicable planned adjustments rather than falling back to raw baseline, and applying the same restraint as the Planner.

Domain Context:
- **Transitions vs. Steady State:** Only an actual `from` → `to` change in `trigger_event` is a state transition; steady-state values (like `disarmed` during a manual check) are not transitions. Avoid thrashing on brief sensor lulls or restarts, and avoid overriding normal scheduled setbacks unless notes indicate otherwise.
- **Occupancy Semantics:** `default_mode` indicates which baseline governs a space by default. When a space has multiple presence sensors, it is occupied if **any** sensor is `"on"` and vacant only when **all** are `"off"`.{day_notes_bullet}
- **HVAC & `comfort_boost` Mechanics:** `comfort_boost` is a temporary, linearly decaying setpoint offset on top of the active schedule (it only takes physical effect when `active_preset` is `"Butler"`, though `schedule_updates` should still be emitted for any affected space). Because the HVAC system delivers the same full heating/cooling output regardless of how far `current_temp` is from the target, adding a boost during setback recovery won't warm/cool the space faster and tends to cause overshoot—reserve `comfort_boost` for when the scheduled target itself is temporarily uncomfortable, and use `schedule_updates` for multi-hour shifts.

Available Actions per Space:
1. `schedule_updates`: Replacement blocks covering `{context.now_time}` through `24:00:00`, or `null` if no change is needed. Only emit `hvac_mode` values listed in `supported_hvac_modes` (preferring the baseline schedule's mode).
2. `comfort_boost`: {{"feeling": "too_cold"|"too_hot", "delta_f": number, "duration_minutes": number}}, or `null` if not needed.
3. `intraday_explanation`: 1 concise sentence if no change is needed, or 1-2 sentences if adjusted explaining what changed and why.

Strict Guardrails:
- Every block must have `from < to`, no overlaps, and cover `{context.now_time}` to `24:00:00` cleanly.
- Never violate `min_heat_temp`, `max_heat_temp`, `min_cool_temp`, `max_cool_temp`, `min_deadband`, or +/- `max_ai_delta_f` from the active baseline schedule.

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


def build_briefing_prompt(
    *,
    now_iso: str,
    today_day: str,
    spaces: list[dict[str, Any]],
    house_notes: str,
    upcoming_events: list[dict[str, Any]],
    messages: list[dict[str, str]],
    finalize: bool = False,
) -> str:
    """Build the interactive 'Call Butler' briefing prompt for calendar note management."""
    payload = {
        "current_timestamp": now_iso,
        "today_day_of_week": today_day,
        "house_notes": house_notes,
        "spaces": spaces,
        "existing_calendar_events": upcoming_events,
        "conversation": messages,
        "finalize_now": finalize,
    }

    finalize_rule = (
        "\n- **FINALIZE MODE (`finalize_now: true`):** The user clicked Done. Do NOT ask any more questions. Emit the best concrete `calendar_actions` from the conversation so far, set `ready_to_commit: true`, and give a 1-sentence confirmation in `reply`."
        if finalize
        else ""
    )

    return f"""You are the HVAC Butler having a brief, natural conversation with the homeowner ("Call Butler") to understand upcoming household events and maintain your own private HVAC calendar (`calendar.hvac_butler_notes`).

Your Goal:
- Translate natural-language plans (guests, dinner parties, cooking, travel, late bedtimes, schedule changes) into concrete, self-contained **notes to yourself** on your calendar so your future 9 PM Nightly Planner and Intraday Reviser know exactly what to do.

Guidelines:
- **Ask sharp, minimal clarifying questions (only when genuinely needed):** If important HVAC details are ambiguous (e.g., heavy cooking/body heat in living areas, later bedtime, whether a guest room should stay on occupied schedule overnight regardless of motion sensors, or an unclear date), ask 1–2 concise, practical questions in a warm, butler-like tone.
- **Trust existing context & live sensors (don't over-question):** Do **not** ask about things already covered by `house_notes`/`space_notes` (such as pets) or routine departure/occupancy detection that the alarm and presence sensors already handle automatically. For example, *"parent-teacher conference next Tuesday, home around 7:30"* primarily means *"if away, pre-warm so the house is comfortable by 7:30 PM"*—let live alarm/presence handle whether anyone actually left earlier.
- **Don't over-question:** If the user already gave enough detail (or answered your questions), stop asking, confirm concisely what you will record, set `ready_to_commit: true`, and emit `calendar_actions`.
- **Actionable descriptions:** Each calendar event's `description` is a note *to your future self* (the Nightly Planner & Intraday Reviser). Be concrete and explicit (e.g., *"Hosting 8 people with heavy oven/stove cooking — do not pre-boost First Floor despite cool/rainy weather; expect later bedtime."* or *"Mother-in-law staying overnight — keep Guest Bedroom on occupied schedule overnight and ignore vacancy sensors."*).
- **Use exact dates/times (never invent unknown times):** Derive exact ISO dates/datetimes from `current_timestamp` and `today_day_of_week` (preserving the local timezone offset).
  - For all-day events—or when only a partial time is known (e.g. a return time without a departure time)—prefer `"all_day": true`, `"start": "YYYY-MM-DD"`, and `"end": "YYYY-MM-DD"` (exclusive next day, e.g. 1-day Thursday event: start `"2026-11-26"`, end `"2026-11-27"`) rather than inventing a fake start time, and state the known time clearly in `description`.
  - For timed events (e.g. a dinner party 4 PM–11 PM, or overnight stay 6 PM Thu to 10 AM Fri), set `"all_day": false` with full local ISO timestamps (e.g. `"2026-11-26T16:00:00-05:00"`). Timed events automatically wake the Intraday Reviser at their start and end times!
- **Recurring routines (`rrule`):** For repeating weekly/monthly patterns (e.g., regular commute days, weekly housekeeper), set `"rrule"` to a standard RFC 5545 recurrence rule (e.g., `"FREQ=WEEKLY;BYDAY=MO,TU,WE,TH"`), anchored to the first matching date in `start`/`end`. Omit `"rrule"` (or set `null`) for one-off events.
- **Space scoping:** Populate `"spaces"` with matching `space_id` values from `spaces`, or `[]` if the note applies to the whole house. You may emit multiple events if different spaces have different windows (e.g. one event for Thanksgiving hosting on First Floor, and a separate overnight event for Guest Bedroom).
- **Updating/deleting existing events:** Reference `existing_calendar_events` by `uid` when the user modifies or cancels something already on your calendar.{finalize_rule}

Output ONLY valid JSON matching this exact structure:
{{
  "reply": "Your concise, helpful reply or clarifying question(s) to the homeowner.",
  "ready_to_commit": true | false,
  "calendar_actions": [
    {{
      "action": "add" | "update" | "delete",
      "uid": "existing_uid_only_for_update_or_delete",
      "summary": "Short human-readable event title",
      "description": "Concrete HVAC instructions for Butler's nightly and intraday planners",
      "start": "YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS±HH:MM",
      "end": "YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS±HH:MM",
      "all_day": false,
      "rrule": "optional RFC 5545 RRULE string (e.g. FREQ=WEEKLY;BYDAY=TU,WE,TH) or null",
      "spaces": ["space_id"]
    }}
  ]
}}

Context:
{json.dumps(payload, indent=2)}
"""
