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
        "\n6. Day-Specific Instructions:\n"
        "   - Honor any instructions in `day_notes` for tonight/tomorrow while still obeying all Strict Guardrails."
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

Guidelines:
1. Default to Baseline & Local Climate Context:
   - Each space's **active baseline schedule** is determined by `default_mode`: use `occupied_schedule` when `default_mode` is `"occupied"`, and `unoccupied_schedule` when `default_mode` is `"unoccupied"` (unless `space_notes` or `day_notes` explicitly indicate otherwise). Never copy `occupied_schedule` into a `default_mode: "unoccupied"` space when maintaining baseline.
   - Use `location_climate` (approximate coordinates, elevation, timezone, and date) to judge whether the forecast is **seasonable** or **unseasonable** for this home's climate and time of year.
   - On ordinary, **seasonable** days, the user's active baseline schedules are already well-tuned: **prefer leaving blocks unchanged** rather than making gratuitous tweaks. Reserve proactive adjustments for genuinely **unseasonable** or severe conditions (especially unseasonably cold, windy, or stormy weather in winter, or unseasonably hot/humid spells in summer).
   - Never raise an **unoccupied** space's setback heat floor just because it is cold outside (`min_heat_temp` already enforces freeze protection).
2. Supported Modes & Deadband:
   - Only emit `hvac_mode` values listed in each space's `supported_hvac_modes` (e.g. a heat-only thermostat must use `"heat"` or `"off"`, never `"heat_cool"` or `"cool"`).
   - Prefer the mode used by the space's baseline schedule (`"heat_cool"` when supported) unless a baseline block uses `"off"`.
   - When using `"heat_cool"`, maintain at least `min_deadband` ({guardrails.min_deadband}°F) between `heat_to` and `cool_to`.
3. Heating Season (Cold Weather):
   - **Deep cold / earlier warm-up:** Only shift morning warm-up earlier (15-45 minutes, by shifting the morning occupied transition earlier rather than inventing intermediate half-step temperatures) or allow extra overnight setback drift when overnight lows are genuinely frigid (below ~20°F, or well below seasonable lows for `location_climate`).
   - **Operative Temperature (Wind & Storm Chill):** Only add +1°F to +2°F to occupied `heat_to` during genuinely **cold AND windy/stormy** conditions (temps below ~35°F combined with sustained winds ≥ 20 mph or active snow/ice storm). Do **not** add a chill boost on calm or lightly breezy sunny days (< 15 mph wind).
   - **Sunny Winter Days:** On bright, sunny days (especially 35°F+), do **not** boost heating; leave baseline unchanged or allow a gentle -1°F midday solar float in spaces noted as having strong solar gain.
4. Cooling Season (Hot Weather):
   - On genuinely hot or humid days (≥ 85°F, when cooling is supported), consider starting pre-cooling 15-45 minutes before peak afternoon heat or occupied return, and allow modest unoccupied daytime drift (within `max_ai_delta_f` and `max_cool_temp`).
   - On hot, sunny afternoons, tighten `cool_to` slightly (-1°F) in spaces noted as having strong solar heat gain.
5. Shoulder Seasons & Mild/Unexpected Weather:
   - Balance comfort and efficiency in both directions: on an unexpectedly warm night in an occupied bedroom (when cooling is supported), keep `cool_to` comfortable for sleeping rather than letting the room stay stuffy, unless outdoor temperatures are dropping rapidly overnight.
   - On mild days or nights where outdoor conditions naturally stay comfortable, avoid unnecessary heating or cooling cycles (keep a generous comfortable deadband when using `"heat_cool"`).{day_notes_guideline}

