"""Config flow and 2-menu Options flow for HVAC Butler."""

from __future__ import annotations

import copy
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult, section
from homeassistant.helpers import selector

from .const import (
    CONF_AI_TASK_ENTITY,
    CONF_ALARM_ENTITY,
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
    DEFAULT_MAX_AI_DELTA_F,
    DEFAULT_MAX_COOL_TEMP,
    DEFAULT_MAX_HEAT_TEMP,
    DEFAULT_MIN_COOL_TEMP,
    DEFAULT_MIN_HEAT_TEMP,
    DEFAULT_NAME,
    DOMAIN,
    MODE_OCCUPIED,
    MODE_UNOCCUPIED,
)
from .coordinator import derive_space_id_and_name


def _discover_hvac_fusion_spaces(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Pre-populate space entries from any existing hvac_fusion climate entities."""
    discovered: list[dict[str, Any]] = []
    for state in hass.states.async_all("climate"):
        attrs = state.attributes
        if "space_id" in attrs and "presets" in attrs:
            discovered.append(
                {
                    CONF_CLIMATE_ENTITY: state.entity_id,
                    CONF_OCCUPIED_SCHEDULE: "",
                    CONF_UNOCCUPIED_SCHEDULE: "",
                    CONF_DEFAULT_MODE: MODE_OCCUPIED,
                    CONF_PRESENCE_SENSORS: [],
                    CONF_SPACE_NOTES: "",
                }
            )
    return discovered


class HvacButlerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle initial setup for HVAC Butler."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> HvacButlerOptionsFlowHandler:
        """Return the options flow handler."""
        return HvacButlerOptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle lightweight onboarding step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors: dict[str, str] = {}
        if user_input is not None:
            ai_task_eid = user_input.get(CONF_AI_TASK_ENTITY)
            if not ai_task_eid:
                errors[CONF_AI_TASK_ENTITY] = "required"
            else:
                name = str(user_input.get(CONF_NAME) or DEFAULT_NAME).strip()
                entry_data: dict[str, Any] = {
                    CONF_NAME: name,
                    CONF_AI_TASK_ENTITY: ai_task_eid,
                    CONF_WEATHER_ENTITY: user_input.get(CONF_WEATHER_ENTITY) or "",
                    CONF_ALARM_ENTITY: user_input.get(CONF_ALARM_ENTITY) or "",
                    CONF_HOUSE_NOTES: "",
                    CONF_MIN_HEAT_TEMP: DEFAULT_MIN_HEAT_TEMP,
                    CONF_MAX_HEAT_TEMP: DEFAULT_MAX_HEAT_TEMP,
                    CONF_MIN_COOL_TEMP: DEFAULT_MIN_COOL_TEMP,
                    CONF_MAX_COOL_TEMP: DEFAULT_MAX_COOL_TEMP,
                    CONF_MAX_AI_DELTA_F: DEFAULT_MAX_AI_DELTA_F,
                    CONF_SPACES: _discover_hvac_fusion_spaces(self.hass),
                }
                return self.async_create_entry(title=name, data=entry_data)

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): selector.TextSelector(),
                vol.Required(CONF_AI_TASK_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="ai_task")
                ),
                vol.Optional(CONF_WEATHER_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="weather")
                ),
                vol.Optional(CONF_ALARM_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="alarm_control_panel")
                ),
            }
        )
        if user_input is not None:
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)


class HvacButlerOptionsFlowHandler(config_entries.OptionsFlowWithReload):
    """2-menu Options Flow for HVAC Butler."""

    def __init__(self) -> None:
        self._working_options: dict[str, Any] | None = None
        self._selected_space_index: int | None = None

    def _ensure_working_options(self) -> dict[str, Any]:
        if self._working_options is None:
            merged = {**self.config_entry.data, **self.config_entry.options}
            self._working_options = copy.deepcopy(merged)
            self._working_options.setdefault(CONF_SPACES, [])
        return self._working_options

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show the 2-menu hub."""
        self._ensure_working_options()
        return self.async_show_menu(
            step_id="init",
            menu_options=["global_settings", "spaces_menu", "finish"],
        )

    async def async_step_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Save working options and reload integration."""
        opts = self._ensure_working_options()
        return self.async_create_entry(title="", data=opts)

    async def async_step_global_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Menu 1: Global Settings, House Notes, and collapsible Temperature Safety Bounds."""
        opts = self._ensure_working_options()
        errors: dict[str, str] = {}

        if user_input is not None:
            opts[CONF_AI_TASK_ENTITY] = user_input[CONF_AI_TASK_ENTITY]
            opts[CONF_WEATHER_ENTITY] = user_input.get(CONF_WEATHER_ENTITY) or ""
            opts[CONF_ALARM_ENTITY] = user_input.get(CONF_ALARM_ENTITY) or ""
            opts[CONF_HOUSE_NOTES] = user_input.get(CONF_HOUSE_NOTES) or ""

            bounds = user_input.get("safety_bounds") or {}
            min_heat = float(bounds.get(CONF_MIN_HEAT_TEMP, DEFAULT_MIN_HEAT_TEMP))
            max_heat = float(bounds.get(CONF_MAX_HEAT_TEMP, DEFAULT_MAX_HEAT_TEMP))
            min_cool = float(bounds.get(CONF_MIN_COOL_TEMP, DEFAULT_MIN_COOL_TEMP))
            max_cool = float(bounds.get(CONF_MAX_COOL_TEMP, DEFAULT_MAX_COOL_TEMP))
            max_delta = float(bounds.get(CONF_MAX_AI_DELTA_F, DEFAULT_MAX_AI_DELTA_F))

            if min_heat >= max_heat or min_cool >= max_cool:
                errors["base"] = "invalid_bounds"
            else:
                opts[CONF_MIN_HEAT_TEMP] = min_heat
                opts[CONF_MAX_HEAT_TEMP] = max_heat
                opts[CONF_MIN_COOL_TEMP] = min_cool
                opts[CONF_MAX_COOL_TEMP] = max_cool
                opts[CONF_MAX_AI_DELTA_F] = max_delta
                return await self.async_step_init()

        schema_dict: dict[Any, Any] = {
            vol.Required(
                CONF_AI_TASK_ENTITY,
                default=opts.get(CONF_AI_TASK_ENTITY, ""),
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="ai_task")),
            vol.Optional(
                CONF_WEATHER_ENTITY,
                description={"suggested_value": opts.get(CONF_WEATHER_ENTITY) or None},
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="weather")),
            vol.Optional(
                CONF_ALARM_ENTITY,
                description={"suggested_value": opts.get(CONF_ALARM_ENTITY) or None},
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="alarm_control_panel")
            ),
            vol.Optional(
                CONF_HOUSE_NOTES,
                default=opts.get(CONF_HOUSE_NOTES, ""),
            ): selector.TextSelector(selector.TextSelectorConfig(multiline=True)),
            vol.Required("safety_bounds"): section(
                vol.Schema(
                    {
                        vol.Required(
                            CONF_MIN_HEAT_TEMP,
                            default=opts.get(CONF_MIN_HEAT_TEMP, DEFAULT_MIN_HEAT_TEMP),
                        ): selector.NumberSelector(
                            selector.NumberSelectorConfig(
                                min=40,
                                max=70,
                                step=1,
                                mode=selector.NumberSelectorMode.BOX,
                            )
                        ),
                        vol.Required(
                            CONF_MAX_HEAT_TEMP,
                            default=opts.get(CONF_MAX_HEAT_TEMP, DEFAULT_MAX_HEAT_TEMP),
                        ): selector.NumberSelector(
                            selector.NumberSelectorConfig(
                                min=60,
                                max=85,
                                step=1,
                                mode=selector.NumberSelectorMode.BOX,
                            )
                        ),
                        vol.Required(
                            CONF_MIN_COOL_TEMP,
                            default=opts.get(CONF_MIN_COOL_TEMP, DEFAULT_MIN_COOL_TEMP),
                        ): selector.NumberSelector(
                            selector.NumberSelectorConfig(
                                min=60,
                                max=80,
                                step=1,
                                mode=selector.NumberSelectorMode.BOX,
                            )
                        ),
                        vol.Required(
                            CONF_MAX_COOL_TEMP,
                            default=opts.get(CONF_MAX_COOL_TEMP, DEFAULT_MAX_COOL_TEMP),
                        ): selector.NumberSelector(
                            selector.NumberSelectorConfig(
                                min=70,
                                max=95,
                                step=1,
                                mode=selector.NumberSelectorMode.BOX,
                            )
                        ),
                        vol.Required(
                            CONF_MAX_AI_DELTA_F,
                            default=opts.get(
                                CONF_MAX_AI_DELTA_F, DEFAULT_MAX_AI_DELTA_F
                            ),
                        ): selector.NumberSelector(
                            selector.NumberSelectorConfig(
                                min=1,
                                max=10,
                                step=0.5,
                                mode=selector.NumberSelectorMode.BOX,
                            )
                        ),
                    }
                ),
                {"collapsed": True},
            ),
        }

        schema = vol.Schema(schema_dict)
        if user_input is not None:
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(
            step_id="global_settings",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_spaces_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Menu 2: List configured spaces (edit directly) or add a new space."""
        opts = self._ensure_working_options()
        spaces: list[dict[str, Any]] = opts.get(CONF_SPACES, [])

        if user_input is not None:
            action = user_input["space_action"]
            if action == "add":
                return await self.async_step_space_add()
            if action == "back":
                return await self.async_step_init()
            if action.startswith("edit_"):
                self._selected_space_index = int(action.removeprefix("edit_"))
                return await self.async_step_space_edit()

        options: list[selector.SelectOptionDict] = []
        for idx, s_conf in enumerate(spaces):
            climate_eid = s_conf.get(CONF_CLIMATE_ENTITY, "")
            _, space_name = derive_space_id_and_name(self.hass, climate_eid)
            has_baselines = bool(s_conf.get(CONF_OCCUPIED_SCHEDULE))
            suffix = "" if has_baselines else " (needs baseline schedule)"
            options.append(
                selector.SelectOptionDict(
                    value=f"edit_{idx}",
                    label=f"{space_name}{suffix}",
                )
            )
        options.append(selector.SelectOptionDict(value="add", label="+ Add space"))
        options.append(
            selector.SelectOptionDict(value="back", label="← Back to main menu")
        )

        return self.async_show_form(
            step_id="spaces_menu",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "space_action", default="add"
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=options,
                            mode=selector.SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
        )

    async def async_step_space_add(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a space leading with its target climate entity."""
        opts = self._ensure_working_options()
        errors: dict[str, str] = {}

        if user_input is not None:
            if user_input.get("cancel"):
                return await self.async_step_spaces_menu()

            climate_eid = user_input.get(CONF_CLIMATE_ENTITY)
            occ_eid = user_input.get(CONF_OCCUPIED_SCHEDULE)
            unocc_eid = user_input.get(CONF_UNOCCUPIED_SCHEDULE) or ""
            default_mode = user_input.get(CONF_DEFAULT_MODE, MODE_OCCUPIED)
            if not climate_eid:
                errors[CONF_CLIMATE_ENTITY] = "required"
            if not occ_eid:
                errors[CONF_OCCUPIED_SCHEDULE] = "required"
            if default_mode == MODE_UNOCCUPIED and not unocc_eid:
                errors[CONF_UNOCCUPIED_SCHEDULE] = "unoccupied_schedule_required"

            if not errors:
                opts[CONF_SPACES].append(
                    {
                        CONF_CLIMATE_ENTITY: climate_eid,
                        CONF_OCCUPIED_SCHEDULE: occ_eid,
                        CONF_UNOCCUPIED_SCHEDULE: unocc_eid,
                        CONF_DEFAULT_MODE: default_mode,
                        CONF_PRESENCE_SENSORS: list(
                            user_input.get(CONF_PRESENCE_SENSORS) or []
                        ),
                        CONF_SPACE_NOTES: user_input.get(CONF_SPACE_NOTES) or "",
                    }
                )
                return await self.async_step_spaces_menu()

        schema = vol.Schema(
            {
                vol.Optional(CONF_CLIMATE_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="climate")
                ),
                vol.Optional(CONF_OCCUPIED_SCHEDULE): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="schedule")
                ),
                vol.Optional(CONF_UNOCCUPIED_SCHEDULE): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="schedule")
                ),
                vol.Required(
                    CONF_DEFAULT_MODE, default=MODE_OCCUPIED
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(
                                value=MODE_OCCUPIED, label="Occupied"
                            ),
                            selector.SelectOptionDict(
                                value=MODE_UNOCCUPIED, label="Unoccupied"
                            ),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_PRESENCE_SENSORS, default=[]
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor", multiple=True)
                ),
                vol.Optional(CONF_SPACE_NOTES, default=""): selector.TextSelector(
                    selector.TextSelectorConfig(multiline=True)
                ),
                vol.Optional("cancel", default=False): selector.BooleanSelector(),
            }
        )
        if user_input is not None:
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(
            step_id="space_add", data_schema=schema, errors=errors
        )

    async def async_step_space_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit or delete an existing space."""
        opts = self._ensure_working_options()
        spaces: list[dict[str, Any]] = opts.get(CONF_SPACES, [])
        if self._selected_space_index is None or self._selected_space_index >= len(
            spaces
        ):
            return await self.async_step_spaces_menu()

        current = spaces[self._selected_space_index]
        errors: dict[str, str] = {}

        if user_input is not None:
            if user_input.get("cancel"):
                return await self.async_step_spaces_menu()
            if user_input.get("delete_space"):
                spaces.pop(self._selected_space_index)
                self._selected_space_index = None
                return await self.async_step_spaces_menu()

            climate_eid = user_input.get(CONF_CLIMATE_ENTITY)
            occ_eid = user_input.get(CONF_OCCUPIED_SCHEDULE)
            unocc_eid = user_input.get(CONF_UNOCCUPIED_SCHEDULE) or ""
            default_mode = user_input.get(CONF_DEFAULT_MODE, MODE_OCCUPIED)
            if not climate_eid:
                errors[CONF_CLIMATE_ENTITY] = "required"
            if not occ_eid:
                errors[CONF_OCCUPIED_SCHEDULE] = "required"
            if default_mode == MODE_UNOCCUPIED and not unocc_eid:
                errors[CONF_UNOCCUPIED_SCHEDULE] = "unoccupied_schedule_required"

            if not errors:
                spaces[self._selected_space_index] = {
                    CONF_CLIMATE_ENTITY: climate_eid,
                    CONF_OCCUPIED_SCHEDULE: occ_eid,
                    CONF_UNOCCUPIED_SCHEDULE: unocc_eid,
                    CONF_DEFAULT_MODE: default_mode,
                    CONF_PRESENCE_SENSORS: list(
                        user_input.get(CONF_PRESENCE_SENSORS) or []
                    ),
                    CONF_SPACE_NOTES: user_input.get(CONF_SPACE_NOTES) or "",
                }
                return await self.async_step_spaces_menu()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_CLIMATE_ENTITY,
                    default=current.get(CONF_CLIMATE_ENTITY, ""),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="climate")
                ),
                vol.Optional(
                    CONF_OCCUPIED_SCHEDULE,
                    description={
                        "suggested_value": current.get(CONF_OCCUPIED_SCHEDULE) or None
                    },
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="schedule")
                ),
                vol.Optional(
                    CONF_UNOCCUPIED_SCHEDULE,
                    description={
                        "suggested_value": current.get(CONF_UNOCCUPIED_SCHEDULE) or None
                    },
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="schedule")
                ),
                vol.Required(
                    CONF_DEFAULT_MODE,
                    default=current.get(CONF_DEFAULT_MODE, MODE_OCCUPIED),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(
                                value=MODE_OCCUPIED, label="Occupied"
                            ),
                            selector.SelectOptionDict(
                                value=MODE_UNOCCUPIED, label="Unoccupied"
                            ),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_PRESENCE_SENSORS,
                    default=list(current.get(CONF_PRESENCE_SENSORS) or []),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor", multiple=True)
                ),
                vol.Optional(
                    CONF_SPACE_NOTES,
                    default=current.get(CONF_SPACE_NOTES, ""),
                ): selector.TextSelector(selector.TextSelectorConfig(multiline=True)),
                vol.Optional("delete_space", default=False): selector.BooleanSelector(),
                vol.Optional("cancel", default=False): selector.BooleanSelector(),
            }
        )
        if user_input is not None:
            schema = self.add_suggested_values_to_schema(schema, user_input)
        return self.async_show_form(
            step_id="space_edit", data_schema=schema, errors=errors
        )
