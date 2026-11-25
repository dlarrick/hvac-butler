"""Pure-Python schedule block parsing, slicing, merging, and HA payload helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .const import DAYS_OF_WEEK

VALID_HVAC_MODES = frozenset({"heat_cool", "heat", "cool", "off"})


@dataclass(slots=True)
class ScheduleBlock:
    """Normalized climate schedule block covering [start_min, end_min) in 0..1440."""

    start_min: int
    end_min: int
    hvac_mode: str = "heat_cool"
    heat_to: float | None = None
    cool_to: float | None = None

    def to_ha_dict(self) -> dict[str, Any]:
        """Serialize to Home Assistant schedule storage / prompt dict format."""
        data: dict[str, Any] = {"hvac_mode": self.hvac_mode}
        if self.heat_to is not None:
            data["heat_to"] = round(float(self.heat_to), 1)
        if self.cool_to is not None:
            data["cool_to"] = round(float(self.cool_to), 1)
        return {
            "from": minutes_to_time_str(self.start_min),
            "to": minutes_to_time_str(self.end_min),
            "data": data,
        }


def time_str_to_minutes(value: str) -> int:
    """Convert 'HH:MM', 'HH:MM:SS', or 'HH:MM:SS.ffffff' (incl. time.max) to 0..1440."""
    if not isinstance(value, str):
        raise TypeError(f"Expected time string, got {type(value).__name__}")
    raw = value.strip()
    parts = raw.split(":")
    if len(parts) not in (2, 3):
        raise ValueError(f"Invalid time format: {value!r}")
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2]) if len(parts) == 3 else 0.0

    if hours == 24 and minutes == 0 and seconds == 0.0:
        return 1440
    if hours == 23 and minutes == 59 and 59.0 <= seconds < 60.0:
        return 1440
    if not (0 <= hours <= 23 and 0 <= minutes <= 59 and 0.0 <= seconds < 60.0):
        raise ValueError(f"Out-of-range time: {value!r}")
    return hours * 60 + minutes


def minutes_to_time_str(minutes: int) -> str:
    """Convert integer minutes in 0..1440 to 'HH:MM:SS' (1440 -> '24:00:00')."""
    if not (0 <= minutes <= 1440):
        raise ValueError(f"Minutes out of range 0..1440: {minutes}")
    if minutes == 1440:
        return "24:00:00"
    hours, mins = divmod(minutes, 60)
    return f"{hours:02d}:{mins:02d}:00"


def parse_ha_blocks(raw_blocks: list[dict[str, Any]] | None) -> list[ScheduleBlock]:
    """Parse raw HA schedule block dicts into sorted ScheduleBlock objects."""
    if not raw_blocks:
        return []

    parsed: list[ScheduleBlock] = []
    for item in raw_blocks:
        if not isinstance(item, dict):
            raise TypeError(f"Schedule block must be a dict, got {type(item).__name__}")
        start_min = time_str_to_minutes(str(item["from"]))
        end_min = time_str_to_minutes(str(item["to"]))
        if end_min <= start_min:
            raise ValueError(
                f"Block end ({item['to']}) must be after start ({item['from']})"
            )

        data = item.get("data") or {}
        if not isinstance(data, dict):
            raise TypeError("Block 'data' must be a dict")

        mode = str(data.get("hvac_mode", "heat_cool")).lower()
        if mode not in VALID_HVAC_MODES:
            raise ValueError(f"Unsupported hvac_mode: {mode!r}")

        heat_raw = data.get("heat_to")
        cool_raw = data.get("cool_to")
        heat_to = float(heat_raw) if heat_raw is not None else None
        cool_to = float(cool_raw) if cool_raw is not None else None

        parsed.append(
            ScheduleBlock(
                start_min=start_min,
                end_min=end_min,
                hvac_mode=mode,
                heat_to=heat_to,
                cool_to=cool_to,
            )
        )

    parsed.sort(key=lambda b: (b.start_min, b.end_min))
    return parsed


def slice_blocks_to_window(
    blocks: list[ScheduleBlock],
    window_start_min: int,
    window_end_min: int,
) -> list[ScheduleBlock]:
    """Clip a day's blocks to [window_start_min, window_end_min)."""
    if window_end_min <= window_start_min:
        return []

    sliced: list[ScheduleBlock] = []
    for blk in blocks:
        s = max(blk.start_min, window_start_min)
        e = min(blk.end_min, window_end_min)
        if e > s:
            sliced.append(
                ScheduleBlock(
                    start_min=s,
                    end_min=e,
                    hvac_mode=blk.hvac_mode,
                    heat_to=blk.heat_to,
                    cool_to=blk.cool_to,
                )
            )
    return sliced


def merge_intraday_blocks(
    existing_today: list[ScheduleBlock],
    replacement_remaining: list[ScheduleBlock],
    split_min: int,
) -> list[ScheduleBlock]:
    """Keep existing blocks before split_min and append replacement blocks from split_min..1440."""
    prefix = slice_blocks_to_window(existing_today, 0, split_min)
    suffix = slice_blocks_to_window(replacement_remaining, split_min, 1440)
    merged = prefix + suffix
    merged.sort(key=lambda b: (b.start_min, b.end_min))
    return merged


def build_butler_week_payload(
    *,
    tonight_day: str,
    tonight_blocks: list[ScheduleBlock],
    tomorrow_day: str | None = None,
    tomorrow_blocks: list[ScheduleBlock] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Build a 7-day HA storage payload populating only active day(s); all other days are []."""
    if tonight_day not in DAYS_OF_WEEK:
        raise ValueError(f"Unknown day: {tonight_day!r}")
    if tomorrow_day is not None and tomorrow_day not in DAYS_OF_WEEK:
        raise ValueError(f"Unknown day: {tomorrow_day!r}")

    week: dict[str, list[dict[str, Any]]] = {day: [] for day in DAYS_OF_WEEK}
    week[tonight_day] = [b.to_ha_dict() for b in tonight_blocks]
    if tomorrow_day is not None and tomorrow_blocks is not None:
        week[tomorrow_day] = [b.to_ha_dict() for b in tomorrow_blocks]
    return week
