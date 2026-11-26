"""HVAC Butler coordinator managing nightly planning and intraday event revisions."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_call_later,
    async_track_point_in_time,
    async_track_state_change_event,
    async_track_time_change,
)
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

from .calendar_store import ButlerCalendarEvent, ButlerCalendarStore
from .const import (
    BUTLER_PRESET_NAME,
    CONF_AI_TASK_ENTITY,
    CONF_ALARM_ENTITY,
    CONF_BUTLER_SCHEDULE,
    CONF_CLIMATE_ENTITY,
    CONF_DEFAULT_MODE,
    CONF_HOUSE_NOTES,
    CONF_MAX_AI_DELTA_F,
    CONF_MAX_COOL_TEMP,
    CONF_MAX_HEAT_TEMP,
    CONF_MIN_COOL_TEMP,
    CONF_MIN_HEAT_TEMP,
    CONF_OCCUPIED_SCHEDULE,
    CONF_PRESENCE_SENSORS,
    CONF_SPACE_NOTES,
    CONF_SPACES,
    CONF_UNOCCUPIED_SCHEDULE,
    CONF_WEATHER_ENTITY,
    DAYS_OF_WEEK,
    DEFAULT_MAX_AI_DELTA_F,
    DEFAULT_MAX_COOL_TEMP,
    DEFAULT_MAX_HEAT_TEMP,
    DEFAULT_MIN_COOL_TEMP,
    DEFAULT_MIN_HEAT_TEMP,
    INTRADAY_COOLDOWN_MINUTES,
    MIN_DEADBAND_F,
    MODE_OCCUPIED,
    NIGHTLY_PLAN_HOUR,
    NIGHTLY_PLAN_MINUTE,
    PRESENCE_OFF_DEBOUNCE_MINUTES,
    PRESENCE_ON_DEBOUNCE_MINUTES,
)
from .guardrails import (
    GuardrailConfig,
    validate_and_clamp_blocks,
    validate_comfort_boost,
)
from .journal import HvacButlerJournal
from .prompts import (
    IntradayPlanContext,
    NightlyPlanContext,
    SpaceIntradayContext,
    SpaceNightlyContext,
    build_briefing_prompt,
    build_intraday_prompt,
    build_nightly_prompt,
    summarize_forecast,
)
from .schedule_store import (
    async_ensure_butler_schedule,
    async_read_schedule,
    async_write_butler_schedule,
)
from .schedule_utils import (
    build_butler_week_payload,
    merge_intraday_blocks,
    minutes_to_time_str,
    slice_blocks_to_window,
)

_LOGGER = logging.getLogger(__name__)

_ALARM_TRIGGER_STATES = frozenset({"armed_away", "disarmed", "armed_home"})
_INVALID_PRIOR_STATES = frozenset({"unknown", "unavailable", "none", ""})
AI_RETRY_DELAYS_SECONDS: tuple[float, ...] = (5.0, 15.0)


async def async_unregister_fusion_presets(
    hass: HomeAssistant, climate_entities: list[str]
) -> None:
    """Unregister the dynamic 'Butler' preset from hvac_fusion climate entities."""
    if not climate_entities or not hass.services.has_service(
        "hvac_fusion", "unregister_space_preset"
    ):
        return
    for climate_eid in climate_entities:
        await hass.services.async_call(
            "hvac_fusion",
            "unregister_space_preset",
            {
                "entity_id": climate_eid,
                "preset_name": BUTLER_PRESET_NAME,
            },
            blocking=True,
        )


def derive_space_id_and_name(
    hass: HomeAssistant, climate_entity_id: str
) -> tuple[str, str]:
    """Derive canonical (space_id, friendly_name) from a target climate entity."""
    state = hass.states.get(climate_entity_id)
    if state is not None:
        space_id = state.attributes.get("space_id")
        friendly = state.attributes.get("friendly_name")
        if space_id:
            name = str(friendly or space_id).removesuffix(" Space").strip()
            return slugify(str(space_id)), name or str(space_id)
        if friendly:
            clean = str(friendly).removesuffix(" Space").strip()
            return slugify(clean), clean

    raw_slug = climate_entity_id.removeprefix("climate.").removesuffix("_space")
    return slugify(raw_slug), raw_slug.replace("_", " ").title()


def _extract_json_object(raw_response: Any) -> dict[str, Any]:
    """Parse structured JSON from ai_task.generate_data response."""
    data = raw_response.get("data") if isinstance(raw_response, dict) else raw_response
    if isinstance(data, dict):
        return data
    if not isinstance(data, str):
        raise TypeError(f"Unexpected AI response type: {type(data).__name__}")

    text = data.strip()
    # Strip optional markdown code fences (```json ... ```)
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    else:
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace > first_brace:
            text = text[first_brace : last_brace + 1]

    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise TypeError("AI JSON root must be an object")
    return parsed


class HvacButlerCoordinator:
    """Central runtime coordinator for HVAC Butler."""

    def __init__(
        self, hass: HomeAssistant, entry_id: str, config: dict[str, Any]
    ) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self.config = config

        # Runtime observability state
        self.status: str = "idle"
        self.last_nightly_run: str | None = None
        self.last_intraday_run: str | None = None
        self.last_error: str | None = None
        self.last_trigger: dict[str, Any] | None = None

        self.daily_plan_headline: str = "No nightly plan yet"
        self.daily_plan_summary: str = "No nightly plan generated yet."
        self.space_daily_summaries: dict[str, str] = {}
        self.intraday_headline: str = "No intraday revisions yet"
        self.intraday_explanation: str = "No intraday revisions yet."
        self.space_intraday_explanations: dict[str, str] = {}

        # Resolved butler schedule entity_ids keyed by space_id
        self.butler_schedules: dict[str, str] = {}
        self._registered_fusion_climates: list[str] = []

        # Listeners, debounce timers, cooldowns, and observer callbacks
        self._unsub_listeners: list[Callable[[], None]] = []
        self._debounce_cancels: dict[str, Callable[[], None]] = {}
        self._debounce_targets: dict[str, str] = {}
        self._deferred_cancels: dict[str, Callable[[], None]] = {}
        self._sensor_to_spaces: dict[str, list[str]] = {}
        self._space_to_sensors: dict[str, list[str]] = {}
        self._last_intraday_by_space: dict[str, datetime] = {}
        self._last_presence_state_by_space: dict[str, str] = {}
        self._entity_listeners: list[Callable[[], None]] = []
        self._calendar_boundary_cancel: Callable[[], None] | None = None
        self.journal = HvacButlerJournal(hass)
        self.calendar_store = ButlerCalendarStore(hass)

    @property
    def guardrails(self) -> GuardrailConfig:
        """Build GuardrailConfig from active options."""
        return GuardrailConfig(
            min_heat_temp=float(
                self.config.get(CONF_MIN_HEAT_TEMP, DEFAULT_MIN_HEAT_TEMP)
            ),
            max_heat_temp=float(
                self.config.get(CONF_MAX_HEAT_TEMP, DEFAULT_MAX_HEAT_TEMP)
            ),
            min_cool_temp=float(
                self.config.get(CONF_MIN_COOL_TEMP, DEFAULT_MIN_COOL_TEMP)
            ),
            max_cool_temp=float(
                self.config.get(CONF_MAX_COOL_TEMP, DEFAULT_MAX_COOL_TEMP)
            ),
            min_deadband=MIN_DEADBAND_F,
            max_ai_delta_f=float(
                self.config.get(CONF_MAX_AI_DELTA_F, DEFAULT_MAX_AI_DELTA_F)
            ),
        )

    @property
    def spaces(self) -> list[dict[str, Any]]:
        """Return configured spaces."""
        return list(self.config.get(CONF_SPACES, []))

    def register_listener(self, cb: Callable[[], None]) -> Callable[[], None]:
        """Register an entity state update callback."""
        self._entity_listeners.append(cb)

        def _remove() -> None:
            if cb in self._entity_listeners:
                self._entity_listeners.remove(cb)

        return _remove

    def _notify_entities(self) -> None:
        for cb in list(self._entity_listeners):
            cb()
        self.hass.bus.async_fire(
            "hvac_butler_updated",
            {
                "status": self.status,
                "last_nightly_run": self.last_nightly_run,
                "last_intraday_run": self.last_intraday_run,
            },
        )

    def notify_state_changed(self) -> None:
        """Public helper for entity platforms to broadcast coordinator state updates."""
        self._notify_entities()

    def reschedule_calendar_boundary(self) -> None:
        """Schedule a single point-in-time trigger for the next timed calendar event boundary."""
        if self._calendar_boundary_cancel is not None:
            self._calendar_boundary_cancel()
            self._calendar_boundary_cancel = None

        nxt = self.calendar_store.get_next_boundary(dt_util.now())
        if nxt is None:
            return
        boundary_dt, phase, ev = nxt

        @callback
        def _on_boundary(
            _now: datetime, _ev: ButlerCalendarEvent = ev, _phase: str = phase
        ) -> None:
            self._calendar_boundary_cancel = None
            trigger = {
                "type": "calendar_event",
                "phase": _phase,
                "summary": _ev.summary,
                "event_uid": _ev.uid,
            }
            target_spaces = list(_ev.spaces) if _ev.spaces else None
            self.hass.async_create_task(
                self.async_run_intraday_revision(
                    trigger_event=trigger,
                    target_space_ids=target_spaces,
                    bypass_cooldown=True,
                )
            )
            self.reschedule_calendar_boundary()
            self._notify_entities()

        self._calendar_boundary_cancel = async_track_point_in_time(
            self.hass, _on_boundary, boundary_dt
        )

    async def async_brief_butler(
        self,
        messages: list[dict[str, str]],
        *,
        finalize: bool = False,
    ) -> dict[str, Any]:
        """Run one conversational briefing turn via ai_task.generate_data."""
        now_local = dt_util.now()
        today_day = DAYS_OF_WEEK[now_local.weekday()]
        spaces_info: list[dict[str, Any]] = []
        for space_conf in self.spaces:
            climate_eid = space_conf.get(CONF_CLIMATE_ENTITY)
            if not climate_eid:
                continue
            space_id, space_name = derive_space_id_and_name(self.hass, climate_eid)
            spaces_info.append(
                {
                    "space_id": space_id,
                    "name": space_name,
                    "default_mode": space_conf.get(CONF_DEFAULT_MODE, MODE_OCCUPIED),
                    "space_notes": str(space_conf.get(CONF_SPACE_NOTES, "")),
                }
            )

        upcoming = [
            ev.to_prompt_dict()
            for ev in self.calendar_store.get_upcoming_events(now_local, days=30)
        ]
        prompt = build_briefing_prompt(
            now_iso=now_local.isoformat(),
            today_day=today_day,
            spaces=spaces_info,
            house_notes=str(self.config.get(CONF_HOUSE_NOTES, "")),
            upcoming_events=upcoming,
            messages=messages,
            finalize=finalize,
        )
        parsed = await self._async_call_ai_task("hvac_butler_briefing", prompt)
        reply = str(parsed.get("reply") or "Noted.")
        ready = bool(parsed.get("ready_to_commit", False))
        actions = parsed.get("calendar_actions")
        if not isinstance(actions, list):
            actions = []
        return {
            "reply": reply,
            "ready_to_commit": ready,
            "calendar_actions": actions,
        }

    async def async_commit_briefing(
        self,
        messages: list[dict[str, str]],
        proposed_actions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Finalize and commit briefing calendar actions, then re-evaluate if active."""
        actions = list(proposed_actions or [])
        summary_reply = ""
        has_user_msg = any(
            str(m.get("role", "")).lower() == "user"
            and str(m.get("content", "")).strip()
            for m in messages
        )
        if not actions and has_user_msg:
            final_res = await self.async_brief_butler(messages, finalize=True)
            actions = list(final_res.get("calendar_actions") or [])
            summary_reply = str(final_res.get("reply") or "")

        valid_space_ids = {
            derive_space_id_and_name(self.hass, str(sc[CONF_CLIMATE_ENTITY]))[0]
            for sc in self.spaces
            if sc.get(CONF_CLIMATE_ENTITY)
        }
        now_local = dt_util.now()
        counts, affected = await self.calendar_store.async_apply_actions(
            actions, now=now_local, valid_space_ids=valid_space_ids
        )
        self.reschedule_calendar_boundary()
        self._notify_entities()

        # Immediate re-evaluation if any committed event affects today/tonight
        # or (after 21:00) tomorrow's already-planned window.
        triggered_reeval = False
        if any(counts.values()):
            end_of_today = now_local.replace(
                hour=23, minute=59, second=59, microsecond=0
            )
            tomorrow_end = end_of_today + timedelta(days=1)
            affects_today = any(
                ev.start_dt() <= end_of_today and ev.end_dt() > now_local
                for ev in affected
            )
            affects_tomorrow = any(
                ev.start_dt() <= tomorrow_end and ev.end_dt() > end_of_today
                for ev in affected
            )
            if now_local.hour >= NIGHTLY_PLAN_HOUR and (
                affects_tomorrow or affects_today
            ):
                triggered_reeval = True
                self.hass.async_create_task(self.async_run_nightly_plan())
            elif affects_today:
                triggered_reeval = True
                trigger = {
                    "type": "calendar_event",
                    "phase": "updated",
                    "summary": affected[0].summary if affected else "Calendar updated",
                }
                self.hass.async_create_task(
                    self.async_run_intraday_revision(
                        trigger_event=trigger, bypass_cooldown=True
                    )
                )

        return {
            "committed": counts,
            "summary_reply": summary_reply,
            "triggered_reeval": triggered_reeval,
        }

    def get_spaces_summary(self) -> list[dict[str, Any]]:
        """Return configured spaces with live preset metadata for dashboard cards."""
        result: list[dict[str, Any]] = []
        for space_conf in self.spaces:
            climate_eid = space_conf.get(CONF_CLIMATE_ENTITY)
            if not climate_eid:
                continue
            space_id, space_name = derive_space_id_and_name(self.hass, climate_eid)
            _curr_temp, preset, _modes, is_locked = self._get_climate_info(climate_eid)
            result.append(
                {
                    "space_id": space_id,
                    "name": space_name,
                    "climate_entity": climate_eid,
                    "butler_schedule": self.butler_schedules.get(space_id),
                    "default_mode": space_conf.get(CONF_DEFAULT_MODE, MODE_OCCUPIED),
                    "active_preset": preset,
                    "locked": is_locked,
                }
            )
        return result

    async def async_setup(self) -> None:
        """Ensure native butler schedules exist and attach nightly + intraday listeners."""
        await self.journal.async_load()
        await self.calendar_store.async_load()
        self.reschedule_calendar_boundary()
        # 1. Ensure native schedule.<space>_butler exists for each configured space
        for space_conf in self.spaces:
            climate_eid = space_conf.get(CONF_CLIMATE_ENTITY)
            if not climate_eid:
                continue
            space_id, space_name = derive_space_id_and_name(self.hass, climate_eid)
            explicit_sched = space_conf.get(CONF_BUTLER_SCHEDULE)
            butler_eid = explicit_sched or await async_ensure_butler_schedule(
                self.hass, space_id, space_name
            )
            if butler_eid:
                self.butler_schedules[space_id] = butler_eid
                # Progressive enhancement: auto-wire "Butler" preset on hvac_fusion spaces
                if self.hass.services.has_service(
                    "hvac_fusion", "register_space_preset"
                ):
                    await self.hass.services.async_call(
                        "hvac_fusion",
                        "register_space_preset",
                        {
                            "entity_id": climate_eid,
                            "preset_name": BUTLER_PRESET_NAME,
                            "schedule_entity": butler_eid,
                        },
                        blocking=True,
                    )
                    self._registered_fusion_climates.append(climate_eid)

        # 2. Schedule nightly macro-planner at 21:00 local time
        self._unsub_listeners.append(
            async_track_time_change(
                self.hass,
                self._handle_nightly_timer,
                hour=NIGHTLY_PLAN_HOUR,
                minute=NIGHTLY_PLAN_MINUTE,
                second=0,
            )
        )

        # 3. Subscribe to alarm transitions (if configured)
        alarm_eid = self.config.get(CONF_ALARM_ENTITY)
        if alarm_eid:
            self._unsub_listeners.append(
                async_track_state_change_event(
                    self.hass, [alarm_eid], self._handle_alarm_change
                )
            )

        # 4. Subscribe to per-space presence sensors (debounced & aggregated per space)
        sensor_to_spaces: dict[str, list[str]] = {}
        space_to_sensors: dict[str, list[str]] = {}
        for space_conf in self.spaces:
            climate_eid = space_conf.get(CONF_CLIMATE_ENTITY)
            if not climate_eid:
                continue
            space_id, _ = derive_space_id_and_name(self.hass, climate_eid)
            sensors = [
                str(s) for s in (space_conf.get(CONF_PRESENCE_SENSORS) or []) if s
            ]
            if sensors:
                space_to_sensors[space_id] = sensors
            for sensor_eid in sensors:
                sensor_to_spaces.setdefault(sensor_eid, []).append(space_id)

        self._space_to_sensors = space_to_sensors
        if sensor_to_spaces:
            self._sensor_to_spaces = sensor_to_spaces
            self._unsub_listeners.append(
                async_track_state_change_event(
                    self.hass,
                    list(sensor_to_spaces.keys()),
                    self._handle_presence_change,
                )
            )
        else:
            self._sensor_to_spaces = {}

    async def async_unload(self, *, unregister_presets: bool = False) -> None:
        """Cancel all timers and state listeners; optionally unregister dynamic presets."""
        for unsub in self._unsub_listeners:
            unsub()
        self._unsub_listeners.clear()

        for cancel in self._debounce_cancels.values():
            cancel()
        self._debounce_cancels.clear()
        self._debounce_targets.clear()

        for cancel in self._deferred_cancels.values():
            cancel()
        self._deferred_cancels.clear()

        if self._calendar_boundary_cancel is not None:
            self._calendar_boundary_cancel()
            self._calendar_boundary_cancel = None

        if unregister_presets and self._registered_fusion_climates:
            await async_unregister_fusion_presets(
                self.hass, list(self._registered_fusion_climates)
            )
        self._registered_fusion_climates.clear()

    async def _handle_nightly_timer(self, now: datetime) -> None:
        await self.async_run_nightly_plan()

    @callback
    def _handle_alarm_change(self, event: Event) -> None:
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        if old_state is None or new_state is None:
            return
        new_val = str(new_state.state).lower()
        old_val = str(old_state.state).lower()
        if (
            old_val in _INVALID_PRIOR_STATES
            or new_val == old_val
            or new_val not in _ALARM_TRIGGER_STATES
        ):
            return
        # Turning off perimeter alarm while already home is not an arrival event
        if old_val == "armed_home" and new_val == "disarmed":
            return

        trigger = {"type": "alarm_change", "from": old_val, "to": new_val}
        self.hass.async_create_task(
            self.async_run_intraday_revision(
                trigger_event=trigger, bypass_cooldown=True
            )
        )

    def _is_space_occupied(self, space_id: str) -> bool:
        """Return True if ANY configured presence sensor for the space is currently 'on'."""
        sensors = self._space_to_sensors.get(space_id) or []
        for sensor_eid in sensors:
            st = self.hass.states.get(sensor_eid)
            if st is not None and str(st.state).lower() == "on":
                return True
        return False

    def _get_space_sensor_states(self, space_id: str) -> dict[str, dict[str, Any]]:
        """Return rich live presence sensor metadata {entity_id: {state, for_minutes, ...}}."""
        sensors = self._space_to_sensors.get(space_id) or []
        now_utc = dt_util.utcnow()
        result: dict[str, dict[str, Any]] = {}
        for sensor_eid in sensors:
            st = self.hass.states.get(sensor_eid)
            if st is None:
                result[sensor_eid] = {"state": "unknown"}
                continue
            info: dict[str, Any] = {"state": str(st.state).lower()}
            if st.last_changed is not None:
                delta_min = max(
                    0, int((now_utc - st.last_changed).total_seconds() // 60)
                )
                info["for_minutes"] = delta_min
            if friendly := st.attributes.get("friendly_name"):
                info["name"] = str(friendly)
            if dev_class := st.attributes.get("device_class"):
                info["device_class"] = str(dev_class)
            result[sensor_eid] = info
        return result

    async def async_run_manual_intraday(self, *, space_id: str | None = None) -> None:
        """Run an on-demand intraday evaluation (live state is passed separately in context)."""
        target_ids = [space_id] if space_id else None
        trigger: dict[str, Any] = {
            "type": "manual_intraday",
            "label": "Manual Check",
        }
        if space_id:
            trigger["space_id"] = space_id

        await self.async_run_intraday_revision(
            trigger_event=trigger,
            target_space_ids=target_ids,
            bypass_cooldown=True,
        )

    @callback
    def _handle_presence_change(self, event: Event) -> None:
        entity_id = event.data.get("entity_id")
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")
        if not entity_id or old_state is None or new_state is None:
            return
        new_val = str(new_state.state).lower()
        old_val = str(old_state.state).lower()
        if (
            old_val in _INVALID_PRIOR_STATES
            or new_val == old_val
            or new_val not in ("on", "off")
        ):
            return

        space_ids = self._sensor_to_spaces.get(entity_id, [])
        for space_id in space_ids:
            # Aggregate occupancy across ALL presence sensors configured for this space:
            # any sensor 'on' => occupied; ALL sensors 'off' => unoccupied.
            space_sensors = self._space_to_sensors.get(space_id) or [entity_id]
            any_on = any(
                (st := self.hass.states.get(s)) is not None
                and str(st.state).lower() == "on"
                for s in space_sensors
            )
            desired_state = "on" if any_on else "off"

            # Ignore an individual sensor turning off while another sensor keeps the space occupied
            if new_val == "off" and any_on:
                continue

            # If a debounce timer is already counting down for the same aggregate state, keep it
            if (
                space_id in self._debounce_cancels
                and self._debounce_targets.get(space_id) == desired_state
            ):
                continue

            # Aggregate state flipped direction: cancel any opposite-direction timer
            if prev := self._debounce_cancels.pop(space_id, None):
                prev()
            self._debounce_targets.pop(space_id, None)
            if prev_def := self._deferred_cancels.pop(space_id, None):
                prev_def()

            delay_minutes = (
                PRESENCE_ON_DEBOUNCE_MINUTES
                if desired_state == "on"
                else PRESENCE_OFF_DEBOUNCE_MINUTES
            )

            @callback
            def _dispatch_presence(
                s_id: str,
                from_state: str,
                target_state: str,
                sensor: str,
                mins: int,
            ) -> None:
                # Re-verify aggregate occupancy still matches target_state
                sensors_now = self._space_to_sensors.get(s_id) or [sensor]
                any_on_now = any(
                    (st := self.hass.states.get(s)) is not None
                    and str(st.state).lower() == "on"
                    for s in sensors_now
                )
                if any_on_now != (target_state == "on"):
                    return

                # Opposite-direction arrival (off -> on) bypasses cooldown immediately
                prev_state = self._last_presence_state_by_space.get(s_id)
                bypass = target_state == "on" and prev_state == "off"

                if not bypass:
                    last_ts = self._last_intraday_by_space.get(s_id)
                    if last_ts is not None:
                        elapsed = (dt_util.now() - last_ts).total_seconds()
                        remaining = INTRADAY_COOLDOWN_MINUTES * 60 - elapsed
                        if remaining > 0:
                            # Defer until cooldown expires instead of silently dropping
                            if prev_d := self._deferred_cancels.pop(s_id, None):
                                prev_d()

                            @callback
                            def _fire_after_cooldown(
                                _now: datetime,
                                _s_id: str = s_id,
                                _from: str = from_state,
                                _target: str = target_state,
                                _sensor: str = sensor,
                                _mins: int = mins,
                            ) -> None:
                                self._deferred_cancels.pop(_s_id, None)
                                _dispatch_presence(
                                    _s_id, _from, _target, _sensor, _mins
                                )

                            self._deferred_cancels[s_id] = async_call_later(
                                self.hass, remaining + 1.0, _fire_after_cooldown
                            )
                            return

                trigger = {
                    "type": "presence_change",
                    "space_id": s_id,
                    "sensor": sensor,
                    "from": from_state,
                    "to": target_state,
                    "state": target_state,
                    "for_minutes": mins,
                }
                self.hass.async_create_task(
                    self.async_run_intraday_revision(
                        trigger_event=trigger,
                        target_space_ids=[s_id],
                        bypass_cooldown=bypass,
                    )
                )

            @callback
            def _fire_debounced(
                _now: datetime,
                s_id: str = space_id,
                from_state: str = old_val,
                target_state: str = desired_state,
                sensor: str = entity_id,
                mins: int = delay_minutes,
            ) -> None:
                self._debounce_cancels.pop(s_id, None)
                self._debounce_targets.pop(s_id, None)
                _dispatch_presence(s_id, from_state, target_state, sensor, mins)

            self._debounce_targets[space_id] = desired_state
            self._debounce_cancels[space_id] = async_call_later(
                self.hass, delay_minutes * 60, _fire_debounced
            )

    async def _async_get_weather_context(
        self, tomorrow_date_str: str
    ) -> tuple[dict[str, Any], float | None]:
        """Fetch current weather and condensed forecast from configured weather.* entity."""
        weather_eid = self.config.get(CONF_WEATHER_ENTITY)
        if not weather_eid:
            return {"current": {}}, None

        state = self.hass.states.get(weather_eid)
        current_temp: float | None = None
        current_condition: str | None = None
        current_wind: float | None = None
        if state is not None:
            current_condition = state.state
            raw_temp = state.attributes.get("temperature")
            if raw_temp is not None:
                try:
                    current_temp = float(raw_temp)
                except (ValueError, TypeError):
                    pass
            raw_wind = state.attributes.get("wind_speed")
            if raw_wind is not None:
                try:
                    current_wind = float(raw_wind)
                except (ValueError, TypeError):
                    pass

        forecast_entries: list[dict[str, Any]] = []
        for forecast_type in ("hourly", "daily"):
            try:
                resp = await self.hass.services.async_call(
                    "weather",
                    "get_forecasts",
                    {"entity_id": weather_eid, "type": forecast_type},
                    blocking=True,
                    return_response=True,
                )
                if isinstance(resp, dict):
                    entity_data = resp.get(weather_eid, resp)
                    entries = (
                        entity_data.get("forecast")
                        if isinstance(entity_data, dict)
                        else None
                    )
                    if entries:
                        forecast_entries = list(entries)
                        break
            except Exception as err:
                _LOGGER.debug(
                    "Weather %s forecast (%s) unavailable: %s",
                    weather_eid,
                    forecast_type,
                    err,
                )

        summary = summarize_forecast(
            forecast_entries,
            current_temp=current_temp,
            current_condition=current_condition,
            current_wind_speed=current_wind,
            tomorrow_date_str=tomorrow_date_str,
        )
        return summary, current_temp

    async def _async_call_ai_task(
        self, task_name: str, instructions: str
    ) -> dict[str, Any]:
        """Call HA's ai_task.generate_data with non-blocking async backoff retries."""
        ai_entity = self.config.get(CONF_AI_TASK_ENTITY)
        service_data: dict[str, Any] = {
            "task_name": task_name,
            "instructions": instructions,
        }
        if ai_entity:
            service_data["entity_id"] = ai_entity

        last_err: Exception | None = None
        total_attempts = 1 + len(AI_RETRY_DELAYS_SECONDS)
        for attempt in range(total_attempts):
            try:
                resp = await self.hass.services.async_call(
                    "ai_task",
                    "generate_data",
                    service_data,
                    blocking=True,
                    return_response=True,
                )
                return _extract_json_object(resp)
            except Exception as err:
                last_err = err
                _LOGGER.warning(
                    "AI task '%s' attempt %d/%d failed: %s",
                    task_name,
                    attempt + 1,
                    total_attempts,
                    err,
                )
                if attempt < len(AI_RETRY_DELAYS_SECONDS):
                    await asyncio.sleep(AI_RETRY_DELAYS_SECONDS[attempt])
        assert last_err is not None
        raise last_err

    def _get_climate_info(
        self, climate_eid: str
    ) -> tuple[float | None, str | None, list[str], bool]:
        """Return (current_temp, active_preset, supported_hvac_modes, is_locked)."""
        state = self.hass.states.get(climate_eid)
        if state is None:
            return None, None, ["heat_cool", "heat", "cool", "off"], False

        attrs = state.attributes
        curr_temp: float | None = None
        if attrs.get("current_temperature") is not None:
            try:
                curr_temp = float(attrs["current_temperature"])
            except (ValueError, TypeError):
                pass
        preset = attrs.get("preset_mode")
        raw_modes = attrs.get("hvac_modes")
        modes = (
            [str(m).lower() for m in raw_modes]
            if isinstance(raw_modes, (list, tuple)) and raw_modes
            else ["heat_cool", "heat", "cool", "off"]
        )
        is_locked = bool(attrs.get("schedule_editing", False))
        return curr_temp, str(preset) if preset is not None else None, modes, is_locked

    async def async_run_nightly_plan(self, *, manual: bool = False) -> None:
        """Run the 21:00 Nightly Macro-Planner across all configured spaces."""
        if not self.spaces:
            self.status = "idle"
            self.daily_plan_summary = "No spaces configured."
            self._notify_entities()
            return

        now_local = dt_util.now()
        tonight_day = DAYS_OF_WEEK[now_local.weekday()]
        tomorrow_dt = now_local + timedelta(days=1)
        tomorrow_day = DAYS_OF_WEEK[tomorrow_dt.weekday()]
        is_weekend_tomorrow = tomorrow_dt.weekday() >= 5
        # When run before 21:00 (e.g. daytime manual button press), plan full today (00:00–24:00)
        # plus tomorrow so the current day is populated immediately rather than left blank.
        tonight_start_min = (
            NIGHTLY_PLAN_HOUR * 60 if now_local.hour >= NIGHTLY_PLAN_HOUR else 0
        )
        today_start_time = minutes_to_time_str(tonight_start_min)

        self.status = "planning"
        self._notify_entities()

        weather_summary, outdoor_temp = await self._async_get_weather_context(
            tomorrow_dt.date().isoformat()
        )

        space_contexts: list[SpaceNightlyContext] = []
        space_meta: dict[str, dict[str, Any]] = {}

        for space_conf in self.spaces:
            climate_eid = space_conf.get(CONF_CLIMATE_ENTITY)
            occ_eid = space_conf.get(CONF_OCCUPIED_SCHEDULE)
            unocc_eid = space_conf.get(CONF_UNOCCUPIED_SCHEDULE) or ""
            if not climate_eid or not occ_eid:
                continue

            space_id, space_name = derive_space_id_and_name(self.hass, climate_eid)
            curr_temp, preset, modes, is_locked = self._get_climate_info(climate_eid)
            default_mode = space_conf.get(CONF_DEFAULT_MODE, MODE_OCCUPIED)

            occ_week = await async_read_schedule(self.hass, occ_eid)
            unocc_week = (
                await async_read_schedule(self.hass, unocc_eid)
                if unocc_eid
                else {day: [] for day in DAYS_OF_WEEK}
            )

            occ_tonight = slice_blocks_to_window(
                occ_week[tonight_day], tonight_start_min, 1440
            )
            occ_tomorrow = slice_blocks_to_window(occ_week[tomorrow_day], 0, 1440)
            unocc_tonight = (
                slice_blocks_to_window(unocc_week[tonight_day], tonight_start_min, 1440)
                if unocc_eid
                else []
            )
            unocc_tomorrow = (
                slice_blocks_to_window(unocc_week[tomorrow_day], 0, 1440)
                if unocc_eid
                else []
            )

            use_unocc = default_mode != MODE_OCCUPIED and bool(unocc_eid)
            space_contexts.append(
                SpaceNightlyContext(
                    space_id=space_id,
                    name=space_name,
                    default_mode=default_mode if use_unocc else MODE_OCCUPIED,
                    current_temp=curr_temp,
                    active_preset=preset,
                    occupied_tonight=occ_tonight,
                    occupied_tomorrow=occ_tomorrow,
                    unoccupied_tonight=unocc_tonight,
                    unoccupied_tomorrow=unocc_tomorrow,
                    supported_hvac_modes=modes,
                    space_notes=str(space_conf.get(CONF_SPACE_NOTES, "")),
                )
            )
            space_meta[space_id] = {
                "name": space_name,
                "climate_eid": climate_eid,
                "default_mode": default_mode,
                "modes": set(modes),
                "is_locked": is_locked,
                "baseline_tonight": unocc_tonight if use_unocc else occ_tonight,
                "baseline_tomorrow": unocc_tomorrow if use_unocc else occ_tomorrow,
            }

        if not space_contexts:
            self.status = "idle"
            self.daily_plan_summary = "No spaces with baseline schedules configured."
            self._notify_entities()
            return

        location_context: dict[str, Any] = {}
        ha_cfg = getattr(self.hass, "config", None)
        if ha_cfg is not None:
            lat = getattr(ha_cfg, "latitude", None)
            lon = getattr(ha_cfg, "longitude", None)
            if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                location_context["latitude"] = round(float(lat), 1)
                location_context["longitude"] = round(float(lon), 1)
            elev = getattr(ha_cfg, "elevation", None)
            if isinstance(elev, (int, float)):
                location_context["elevation_m"] = round(float(elev))
            tz = getattr(ha_cfg, "time_zone", None)
            if tz:
                location_context["time_zone"] = str(tz)

        tonight_start_dt = now_local.replace(
            hour=tonight_start_min // 60,
            minute=tonight_start_min % 60,
            second=0,
            microsecond=0,
        )
        tomorrow_end_dt = (now_local + timedelta(days=2)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        nightly_day_notes = self.calendar_store.format_day_notes(
            tonight_start_dt, tomorrow_end_dt
        )

        ctx = NightlyPlanContext(
            timestamp_iso=now_local.isoformat(),
            tonight_day=tonight_day,
            tomorrow_day=tomorrow_day,
            is_weekend_tomorrow=is_weekend_tomorrow,
            weather_summary=weather_summary,
            spaces=space_contexts,
            today_start_time=today_start_time,
            location_context=location_context,
            house_notes=str(self.config.get(CONF_HOUSE_NOTES, "")),
            day_notes=nightly_day_notes,
        )
        prompt = build_nightly_prompt(ctx, self.guardrails)

        ai_json: dict[str, Any] | None = None
        ai_spaces: dict[str, Any] = {}
        ai_failed = False
        try:
            ai_json = await self._async_call_ai_task("hvac_butler_nightly_plan", prompt)
            ai_spaces = ai_json.get("spaces", {}) if isinstance(ai_json, dict) else {}
            self.last_error = None
        except Exception as err:
            ai_failed = True
            self.last_error = str(err).splitlines()[0][:240]
            _LOGGER.error(
                "Nightly plan AI task failed, using baseline fallback: %s", err
            )

        any_guardrail_fallback = False
        summaries: dict[str, str] = {}
        journal_spaces: dict[str, dict[str, Any]] = {}
        spaces_modified = 0
        guardrails = self.guardrails

        for space_id, meta in space_meta.items():
            if meta["is_locked"]:
                summaries[space_id] = "Skipped (schedule currently being edited)."
                journal_spaces[space_id] = {
                    "name": meta["name"],
                    "changed": False,
                    "summary": summaries[space_id],
                    "fallback": False,
                    "locked": True,
                    "comfort_boost": None,
                    "guardrail_notes": [],
                    "before_blocks": {
                        tonight_day: [b.to_ha_dict() for b in meta["baseline_tonight"]],
                        tomorrow_day: [
                            b.to_ha_dict() for b in meta["baseline_tomorrow"]
                        ],
                    },
                    "after_blocks": {
                        tonight_day: [b.to_ha_dict() for b in meta["baseline_tonight"]],
                        tomorrow_day: [
                            b.to_ha_dict() for b in meta["baseline_tomorrow"]
                        ],
                    },
                }
                continue

            ai_entry = (
                ai_spaces.get(space_id, {}) if isinstance(ai_spaces, dict) else {}
            )
            tonight_res = validate_and_clamp_blocks(
                ai_entry.get("tonight_remaining"),
                meta["baseline_tonight"],
                tonight_start_min,
                1440,
                guardrails,
                outdoor_temp_f=outdoor_temp,
                supported_hvac_modes=meta["modes"],
            )
            tomorrow_res = validate_and_clamp_blocks(
                ai_entry.get("tomorrow"),
                meta["baseline_tomorrow"],
                0,
                1440,
                guardrails,
                outdoor_temp_f=outdoor_temp,
                supported_hvac_modes=meta["modes"],
            )
            used_fallback = tonight_res.used_fallback or tomorrow_res.used_fallback
            blocks_changed = (
                tonight_res.blocks != meta["baseline_tonight"]
                or tomorrow_res.blocks != meta["baseline_tomorrow"]
            )
            if used_fallback:
                if not ai_failed:
                    any_guardrail_fallback = True
            elif blocks_changed:
                spaces_modified += 1

            butler_eid = self.butler_schedules.get(space_id)
            if not butler_eid:
                butler_eid = await async_ensure_butler_schedule(
                    self.hass, space_id, meta["name"]
                )
                if butler_eid:
                    self.butler_schedules[space_id] = butler_eid

            if butler_eid:
                tonight_write_blocks = tonight_res.blocks
                if tonight_start_min > 0:
                    existing_butler_week = await async_read_schedule(
                        self.hass, butler_eid
                    )
                    existing_today = existing_butler_week.get(tonight_day, [])
                    if existing_today:
                        tonight_write_blocks = merge_intraday_blocks(
                            existing_today,
                            tonight_res.blocks,
                            split_min=tonight_start_min,
                        )
                week_payload = build_butler_week_payload(
                    tonight_day=tonight_day,
                    tonight_blocks=tonight_write_blocks,
                    tomorrow_day=tomorrow_day,
                    tomorrow_blocks=tomorrow_res.blocks,
                )
                await async_write_butler_schedule(
                    self.hass, butler_eid, f"{meta['name']} Butler", week_payload
                )

            if used_fallback:
                summaries[space_id] = "Fallback to baseline schedule."
            else:
                summaries[space_id] = str(
                    ai_entry.get("daily_plan_summary") or "Plan updated."
                )

            guardrail_notes: list[str] = []
            if tonight_res.warnings:
                guardrail_notes.extend(tonight_res.warnings)
            if tonight_res.fallback_reason:
                guardrail_notes.append(
                    f"Tonight fallback: {tonight_res.fallback_reason}"
                )
            if tomorrow_res.warnings:
                guardrail_notes.extend(tomorrow_res.warnings)
            if tomorrow_res.fallback_reason:
                guardrail_notes.append(
                    f"Tomorrow fallback: {tomorrow_res.fallback_reason}"
                )

            journal_spaces[space_id] = {
                "name": meta["name"],
                "changed": bool(blocks_changed and not used_fallback),
                "summary": summaries[space_id],
                "fallback": bool(used_fallback),
                "locked": False,
                "comfort_boost": None,
                "guardrail_notes": guardrail_notes,
                "before_blocks": {
                    tonight_day: [b.to_ha_dict() for b in meta["baseline_tonight"]],
                    tomorrow_day: [b.to_ha_dict() for b in meta["baseline_tomorrow"]],
                },
                "after_blocks": {
                    tonight_day: [b.to_ha_dict() for b in tonight_res.blocks],
                    tomorrow_day: [b.to_ha_dict() for b in tomorrow_res.blocks],
                },
            }

        total_spaces = len(space_meta)
        if ai_failed:
            self.daily_plan_headline = f"Fallback to baseline ({total_spaces} spaces)"
        elif spaces_modified == 0:
            self.daily_plan_headline = f"All {total_spaces} spaces match baseline"
        else:
            self.daily_plan_headline = (
                f"{spaces_modified} of {total_spaces} spaces differ from baseline"
            )
        self.space_daily_summaries = summaries
        self.daily_plan_summary = " | ".join(
            f"{space_meta[s]['name']}: {txt}" for s, txt in summaries.items()
        )
        self.last_nightly_run = now_local.isoformat()
        self.status = (
            "error" if ai_failed else "fallback" if any_guardrail_fallback else "ok"
        )
        await self.journal.async_append(
            {
                "timestamp": now_local.isoformat(),
                "kind": "plan",
                "status": self.status,
                "trigger": {
                    "type": "manual_plan" if manual else "scheduled_plan",
                    "label": "Plan",
                    "manual": manual,
                },
                "target_days": [tonight_day, tomorrow_day],
                "weather_snapshot": weather_summary,
                "headline": self.daily_plan_headline,
                "error": self.last_error,
                "spaces": journal_spaces,
                "raw_response": ai_json,
            }
        )
        self._notify_entities()

    async def async_run_intraday_revision(
        self,
        trigger_event: dict[str, Any],
        target_space_ids: list[str] | None = None,
        bypass_cooldown: bool = False,
    ) -> None:
        """Run event-driven Intraday Plan-Revision for affected space(s)."""
        now_local = dt_util.now()
        current_day = DAYS_OF_WEEK[now_local.weekday()]
        # Quantize now to current minute (clamped < 1440)
        now_min = min(1439, now_local.hour * 60 + now_local.minute)
        now_time_str = minutes_to_time_str(now_min)

        weather_summary, outdoor_temp = await self._async_get_weather_context(
            now_local.date().isoformat()
        )

        alarm_eid = self.config.get(CONF_ALARM_ENTITY)
        current_alarm_state: str | None = None
        if alarm_eid:
            alarm_st = self.hass.states.get(alarm_eid)
            if (
                alarm_st is not None
                and str(alarm_st.state).lower() not in _INVALID_PRIOR_STATES
            ):
                current_alarm_state = str(alarm_st.state).lower()

        space_contexts: list[SpaceIntradayContext] = []
        space_meta: dict[str, dict[str, Any]] = {}

        for space_conf in self.spaces:
            climate_eid = space_conf.get(CONF_CLIMATE_ENTITY)
            occ_eid = space_conf.get(CONF_OCCUPIED_SCHEDULE)
            unocc_eid = space_conf.get(CONF_UNOCCUPIED_SCHEDULE) or ""
            if not climate_eid or not occ_eid:
                continue

            space_id, space_name = derive_space_id_and_name(self.hass, climate_eid)
            if target_space_ids is not None and space_id not in target_space_ids:
                continue

            if not bypass_cooldown:
                last_ts = self._last_intraday_by_space.get(space_id)
                if (
                    last_ts is not None
                    and (now_local - last_ts).total_seconds()
                    < INTRADAY_COOLDOWN_MINUTES * 60
                ):
                    _LOGGER.debug(
                        "Skipping intraday revision for %s (cooldown active)", space_id
                    )
                    continue

            curr_temp, preset, modes, is_locked = self._get_climate_info(climate_eid)
            default_mode = space_conf.get(CONF_DEFAULT_MODE, MODE_OCCUPIED)

            occ_week = await async_read_schedule(self.hass, occ_eid)
            unocc_week = (
                await async_read_schedule(self.hass, unocc_eid)
                if unocc_eid
                else {day: [] for day in DAYS_OF_WEEK}
            )
            butler_eid = self.butler_schedules.get(space_id)
            butler_week = (
                await async_read_schedule(self.hass, butler_eid)
                if butler_eid
                else {day: [] for day in DAYS_OF_WEEK}
            )

            occ_rem = slice_blocks_to_window(occ_week[current_day], now_min, 1440)
            unocc_rem = (
                slice_blocks_to_window(unocc_week[current_day], now_min, 1440)
                if unocc_eid
                else []
            )
            butler_rem = slice_blocks_to_window(butler_week[current_day], now_min, 1440)

            trigger_type = trigger_event.get("type")
            if trigger_type == "presence_change":
                wants_unocc = trigger_event.get("state") == "off"
            elif trigger_type == "manual_intraday":
                if current_alarm_state == "armed_away":
                    wants_unocc = True
                elif self._space_to_sensors.get(space_id):
                    wants_unocc = not self._is_space_occupied(space_id)
                else:
                    wants_unocc = default_mode != MODE_OCCUPIED
            elif trigger_event.get("to") == "armed_away":
                wants_unocc = True
            else:
                # On disarmed / armed_home, each space reverts to its own default_mode
                wants_unocc = default_mode != MODE_OCCUPIED
            space_contexts.append(
                SpaceIntradayContext(
                    space_id=space_id,
                    name=space_name,
                    default_mode=default_mode,
                    current_temp=curr_temp,
                    active_preset=preset,
                    occupied_remaining=occ_rem,
                    unoccupied_remaining=unocc_rem,
                    current_butler_remaining=butler_rem,
                    supported_hvac_modes=modes,
                    space_notes=str(space_conf.get(CONF_SPACE_NOTES, "")),
                    presence_sensors=self._get_space_sensor_states(space_id),
                )
            )
            space_meta[space_id] = {
                "name": space_name,
                "climate_eid": climate_eid,
                "preset": preset,
                "modes": set(modes),
                "is_locked": is_locked,
                "existing_butler_today": butler_week[current_day],
                "existing_butler_week": butler_week,
                "current_butler_remaining": butler_rem,
                "baseline_remaining": (
                    unocc_rem if (wants_unocc and unocc_rem) else occ_rem
                ),
            }

        if not space_contexts:
            return

        self.status = "revising"
        self._notify_entities()

        raw_trigger_type = str(trigger_event.get("type", "intraday"))
        deterministic_trigger_label = (
            "Presence"
            if raw_trigger_type == "presence_change"
            else "Arm/Disarm"
            if raw_trigger_type == "alarm_change"
            else "Calendar"
            if raw_trigger_type == "calendar_event"
            else "Manual Check"
            if raw_trigger_type == "manual_intraday"
            else raw_trigger_type.replace("_", " ").title()
        )
        journal_trigger = {
            **trigger_event,
            "type": raw_trigger_type,
            "label": deterministic_trigger_label,
        }

        recent_events = self.journal.get_recent_context_since_keyframe(
            target_space_ids=list(space_meta.keys())
        )
        end_of_today_dt = (now_local + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        intraday_day_notes = self.calendar_store.format_day_notes(
            now_local, end_of_today_dt
        )
        ctx = IntradayPlanContext(
            timestamp_iso=now_local.isoformat(),
            current_day=current_day,
            now_time=now_time_str,
            trigger_event=trigger_event,
            current_weather=weather_summary.get("current", {}),
            spaces=space_contexts,
            current_alarm_state=current_alarm_state,
            recent_events=recent_events,
            house_notes=str(self.config.get(CONF_HOUSE_NOTES, "")),
            day_notes=intraday_day_notes,
        )
        prompt = build_intraday_prompt(ctx, self.guardrails)

        ai_json: dict[str, Any] | None = None
        try:
            ai_json = await self._async_call_ai_task(
                "hvac_butler_intraday_revision", prompt
            )
            ai_spaces = ai_json.get("spaces", {}) if isinstance(ai_json, dict) else {}
            self.last_error = None
        except Exception as err:
            self.last_error = str(err).splitlines()[0][:240]
            self.status = "error"
            await self.journal.async_append(
                {
                    "timestamp": now_local.isoformat(),
                    "kind": "intraday",
                    "status": "error",
                    "trigger": journal_trigger,
                    "target_days": [current_day],
                    "weather_snapshot": weather_summary,
                    "headline": f"Intraday evaluation failed ({deterministic_trigger_label})",
                    "error": self.last_error,
                    "spaces": {
                        s_id: {
                            "name": m["name"],
                            "changed": False,
                            "summary": f"Evaluation error: {self.last_error}",
                            "fallback": False,
                            "locked": bool(m["is_locked"]),
                            "comfort_boost": None,
                            "guardrail_notes": [],
                            "before_blocks": {
                                current_day: [
                                    b.to_ha_dict()
                                    for b in m["current_butler_remaining"]
                                ]
                            },
                            "after_blocks": {
                                current_day: [
                                    b.to_ha_dict()
                                    for b in m["current_butler_remaining"]
                                ]
                            },
                        }
                        for s_id, m in space_meta.items()
                    },
                    "raw_response": None,
                }
            )
            self._notify_entities()
            _LOGGER.error("Intraday revision AI task failed: %s", err)
            return

        explanations: dict[str, str] = {}
        journal_spaces: dict[str, dict[str, Any]] = {}
        spaces_changed = 0
        any_guardrail_fallback = False
        guardrails = self.guardrails
        has_comfort_boost = self.hass.services.has_service(
            "hvac_fusion", "comfort_boost"
        )

        for space_id, meta in space_meta.items():
            self._last_intraday_by_space[space_id] = now_local
            if raw_trigger_type == "presence_change" and trigger_event.get("state") in (
                "on",
                "off",
            ):
                self._last_presence_state_by_space[space_id] = str(
                    trigger_event["state"]
                )
            elif raw_trigger_type == "manual_intraday" and self._space_to_sensors.get(
                space_id
            ):
                self._last_presence_state_by_space[space_id] = (
                    "on" if self._is_space_occupied(space_id) else "off"
                )
            ai_entry = (
                ai_spaces.get(space_id, {}) if isinstance(ai_spaces, dict) else {}
            )
            explanations[space_id] = str(
                ai_entry.get("intraday_explanation") or "No change needed."
            )

            before_remaining = meta["current_butler_remaining"]
            after_remaining = before_remaining
            blocks_changed = False
            used_fallback = False
            guardrail_notes: list[str] = []

            # 1. Apply schedule_updates if proposed and not edit-locked
            raw_updates = ai_entry.get("schedule_updates")
            if raw_updates and not meta["is_locked"]:
                res = validate_and_clamp_blocks(
                    raw_updates,
                    meta["baseline_remaining"],
                    now_min,
                    1440,
                    guardrails,
                    outdoor_temp_f=outdoor_temp,
                    supported_hvac_modes=meta["modes"],
                )
                after_remaining = res.blocks
                used_fallback = bool(res.used_fallback)
                if res.warnings:
                    guardrail_notes.extend(res.warnings)
                if res.fallback_reason:
                    guardrail_notes.append(f"Fallback: {res.fallback_reason}")
                if used_fallback:
                    any_guardrail_fallback = True
                blocks_changed = after_remaining != before_remaining
                if blocks_changed:
                    spaces_changed += 1
                merged_today = merge_intraday_blocks(
                    meta["existing_butler_today"], res.blocks, split_min=now_min
                )
                butler_eid = self.butler_schedules.get(space_id)
                if butler_eid:
                    # Preserve tomorrow if already populated (e.g. after 21:00)
                    tomorrow_day = DAYS_OF_WEEK[(now_local.weekday() + 1) % 7]
                    tomorrow_existing = meta["existing_butler_week"].get(
                        tomorrow_day, []
                    )
                    week_payload = build_butler_week_payload(
                        tonight_day=current_day,
                        tonight_blocks=merged_today,
                        tomorrow_day=tomorrow_day if tomorrow_existing else None,
                        tomorrow_blocks=tomorrow_existing
                        if tomorrow_existing
                        else None,
                    )
                    await async_write_butler_schedule(
                        self.hass, butler_eid, f"{meta['name']} Butler", week_payload
                    )

            # 2. Progressive enhancement: dispatch hvac_fusion.comfort_boost only if space is on "Butler"
            boost = validate_comfort_boost(ai_entry.get("comfort_boost"))
            boost_applied = False
            if boost and has_comfort_boost and meta["preset"] == BUTLER_PRESET_NAME:
                boost_applied = True
                await self.hass.services.async_call(
                    "hvac_fusion",
                    "comfort_boost",
                    {"entity_id": meta["climate_eid"], **boost},
                    blocking=False,
                )

            journal_spaces[space_id] = {
                "name": meta["name"],
                "changed": bool(blocks_changed or boost_applied),
                "summary": explanations[space_id],
                "fallback": used_fallback,
                "locked": bool(meta["is_locked"]),
                "comfort_boost": (
                    {**boost, "applied": boost_applied} if boost else None
                ),
                "guardrail_notes": guardrail_notes,
                "before_blocks": {
                    current_day: [b.to_ha_dict() for b in before_remaining]
                },
                "after_blocks": {
                    current_day: [b.to_ha_dict() for b in after_remaining]
                },
            }

        trigger_label = str(trigger_event.get("type", "event")).replace("_", " ")
        self.intraday_headline = (
            f"{spaces_changed} of {len(space_meta)} spaces revised ({trigger_label})"
            if spaces_changed
            else f"No schedule changes ({trigger_label})"
        )
        self.space_intraday_explanations = explanations
        self.intraday_explanation = " | ".join(
            f"{space_meta[s]['name']}: {txt}" for s, txt in explanations.items()
        )
        self.last_trigger = trigger_event
        self.last_intraday_run = now_local.isoformat()
        self.status = "fallback" if any_guardrail_fallback else "ok"
        await self.journal.async_append(
            {
                "timestamp": now_local.isoformat(),
                "kind": "intraday",
                "status": self.status,
                "trigger": journal_trigger,
                "target_days": [current_day],
                "weather_snapshot": weather_summary,
                "headline": self.intraday_headline,
                "error": None,
                "spaces": journal_spaces,
                "raw_response": ai_json,
            }
        )
        self._notify_entities()
