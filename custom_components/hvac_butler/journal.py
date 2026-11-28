"""Persisted rolling activity journal for HVAC Butler."""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

JOURNAL_STORAGE_VERSION = 1
JOURNAL_STORAGE_KEY = f"{DOMAIN}.journal"
JOURNAL_EVENT_SCHEMA_VERSION = 1
JOURNAL_MAX_ENTRIES = 500
JOURNAL_RETENTION_DAYS = 7


class HvacButlerJournal:
    """Rolling persisted log of Butler nightly plans and intraday evaluations."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        max_entries: int = JOURNAL_MAX_ENTRIES,
        retention_days: int = JOURNAL_RETENTION_DAYS,
    ) -> None:
        self._hass = hass
        self._max_entries = max_entries
        self._retention_days = retention_days
        self._store: Store[dict[str, Any]] = Store(
            hass, JOURNAL_STORAGE_VERSION, JOURNAL_STORAGE_KEY
        )
        self._entries: list[dict[str, Any]] = []
        self._loaded = False

    @property
    def entries(self) -> list[dict[str, Any]]:
        """Return all currently retained journal entries (newest first)."""
        return list(self._entries)

    async def async_load(self) -> None:
        """Load persisted journal entries from HA storage and prune expired ones."""
        if self._loaded:
            return
        try:
            data = await self._store.async_load()
        except Exception as err:  # pragma: no cover - defensive storage guard
            _LOGGER.warning("Failed to load HVAC Butler journal: %s", err)
            data = None

        if isinstance(data, dict) and isinstance(data.get("entries"), list):
            self._entries = [e for e in data["entries"] if isinstance(e, dict)]
            self._prune()
        else:
            self._entries = []
        self._loaded = True

    def _prune(self) -> None:
        """Drop entries older than retention_days and cap total count."""
        cutoff = dt_util.now() - timedelta(days=self._retention_days)
        kept: list[dict[str, Any]] = []
        for entry in self._entries:
            ts_raw = entry.get("timestamp")
            if isinstance(ts_raw, str):
                parsed = dt_util.parse_datetime(ts_raw)
                if parsed is not None:
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=cutoff.tzinfo)
                    if parsed < cutoff:
                        continue
            kept.append(entry)
        self._entries = kept[: self._max_entries]

    async def async_append(self, entry: dict[str, Any]) -> dict[str, Any]:
        """Append a versioned event record (newest first), prune, and persist."""
        if not self._loaded:
            await self.async_load()

        now_iso = dt_util.now().isoformat()
        record: dict[str, Any] = {
            "schema_version": JOURNAL_EVENT_SCHEMA_VERSION,
            "id": entry.get("id") or f"{now_iso}_{uuid.uuid4().hex[:8]}",
            "timestamp": entry.get("timestamp") or now_iso,
            **{
                k: v
                for k, v in entry.items()
                if k not in ("schema_version", "id", "timestamp")
            },
        }
        self._entries.insert(0, record)
        self._prune()
        try:
            await self._store.async_save({"entries": self._entries})
        except Exception as err:  # pragma: no cover - defensive storage guard
            _LOGGER.warning("Failed to save HVAC Butler journal: %s", err)
        return record

    def get_entries(
        self,
        *,
        space_id: str | None = None,
        days: int | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return newest-first journal entries filtered by optional time window and space."""
        self._prune()
        entries = list(self._entries)

        if days is not None:
            window_days = max(1, min(int(days), self._retention_days))
            cutoff = dt_util.now() - timedelta(days=window_days)
            windowed: list[dict[str, Any]] = []
            for entry in entries:
                ts_raw = entry.get("timestamp")
                if isinstance(ts_raw, str):
                    parsed = dt_util.parse_datetime(ts_raw)
                    if parsed is not None:
                        if parsed.tzinfo is None:
                            parsed = parsed.replace(tzinfo=cutoff.tzinfo)
                        if parsed < cutoff:
                            continue
                windowed.append(entry)
            entries = windowed

        if space_id:
            entries = [
                e
                for e in entries
                if isinstance(e.get("spaces"), dict) and space_id in e["spaces"]
            ]

        if limit is not None:
            clamped_limit = max(1, min(int(limit), self._max_entries))
            return entries[:clamped_limit]

        return entries[: self._max_entries]

    def get_latest_plan(self, *, space_id: str | None = None) -> dict[str, Any] | None:
        """Return the most recent 'plan' keyframe entry in the retained journal."""
        self._prune()
        for entry in self._entries:
            if entry.get("kind") != "plan":
                continue
            if space_id and not (
                isinstance(entry.get("spaces"), dict) and space_id in entry["spaces"]
            ):
                continue
            return entry
        return None

    def get_recent_context_since_keyframe(
        self,
        *,
        target_space_ids: list[str] | None = None,
        max_entries: int = 20,
    ) -> list[dict[str, Any]]:
        """Return compact chronological short-term memory back to the latest Plan keyframe.

        Includes cross-space events by default; only filters to target_space_ids if
        the slice since the last Plan keyframe exceeds max_entries.
        """
        self._prune()
        if not self._entries:
            return []

        # Collect newest-first entries back to and including the most recent 'plan' keyframe
        since_keyframe: list[dict[str, Any]] = []
        for entry in self._entries:
            since_keyframe.append(entry)
            if entry.get("kind") == "plan":
                break

        # Fallback: only filter to target_space_ids if we exceed max_entries
        if len(since_keyframe) > max_entries and target_space_ids:
            target_set = set(target_space_ids)
            since_keyframe = [
                e
                for e in since_keyframe
                if e.get("kind") == "plan"
                or (
                    isinstance(e.get("spaces"), dict)
                    and bool(target_set.intersection(e["spaces"].keys()))
                )
            ]

        if len(since_keyframe) > max_entries:
            # Preserve the oldest entry if it's the Plan keyframe, plus the most recent entries
            if since_keyframe[-1].get("kind") == "plan":
                since_keyframe = [
                    *since_keyframe[: max_entries - 1],
                    since_keyframe[-1],
                ]
            else:
                since_keyframe = since_keyframe[:max_entries]

        compact: list[dict[str, Any]] = []
        for entry in reversed(since_keyframe):
            spaces_compact: dict[str, dict[str, Any]] = {}
            raw_spaces = entry.get("spaces")
            if isinstance(raw_spaces, dict):
                for s_id, rec in raw_spaces.items():
                    if not isinstance(rec, dict):
                        continue
                    item: dict[str, Any] = {
                        "changed": bool(rec.get("changed", False)),
                        "summary": str(rec.get("summary") or ""),
                    }
                    if rec.get("comfort_boost"):
                        item["comfort_boost"] = rec["comfort_boost"]
                    spaces_compact[s_id] = item
            record: dict[str, Any] = {
                "timestamp": entry.get("timestamp"),
                "kind": entry.get("kind"),
                "trigger": entry.get("trigger"),
                "spaces": spaces_compact,
            }
            if entry.get("kind") == "plan" and entry.get("weather_snapshot"):
                record["weather_snapshot"] = entry["weather_snapshot"]
            compact.append(record)
        return compact
