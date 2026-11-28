"""Tests for HVAC Butler's private calendar store, CalendarEntity, boundary triggers, and Call Butler briefing."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock

import pytest
from homeassistant.components.calendar import CalendarEntityFeature
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.util import dt as dt_util
from pytest_homeassistant.common import MockConfigEntry

from custom_components.hvac_butler.calendar_store import ButlerCalendarStore
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
from custom_components.hvac_butler.prompts import build_briefing_prompt


@pytest.mark.asyncio
async def test_calendar_store_crud_boundaries_and_persistence(
    hass: HomeAssistant,
) -> None:
    """Verify ButlerCalendarStore add/update/delete, day_notes formatting, and boundary lookup."""
    tz = dt_util.DEFAULT_TIME_ZONE
    now = datetime(2026, 11, 25, 19, 30, 0, tzinfo=tz)

    store = ButlerCalendarStore(hass)
    await store.async_load()

    counts, affected = await store.async_apply_actions(
        [
            {
                "action": "add",
                "summary": "Thanksgiving Hosting",
                "description": "8 people, heavy cooking; do not pre-boost First Floor.",
                "start": "2026-11-26",
                "end": "2026-11-27",
                "all_day": True,
                "spaces": ["first_floor"],
            },
            {
                "action": "add",
                "summary": "M-I-L in Guest Room",
                "description": "Keep Guest Bedroom on occupied schedule overnight regardless of motion.",
                "start": "2026-11-26T18:00:00",
                "end": "2026-11-27T10:00:00",
                "all_day": False,
                "spaces": ["guest_bedroom"],
            },
        ],
        now=now,
        valid_space_ids={"first_floor", "guest_bedroom"},
    )
    assert counts == {"added": 2, "updated": 0, "deleted": 0}
    assert len(affected) == 2

    # Format day notes for Thanksgiving window
    notes = store.format_day_notes(
        datetime(2026, 11, 26, 0, 0, tzinfo=tz),
        datetime(2026, 11, 27, 0, 0, tzinfo=tz),
    )
    assert len(notes) == 2
    assert any("Thanksgiving Hosting" in n and "first_floor" in n for n in notes)
    assert any("M-I-L in Guest Room" in n and "guest_bedroom" in n for n in notes)

    # Next timed boundary should skip all-day event and return timed start at 18:00 Thu
    nxt = store.get_next_boundary(now)
    assert nxt is not None
    boundary_dt, phase, ev = nxt
    assert phase == "start"
    assert ev.summary == "M-I-L in Guest Room"
    assert boundary_dt.hour == 18 and boundary_dt.day == 26

    # Update the timed event via uid
    counts2, _ = await store.async_apply_actions(
        [
            {
                "action": "update",
                "uid": ev.uid,
                "summary": "M-I-L in Guest Room (Extended)",
                "description": "Staying through Saturday morning.",
                "start": "2026-11-26T18:00:00",
                "end": "2026-11-28T10:00:00",
                "all_day": False,
                "spaces": ["guest_bedroom"],
            }
        ],
        now=now,
    )
    assert counts2 == {"added": 0, "updated": 1, "deleted": 0}

    # Reload into a fresh store instance to verify HA Store persistence
    store2 = ButlerCalendarStore(hass)
    await store2.async_load()
    assert len(store2.events) == 2
    assert any(e.summary == "M-I-L in Guest Room (Extended)" for e in store2.events)

    # Delete recovery
    assert await store2.async_delete_event(ev.uid) is True
    assert len(store2.events) == 1


def test_build_briefing_prompt_includes_finalize_and_context() -> None:
    """Verify Call Butler briefing prompt renders spaces, existing events, and finalize mode."""
    prompt = build_briefing_prompt(
        now_iso="2026-11-25T19:30:00-05:00",
        today_day="wednesday",
        spaces=[
            {
                "space_id": "guest_bedroom",
                "name": "Guest Bedroom",
                "default_mode": "unoccupied",
                "space_notes": "PIR sensor",
            }
        ],
        house_notes="Victorian home",
        upcoming_events=[],
        messages=[
            {
                "role": "user",
                "content": "Tomorrow is Thanksgiving, M-I-L staying in guest room.",
            }
        ],
        finalize=True,
    )
    assert "FINALIZE MODE" in prompt
    assert "guest_bedroom" in prompt
    assert "calendar_actions" in prompt


@pytest.mark.asyncio
async def test_calendar_entity_brief_commit_and_day_notes_integration(
    hass: HomeAssistant,
) -> None:
    """End-to-end test: CalendarEntity is delete-only, Call Butler commits notes, and planner sees day_notes."""
    # Wire fake schedule storage so coordinator setup succeeds cleanly
    ws_owner = MagicMock()
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

    ws_owner.storage_collection = _FakeCollection()
    bound = MagicMock()
    bound.__self__ = ws_owner
    hass.data.setdefault("websocket_api", {})["schedule/update"] = (bound, None)

    hass.states.async_set(
        "climate.guest_bedroom_space",
        "heat_cool",
        {
            "friendly_name": "Guest Bedroom Space",
            "space_id": "guest_bedroom",
            "current_temperature": 62.0,
            "preset_mode": "Butler",
            "hvac_modes": ["heat_cool", "heat", "cool", "off"],
            "schedule_editing": False,
        },
    )

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
                "data": {"hvac_mode": "heat_cool", "heat_to": 60.0, "cool_to": 80.0},
            }
        ]
        for day in DAYS_OF_WEEK
    }

    async def _handle_get_schedule(call: ServiceCall) -> dict[str, Any]:
        eid = call.data["entity_id"]
        if eid == "schedule.guest_occ":
            return {eid: occ_week}
        if eid == "schedule.guest_unocc":
            return {eid: unocc_week}
        return {eid: {day: [] for day in DAYS_OF_WEEK}}

    captured_prompts: list[tuple[str, str]] = []
    now_local = dt_util.now()
    active_start = (now_local - timedelta(minutes=5)).isoformat()
    active_end = (now_local + timedelta(hours=4)).isoformat()

    async def _handle_generate_data(call: ServiceCall) -> dict[str, Any]:
        task_name = call.data["task_name"]
        instructions = call.data["instructions"]
        captured_prompts.append((task_name, instructions))
        if task_name == "hvac_butler_briefing":
            return {
                "data": json.dumps(
                    {
                        "reply": "Understood—I've noted that Guest Bedroom should stay occupied tonight.",
                        "ready_to_commit": True,
                        "calendar_actions": [
                            {
                                "action": "add",
                                "summary": "Guest staying overnight",
                                "description": "Keep Guest Bedroom on occupied schedule regardless of vacancy sensors.",
                                "start": active_start,
                                "end": active_end,
                                "all_day": False,
                                "spaces": ["guest_bedroom"],
                            }
                        ],
                    }
                )
            }
        # Intraday revision triggered by immediate re-eval
        return {
            "data": json.dumps(
                {
                    "spaces": {
                        "guest_bedroom": {
                            "schedule_updates": None,
                            "comfort_boost": None,
                            "intraday_explanation": "Honored calendar note.",
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
                    CONF_CLIMATE_ENTITY: "climate.guest_bedroom_space",
                    CONF_OCCUPIED_SCHEDULE: "schedule.guest_occ",
                    CONF_UNOCCUPIED_SCHEDULE: "schedule.guest_unocc",
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

    # Verify calendar.hvac_butler_notes entity exists and is DELETE_EVENT-only
    cal_state = hass.states.get("calendar.hvac_butler_notes")
    assert cal_state is not None
    assert cal_state.attributes.get("supported_features") == int(
        CalendarEntityFeature.DELETE_EVENT
    )

    coordinator = hass.data[DOMAIN][entry.entry_id]
    # Simulate user hitting Done directly after stating their plan -> triggers finalize + commit + immediate re-eval
    res = await coordinator.async_commit_briefing(
        [{"role": "user", "content": "Guest staying in guest bedroom tonight."}],
        proposed_actions=[],
    )
    await hass.async_block_till_done()

    assert res["committed"] == {"added": 1, "updated": 0, "deleted": 0}
    assert res["triggered_reeval"] is True

    # Confirm the immediately triggered intraday revision received `day_notes` in its prompt
    intraday_prompts = [
        instr
        for tname, instr in captured_prompts
        if tname == "hvac_butler_intraday_revision"
    ]
    assert len(intraday_prompts) == 1
    assert "Guest staying overnight" in intraday_prompts[0]
    assert "Calendar / Day Notes" in intraday_prompts[0]

    # Confirm calendar entity now reflects the active event
    cal_state_after = hass.states.get("calendar.hvac_butler_notes")
    assert cal_state_after is not None
    assert cal_state_after.state == "on"
    assert cal_state_after.attributes.get("message") == "Guest staying overnight"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.asyncio
async def test_calendar_store_recurring_events_rrule_and_exdates(
    hass: HomeAssistant,
) -> None:
    """Verify RFC 5545 RRULE recurring events expand, survive pruning, fire boundaries, and support single-occurrence delete."""
    tz = dt_util.DEFAULT_TIME_ZONE
    # Monday 2026-11-30 07:00
    now = datetime(2026, 11, 30, 7, 0, 0, tzinfo=tz)

    store = ButlerCalendarStore(hass)
    await store.async_load()

    counts, affected = await store.async_apply_actions(
        [
            {
                "action": "add",
                "summary": "Doug Office Commute",
                "description": "Typically in office Tue-Thu; Home Office unoccupied unless presence triggers.",
                "start": "2026-11-10T08:00:00",  # Started 3 weeks ago — must NOT be pruned
                "end": "2026-11-10T17:30:00",
                "all_day": False,
                "rrule": "RRULE:FREQ=WEEKLY;BYDAY=TU,WE,TH",
                "spaces": ["home_office"],
            }
        ],
        now=now,
        valid_space_ids={"home_office"},
    )
    assert counts == {"added": 1, "updated": 0, "deleted": 0}
    assert len(store.events) == 1
    ev = store.events[0]
    assert ev.rrule == "FREQ=WEEKLY;BYDAY=TU,WE,TH"

    # Monday has no occurrence; Tuesday Dec 1 has 08:00-17:30
    mon_notes = store.format_day_notes(
        datetime(2026, 11, 30, 0, 0, tzinfo=tz),
        datetime(2026, 12, 1, 0, 0, tzinfo=tz),
    )
    assert mon_notes == []

    tue_notes = store.format_day_notes(
        datetime(2026, 12, 1, 0, 0, tzinfo=tz),
        datetime(2026, 12, 2, 0, 0, tzinfo=tz),
    )
    assert len(tue_notes) == 1
    assert "2026-12-01 08:00–17:30" in tue_notes[0]
    assert "Doug Office Commute" in tue_notes[0]

    # Full week query returns 3 concrete occurrences (Tue, Wed, Thu)
    week_events = store.get_events_in_range(
        datetime(2026, 11, 30, 0, 0, tzinfo=tz),
        datetime(2026, 12, 7, 0, 0, tzinfo=tz),
    )
    assert len(week_events) == 3
    assert [e.start[:10] for e in week_events] == [
        "2026-12-01",
        "2026-12-02",
        "2026-12-03",
    ]
    # HA CalendarEvent carries rrule and recurrence_id
    ha_ev = week_events[0].to_ha_calendar_event()
    assert ha_ev.rrule == "FREQ=WEEKLY;BYDAY=TU,WE,TH"
    assert ha_ev.recurrence_id == week_events[0].start

    # get_upcoming_events returns 1 concise master series for briefing prompt
    upcoming = store.get_upcoming_events(now, days=30)
    assert len(upcoming) == 1
    assert upcoming[0].to_prompt_dict()["rrule"] == "FREQ=WEEKLY;BYDAY=TU,WE,TH"

    # Next timed boundary from Monday 07:00 is Tuesday Dec 1 08:00 start
    nxt = store.get_next_boundary(now)
    assert nxt is not None
    b_dt, phase, b_ev = nxt
    assert phase == "start"
    assert b_dt.date().isoformat() == "2026-12-01"
    assert b_dt.hour == 8
    assert b_ev.summary == "Doug Office Commute"

    # Deleting a single occurrence (Tuesday Dec 1) records an exdate and leaves Wed/Thu intact
    assert (
        await store.async_delete_event(ev.uid, recurrence_id=week_events[0].start)
        is True
    )
    week_after = store.get_events_in_range(
        datetime(2026, 11, 30, 0, 0, tzinfo=tz),
        datetime(2026, 12, 7, 0, 0, tzinfo=tz),
    )
    assert [e.start[:10] for e in week_after] == ["2026-12-02", "2026-12-03"]

    # Persistence round-trip preserves rrule and exdates
    store2 = ButlerCalendarStore(hass)
    await store2.async_load()
    assert len(store2.events) == 1
    assert store2.events[0].rrule == "FREQ=WEEKLY;BYDAY=TU,WE,TH"
    assert len(store2.events[0].exdates) == 1
