"""WebSocket API endpoints for the HVAC Butler dashboard card."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.util.hass_dict import HassKey

from .const import DOMAIN
from .coordinator import HvacButlerCoordinator

_WS_REGISTERED: HassKey[bool] = HassKey(f"{DOMAIN}.websocket_registered")


def _get_coordinator(hass: HomeAssistant) -> HvacButlerCoordinator | None:
    """Return the active HvacButlerCoordinator instance if loaded."""
    domain_data = hass.data.get(DOMAIN)
    if not isinstance(domain_data, dict):
        return None
    for val in domain_data.values():
        if isinstance(val, HvacButlerCoordinator):
            return val
    return None


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/journal",
        vol.Optional("space_id"): str,
        vol.Optional("days"): vol.All(vol.Coerce(int), vol.Range(min=1, max=7)),
        vol.Optional("limit"): vol.All(vol.Coerce(int), vol.Range(min=1, max=500)),
    }
)
@callback
def ws_get_journal(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return Butler runtime status, configured spaces, and journal entries."""
    coordinator = _get_coordinator(hass)
    if coordinator is None:
        connection.send_error(
            msg["id"], "not_loaded", "HVAC Butler is not currently loaded."
        )
        return

    space_id = msg.get("space_id") or None
    days = int(msg["days"]) if msg.get("days") is not None else None
    limit = int(msg["limit"]) if msg.get("limit") is not None else None
    if days is None and limit is None:
        days = 2
    entries = coordinator.journal.get_entries(space_id=space_id, days=days, limit=limit)
    latest_plan = coordinator.journal.get_latest_plan(space_id=space_id)

    connection.send_result(
        msg["id"],
        {
            "status": coordinator.status,
            "last_nightly_run": coordinator.last_nightly_run,
            "last_intraday_run": coordinator.last_intraday_run,
            "last_error": coordinator.last_error,
            "spaces": coordinator.get_spaces_summary(),
            "entries": entries,
            "latest_plan": latest_plan,
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/run_plan",
    }
)
@callback
def ws_run_plan(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Trigger an on-demand macro-plan run in the background."""
    coordinator = _get_coordinator(hass)
    if coordinator is None:
        connection.send_error(
            msg["id"], "not_loaded", "HVAC Butler is not currently loaded."
        )
        return

    if coordinator.status in ("planning", "revising"):
        connection.send_result(
            msg["id"], {"started": False, "status": coordinator.status}
        )
        return

    hass.async_create_task(coordinator.async_run_nightly_plan(manual=True))
    connection.send_result(msg["id"], {"started": True, "status": "planning"})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/run_intraday",
        vol.Optional("space_id"): str,
    }
)
@callback
def ws_run_intraday(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Trigger an on-demand intraday evaluation in the background."""
    coordinator = _get_coordinator(hass)
    if coordinator is None:
        connection.send_error(
            msg["id"], "not_loaded", "HVAC Butler is not currently loaded."
        )
        return

    if coordinator.status in ("planning", "revising"):
        connection.send_result(
            msg["id"], {"started": False, "status": coordinator.status}
        )
        return

    space_id = msg.get("space_id") or None
    hass.async_create_task(coordinator.async_run_manual_intraday(space_id=space_id))
    connection.send_result(msg["id"], {"started": True, "status": "revising"})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/brief",
        vol.Required("messages"): [
            vol.Schema(
                {
                    vol.Required("role"): vol.In(["user", "assistant"]),
                    vol.Required("content"): str,
                }
            )
        ],
    }
)
@websocket_api.async_response
async def ws_brief_butler(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle one conversational 'Call Butler' briefing turn."""
    coordinator = _get_coordinator(hass)
    if coordinator is None:
        connection.send_error(
            msg["id"], "not_loaded", "HVAC Butler is not currently loaded."
        )
        return

    try:
        result = await coordinator.async_brief_butler(msg["messages"])
    except Exception as err:
        connection.send_error(msg["id"], "brief_failed", str(err).splitlines()[0][:240])
        return

    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/brief_commit",
        vol.Required("messages"): [
            vol.Schema(
                {
                    vol.Required("role"): vol.In(["user", "assistant"]),
                    vol.Required("content"): str,
                }
            )
        ],
        vol.Optional("calendar_actions", default=[]): list,
    }
)
@websocket_api.async_response
async def ws_brief_commit(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Finalize and commit calendar notes from a 'Call Butler' conversation."""
    coordinator = _get_coordinator(hass)
    if coordinator is None:
        connection.send_error(
            msg["id"], "not_loaded", "HVAC Butler is not currently loaded."
        )
        return

    try:
        result = await coordinator.async_commit_briefing(
            msg["messages"], proposed_actions=msg.get("calendar_actions") or []
        )
    except Exception as err:
        connection.send_error(
            msg["id"], "commit_failed", str(err).splitlines()[0][:240]
        )
        return

    connection.send_result(msg["id"], result)


@callback
def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register HVAC Butler WebSocket API commands once per HA process."""
    if hass.data.get(_WS_REGISTERED):
        return
    websocket_api.async_register_command(hass, ws_get_journal)
    websocket_api.async_register_command(hass, ws_run_plan)
    websocket_api.async_register_command(hass, ws_run_intraday)
    websocket_api.async_register_command(hass, ws_brief_butler)
    websocket_api.async_register_command(hass, ws_brief_commit)
    hass.data[_WS_REGISTERED] = True
