"""Unit tests for pure-Python prompt & context builders."""

from __future__ import annotations

from custom_components.hvac_butler.guardrails import GuardrailConfig
from custom_components.hvac_butler.prompts import (
    IntradayPlanContext,
    NightlyPlanContext,
    SpaceIntradayContext,
    SpaceNightlyContext,
    build_intraday_prompt,
    build_nightly_prompt,
    summarize_forecast,
)
from custom_components.hvac_butler.schedule_utils import ScheduleBlock


def test_summarize_forecast_hourly_and_daily() -> None:
    hourly = [
        {
            "datetime": "2026-11-22T22:00:00-05:00",
            "temperature": 28.0,
            "wind_speed": 15.0,
            "condition": "clear-night",
        },
        {
            "datetime": "2026-11-23T02:00:00-05:00",
            "temperature": 22.0,
            "wind_speed": 18.0,
            "condition": "snowy",
        },
        {
            "datetime": "2026-11-23T08:00:00-05:00",
            "temperature": 26.0,
            "wind_speed": 12.0,
            "condition": "sunny",
        },
        {
            "datetime": "2026-11-23T13:00:00-05:00",
            "temperature": 36.0,
            "wind_speed": 8.0,
            "condition": "sunny",
        },
    ]
    summary = summarize_forecast(
        hourly,
        current_temp=31.0,
        current_condition="cloudy",
        current_wind_speed=10.0,
    )
    assert summary["current"]["temperature"] == 31.0
    assert summary["periods"]["overnight"]["temp_min"] == 22.0
    assert summary["periods"]["overnight"]["wind_max"] == 18.0
    assert summary["periods"]["midday"]["conditions"] == ["sunny"]


def test_build_nightly_prompt_with_and_without_day_notes() -> None:
    space = SpaceNightlyContext(
        space_id="living_room",
        name="Living Room Space",
        default_mode="occupied",
        current_temp=68.5,
        active_preset="Butler",
        occupied_tonight=[ScheduleBlock(1260, 1440, "heat_cool", 68.0, 74.0)],
        occupied_tomorrow=[ScheduleBlock(0, 1440, "heat_cool", 68.0, 74.0)],
        unoccupied_tonight=[ScheduleBlock(1260, 1440, "heat_cool", 58.0, 82.0)],
        unoccupied_tomorrow=[ScheduleBlock(0, 1440, "heat_cool", 58.0, 82.0)],
        space_notes="South-facing windows, woodstove",
    )
    ctx = NightlyPlanContext(
        timestamp_iso="2026-11-22T21:00:00-05:00",
        tonight_day="sunday",
        tomorrow_day="monday",
        is_weekend_tomorrow=False,
        weather_summary={"current": {"temperature": 30.0}},
        spaces=[space],
        house_notes="3-story Victorian",
    )
    prompt = build_nightly_prompt(ctx, GuardrailConfig())
    assert '"living_room"' in prompt
    assert '"day_notes"' not in prompt
    assert "3-story Victorian" in prompt
    assert "South-facing windows, woodstove" in prompt

    # Future day-specific instructions slot activates cleanly when populated
    ctx.day_notes = ["Guests arriving at 5 PM tomorrow"]
    prompt_with_notes = build_nightly_prompt(ctx, GuardrailConfig())
    assert '"day_notes"' in prompt_with_notes
    assert "Guests arriving at 5 PM tomorrow" in prompt_with_notes


def test_build_intraday_prompt() -> None:
    space = SpaceIntradayContext(
        space_id="guest_room",
        name="Guest Room Space",
        default_mode="unoccupied",
        current_temp=60.5,
        active_preset="Butler",
        occupied_remaining=[ScheduleBlock(600, 1440, "heat_cool", 68.0, 74.0)],
        unoccupied_remaining=[ScheduleBlock(600, 1440, "heat_cool", 58.0, 82.0)],
        current_butler_remaining=[ScheduleBlock(600, 1440, "heat_cool", 58.0, 82.0)],
        space_notes="mmWave presence sensor is very accurate",
    )
    ctx = IntradayPlanContext(
        timestamp_iso="2026-11-23T10:00:00-05:00",
        current_day="monday",
        now_time="10:00:00",
        trigger_event={
            "type": "presence_change",
            "space_id": "guest_room",
            "state": "on",
            "for_minutes": 3,
        },
        current_weather={"temperature": 35.0, "condition": "sunny"},
        spaces=[space],
    )
    prompt = build_intraday_prompt(ctx, GuardrailConfig())
    assert "10:00:00" in prompt
    assert '"guest_room"' in prompt
    assert "mmWave presence sensor is very accurate" in prompt
