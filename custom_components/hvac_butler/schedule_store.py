"""Native Home Assistant schedule.* reader and ScheduleStorageCollection writer.

Strictly uses native Home Assistant `schedule` entities (never subclasses Schedule).
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.const import CONF_ICON, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify

from .const import DAYS_OF_WEEK
from .schedule_utils import ScheduleBlock, parse_ha_blocks

_LOGGER = logging.getLogger(__name__)

BUTLER_SCHEDULE_ICON = "mdi:robot-outline"


def get_schedule_storage_collection(hass: HomeAssistant) -> Any | None:
    """Return HA's native ScheduleStorageCollection from registered WebSocket handlers."""
    ws_handlers = hass.data.get("websocket_api")
    if not isinstance(ws_handlers, dict):
        return None

    for cmd in ("schedule/update", "schedule/create", "schedule/list"):
        entry = ws_handlers.get(cmd)
        if not entry:
            continue
        handler = entry[0] if isinstance(entry, tuple) else entry
        ws_owner = getattr(handler, "__self__", None)
        collection = getattr(ws_owner, "storage_collection", None)
        if collection is not None:
            return collection

    return None


async def async_read_schedule(
    hass: HomeAssistant, entity_id: str
) -> dict[str, list[ScheduleBlock]]:
    """Read all 7 days of a native schedule.* entity via schedule.get_schedule."""
    empty: dict[str, list[ScheduleBlock]] = {day: [] for day in DAYS_OF_WEEK}
    if not entity_id:
        return empty

    try:
        response = await hass.services.async_call(
            "schedule",
            "get_schedule",
            {"entity_id": entity_id},
            blocking=True,
            return_response=True,
        )
    except Exception as err:
        _LOGGER.warning("Failed to read schedule %s: %s", entity_id, err)
        return empty

    if not isinstance(response, dict):
        return empty

    # HA returns {entity_id: {monday: [...], ...}} for entity services
    raw_week = response.get(entity_id, response)
    if not isinstance(raw_week, dict):
        return empty

    result: dict[str, list[ScheduleBlock]] = {}
    for day in DAYS_OF_WEEK:
        raw_blocks = raw_week.get(day) or []
        try:
            result[day] = parse_ha_blocks(raw_blocks)
        except (ValueError, KeyError, TypeError) as err:
            _LOGGER.warning(
                "Skipping invalid blocks in %s (%s): %s", entity_id, day, err
            )
            result[day] = []
    return result


def _resolve_storage_id(
    hass: HomeAssistant, collection: Any, entity_id: str
) -> str | None:
    """Resolve entity_id -> storage item ID via entity registry unique_id first."""
    ent_reg = er.async_get(hass)
    reg_entry = ent_reg.async_get(entity_id)
    if reg_entry and reg_entry.unique_id and reg_entry.unique_id in collection.data:
        return reg_entry.unique_id

    slug = entity_id.removeprefix("schedule.")
    if slug in collection.data:
        return slug
    return None


async def async_ensure_butler_schedule(
    hass: HomeAssistant,
    space_slug: str,
    space_name: str,
) -> str | None:
    """Ensure a native HA storage schedule exists for a space; return its entity_id."""
    expected_slug = slugify(f"{space_slug}_butler")
    expected_entity_id = f"schedule.{expected_slug}"

    # 1. Check if entity already exists in entity registry or state machine
    ent_reg = er.async_get(hass)
    if ent_reg.async_get(expected_entity_id) is not None:
        return expected_entity_id
    if hass.states.get(expected_entity_id) is not None:
        return expected_entity_id

    # 2. Check storage collection directly (e.g. if renamed or recently created)
    collection = get_schedule_storage_collection(hass)
    if collection is None:
        _LOGGER.warning(
            "Native schedule storage collection unavailable; cannot auto-create %s",
            expected_entity_id,
        )
        return None

    if expected_slug in collection.data:
        existing_eid = ent_reg.async_get_entity_id(
            "schedule", "schedule", expected_slug
        )
        return existing_eid or expected_entity_id

    # 3. Create new native storage schedule helper
    display_name = (
        f"{space_name} Butler"
        if not space_name.lower().endswith("butler")
        else space_name
    )
    payload: dict[str, Any] = {
        CONF_NAME: display_name,
        CONF_ICON: BUTLER_SCHEDULE_ICON,
        **{day: [] for day in DAYS_OF_WEEK},
    }
    try:
        created = await collection.async_create_item(payload)
    except Exception as err:
        _LOGGER.error(
            "Failed to create native butler schedule '%s': %s", display_name, err
        )
        return None

    created_id = created.get("id", expected_slug)
    resolved_eid = ent_reg.async_get_entity_id("schedule", "schedule", created_id)
    return resolved_eid or f"schedule.{created_id}"


async def async_write_butler_schedule(
    hass: HomeAssistant,
    entity_id: str,
    display_name: str,
    week_payload: dict[str, list[dict[str, Any]]],
) -> bool:
    """Update an existing native HA storage schedule with a 7-day payload."""
    collection = get_schedule_storage_collection(hass)
    if collection is None:
        _LOGGER.warning(
            "Native schedule storage collection unavailable; cannot update %s",
            entity_id,
        )
        return False

    storage_id = _resolve_storage_id(hass, collection, entity_id)
    if storage_id is None:
        _LOGGER.warning(
            "Could not resolve storage ID for schedule %s; skipping update", entity_id
        )
        return False

    existing = collection.data.get(storage_id, {})
    update_data: dict[str, Any] = {
        CONF_NAME: existing.get(CONF_NAME, display_name),
        CONF_ICON: existing.get(CONF_ICON, BUTLER_SCHEDULE_ICON),
        **{day: week_payload.get(day, []) for day in DAYS_OF_WEEK},
    }
    try:
        await collection.async_update_item(storage_id, update_data)
        return True
    except Exception as err:
        _LOGGER.error("Failed to update schedule %s: %s", entity_id, err)
        return False
