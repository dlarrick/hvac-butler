"""HA Store-backed private calendar storage for HVAC Butler's self-maintained notes."""

from __future__ import annotations

import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any

from homeassistant.components.calendar import CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CALENDAR_STORAGE_VERSION = 1
CALENDAR_STORAGE_KEY = f"{DOMAIN}.calendar_notes"
CALENDAR_RETENTION_DAYS = 7


@dataclass(slots=True)
class ButlerCalendarEvent:
    """Persisted Butler calendar note representing an upcoming or active event."""

    uid: str
    summary: str
    description: str
    start: str  # ISO datetime (with tz) or YYYY-MM-DD for all-day
    end: str  # ISO datetime (with tz) or YYYY-MM-DD (exclusive) for all-day
    all_day: bool = False
    spaces: list[str] = field(default_factory=list)
    created_at: str = ""

    def start_dt(self) -> datetime:
        """Return timezone-aware local start datetime for range comparisons."""
        tz = dt_util.DEFAULT_TIME_ZONE
        if self.all_day:
            d = date.fromisoformat(self.start[:10])
            return datetime.combine(d, time.min, tzinfo=tz)
        parsed = dt_util.parse_datetime(self.start)
        if parsed is None:
            d = date.fromisoformat(self.start[:10])
            return datetime.combine(d, time.min, tzinfo=tz)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=tz)
        return dt_util.as_local(parsed)

    def end_dt(self) -> datetime:
        """Return timezone-aware local end datetime for range comparisons."""
        tz = dt_util.DEFAULT_TIME_ZONE
        if self.all_day:
            d = date.fromisoformat(self.end[:10])
            return datetime.combine(d, time.min, tzinfo=tz)
        parsed = dt_util.parse_datetime(self.end)
        if parsed is None:
            d = date.fromisoformat(self.end[:10])
            return datetime.combine(d, time.max, tzinfo=tz)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=tz)
        return dt_util.as_local(parsed)

    def to_ha_calendar_event(self) -> CalendarEvent:
        """Convert to Home Assistant's native CalendarEvent object."""
        if self.all_day:
            start_val: date | datetime = date.fromisoformat(self.start[:10])
            end_val: date | datetime = date.fromisoformat(self.end[:10])
            if end_val <= start_val:
                end_val = start_val + timedelta(days=1)
        else:
            start_val = self.start_dt()
            end_val = self.end_dt()
            if end_val <= start_val:
                end_val = start_val + timedelta(hours=1)

        desc = self.description
        if self.spaces:
            spaces_tag = f"Spaces: {', '.join(self.spaces)}"
            desc = f"{desc}\n({spaces_tag})" if desc else spaces_tag

        return CalendarEvent(
            start=start_val,
            end=end_val,
            summary=self.summary,
            description=desc or None,
            uid=self.uid,
        )

    def to_prompt_dict(self) -> dict[str, Any]:
        """Serialize compactly for briefing prompt context."""
        return {
            "uid": self.uid,
            "summary": self.summary,
            "description": self.description,
            "start": self.start,
            "end": self.end,
            "all_day": self.all_day,
            "spaces": list(self.spaces),
        }

    def format_day_note(self) -> str:
        """Format into a clear single-string note for the planner's `day_notes` slot."""
        if self.all_day:
            start_d = self.start[:10]
            end_d = self.end[:10]
            try:
                s_date = date.fromisoformat(start_d)
                e_date = date.fromisoformat(end_d)
                if e_date <= s_date + timedelta(days=1):
                    when = f"{start_d} (All Day)"
                else:
                    last_inclusive = (e_date - timedelta(days=1)).isoformat()
                    when = f"{start_d} through {last_inclusive} (All Day)"
            except ValueError:
                when = f"{start_d} (All Day)"
        else:
            s_dt = self.start_dt()
            e_dt = self.end_dt()
            if s_dt.date() == e_dt.date():
                when = f"{s_dt.strftime('%Y-%m-%d %H:%M')}–{e_dt.strftime('%H:%M')}"
            else:
                when = f"{s_dt.strftime('%Y-%m-%d %H:%M')} to {e_dt.strftime('%Y-%m-%d %H:%M')}"

        scope = (
            f" | Spaces: {', '.join(self.spaces)}" if self.spaces else " | Whole House"
        )
        body = f": {self.description}" if self.description else ""
        return f"[{when}{scope}] {self.summary}{body}"


