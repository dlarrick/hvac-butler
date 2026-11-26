"""Standard Home Assistant Calendar entity for HVAC Butler's self-maintained notes."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from homeassistant.components.calendar import (
    CalendarEntity,
    CalendarEntityFeature,
    CalendarEvent,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DEFAULT_NAME, DOMAIN
from .coordinator import HvacButlerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HVAC Butler calendar entity."""
    coordinator: HvacButlerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HvacButlerCalendarEntity(coordinator, entry)])


class HvacButlerCalendarEntity(CalendarEntity):
    """Read-only (+ delete recovery) HA Calendar entity maintained by HVAC Butler."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_name = "Notes"
    _attr_supported_features = CalendarEntityFeature.DELETE_EVENT

    def __init__(self, coordinator: HvacButlerCoordinator, entry: ConfigEntry) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_calendar_notes"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title or DEFAULT_NAME,
            manufacturer="HVAC Butler",
            model="Contextual Climate Supervisor",
        )
        self._unsub: Callable[[], None] | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._unsub = self._coordinator.register_listener(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None
        await super().async_will_remove_from_hass()

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current or next upcoming Butler calendar event."""
        ev = self._coordinator.calendar_store.get_current_or_next_event(dt_util.now())
        return ev.to_ha_calendar_event() if ev is not None else None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return Butler calendar events within [start_date, end_date)."""
        events = self._coordinator.calendar_store.get_events_in_range(
            start_date, end_date
        )
        return [ev.to_ha_calendar_event() for ev in events]

    async def async_delete_event(
        self,
        uid: str,
        recurrence_id: str | None = None,
        recurrence_range: str | None = None,
    ) -> None:
        """Allow deleting an event from HA's native Calendar UI as a recovery escape hatch."""
        deleted = await self._coordinator.calendar_store.async_delete_event(uid)
        if deleted:
            self._coordinator.reschedule_calendar_boundary()
            self._coordinator.notify_state_changed()
