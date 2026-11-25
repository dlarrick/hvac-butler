"""The HVAC Butler integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_CLIMATE_ENTITY, CONF_SPACES, DOMAIN
from .coordinator import HvacButlerCoordinator, async_unregister_fusion_presets
from .frontend_loader import async_register_frontend
from .websocket_api import async_register_websocket_commands

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up HVAC Butler static frontend and WebSocket endpoints."""
    await async_register_frontend(hass)
    async_register_websocket_commands(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HVAC Butler from a config entry."""
    await async_register_frontend(hass)
    async_register_websocket_commands(hass)

    merged_config = {**entry.data, **entry.options}
    coordinator = HvacButlerCoordinator(hass, entry.entry_id, merged_config)
    await coordinator.async_setup()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry without wiping active 'Butler' presets on reload/restart."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: HvacButlerCoordinator | None = hass.data.get(DOMAIN, {}).pop(
            entry.entry_id, None
        )
        if coordinator is not None:
            # Only unregister dynamic presets if the user explicitly disabled the entry
            await coordinator.async_unload(
                unregister_presets=bool(entry.disabled_by is not None)
            )
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Unregister dynamic 'Butler' presets when the integration is permanently removed."""
    merged_config = {**entry.data, **entry.options}
    climate_entities = [
        str(space[CONF_CLIMATE_ENTITY])
        for space in merged_config.get(CONF_SPACES, [])
        if isinstance(space, dict) and space.get(CONF_CLIMATE_ENTITY)
    ]
    await async_unregister_fusion_presets(hass, climate_entities)