def _normalize_event_times(
    raw_start: str, raw_end: str | None, all_day: bool
) -> tuple[str, str, bool]:
    """Normalize AI-emitted start/end strings into consistent ISO or YYYY-MM-DD values."""
    tz = dt_util.DEFAULT_TIME_ZONE
    raw_start = str(raw_start).strip()
    raw_end_str = str(raw_end).strip() if raw_end else ""

    # Detect date-only strings as all-day automatically
    is_date_only = (
        len(raw_start) == 10 and "T" not in raw_start and " " not in raw_start
    )
    if all_day or is_date_only:
        s_date = date.fromisoformat(raw_start[:10])
        if raw_end_str:
            e_date = date.fromisoformat(raw_end_str[:10])
            if e_date <= s_date:
                e_date = s_date + timedelta(days=1)
        else:
            e_date = s_date + timedelta(days=1)
        return s_date.isoformat(), e_date.isoformat(), True

    s_dt = dt_util.parse_datetime(raw_start)
    if s_dt is None:
        s_date = date.fromisoformat(raw_start[:10])
        return s_date.isoformat(), (s_date + timedelta(days=1)).isoformat(), True
    if s_dt.tzinfo is None:
        s_dt = s_dt.replace(tzinfo=tz)
    else:
        s_dt = dt_util.as_local(s_dt)

    e_dt = dt_util.parse_datetime(raw_end_str) if raw_end_str else None
    if e_dt is None:
        e_dt = s_dt + timedelta(hours=2)
    elif e_dt.tzinfo is None:
        e_dt = e_dt.replace(tzinfo=tz)
    else:
        e_dt = dt_util.as_local(e_dt)

    if e_dt <= s_dt:
        e_dt = s_dt + timedelta(hours=1)

    return s_dt.isoformat(), e_dt.isoformat(), False


