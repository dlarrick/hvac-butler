"""Tests for HVAC Butler Config Flow and 2-menu Options Flow."""

from __future__ import annotations

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant.common import MockConfigEntry

from custom_components.hvac_butler.const import (
    CONF_AI_TASK_ENTITY,
    CONF_ALARM_ENTITY,
    CONF_CLIMATE_ENTITY,
    CONF_DEFAULT_MODE,
    CONF_HOUSE_NOTES,
    CONF_MAX_AI_DELTA_F,
    CONF_MAX_COOL_TEMP,
    CONF_MAX_HEAT_TEMP,
    CONF_MIN_COOL_TEMP,
    CONF_MIN_HEAT_TEMP,
    CONF_OCCUPIED_SCHEDULE,
    CONF_PRESENCE_SENSORS,
    CONF_SPACE_NOTES,
    CONF_SPACES,
    CONF_UNOCCUPIED_SCHEDULE,
    CONF_WEATHER_ENTITY,
    DOMAIN,
    MODE_UNOCCUPIED,
)


@pytest.mark.asyncio
async def test_config_flow_prepopulates_hvac_fusion_spaces(
    hass: HomeAssistant,
) -> None:
    """Initial setup auto-discovers existing hvac_fusion spaces and enforces single instance."""
    hass.states.async_set(
        "climate.living_room_space",
        "heat_cool",
        {
            "friendly_name": "Living Room Space",
            "space_id": "living_room",
            "presets": {"Baseline": "schedule.living_room_baseline"},
        },
    )
    # Non-hvac_fusion climate entity should NOT be auto-added
    hass.states.async_set(
        "climate.garage_heater",
        "heat",
        {"friendly_name": "Garage Heater"},
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "My Butler",
            CONF_AI_TASK_ENTITY: "ai_task.gemini",
            CONF_WEATHER_ENTITY: "weather.home",
            CONF_ALARM_ENTITY: "alarm_control_panel.home",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "My Butler"
    spaces = result["data"][CONF_SPACES]
    assert len(spaces) == 1
    assert spaces[0][CONF_CLIMATE_ENTITY] == "climate.living_room_space"

    # Second instance must abort
    result2 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "single_instance_allowed"


@pytest.mark.asyncio
async def test_options_flow_two_menu_hub(hass: HomeAssistant) -> None:
    """Test Global Settings, Space Add/Edit/Delete, and Cancel flows."""
    hass.states.async_set(
        "climate.living_room_space",
        "heat_cool",
        {"friendly_name": "Living Room Space", "space_id": "living_room"},
    )
    hass.states.async_set(
        "climate.guest_room_space",
        "heat_cool",
        {"friendly_name": "Guest Room Space", "space_id": "guest_room"},
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="HVAC Butler",
        data={
            CONF_NAME: "HVAC Butler",
            CONF_AI_TASK_ENTITY: "ai_task.gemini",
            CONF_WEATHER_ENTITY: "weather.home",
            CONF_ALARM_ENTITY: "",
            CONF_HOUSE_NOTES: "",
            CONF_SPACES: [
                {
                    CONF_CLIMATE_ENTITY: "climate.living_room_space",
                    CONF_OCCUPIED_SCHEDULE: "",
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
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Open options menu
    res = await hass.config_entries.options.async_init(entry.entry_id)
    assert res["type"] is FlowResultType.MENU
    assert res["step_id"] == "init"

    # Menu 1: Global Settings & Safety Bounds
    res = await hass.config_entries.options.async_configure(
        res["flow_id"], {"next_step_id": "global_settings"}
    )
    res = await hass.config_entries.options.async_configure(
        res["flow_id"],
        {
            CONF_AI_TASK_ENTITY: "ai_task.gemini",
            CONF_WEATHER_ENTITY: "weather.home",
            CONF_HOUSE_NOTES: "3-story Victorian, dogs stay downstairs",
            "safety_bounds": {
                CONF_MIN_HEAT_TEMP: 52.0,
                CONF_MAX_HEAT_TEMP: 75.0,
                CONF_MIN_COOL_TEMP: 68.0,
                CONF_MAX_COOL_TEMP: 84.0,
                CONF_MAX_AI_DELTA_F: 3.5,
            },
        },
    )
    assert res["step_id"] == "init"

    # Menu 2: Manage Spaces -> Edit pre-populated space
    res = await hass.config_entries.options.async_configure(
        res["flow_id"], {"next_step_id": "spaces_menu"}
    )
    res = await hass.config_entries.options.async_configure(
        res["flow_id"], {"space_action": "edit_0"}
    )
    res = await hass.config_entries.options.async_configure(
        res["flow_id"],
        {
            CONF_CLIMATE_ENTITY: "climate.living_room_space",
            CONF_OCCUPIED_SCHEDULE: "schedule.lr_occupied",
            CONF_UNOCCUPIED_SCHEDULE: "schedule.lr_unoccupied",
            CONF_DEFAULT_MODE: "occupied",
            CONF_PRESENCE_SENSORS: ["binary_sensor.lr_motion"],
            CONF_SPACE_NOTES: "South-facing windows",
            "delete_space": False,
            "cancel": False,
        },
    )
    assert res["step_id"] == "spaces_menu"

    # Add a second space (Guest Room, default_mode=unoccupied)
    res = await hass.config_entries.options.async_configure(
        res["flow_id"], {"space_action": "add"}
    )
    res = await hass.config_entries.options.async_configure(
        res["flow_id"],
        {
            CONF_CLIMATE_ENTITY: "climate.guest_room_space",
            CONF_OCCUPIED_SCHEDULE: "schedule.guest_occupied",
            CONF_UNOCCUPIED_SCHEDULE: "schedule.guest_unoccupied",
            CONF_DEFAULT_MODE: MODE_UNOCCUPIED,
            CONF_PRESENCE_SENSORS: ["binary_sensor.guest_mmwave"],
            CONF_SPACE_NOTES: "mmWave sensor is very accurate",
            "cancel": False,
        },
    )
    assert res["step_id"] == "spaces_menu"

    # Back to main menu and Finish
    res = await hass.config_entries.options.async_configure(
        res["flow_id"], {"space_action": "back"}
    )
    res = await hass.config_entries.options.async_configure(
        res["flow_id"], {"next_step_id": "finish"}
    )
    await hass.async_block_till_done()

    assert res["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_HOUSE_NOTES] == "3-story Victorian, dogs stay downstairs"
    assert entry.options[CONF_MAX_AI_DELTA_F] == 3.5
    assert len(entry.options[CONF_SPACES]) == 2
    assert (
        entry.options[CONF_SPACES][0][CONF_OCCUPIED_SCHEDULE] == "schedule.lr_occupied"
    )
    assert entry.options[CONF_SPACES][1][CONF_DEFAULT_MODE] == MODE_UNOCCUPIED

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.asyncio
async def test_single_schedule_space_and_error_preserves_inputs(
    hass: HomeAssistant,
) -> None:
    """Unoccupied schedule is optional, and validation errors preserve entered fields."""
    hass.states.async_set(
        "climate.primary_bedroom_space",
        "heat_cool",
        {"friendly_name": "Primary Bedroom Space", "space_id": "primary_bedroom"},
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="HVAC Butler",
        data={
            CONF_NAME: "HVAC Butler",
            CONF_AI_TASK_ENTITY: "ai_task.gemini",
            CONF_WEATHER_ENTITY: "weather.home",
            CONF_ALARM_ENTITY: "",
            CONF_HOUSE_NOTES: "",
            CONF_SPACES: [],
        },
        options={},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    res = await hass.config_entries.options.async_init(entry.entry_id)
    res = await hass.config_entries.options.async_configure(
        res["flow_id"], {"next_step_id": "spaces_menu"}
    )
    res = await hass.config_entries.options.async_configure(
        res["flow_id"], {"space_action": "add"}
    )

    # 1. Submit with missing occupied_schedule -> error, but space_notes & climate_entity preserved!
    res = await hass.config_entries.options.async_configure(
        res["flow_id"],
        {
            CONF_CLIMATE_ENTITY: "climate.primary_bedroom_space",
            CONF_DEFAULT_MODE: "occupied",
            CONF_PRESENCE_SENSORS: ["binary_sensor.bed_motion"],
            CONF_SPACE_NOTES: "Motion sensor cannot detect sleeping occupants",
            "cancel": False,
        },
    )
    assert res["type"] is FlowResultType.FORM
    assert res["errors"] == {CONF_OCCUPIED_SCHEDULE: "required"}
    suggested = {
        k.schema: k.description.get("suggested_value")
        for k in res["data_schema"].schema
        if hasattr(k, "description") and isinstance(k.description, dict)
    }
    assert suggested[CONF_CLIMATE_ENTITY] == "climate.primary_bedroom_space"
    assert (
        suggested[CONF_SPACE_NOTES] == "Motion sensor cannot detect sleeping occupants"
    )
    assert suggested[CONF_PRESENCE_SENSORS] == ["binary_sensor.bed_motion"]

    # 2. Submit with only occupied_schedule (no unoccupied_schedule) -> succeeds!
    res = await hass.config_entries.options.async_configure(
        res["flow_id"],
        {
            CONF_CLIMATE_ENTITY: "climate.primary_bedroom_space",
            CONF_OCCUPIED_SCHEDULE: "schedule.primary_bedroom_sleep",
            CONF_DEFAULT_MODE: "occupied",
            CONF_PRESENCE_SENSORS: ["binary_sensor.bed_motion"],
            CONF_SPACE_NOTES: "Motion sensor cannot detect sleeping occupants",
            "cancel": False,
        },
    )
    assert res["step_id"] == "spaces_menu"

    res = await hass.config_entries.options.async_configure(
        res["flow_id"], {"space_action": "back"}
    )
    res = await hass.config_entries.options.async_configure(
        res["flow_id"], {"next_step_id": "finish"}
    )
    await hass.async_block_till_done()

    assert len(entry.options[CONF_SPACES]) == 1
    assert (
        entry.options[CONF_SPACES][0][CONF_OCCUPIED_SCHEDULE]
        == "schedule.primary_bedroom_sleep"
    )
    assert entry.options[CONF_SPACES][0][CONF_UNOCCUPIED_SCHEDULE] == ""

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
