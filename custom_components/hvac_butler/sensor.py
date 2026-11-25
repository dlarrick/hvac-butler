"""Observability sensors for HVAC Butler (with RestoreEntity restart persistence)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DEFAULT_NAME, DOMAIN
from .coordinator import HvacButlerCoordinator

MAX_STATE_LENGTH = 250


def _truncate_state(text: str) -> str:
    if len(text) <= MAX_STATE_LENGTH:
        return text
    return f"{text[: MAX_STATE_LENGTH - 1]}…"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HVAC Butler observability sensors."""
    coordinator: HvacButlerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            HvacButlerStatusSensor(coordinator),
            HvacButlerDailyPlanSummarySensor(coordinator),
            HvacButlerIntradayExplanationSensor(coordinator),
        ]
    )


class HvacButlerSensorBase(SensorEntity, RestoreEntity):
    """Base sensor for HVAC Butler (strictly non-polling, survives restarts)."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator: HvacButlerCoordinator) -> None:
        self.coordinator = coordinator
        self._unsub: Callable[[], None] | None = None
        butler_name = coordinator.config.get(CONF_NAME, DEFAULT_NAME)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry_id)},
            name=butler_name,
            manufacturer="HVAC Butler",
            model="Contextual Climate Supervisor",
        )

    def _restore_from_last_state(self, last_state: State) -> None:
        """Hook for subclasses to restore persisted coordinator fields."""

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (
            "unknown",
            "unavailable",
            None,
        ):
            self._restore_from_last_state(last_state)
        self._unsub = self.coordinator.register_listener(self._handle_update)
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()


class HvacButlerStatusSensor(HvacButlerSensorBase):
    """Reports overall Butler status: idle, planning, revising, ok, fallback, or error."""

    _attr_translation_key = "status"
    _attr_icon = "mdi:robot-outline"

    def __init__(self, coordinator: HvacButlerCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry_id}_status"
        self._attr_name = "Status"

    def _restore_from_last_state(self, last_state: State) -> None:
        if self.coordinator.status == "idle" and last_state.state not in (
            "planning",
            "revising",
        ):
            self.coordinator.status = last_state.state
        attrs = last_state.attributes
        if self.coordinator.last_nightly_run is None and attrs.get("last_nightly_run"):
            self.coordinator.last_nightly_run = str(attrs["last_nightly_run"])
        if self.coordinator.last_intraday_run is None and attrs.get(
            "last_intraday_run"
        ):
            self.coordinator.last_intraday_run = str(attrs["last_intraday_run"])
        if self.coordinator.last_error is None and attrs.get("last_error"):
            self.coordinator.last_error = str(attrs["last_error"])

    @property
    def native_value(self) -> str:
        return self.coordinator.status

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "last_nightly_run": self.coordinator.last_nightly_run,
            "last_intraday_run": self.coordinator.last_intraday_run,
            "spaces_configured": len(self.coordinator.spaces),
            "butler_schedules": dict(self.coordinator.butler_schedules),
            "last_error": self.coordinator.last_error,
        }


class HvacButlerDailyPlanSummarySensor(HvacButlerSensorBase):
    """Reports the latest nightly macro-planner headline and full per-space summaries."""

    _attr_translation_key = "daily_plan_summary"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: HvacButlerCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry_id}_daily_plan_summary"
        self._attr_name = "Daily plan summary"

    def _restore_from_last_state(self, last_state: State) -> None:
        if self.coordinator.space_daily_summaries:
            return
        self.coordinator.daily_plan_headline = last_state.state
        attrs = last_state.attributes
        if attrs.get("full_summary"):
            self.coordinator.daily_plan_summary = str(attrs["full_summary"])
        if isinstance(attrs.get("space_summaries"), dict):
            self.coordinator.space_daily_summaries = dict(attrs["space_summaries"])
        if self.coordinator.last_nightly_run is None and attrs.get("updated_at"):
            self.coordinator.last_nightly_run = str(attrs["updated_at"])

    @property
    def native_value(self) -> str:
        return _truncate_state(self.coordinator.daily_plan_headline)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "full_summary": self.coordinator.daily_plan_summary,
            "space_summaries": dict(self.coordinator.space_daily_summaries),
            "updated_at": self.coordinator.last_nightly_run,
        }


class HvacButlerIntradayExplanationSensor(HvacButlerSensorBase):
    """Reports the latest intraday event-driven revision headline and full explanations."""

    _attr_translation_key = "intraday_explanation"
    _attr_icon = "mdi:lightning-bolt-outline"

    def __init__(self, coordinator: HvacButlerCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry_id}_intraday_explanation"
        self._attr_name = "Intraday explanation"

    def _restore_from_last_state(self, last_state: State) -> None:
        if self.coordinator.space_intraday_explanations:
            return
        self.coordinator.intraday_headline = last_state.state
        attrs = last_state.attributes
        if attrs.get("full_explanation"):
            self.coordinator.intraday_explanation = str(attrs["full_explanation"])
        if isinstance(attrs.get("space_explanations"), dict):
            self.coordinator.space_intraday_explanations = dict(
                attrs["space_explanations"]
            )
        if isinstance(attrs.get("last_trigger"), dict):
            self.coordinator.last_trigger = dict(attrs["last_trigger"])
        if self.coordinator.last_intraday_run is None and attrs.get("updated_at"):
            self.coordinator.last_intraday_run = str(attrs["updated_at"])

    @property
    def native_value(self) -> str:
        return _truncate_state(self.coordinator.intraday_headline)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "full_explanation": self.coordinator.intraday_explanation,
            "space_explanations": dict(self.coordinator.space_intraday_explanations),
            "last_trigger": self.coordinator.last_trigger,
            "updated_at": self.coordinator.last_intraday_run,
        }