class ButlerCalendarStore:
    """Persisted store for HVAC Butler's private, self-maintained calendar events."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._store: Store[dict[str, Any]] = Store(
            hass, CALENDAR_STORAGE_VERSION, CALENDAR_STORAGE_KEY
        )
        self._events: list[ButlerCalendarEvent] = []
        self._loaded = False

    @property
    def events(self) -> list[ButlerCalendarEvent]:
        """Return all stored events sorted by start time."""
        return list(self._events)

    async def async_load(self) -> None:
        """Load persisted calendar events and prune stale entries."""
        if self._loaded:
            return
        try:
            data = await self._store.async_load()
        except Exception as err:  # pragma: no cover - defensive storage guard
            _LOGGER.warning("Failed to load HVAC Butler calendar notes: %s", err)
            data = None

        loaded: list[ButlerCalendarEvent] = []
        if isinstance(data, dict) and isinstance(data.get("events"), list):
            for raw in data["events"]:
                if not isinstance(raw, dict):
                    continue
                try:
                    loaded.append(
                        ButlerCalendarEvent(
                            uid=str(raw["uid"]),
                            summary=str(raw["summary"]),
                            description=str(raw.get("description", "")),
                            start=str(raw["start"]),
                            end=str(raw["end"]),
                            all_day=bool(raw.get("all_day", False)),
                            spaces=[
                                str(s)
                                for s in (raw.get("spaces") or [])
                                if isinstance(s, str) and s
                            ],
                            created_at=str(raw.get("created_at", "")),
                        )
                    )
                except (KeyError, ValueError, TypeError):
                    continue

        self._events = loaded
        self._prune_and_sort(dt_util.now())
        self._loaded = True

    def _prune_and_sort(self, now: datetime) -> None:
        cutoff = now - timedelta(days=CALENDAR_RETENTION_DAYS)
        kept: list[ButlerCalendarEvent] = []
        for ev in self._events:
            try:
                if ev.end_dt() >= cutoff:
                    kept.append(ev)
            except ValueError:
                continue
        kept.sort(key=lambda e: (e.start_dt(), e.summary))
        self._events = kept

    async def _async_save(self) -> None:
        try:
            await self._store.async_save(
                {"events": [asdict(ev) for ev in self._events]}
            )
        except Exception as err:  # pragma: no cover - defensive storage guard
            _LOGGER.warning("Failed to save HVAC Butler calendar notes: %s", err)

    def get_events_in_range(
        self, start_dt: datetime, end_dt: datetime
    ) -> list[ButlerCalendarEvent]:
        """Return events overlapping [start_dt, end_dt)."""
        start_local = dt_util.as_local(start_dt)
        end_local = dt_util.as_local(end_dt)
        result: list[ButlerCalendarEvent] = []
        for ev in self._events:
            try:
                if ev.end_dt() > start_local and ev.start_dt() < end_local:
                    result.append(ev)
            except ValueError:
                continue
        return result

    def get_upcoming_events(
        self, now: datetime, days: int = 30
    ) -> list[ButlerCalendarEvent]:
        """Return active and upcoming events within the next `days` days."""
        return self.get_events_in_range(now, now + timedelta(days=days))

    def get_current_or_next_event(self, now: datetime) -> ButlerCalendarEvent | None:
        """Return the currently active event, or the soonest upcoming event."""
        now_local = dt_util.as_local(now)
        upcoming = [ev for ev in self._events if ev.end_dt() > now_local]
        if not upcoming:
            return None
        # Prefer an active event over a future one
        active = [ev for ev in upcoming if ev.start_dt() <= now_local]
        if active:
            return active[0]
        return upcoming[0]

    def format_day_notes(self, start_dt: datetime, end_dt: datetime) -> list[str]:
        """Return formatted `day_notes` strings for events overlapping [start_dt, end_dt)."""
        return [
            ev.format_day_note() for ev in self.get_events_in_range(start_dt, end_dt)
        ]

    def get_next_boundary(
        self, now: datetime
    ) -> tuple[datetime, str, ButlerCalendarEvent] | None:
        """Return the earliest future (timestamp, 'start'|'end', event) for timed events."""
        now_local = dt_util.as_local(now)
        best: tuple[datetime, str, ButlerCalendarEvent] | None = None
        for ev in self._events:
            if ev.all_day:
                continue
            try:
                s_dt = ev.start_dt()
                e_dt = ev.end_dt()
            except ValueError:
                continue
            for ts, phase in ((s_dt, "start"), (e_dt, "end")):
                if ts > now_local and (best is None or ts < best[0]):
                    best = (ts, phase, ev)
        return best

    async def async_delete_event(self, uid: str) -> bool:
        """Delete a single calendar event by uid."""
        before = len(self._events)
        self._events = [ev for ev in self._events if ev.uid != uid]
        if len(self._events) == before:
            return False
        await self._async_save()
        return True

    async def async_apply_actions(
        self,
        actions: list[dict[str, Any]],
        *,
        now: datetime | None = None,
        valid_space_ids: set[str] | None = None,
    ) -> tuple[dict[str, int], list[ButlerCalendarEvent]]:
        """Apply AI-proposed add/update/delete calendar actions and persist.

        Returns (counts_dict, affected_events).
        """
        now_dt = dt_util.as_local(now or dt_util.now())
        counts = {"added": 0, "updated": 0, "deleted": 0}
        affected: list[ButlerCalendarEvent] = []

        for raw in actions or []:
            if not isinstance(raw, dict):
                continue
            action = str(raw.get("action", "add")).lower().strip()

            if action == "delete":
                uid = str(raw.get("uid", "")).strip()
                if uid:
                    before = len(self._events)
                    self._events = [ev for ev in self._events if ev.uid != uid]
                    if len(self._events) < before:
                        counts["deleted"] += 1
                continue

            summary = str(raw.get("summary", "")).strip()
            description = str(raw.get("description", "")).strip()
            raw_start = raw.get("start")
            if not summary or not raw_start:
                continue
            try:
                start_iso, end_iso, all_day = _normalize_event_times(
                    str(raw_start),
                    str(raw.get("end")) if raw.get("end") else None,
                    bool(raw.get("all_day", False)),
                )
            except ValueError as err:
                _LOGGER.warning("Skipping invalid calendar event %r: %s", summary, err)
                continue

            raw_spaces = raw.get("spaces") or []
            spaces = [
                str(s).strip()
                for s in raw_spaces
                if isinstance(s, str)
                and s.strip()
                and (valid_space_ids is None or s.strip() in valid_space_ids)
            ]

            if action == "update":
                uid = str(raw.get("uid", "")).strip()
                existing = next((ev for ev in self._events if ev.uid == uid), None)
                if existing is not None:
                    existing.summary = summary
                    existing.description = description
                    existing.start = start_iso
                    existing.end = end_iso
                    existing.all_day = all_day
                    existing.spaces = spaces
                    counts["updated"] += 1
                    affected.append(existing)
                    continue

            new_ev = ButlerCalendarEvent(
                uid=uuid.uuid4().hex[:12],
                summary=summary,
                description=description,
                start=start_iso,
                end=end_iso,
                all_day=all_day,
                spaces=spaces,
                created_at=now_dt.isoformat(),
            )
            self._events.append(new_ev)
            counts["added"] += 1
            affected.append(new_ev)

        self._prune_and_sort(now_dt)
        if any(counts.values()):
            await self._async_save()
        return counts, affected
