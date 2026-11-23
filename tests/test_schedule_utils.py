"""Unit tests for pure-Python schedule_utils."""

from __future__ import annotations

import pytest

from custom_components.hvac_butler.const import DAYS_OF_WEEK
from custom_components.hvac_butler.schedule_utils import (
    ScheduleBlock,
    build_butler_week_payload,
    merge_intraday_blocks,
    minutes_to_time_str,
    parse_ha_blocks,
    slice_blocks_to_window,
    time_str_to_minutes,
)


def test_time_str_roundtrip_and_midnight() -> None:
    assert time_str_to_minutes("00:00:00") == 0
    assert time_str_to_minutes("06:30") == 390
    assert time_str_to_minutes("21:00:00") == 1260
    assert time_str_to_minutes("24:00:00") == 1440
    assert time_str_to_minutes("23:59:59") == 1440

    assert minutes_to_time_str(0) == "00:00:00"
    assert minutes_to_time_str(390) == "06:30:00"
    assert minutes_to_time_str(1260) == "21:00:00"
    assert minutes_to_time_str(1440) == "24:00:00"

    with pytest.raises(ValueError):
        time_str_to_minutes("25:00:00")


def test_parse_and_slice_blocks() -> None:
    raw = [
        {
            "from": "06:30:00",
            "to": "22:00:00",
            "data": {"hvac_mode": "heat_cool", "heat_to": 68, "cool_to": 74},
        },
        {
            "from": "00:00:00",
            "to": "06:30:00",
            "data": {"hvac_mode": "heat_cool", "heat_to": 62, "cool_to": 76},
        },
        {
            "from": "22:00:00",
            "to": "24:00:00",
            "data": {"hvac_mode": "heat_cool", "heat_to": 62, "cool_to": 76},
        },
    ]
    blocks = parse_ha_blocks(raw)
    assert [b.start_min for b in blocks] == [0, 390, 1320]

    # Slice tonight 21:00 (1260) to 24:00 (1440)
    tonight = slice_blocks_to_window(blocks, 1260, 1440)
    assert len(tonight) == 2
    assert (tonight[0].start_min, tonight[0].end_min, tonight[0].heat_to) == (
        1260,
        1320,
        68.0,
    )
    assert (tonight[1].start_min, tonight[1].end_min, tonight[1].heat_to) == (
        1320,
        1440,
        62.0,
    )


def test_merge_intraday_blocks() -> None:
    existing = [
        ScheduleBlock(0, 390, "heat_cool", 62.0, 76.0),
        ScheduleBlock(390, 1320, "heat_cool", 68.0, 74.0),
        ScheduleBlock(1320, 1440, "heat_cool", 62.0, 76.0),
    ]
    replacement = [
        ScheduleBlock(600, 1020, "heat_cool", 58.0, 82.0),
        ScheduleBlock(1020, 1440, "heat_cool", 68.0, 74.0),
    ]
    merged = merge_intraday_blocks(existing, replacement, split_min=600)
    assert [(b.start_min, b.end_min, b.heat_to) for b in merged] == [
        (0, 390, 62.0),
        (390, 600, 68.0),
        (600, 1020, 58.0),
        (1020, 1440, 68.0),
    ]


def test_build_butler_week_payload_leaves_other_days_blank() -> None:
    tonight = [ScheduleBlock(1260, 1440, "heat_cool", 62.0, 76.0)]
    tomorrow = [ScheduleBlock(0, 1440, "heat_cool", 68.0, 74.0)]

    week = build_butler_week_payload(
        tonight_day="sunday",
        tonight_blocks=tonight,
        tomorrow_day="monday",
        tomorrow_blocks=tomorrow,
    )
    assert set(week.keys()) == set(DAYS_OF_WEEK)
    assert len(week["sunday"]) == 1
    assert len(week["monday"]) == 1
    for day in ("tuesday", "wednesday", "thursday", "friday", "saturday"):
        assert week[day] == []
