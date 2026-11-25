"""Unit tests for HvacButlerJournal persistence, pruning, versioning, and WebSocket API."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.hvac_butler.const import (
    CONF_CLIMATE_ENTITY,
    CONF_DEFAULT_MODE,
    CONF_OCCUPIED_SCHEDULE,
    CONF_SPACES,
    DOMAIN,
)
from custom_components.hvac_butler.coordinator import HvacButlerCoordinator
from custom_components.hvac_butler.journal import (
    JOURNAL_EVENT_SCHEMA_VERSION,
    HvacButlerJournal,
)
from custom_components.hvac_butler.websocket_api import ws_get_journal, ws_run_plan


@pytest.mark.asyncio
async def test_journal_append_versioning_filtering_and_pruning(
    hass: HomeAssistant,
) -> None:
    """Journal stamps schema_version, filters by space, prunes expired/excess entries, and persists."""
    journal = HvacButlerJournal(hass, max_entries=3, retention_days=7)
    await journal.async_load()
    assert journal.entries == []

    now = dt_util.now()
    old_ts = (now - timedelta(days=10)).isoformat()
    recent_1 = (now - timedelta(hours=3)).isoformat()
    recent_2 = (now - timedelta(hours=2)).isoformat()
    recent_3 = (now - timedelta(hours=1)).isoformat()
    recent_4 = now.isoformat()

    # Expired entry should be pruned immediately
    await journal.async_append(
        {
            "timestamp": old_ts,
            "kind": "plan",
            "spaces": {"first_floor": {"changed": False, "summary": "Expired"}},
        }
    )
    assert journal.entries == []

    # Append 4 recent entries with max_entries=3 -> oldest recent is capped out
    rec1 = await journal.async_append(
        {
            "timestamp": recent_1,
            "kind": "plan",
            "spaces": {
                "first_floor": {"changed": False, "summary": "Plan 1"},
                "guest_bedroom": {"changed": False, "summary": "Plan 1"},
            },
        }
    )
    assert rec1["schema_version"] == JOURNAL_EVENT_SCHEMA_VERSION
    assert rec1["id"]

    await journal.async_append(
        {
            "timestamp": recent_2,
            "kind": "intraday",
            "spaces": {"guest_bedroom": {"changed": True, "summary": "Presence on"}},
        }
    )
    await journal.async_append(
        {
            "timestamp": recent_3,
            "kind": "intraday",
            "spaces": {"first_floor": {"changed": False, "summary": "No change"}},
        }
    )
    await journal.async_append(
        {
            "timestamp": recent_4,
            "kind": "plan",
            "spaces": {
                "first_floor": {"changed": True, "summary": "Plan 2"},
                "guest_bedroom": {"changed": False, "summary": "Plan 2"},
            },
        }
    )

    assert len(journal.entries) == 3
    # Newest first
    assert journal.entries[0]["timestamp"] == recent_4
    # Space filtering returns only entries touching that space
    guest_entries = journal.get_entries(space_id="guest_bedroom")
    assert len(guest_entries) == 2
    assert [e["timestamp"] for e in guest_entries] == [recent_4, recent_2]

    # Reload into a new journal instance to verify HA Store persistence
    reloaded = HvacButlerJournal(hass, max_entries=3, retention_days=7)
    await reloaded.async_load()
    assert len(reloaded.entries) == 3
    assert reloaded.entries[0]["schema_version"] == JOURNAL_EVENT_SCHEMA_VERSION
    assert reloaded.entries[0]["timestamp"] == recent_4


@pytest.mark.asyncio
async def test_websocket_journal_and_run_plan_handlers(hass: HomeAssistant) -> None:
    """WebSocket endpoints return status/spaces/journal entries and trigger manual plans."""
    hass.states.async_set(
        "climate.guest_bedroom_space",
        "heat_cool",
        {
            "friendly_name": "Guest Bedroom Space",
            "space_id": "guest_bedroom",
            "preset_mode": "Butler",
            "hvac_modes": ["heat_cool", "heat", "cool", "off"],
        },
    )

    coordinator = HvacButlerCoordinator(
        hass,
        "ws_test_entry",
        {
            CONF_SPACES: [
                {
                    CONF_CLIMATE_ENTITY: "climate.guest_bedroom_space",
                    CONF_OCCUPIED_SCHEDULE: "schedule.guest_occ",
                    CONF_DEFAULT_MODE: "unoccupied",
                }
            ]
        },
    )
    coordinator.status = "ok"
    coordinator.butler_schedules["guest_bedroom"] = "schedule.guest_bedroom_butler"
    await coordinator.journal.async_append(
        {
            "kind": "intraday",
            "status": "ok",
            "trigger": {"type": "presence_change", "label": "Presence"},
            "spaces": {
                "guest_bedroom": {
                    "name": "Guest Bedroom",
                    "changed": True,
                    "summary": "Occupied.",
                }
            },
        }
    )
    hass.data.setdefault(DOMAIN, {})["ws_test_entry"] = coordinator

    conn = MagicMock()
    ws_get_journal(
        hass,
        conn,
        {
            "id": 1,
            "type": f"{DOMAIN}/journal",
            "space_id": "guest_bedroom",
            "limit": 20,
        },
    )
    conn.send_result.assert_called_once()
    msg_id, payload = conn.send_result.call_args[0]
    assert msg_id == 1
    assert payload["status"] == "ok"
    assert len(payload["spaces"]) == 1
    assert payload["spaces"][0]["space_id"] == "guest_bedroom"
    assert payload["spaces"][0]["active_preset"] == "Butler"
    assert len(payload["entries"]) == 1
    assert payload["entries"][0]["trigger"]["label"] == "Presence"

    # Trigger manual run via ws_run_plan
    coordinator.async_run_nightly_plan = AsyncMock()
    conn_run = MagicMock()
    ws_run_plan(hass, conn_run, {"id": 2, "type": f"{DOMAIN}/run_plan"})
    await hass.async_block_till_done()
    conn_run.send_result.assert_called_once_with(
        2, {"started": True, "status": "planning"}
    )
    coordinator.async_run_nightly_plan.assert_awaited_once_with(manual=True)


@pytest.mark.asyncio
async def test_journal_keyframed_short_term_memory_and_cap_fallback(
    hass: HomeAssistant,
) -> None:
    """Short-term memory returns cross-space events back to latest Plan, filtering only if > cap."""
    journal = HvacButlerJournal(hass, max_entries=50, retention_days=7)
    await journal.async_load()

    now = dt_util.now()
    # Older plan before latest keyframe (must NOT be included)
    await journal.async_append(
        {
            "timestamp": (now - timedelta(hours=24)).isoformat(),
            "kind": "plan",
            "trigger": {"type": "scheduled_plan", "label": "Plan"},
            "spaces": {"first_floor": {"changed": False, "summary": "Yesterday plan"}},
        }
    )
    # Latest Plan keyframe
    await journal.async_append(
        {
            "timestamp": (now - timedelta(hours=6)).isoformat(),
            "kind": "plan",
            "trigger": {"type": "scheduled_plan", "label": "Plan"},
            "spaces": {
                "first_floor": {"changed": False, "summary": "Today plan"},
                "loft": {"changed": False, "summary": "Today plan"},
            },
        }
    )
    # 2 intraday events across different spaces
    await journal.async_append(
        {
            "timestamp": (now - timedelta(hours=2)).isoformat(),
            "kind": "intraday",
            "trigger": {"type": "presence_change", "label": "Presence"},
            "spaces": {"loft": {"changed": True, "summary": "Loft occupied"}},
        }
    )
    await journal.async_append(
        {
            "timestamp": (now - timedelta(hours=1)).isoformat(),
            "kind": "intraday",
            "trigger": {"type": "presence_change", "label": "Presence"},
            "spaces": {"first_floor": {"changed": True, "summary": "FF vacant"}},
        }
    )

    # Under cap: includes cross-space events in chronological order starting at latest Plan
    mem = journal.get_recent_context_since_keyframe(
        target_space_ids=["first_floor"], max_entries=20
    )
    assert len(mem) == 3
    assert mem[0]["kind"] == "plan"
    assert mem[0]["spaces"]["first_floor"]["summary"] == "Today plan"
    assert "loft" in mem[1]["spaces"]
    assert "first_floor" in mem[2]["spaces"]

    # Over cap (max_entries=2): falls back to filtering to target_space_ids + Plan keyframe
    mem_capped = journal.get_recent_context_since_keyframe(
        target_space_ids=["first_floor"], max_entries=2
    )
    assert len(mem_capped) == 2
    assert mem_capped[0]["kind"] == "plan"
    assert "first_floor" in mem_capped[1]["spaces"]
    assert "loft" not in mem_capped[1]["spaces"]
