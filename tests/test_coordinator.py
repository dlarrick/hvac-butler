"""Integration tests for HvacButlerCoordinator, sensors, button, and native schedule writes."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

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


class FakeScheduleStorageCollection:
    """In-memory stand-in for HA's native ScheduleStorageCollection."""

    def __init__(self) -> None:
        self.data: dict[str, dict[str, Any]] = {}

    async def async_create_item(self, data: dict[str, Any]) -> dict[str, Any]:
        slug = data["name"].lower().replace(" ", "_")
        item = {"id": slug, **data}
        self.data[slug] = item
        return item

    async def async_update_item(
        self, item_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        item = {"id": item_id, **data}
        self.data[item_id] = item
        return item


def _wire_fake_schedule_storage(
    hass: HomeAssistant, collection: FakeScheduleStorageCollection
) -> None:
    """Attach FakeScheduleStorageCollection to hass.data['websocket_api'] like HA core."""
    ws_owner = MagicMock()
    ws_owner.storage_collection = collection

    def _dummy_handler():
        pass

    bound = MagicMock()
    bound.__self__ = ws_owner
    hass.data.setdefault("websocket_api", {})["schedule/update"] = (bound, None)


def _baseline_week(heat_to: float, cool_to: float) -> dict[str, list[dict[str, Any]]]:
    return {
        day: [
            {
                "from": "00:00:00",
                "to": "24:00:00",
                "data": {
                    "hvac_mode": "heat_cool",
                    "heat_to": heat_to,
                    "cool_to": cool_to,
                },
            }
        ]
        for day in DAYS_OF_WEEK
    }


@pytest.mark.asyncio
async def test_nightly_plan_and_button_writes_native_schedule(
    hass: HomeAssistant,
) -> None:
    """Nightly plan reads baselines, calls ai_task, writes native schedule, updates sensors."""
    collection = FakeScheduleStorageCollection()
    _wire_fake_schedule_storage(hass, collection)

    hass.states.async_set(
        "climate.living_room_space",
        "heat_cool",
        {
            "friendly_name": "Living Room Space",
            "space_id": "living_room",
            "current_temperature": 67.5,
            "preset_mode": "Baseline",
            "hvac_modes": ["heat_cool", "heat", "cool", "off"],
            "schedule_editing": False,
        },
    )
    hass.states.async_set(
        "weather.home",
        "cloudy",
        {"temperature": 28.0, "wind_speed": 14.0},
    )

    occ_week = _baseline_week(68.0, 74.0)
    unocc_week = _baseline_week(58.0, 82.0)

    async def _handle_get_schedule(call: ServiceCall) -> dict[str, Any]:
        eid = call.data["entity_id"]
        if eid == "schedule.lr_occupied":
            return {eid: occ_week}
        if eid == "schedule.lr_unoccupied":
            return {eid: unocc_week}
        return {eid: {day: [] for day in DAYS_OF_WEEK}}

    async def _handle_get_forecasts(call: ServiceCall) -> dict[str, Any]:
        return {
            "weather.home": {
                "forecast": [
                    {
                        "datetime": "2026-11-22T22:00:00-05:00",
                        "temperature": 24.0,
                        "wind_speed": 18.0,
                        "condition": "snowy",
                    }
                ]
            }
        }

    async def _handle_generate_data(call: ServiceCall) -> dict[str, Any]:
        # Match the dynamic start time requested by the prompt (00:00:00 daytime vs 21:00:00 nightly)
        start_time = (
            "00:00:00"
            if "tonight_remaining: 00:00:00 to 24:00:00" in call.data["instructions"]
            else "21:00:00"
        )
        payload = {
            "spaces": {
                "living_room": {
                    "tonight_remaining": [
                        {
                            "from": start_time,
                            "to": "24:00:00",
                            "data": {
                                "hvac_mode": "heat_cool",
                                "heat_to": 67.0,
                                "cool_to": 74.0,
                            },
                        }
                    ],
                    "tomorrow": [
                        {
                            "from": "00:00:00",
                            "to": "24:00:00",
                            "data": {
                                "hvac_mode": "heat_cool",
                                "heat_to": 69.0,
                                "cool_to": 74.0,
                            },
                        }
                    ],
                    "daily_plan_summary": "Added +1F tomorrow for cold windy snow.",
                }
            }
        }
        return {"data": json.dumps(payload)}

    hass.services.async_register(
        "schedule",
        "get_schedule",
        _handle_get_schedule,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        "weather",
        "get_forecasts",
        _handle_get_forecasts,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        "ai_task",
        "generate_data",
        _handle_generate_data,
        supports_response=SupportsResponse.ONLY,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="HVAC Butler",
        data={
            CONF_NAME: "HVAC Butler",
            CONF_AI_TASK_ENTITY: "ai_task.gemini",
            CONF_WEATHER_ENTITY: "weather.home",
            CONF_ALARM_ENTITY: "",
            CONF_HOUSE_NOTES: "Drafty Victorian",
            CONF_SPACES: [
                {
                    CONF_CLIMATE_ENTITY: "climate.living_room_space",
                    CONF_OCCUPIED_SCHEDULE: "schedule.lr_occupied",
                    CONF_UNOCCUPIED_SCHEDULE: "schedule.lr_unoccupied",
                    CONF_DEFAULT_MODE: "occupied",
                    CONF_PRESENCE_SENSORS: [],
                    CONF_SPACE_NOTES: "Woodstove in corner",
                }
            ],
        },
        options={},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Auto-created native butler schedule
    assert "living_room_butler" in collection.data

    # Press the manual "Run nightly plan now" button
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.hvac_butler_run_nightly_plan_now"},
        blocking=True,
    )
    await hass.async_block_till_done()

    status_state = hass.states.get("sensor.hvac_butler_status")
    summary_state = hass.states.get("sensor.hvac_butler_daily_plan_summary")
    assert status_state is not None
    assert status_state.state == "ok"
    assert summary_state is not None
    assert summary_state.state == "1 of 1 spaces differ from baseline"
    assert "cold windy snow" in summary_state.attributes["full_summary"]

    # Verify only tonight + tomorrow are populated in native storage schedule
    stored = collection.data["living_room_butler"]
    non_empty_days = [d for d in DAYS_OF_WEEK if stored[d]]
    assert len(non_empty_days) == 2

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.asyncio
async def test_intraday_shadow_mode_vs_active_butler_comfort_boost(
    hass: HomeAssistant,
) -> None:
    """Intraday updates schedule in shadow mode, but only calls comfort_boost on 'Butler' preset."""
    collection = FakeScheduleStorageCollection()
    _wire_fake_schedule_storage(hass, collection)

    hass.states.async_set(
        "climate.guest_room_space",
        "heat_cool",
        {
            "friendly_name": "Guest Room Space",
            "space_id": "guest_room",
            "current_temperature": 60.0,
            "preset_mode": "Butler",
            "hvac_modes": ["heat_cool", "heat", "cool", "off"],
            "schedule_editing": False,
        },
    )

    occ_week = _baseline_week(68.0, 74.0)
    unocc_week = _baseline_week(58.0, 82.0)

    async def _handle_get_schedule(call: ServiceCall) -> dict[str, Any]:
        eid = call.data["entity_id"]
        if eid == "schedule.guest_occupied":
            return {eid: occ_week}
        return {eid: unocc_week}

    boost_calls: list[dict[str, Any]] = []
    preset_reg_calls: list[dict[str, Any]] = []
    preset_unreg_calls: list[dict[str, Any]] = []

    async def _handle_comfort_boost(call: ServiceCall) -> None:
        boost_calls.append(dict(call.data))

    async def _handle_register_preset(call: ServiceCall) -> None:
        preset_reg_calls.append(dict(call.data))

    async def _handle_unregister_preset(call: ServiceCall) -> None:
        preset_unreg_calls.append(dict(call.data))

    async def _handle_generate_data(call: ServiceCall) -> dict[str, Any]:
        # Extract now_time from instructions so replacement block matches exact window
        import re

        m = re.search(r'"now_time": "(\d\d:\d\d:\d\d)"', call.data["instructions"])
        now_str = m.group(1) if m else "10:00:00"
        return {
            "data": json.dumps(
                {
                    "spaces": {
                        "guest_room": {
                            "schedule_updates": [
                                {
                                    "from": now_str,
                                    "to": "24:00:00",
                                    "data": {
                                        "hvac_mode": "heat_cool",
                                        "heat_to": 68.0,
                                        "cool_to": 74.0,
                                    },
                                }
                            ],
                            "comfort_boost": {
                                "feeling": "too_cold",
                                "delta_f": 2.0,
                                "duration_minutes": 60,
                            },
                            "intraday_explanation": "Guest arrived; warming room and boosting.",
                        }
                    }
                }
            )
        }

    hass.services.async_register(
        "schedule",
        "get_schedule",
        _handle_get_schedule,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        "ai_task",
        "generate_data",
        _handle_generate_data,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register("hvac_fusion", "comfort_boost", _handle_comfort_boost)
    hass.services.async_register(
        "hvac_fusion", "register_space_preset", _handle_register_preset
    )
    hass.services.async_register(
        "hvac_fusion", "unregister_space_preset", _handle_unregister_preset
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
                    CONF_CLIMATE_ENTITY: "climate.guest_room_space",
                    CONF_OCCUPIED_SCHEDULE: "schedule.guest_occupied",
                    CONF_UNOCCUPIED_SCHEDULE: "schedule.guest_unoccupied",
                    CONF_DEFAULT_MODE: "unoccupied",
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

    # Verify Butler auto-registered the "Butler" preset on hvac_fusion
    assert len(preset_reg_calls) == 1
    assert preset_reg_calls[0] == {
        "entity_id": "climate.guest_room_space",
        "preset_name": "Butler",
        "schedule_entity": "schedule.guest_room_butler",
    }

    # 1. Active Butler preset -> comfort_boost SHOULD fire
    await coordinator.async_run_intraday_revision(
        {"type": "presence_change", "space_id": "guest_room", "state": "on"},
        target_space_ids=["guest_room"],
        bypass_cooldown=True,
    )
    await hass.async_block_till_done()
    assert len(boost_calls) == 1
    assert boost_calls[0]["entity_id"] == "climate.guest_room_space"
    assert boost_calls[0]["feeling"] == "too_cold"

    expl_state = hass.states.get("sensor.hvac_butler_intraday_explanation")
    assert expl_state is not None
    assert "1 of 1 spaces revised" in expl_state.state
    assert "Guest arrived" in expl_state.attributes["full_explanation"]

    # 2. Shadow mode (preset_mode == "Baseline") -> comfort_boost MUST NOT fire
    hass.states.async_set(
        "climate.guest_room_space",
        "heat_cool",
        {
            "friendly_name": "Guest Room Space",
            "space_id": "guest_room",
            "current_temperature": 60.0,
            "preset_mode": "Baseline",
            "hvac_modes": ["heat_cool", "heat", "cool", "off"],
            "schedule_editing": False,
        },
    )
    await coordinator.async_run_intraday_revision(
        {"type": "alarm_change", "from": "armed_away", "to": "disarmed"},
        bypass_cooldown=True,
    )
    await hass.async_block_till_done()
    assert len(boost_calls) == 1  # Still 1 — no new boost fired in shadow mode!

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    # Normal reload/unload must preserve active "Butler" presets on hvac_fusion
    assert preset_unreg_calls == []

    # Permanent entry removal DOES cleanly unregister the dynamic "Butler" preset
    from custom_components.hvac_butler import async_remove_entry

    await async_remove_entry(hass, entry)
    await hass.async_block_till_done()

    assert preset_unreg_calls == [
        {
            "entity_id": "climate.guest_room_space",
            "preset_name": "Butler",
        }
    ]


@pytest.mark.asyncio
async def test_sensors_restore_state_across_restart(hass: HomeAssistant) -> None:
    """Verify all 3 observability sensors restore state and attributes across restarts."""
    from homeassistant.core import State

    from custom_components.hvac_butler.coordinator import HvacButlerCoordinator
    from custom_components.hvac_butler.sensor import (
        HvacButlerDailyPlanSummarySensor,
        HvacButlerIntradayExplanationSensor,
        HvacButlerStatusSensor,
    )

    coordinator = HvacButlerCoordinator(
        hass, "restore_entry", {CONF_NAME: "HVAC Butler"}
    )

    status_sensor = HvacButlerStatusSensor(coordinator)
    status_sensor.hass = hass
    status_sensor.async_write_ha_state = MagicMock()
    status_sensor.async_get_last_state = AsyncMock(
        return_value=State(
            "sensor.hvac_butler_status",
            "ok",
            {
                "last_nightly_run": "2026-11-22T21:00:00-05:00",
                "last_intraday_run": "2026-11-23T08:15:00-05:00",
                "last_error": None,
            },
        )
    )
    await status_sensor.async_added_to_hass()
    assert coordinator.status == "ok"
    assert coordinator.last_nightly_run == "2026-11-22T21:00:00-05:00"

    summary_sensor = HvacButlerDailyPlanSummarySensor(coordinator)
    summary_sensor.hass = hass
    summary_sensor.async_write_ha_state = MagicMock()
    # Simulate fresh coordinator where status sensor hasn't set last_nightly_run yet
    coordinator.last_nightly_run = None
    summary_sensor.async_get_last_state = AsyncMock(
        return_value=State(
            "sensor.hvac_butler_daily_plan_summary",
            "2 of 4 spaces differ from baseline",
            {
                "full_summary": "Living Room: +1F for storm.",
                "space_summaries": {"living_room": "+1F for storm."},
                "updated_at": "2026-11-22T21:00:00-05:00",
            },
        )
    )
    await summary_sensor.async_added_to_hass()
    assert summary_sensor.native_value == "2 of 4 spaces differ from baseline"
    assert summary_sensor.extra_state_attributes["space_summaries"] == {
        "living_room": "+1F for storm."
    }

    intraday_sensor = HvacButlerIntradayExplanationSensor(coordinator)
    intraday_sensor.hass = hass
    intraday_sensor.async_write_ha_state = MagicMock()
    coordinator.last_intraday_run = None
    intraday_sensor.async_get_last_state = AsyncMock(
        return_value=State(
            "sensor.hvac_butler_intraday_explanation",
            "1 of 1 spaces revised (presence change)",
            {
                "full_explanation": "Guest Room: Warming for arrival.",
                "space_explanations": {"guest_room": "Warming for arrival."},
                "last_trigger": {"type": "presence_change"},
                "updated_at": "2026-11-23T08:15:00-05:00",
            },
        )
    )
    await intraday_sensor.async_added_to_hass()
    assert intraday_sensor.native_value == "1 of 1 spaces revised (presence change)"
    assert intraday_sensor.extra_state_attributes["last_trigger"] == {
        "type": "presence_change"
    }


@pytest.mark.asyncio
async def test_startup_and_offline_alarm_presence_transitions_ignored(
    hass: HomeAssistant,
) -> None:
    """Startup (None -> state) and offline (unavailable -> state) transitions must not trigger revisions."""
    from homeassistant.core import Event, State

    from custom_components.hvac_butler.coordinator import HvacButlerCoordinator

    coordinator = HvacButlerCoordinator(
        hass,
        "startup_filter",
        {
            CONF_NAME: "HVAC Butler",
            CONF_ALARM_ENTITY: "alarm_control_panel.home",
            CONF_SPACES: [],
        },
    )
    coordinator._sensor_to_spaces = {"binary_sensor.lr_motion": ["living_room"]}
    coordinator.async_run_intraday_revision = AsyncMock()

    # 1. Alarm: None -> disarmed, unavailable -> disarmed, armed_home -> disarmed -> all ignored
    for old_s in (
        None,
        State("alarm_control_panel.home", "unavailable"),
        State("alarm_control_panel.home", "unknown"),
        State("alarm_control_panel.home", "armed_home"),
    ):
        ev = Event(
            "state_changed",
            {
                "entity_id": "alarm_control_panel.home",
                "old_state": old_s,
                "new_state": State("alarm_control_panel.home", "disarmed"),
            },
        )
        coordinator._handle_alarm_change(ev)

    await hass.async_block_till_done()
    coordinator.async_run_intraday_revision.assert_not_called()

    # 2. Presence: None -> on and unavailable -> on -> no debounce timers scheduled
    for old_s in (None, State("binary_sensor.lr_motion", "unavailable")):
        ev = Event(
            "state_changed",
            {
                "entity_id": "binary_sensor.lr_motion",
                "old_state": old_s,
                "new_state": State("binary_sensor.lr_motion", "on"),
            },
        )
        coordinator._handle_presence_change(ev)

    assert coordinator._debounce_cancels == {}

    # 3. Genuine armed_away -> disarmed DOES trigger intraday revision
    real_ev = Event(
        "state_changed",
        {
            "entity_id": "alarm_control_panel.home",
            "old_state": State("alarm_control_panel.home", "armed_away"),
            "new_state": State("alarm_control_panel.home", "disarmed"),
        },
    )
    coordinator._handle_alarm_change(real_ev)
    await hass.async_block_till_done()
    coordinator.async_run_intraday_revision.assert_called_once()


@pytest.mark.asyncio
async def test_multisensor_presence_aggregation_and_arrival_cooldown_bypass(
    hass: HomeAssistant,
) -> None:
    """Multi-sensor spaces require ALL sensors off for vacancy; off->on arrival bypasses cooldown."""
    from unittest.mock import patch

    from homeassistant.core import Event, State
    from homeassistant.util import dt as dt_util

    from custom_components.hvac_butler.coordinator import HvacButlerCoordinator

    coordinator = HvacButlerCoordinator(
        hass,
        "multi_presence",
        {
            CONF_NAME: "HVAC Butler",
            CONF_SPACES: [
                {
                    CONF_CLIMATE_ENTITY: "climate.first_floor_space",
                    CONF_OCCUPIED_SCHEDULE: "schedule.ff_occ",
                    CONF_PRESENCE_SENSORS: [
                        "binary_sensor.kitchen",
                        "binary_sensor.dining",
                    ],
                }
            ],
        },
    )
    coordinator._space_to_sensors = {
        "first_floor": ["binary_sensor.kitchen", "binary_sensor.dining"]
    }
    coordinator._sensor_to_spaces = {
        "binary_sensor.kitchen": ["first_floor"],
        "binary_sensor.dining": ["first_floor"],
    }
    coordinator.async_run_intraday_revision = AsyncMock()

    # 1. Kitchen is ON, Dining turns OFF -> space is still occupied, so NO off timer scheduled
    hass.states.async_set("binary_sensor.kitchen", "on")
    hass.states.async_set("binary_sensor.dining", "off")
    scheduled: list[tuple[float, Any]] = []

    def _fake_call_later(_hass, delay, action):
        scheduled.append((delay, action))
        return lambda: None

    with patch(
        "custom_components.hvac_butler.coordinator.async_call_later",
        side_effect=_fake_call_later,
    ):
        coordinator._handle_presence_change(
            Event(
                "state_changed",
                {
                    "entity_id": "binary_sensor.dining",
                    "old_state": State("binary_sensor.dining", "on"),
                    "new_state": State("binary_sensor.dining", "off"),
                },
            )
        )
        assert scheduled == []

        # 2. Now Kitchen also turns OFF -> all sensors off -> 25m off debounce scheduled
        hass.states.async_set("binary_sensor.kitchen", "off")
        coordinator._handle_presence_change(
            Event(
                "state_changed",
                {
                    "entity_id": "binary_sensor.kitchen",
                    "old_state": State("binary_sensor.kitchen", "on"),
                    "new_state": State("binary_sensor.kitchen", "off"),
                },
            )
        )
        assert len(scheduled) == 1
        assert scheduled[0][0] == 15 * 60

        # Simulate prior off revision 10 minutes ago (within 30m cooldown)
        coordinator._last_intraday_by_space["first_floor"] = dt_util.now()
        coordinator._last_presence_state_by_space["first_floor"] = "off"

        # 3. Dining turns ON -> 3m arrival debounce fires and MUST bypass cooldown (off -> on)
        scheduled.clear()
        hass.states.async_set("binary_sensor.dining", "on")
        coordinator._handle_presence_change(
            Event(
                "state_changed",
                {
                    "entity_id": "binary_sensor.dining",
                    "old_state": State("binary_sensor.dining", "off"),
                    "new_state": State("binary_sensor.dining", "on"),
                },
            )
        )
        assert len(scheduled) == 1
        assert scheduled[0][0] == 3 * 60

        # Fire the debounced callback
        scheduled[0][1](dt_util.now())
        await hass.async_block_till_done()

        coordinator.async_run_intraday_revision.assert_awaited_once()
        kwargs = coordinator.async_run_intraday_revision.call_args.kwargs
        assert kwargs["bypass_cooldown"] is True
        assert kwargs["trigger_event"]["from"] == "off"
        assert kwargs["trigger_event"]["to"] == "on"
        assert kwargs["trigger_event"]["state"] == "on"
        assert kwargs["target_space_ids"] == ["first_floor"]

    # 4. Manual intraday check bypasses cooldown and keeps trigger strictly about what woke Butler
    coordinator.async_run_intraday_revision.reset_mock()
    await coordinator.async_run_manual_intraday(space_id="first_floor")
    coordinator.async_run_intraday_revision.assert_awaited_once()
    m_kwargs = coordinator.async_run_intraday_revision.call_args.kwargs
    assert m_kwargs["bypass_cooldown"] is True
    assert m_kwargs["trigger_event"]["type"] == "manual_intraday"
    assert m_kwargs["target_space_ids"] == ["first_floor"]
    sensor_states = coordinator._get_space_sensor_states("first_floor")
    assert sensor_states["binary_sensor.kitchen"]["state"] == "off"
    assert sensor_states["binary_sensor.dining"]["state"] == "on"
    assert "for_minutes" in sensor_states["binary_sensor.dining"]


@pytest.mark.asyncio
async def test_nightly_plan_at_2100_preserves_earlier_today_and_clears_yesterday(
    hass: HomeAssistant,
) -> None:
    """At 21:00, nightly plan preserves 00:00-21:00 of today while clearing yesterday."""
    from datetime import datetime
    from unittest.mock import patch

    collection = FakeScheduleStorageCollection()
    _wire_fake_schedule_storage(hass, collection)

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

    occ_week = _baseline_week(68.0, 74.0)
    # Existing butler schedule has yesterday (monday) and full today (tuesday) populated
    existing_butler = {day: [] for day in DAYS_OF_WEEK}
    existing_butler["monday"] = [
        {
            "from": "00:00:00",
            "to": "24:00:00",
            "data": {"hvac_mode": "heat_cool", "heat_to": 68.0, "cool_to": 74.0},
        }
    ]
    existing_butler["tuesday"] = [
        {
            "from": "00:00:00",
            "to": "07:00:00",
            "data": {"hvac_mode": "heat_cool", "heat_to": 64.0, "cool_to": 74.0},
        },
        {
            "from": "07:00:00",
            "to": "24:00:00",
            "data": {"hvac_mode": "heat_cool", "heat_to": 69.0, "cool_to": 74.0},
        },
    ]

    async def _handle_get_schedule(call: ServiceCall) -> dict[str, Any]:
        eid = call.data["entity_id"]
        if eid == "schedule.lr_occupied":
            return {eid: occ_week}
        if eid == "schedule.living_room_butler":
            return {eid: existing_butler}
        return {eid: {day: [] for day in DAYS_OF_WEEK}}

    async def _handle_generate_data(call: ServiceCall) -> dict[str, Any]:
        payload = {
            "spaces": {
                "living_room": {
                    "tonight_remaining": [
                        {
                            "from": "21:00:00",
                            "to": "24:00:00",
                            "data": {
                                "hvac_mode": "heat_cool",
                                "heat_to": 66.0,
                                "cool_to": 74.0,
                            },
                        }
                    ],
                    "tomorrow": [
                        {
                            "from": "00:00:00",
                            "to": "24:00:00",
                            "data": {
                                "hvac_mode": "heat_cool",
                                "heat_to": 68.0,
                                "cool_to": 74.0,
                            },
                        }
                    ],
                    "daily_plan_summary": "Baseline maintained.",
                }
            }
        }
        return {"data": json.dumps(payload)}

    hass.services.async_register(
        "schedule",
        "get_schedule",
        _handle_get_schedule,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        "ai_task",
        "generate_data",
        _handle_generate_data,
        supports_response=SupportsResponse.ONLY,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="HVAC Butler",
        data={
            CONF_NAME: "HVAC Butler",
            CONF_AI_TASK_ENTITY: "ai_task.gemini",
            CONF_WEATHER_ENTITY: "",
            CONF_ALARM_ENTITY: "",
            CONF_HOUSE_NOTES: "",
            CONF_SPACES: [
                {
                    CONF_CLIMATE_ENTITY: "climate.living_room_space",
                    CONF_OCCUPIED_SCHEDULE: "schedule.lr_occupied",
                    CONF_UNOCCUPIED_SCHEDULE: "",
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

    # Tuesday 2026-11-24 21:00 local time
    fake_now = datetime(2026, 11, 24, 21, 0, 0)
    with patch(
        "custom_components.hvac_butler.coordinator.dt_util.now", return_value=fake_now
    ):
        coordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.async_run_nightly_plan()

    stored = collection.data["living_room_butler"]
    # Yesterday (monday) is cleared
    assert stored["monday"] == []
    # Today (tuesday) preserves 00:00-07:00 and 07:00-21:00, plus new 21:00-24:00
    assert stored["tuesday"] == [
        {
            "from": "00:00:00",
            "to": "07:00:00",
            "data": {"hvac_mode": "heat_cool", "heat_to": 64.0, "cool_to": 74.0},
        },
        {
            "from": "07:00:00",
            "to": "21:00:00",
            "data": {"hvac_mode": "heat_cool", "heat_to": 69.0, "cool_to": 74.0},
        },
        {
            "from": "21:00:00",
            "to": "24:00:00",
            "data": {"hvac_mode": "heat_cool", "heat_to": 66.0, "cool_to": 74.0},
        },
    ]
    # Tomorrow (wednesday) is populated
    assert len(stored["wednesday"]) == 1
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
