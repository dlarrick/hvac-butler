"""Button platform for HVAC Butler on-demand actions."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEFAULT_NAME, DOMAIN
from .coordinator import HvacButlerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HVAC Butler button entities."""
    coordinator: HvacButlerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            HvacButlerRunNightlyPlanButton(coordinator),
            HvacButlerRunIntradayButton(coordinator),
        ]
    )


class HvacButlerRunNightlyPlanButton(ButtonEntity):
    """Button to trigger the nightly macro-planner on demand."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = "run_nightly_plan"
    _attr_icon = "mdi:play-circle-outline"

    def __init__(self, coordinator: HvacButlerCoordinator) -> None:
        self.coordinator = coordinator
        butler_name = coordinator.config.get(CONF_NAME, DEFAULT_NAME)
        self._attr_unique_id = f"{coordinator.entry_id}_run_nightly_plan"
        self._attr_name = "Run nightly plan now"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry_id)},
            name=butler_name,
            manufacturer="HVAC Butler",
            model="Contextual Climate Supervisor",
        )

    async def async_press(self) -> None:
        """Run the nightly macro-planner immediately."""
        await self.coordinator.async_run_nightly_plan(manual=True)


class HvacButlerRunIntradayButton(ButtonEntity):
    """Button to trigger an on-demand intraday evaluation across all spaces."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = "run_intraday"
    _attr_icon = "mdi:refresh-circle"

    def __init__(self, coordinator: HvacButlerCoordinator) -> None:
        self.coordinator = coordinator
        butler_name = coordinator.config.get(CONF_NAME, DEFAULT_NAME)
        self._attr_unique_id = f"{coordinator.entry_id}_run_intraday"
        self._attr_name = "Run intraday check now"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry_id)},
            name=butler_name,
            manufacturer="HVAC Butler",
            model="Contextual Climate Supervisor",
        )

    async def async_press(self) -> None:
        """Run an on-demand intraday evaluation immediately."""
        await self.coordinator.async_run_manual_intraday()
