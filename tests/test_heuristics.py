"""Tests for deterministic non-AI heuristic fallback planners and coordinator outage degradation."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from pytest_homeassistant.common import MockConfigEntry

from custom_components.hvac_butler.const import (
    CONF_AI_TASK_ENTITY,
    CONF_ALARM_ENTITY,
    CONF_CLIMATE_ENTITY,
    CONF_DEFAULT_MODE,
    CONF_HOUSE_NOTES,
    CONF_OCCUPIED_SCHEDULE,
    CONF_PRESENCE_SENSORS,
    CONF_SPACE_NOTES,
    CONF_SPACES,
    CONF_UNOCCUPIED_SCHEDULE,
    CONF_WEATHER_ENTITY,
    DAYS_OF_WEEK,
    DOMAIN,
)
from custom_components.hvac_butler.guardrails import GuardrailConfig
from custom_components.hvac_butler.heuristics import (
    build_heuristic_intraday_revision,
    build_heuristic_nightly_plan,
)
from custom_components.hvac_butler.prompts import (
    IntradayPlanContext,
    NightlyPlanContext,
    SpaceIntradayContext,
    SpaceNightlyContext,
)
from custom_components.hvac_butler.schedule_utils import ScheduleBlock


def test_heuristic_nightly_early_warmup_and_wind_chill() -> None:
    """Frigid overnight low shifts morning warm-up earlier; cold+windy adds occupied heat offset; unoccupied stays unchanged."""
    occ_tomorrow = [
        ScheduleBlock(0, 420, "heat_cool", 60.0, 76.0),  # 00:00-07:00 sleep
        ScheduleBlock(420, 1320, "heat_cool", 68.0, 74.0),  # 07:00-22:00 day
        ScheduleBlock(1320, 1440, "heat_cool", 60.0, 76.0),  # 22:00-24:00 sleep
    ]
    occ_tonight = [ScheduleBlock(1260, 1440, "heat_cool", 68.0, 74.0)]
    unocc_day = [ScheduleBlock(0, 1440, "heat_cool", 58.0, 82.0)]
    unocc_tonight = [ScheduleBlock(1260, 1440, "heat_cool", 58.0, 82.0)]

    ctx = NightlyPlanContext(
        timestamp_iso="2026-01-15T21:00:00-05:00",
        tonight_day="thursday",
        tomorrow_day="friday",
        is_weekend_tomorrow=False,
        weather_summary={
            "current": {"temperature": 22.0, "condition": "snowy", "wind_speed": 22.0},
            "periods": {
                "overnight": {
                    "temp_min": 14.0,
                    "temp_max": 22.0,
                    "wind_max": 24.0,
                    "conditions": ["snowy"],
                },
                "morning": {
                    "temp_min": 18.0,
                    "temp_max": 24.0,
                    "wind_max": 25.0,
                    "conditions": ["snowy"],
                },
            },
        },
        spaces=[
            SpaceNightlyContext(
                space_id="living_room",
                name="Living Room",
                default_mode="occupied",
                current_temp=68.0,
                active_preset="Butler",
                occupied_tonight=occ_tonight,
                occupied_tomorrow=occ_tomorrow,
                unoccupied_tonight=unocc_tonight,
                unoccupied_tomorrow=unocc_day,
            ),
            SpaceNightlyContext(
                space_id="guest_room",
                name="Guest Room",
                default_mode="unoccupied",
                current_temp=58.0,
                active_preset="Butler",
                occupied_tonight=occ_tonight,
                occupied_tomorrow=occ_tomorrow,
                unoccupied_tonight=unocc_tonight,
                unoccupied_tomorrow=unocc_day,
            ),
        ],
    )

    plan = build_heuristic_nightly_plan(ctx, GuardrailConfig())
    lr = plan["spaces"]["living_room"]
    gr = plan["spaces"]["guest_room"]

    # Living room morning warm-up shifted 30m earlier (07:00 -> 06:30) and +2°F severe snow/cold boost on occupied block only
    assert lr["tomorrow"][0]["to"] == "06:30:00"
    assert lr["tomorrow"][0]["data"]["heat_to"] == 60.0  # Sleep setback untouched
    assert lr["tomorrow"][1]["from"] == "06:30:00"
    assert lr["tomorrow"][1]["data"]["heat_to"] == 70.0  # 68 + 2
    assert lr["tomorrow"][2]["data"]["heat_to"] == 60.0  # Evening sleep untouched
    assert "heuristic fallback" in lr["daily_plan_summary"].lower()

    # Guest room (default_mode: unoccupied) stays at 58°F baseline
    assert gr["tomorrow"][0]["data"]["heat_to"] == 58.0
    assert "unoccupied baseline" in gr["daily_plan_summary"].lower()


def test_heuristic_intraday_alarm_and_presence_behaviors() -> None:
    """Verify alarm away/disarmed and debounced presence on/off without clobbering planned occupied schedules."""
    occ = [ScheduleBlock(600, 1440, "heat_cool", 68.0, 74.0)]
    planned_occ = [ScheduleBlock(600, 1440, "heat_cool", 69.0, 74.0)]
    unocc = [ScheduleBlock(600, 1440, "heat_cool", 58.0, 82.0)]
    cfg = GuardrailConfig()

    # 1. Alarm armed_away -> shifts occupied space to unoccupied
    ctx_away = IntradayPlanContext(
        timestamp_iso="2026-11-27T10:00:00-05:00",
        current_day="friday",
        now_time="10:00:00",
        trigger_event={"type": "alarm_change", "from": "disarmed", "to": "armed_away"},
        current_weather={"temperature": 40.0},
        current_alarm_state="armed_away",
        spaces=[
            SpaceIntradayContext(
                space_id="living_room",
                name="Living Room",
                default_mode="occupied",
                current_temp=68.0,
                active_preset="Butler",
                occupied_remaining=occ,
                unoccupied_remaining=unocc,
                current_butler_remaining=occ,
            )
        ],
    )
    res_away = build_heuristic_intraday_revision(ctx_away, cfg)
    assert (
        res_away["spaces"]["living_room"]["schedule_updates"][0]["data"]["heat_to"]
        == 58.0
    )
    assert res_away["spaces"]["living_room"]["comfort_boost"] is None

    # 2. Alarm armed_away -> disarmed restores each space to its own default_mode
    ctx_disarm = IntradayPlanContext(
        timestamp_iso="2026-11-27T10:00:00-05:00",
        current_day="friday",
        now_time="10:00:00",
        trigger_event={"type": "alarm_change", "from": "armed_away", "to": "disarmed"},
        current_weather={"temperature": 40.0},
        current_alarm_state="disarmed",
        spaces=[
            SpaceIntradayContext(
                space_id="living_room",
                name="Living Room",
                default_mode="occupied",
                current_temp=60.0,
                active_preset="Butler",
                occupied_remaining=occ,
                unoccupied_remaining=unocc,
                current_butler_remaining=unocc,
            ),
            SpaceIntradayContext(
                space_id="guest_room",
                name="Guest Room",
                default_mode="unoccupied",
                current_temp=58.0,
                active_preset="Butler",
                occupied_remaining=occ,
                unoccupied_remaining=unocc,
                current_butler_remaining=unocc,
            ),
        ],
    )
    res_disarm = build_heuristic_intraday_revision(ctx_disarm, cfg)
    assert (
        res_disarm["spaces"]["living_room"]["schedule_updates"][0]["data"]["heat_to"]
        == 68.0
    )
    assert res_disarm["spaces"]["guest_room"]["schedule_updates"] is None

    # 3. Presence on in an unoccupied guest room -> switches to occupied;
    #    Presence on in an already-planned living room -> preserves Plan (None)
    ctx_pres = IntradayPlanContext(
        timestamp_iso="2026-11-27T10:00:00-05:00",
        current_day="friday",
        now_time="10:00:00",
        trigger_event={
            "type": "presence_change",
            "from": "off",
            "to": "on",
            "state": "on",
        },
        current_weather={"temperature": 40.0},
        current_alarm_state="disarmed",
        spaces=[
            SpaceIntradayContext(
                space_id="guest_room",
                name="Guest Room",
                default_mode="unoccupied",
                current_temp=58.0,
                active_preset="Butler",
                occupied_remaining=occ,
                unoccupied_remaining=unocc,
                current_butler_remaining=unocc,
            ),
            SpaceIntradayContext(
                space_id="living_room",
                name="Living Room",
                default_mode="occupied",
                current_temp=68.0,
                active_preset="Butler",
                occupied_remaining=occ,
                unoccupied_remaining=unocc,
                current_butler_remaining=planned_occ,
            ),
        ],
    )
    res_pres = build_heuristic_intraday_revision(ctx_pres, cfg)
    assert (
        res_pres["spaces"]["guest_room"]["schedule_updates"][0]["data"]["heat_to"]
        == 68.0
    )
    assert res_pres["spaces"]["living_room"]["schedule_updates"] is None


@pytest.mark.asyncio
async def test_coordinator_degrades_to_heuristics_during_llm_outage(
    hass: HomeAssistant,
) -> None:
    """When ai_task fails (e.g. 503 outage), both nightly plan and intraday apply deterministic heuristics."""
    storage_data: dict[str, Any] = {}

    class _FakeCollection:
        data = storage_data

        async def async_create_item(self, data: dict[str, Any]) -> dict[str, Any]:
            slug = data["name"].lower().replace(" ", "_")
            item = {"id": slug, **data}
            storage_data[slug] = item
            return item

        async def async_update_item(
            self, item_id: str, data: dict[str, Any]
        ) -> dict[str, Any]:
            item = {"id": item_id, **data}
            storage_data[item_id] = item
            return item

    ws_owner = MagicMock()
    ws_owner.storage_collection = _FakeCollection()
    bound = MagicMock()
    bound.__self__ = ws_owner
    hass.data.setdefault("websocket_api", {})["schedule/update"] = (bound, None)

    hass.states.async_set(
        "climate.living_room_space",
        "heat_cool",
        {
            "friendly_name": "Living Room Space",
            "space_id": "living_room",
            "current_temperature": 68.0,
            "preset_mode": "Butler",
            "hvac_modes": ["heat_cool", "heat", "cool", "off"],
            "schedule_editing": False,
        },
    )
    hass.states.async_set("alarm_control_panel.home", "armed_away")

    occ_week = {
        day: [
            {
                "from": "00:00:00",
                "to": "24:00:00",
                "data": {"hvac_mode": "heat_cool", "heat_to": 68.0, "cool_to": 74.0},
            }
        ]
        for day in DAYS_OF_WEEK
    }
    unocc_week = {
        day: [
            {
                "from": "00:00:00",
                "to": "24:00:00",
                "data": {"hvac_mode": "heat_cool", "heat_to": 58.0, "cool_to": 82.0},
            }
        ]
        for day in DAYS_OF_WEEK
    }

    async def _handle_get_schedule(call: ServiceCall) -> dict[str, Any]:
        eid = call.data["entity_id"]
        if eid == "schedule.lr_occupied":
            return {eid: occ_week}
        if eid == "schedule.lr_unoccupied":
            return {eid: unocc_week}
        return {eid: occ_week}

    async def _handle_failing_ai(call: ServiceCall) -> dict[str, Any]:
        raise RuntimeError("503 Service Unavailable")

    hass.services.async_register(
        "schedule",
        "get_schedule",
        _handle_get_schedule,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        "ai_task",
        "generate_data",
        _handle_failing_ai,
        supports_response=SupportsResponse.ONLY,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="HVAC Butler",
        data={
            CONF_NAME: "HVAC Butler",
            CONF_AI_TASK_ENTITY: "ai_task.gemini",
            CONF_WEATHER_ENTITY: "",
            CONF_ALARM_ENTITY: "alarm_control_panel.home",
            CONF_HOUSE_NOTES: "",
            CONF_SPACES: [
                {
                    CONF_CLIMATE_ENTITY: "climate.living_room_space",
                    CONF_OCCUPIED_SCHEDULE: "schedule.lr_occupied",
                    CONF_UNOCCUPIED_SCHEDULE: "schedule.lr_unoccupied",
                    CONF_DEFAULT_MODE: "occupied",
                    CONF_PRESENCE_SENSORS: [],
                    CONF_SPACE_NOTES: "",
                }
            ],
        },
        options={},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][entry.entry_id]
    with patch("custom_components.hvac_butler.coordinator.AI_RETRY_DELAYS_SECONDS", ()):
        # 1. Nightly plan degrades gracefully to heuristic fallback
        await coordinator.async_run_nightly_plan(manual=True)
        assert coordinator.status == "fallback"
        assert "Heuristic fallback" in coordinator.daily_plan_headline
        assert "503" in (coordinator.last_error or "")

        # 2. Intraday alarm armed_away still shifts Living Room to unoccupied despite 503 outage
        await coordinator.async_run_intraday_revision(
            {"type": "alarm_change", "from": "disarmed", "to": "armed_away"},
            bypass_cooldown=True,
        )
        assert coordinator.status == "fallback"
        assert "Heuristic fallback" in coordinator.intraday_headline
        latest = coordinator.journal.entries[0]
        assert latest["kind"] == "intraday"
        assert latest["heuristic"] is True
        assert latest["spaces"]["living_room"]["changed"] is True
        assert latest["spaces"]["living_room"]["fallback"] is False
        after_blocks = next(
            iter(latest["spaces"]["living_room"]["after_blocks"].values())
        )
        assert after_blocks[0]["data"]["heat_to"] == 58.0

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