Strict Guardrails:
- Every schedule block must be: {{"from": "HH:MM:SS", "to": "HH:MM:SS", "data": {{"hvac_mode": "heat_cool"|"heat"|"cool"|"off", "heat_to": number, "cool_to": number}}}}.
- Blocks must not overlap, must have from < to, and must cover the full window cleanly (tonight_remaining: {context.today_start_time} to 24:00:00; tomorrow: 00:00:00 to 24:00:00).
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
        "\n- **Calendar / Day Notes (`day_notes`):** Treat instructions in `day_notes` as authoritative overrides for the covered time window and spaces (e.g., keeping a guest bedroom on `occupied_schedule_remaining` overnight regardless of vacancy sensors, holding off on weather pre-boosts during heavy cooking, or delaying bedtime setbacks)."
        if context.day_notes
        else ""
    )

    return f"""You are the HVAC Butler Intraday Reviser.
You wake up when an intraday event occurs (alarm state change or debounced space presence/vacancy) and decide how to adjust the remaining schedule for today (from `{context.now_time}` to `24:00:00`) and whether to trigger an immediate `comfort_boost`.

Available Actions per Space:
1. `schedule_updates`: Replacement blocks covering `{context.now_time}` through `24:00:00` for that space's butler schedule, or `null` if no change is needed. Only emit `hvac_mode` values listed in each space's `supported_hvac_modes` (preferring the baseline schedule's mode).
2. `comfort_boost` (optional, `null` if not needed): {{"feeling": "too_cold"|"too_hot", "delta_f": number, "duration_minutes": number}}. A **temporary, linearly decaying setpoint offset** above/below the active schedule. Use **only** when the scheduled setpoint itself is temporarily inappropriate for comfort and should gently decay back to the schedule (for ongoing multi-hour conditions, adjust `schedule_updates` instead). **Never** issue `comfort_boost` merely because `current_temp` is far from the target setpoint (e.g., during setback recovery after disarming or switching to an occupied schedule)—the HVAC system already heats/cools toward the target at full capacity, and adding a boost only causes unnecessary overshoot. Note: `comfort_boost` only takes physical effect if `active_preset` is `"Butler"`, though you should still update `schedule_updates` for all affected spaces.
3. `intraday_explanation`: 1 concise sentence if no change is needed, or 1-2 sentences if adjusted explaining what changed and why.

Guidelines:
- **Steady State vs. Transitions & Short-Term Memory:** `trigger_event` describes *what woke you* (including `from` → `to` state when a sensor or alarm transitioned), `current_alarm_state` and each space's `presence_sensors` (with `state`, `for_minutes`, `device_class`, and `name`) show the **live current state** of the house, and `recent_events` (when present) provides chronological short-term memory of Butler's decisions since the last daily Plan keyframe. Use `recent_events` and `for_minutes` to avoid thrashing and to distinguish brief lulls from sustained occupancy or vacancy.
- **Alarm Semantics:**
  - Steady-state `current_alarm_state: "armed_away"` (or a transition to `armed_away`) is a clear signal that nobody is home in any space: transition spaces toward `unoccupied_schedule_remaining`, except where `house_notes` or `space_notes` indicate a reason to keep a room conditioned (e.g., pets, sensitive plants, or a housesitter).
  - Steady-state `current_alarm_state: "disarmed"` is **NOT** an arrival signal by itself — only the **transition** `armed_away` → `disarmed` means occupants just returned home from being away. On `armed_away` → `disarmed`, revert each space to its own `default_mode` baseline (`occupied_schedule_remaining` for `default_mode: "occupied"` spaces; keep `default_mode: "unoccupied"` spaces on `unoccupied_schedule_remaining` rather than assuming every room will be used) with `comfort_boost: null` (let the system recover cleanly to the restored setpoint without overshooting).
  - On `armed_home` (perimeter alarm armed while occupants are home and staying in): confirms occupants are home — ensure each space follows its own `default_mode` baseline (respecting live `presence_sensors`).
- **Presence Semantics:** A space with multiple `presence_sensors` is occupied if **any** sensor is `"on"` and vacant only when **all** sensors are `"off"`.
  - On sustained presence `on` (e.g. `off` → `on`): if the space is **already following its `occupied_schedule_remaining`** (e.g., normal evening occupancy in a `default_mode: "occupied"` space, or a presence `"on"` event triggered after a Home Assistant restart or brief sensor lull), return `schedule_updates: null` — do **not** extend daytime heating or override scheduled evening/bedtime setbacks unless `day_notes` or `space_notes` explicitly indicate occupants are staying up late. If the space is currently on an **unoccupied** schedule, switch upcoming blocks to `occupied_schedule_remaining` (for a reasonable window in `default_mode: "unoccupied"` spaces before returning to `unoccupied_schedule_remaining`) with `comfort_boost: null` (do not stack a boost on top of setback recovery).
  - On sustained vacancy `off` (all sensors `"off"`): gently shift toward `unoccupied_schedule_remaining` (respecting `space_notes` about stationary occupants or sensor quirks).
- **On `manual_intraday`** (user-initiated reconciliation check — NOT an alarm or sensor transition): evaluate each space truthfully from its live `presence_sensors`, `current_alarm_state`, `default_mode`, `current_temp`, and `current_butler_schedule_remaining`. Do not claim the alarm was just disarmed or invent a transition that did not occur; explain any adjustments based on actual current occupancy and schedule state.{day_notes_bullet}
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
      "spaces": ["space_id"]
    }}
  ]
}}

Context:
{json.dumps(payload, indent=2)}
"""
