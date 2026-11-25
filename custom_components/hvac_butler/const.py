"""Constants for the HVAC Butler integration."""

from __future__ import annotations

DOMAIN = "hvac_butler"
DEFAULT_NAME = "HVAC Butler"

# Config keys — Global
CONF_AI_TASK_ENTITY = "ai_task_entity"
CONF_WEATHER_ENTITY = "weather_entity"
CONF_ALARM_ENTITY = "alarm_entity"
CONF_HOUSE_NOTES = "house_notes"
CONF_SPACES = "spaces"

# Config keys — Guardrails
CONF_MIN_HEAT_TEMP = "min_heat_temp"
CONF_MAX_HEAT_TEMP = "max_heat_temp"
CONF_MIN_COOL_TEMP = "min_cool_temp"
CONF_MAX_COOL_TEMP = "max_cool_temp"
CONF_MAX_AI_DELTA_F = "max_ai_delta_f"

# Config keys — Per-Space
CONF_CLIMATE_ENTITY = "climate_entity"
CONF_BUTLER_SCHEDULE = "butler_schedule"
CONF_OCCUPIED_SCHEDULE = "occupied_schedule"
CONF_UNOCCUPIED_SCHEDULE = "unoccupied_schedule"
CONF_DEFAULT_MODE = "default_mode"
CONF_PRESENCE_SENSORS = "presence_sensors"
CONF_SPACE_NOTES = "space_notes"

MODE_OCCUPIED = "occupied"
MODE_UNOCCUPIED = "unoccupied"

# Baked-in operational defaults (intentionally not exposed as UI knobs in MVP)
NIGHTLY_PLAN_HOUR = 21
NIGHTLY_PLAN_MINUTE = 0
BUTLER_PRESET_NAME = "Butler"
MIN_DEADBAND_F = 3.0
HEATING_REGIME_OUTDOOR_THRESHOLD_F = 60.0

DEFAULT_MIN_HEAT_TEMP = 50.0
DEFAULT_MAX_HEAT_TEMP = 76.0
DEFAULT_MIN_COOL_TEMP = 68.0
DEFAULT_MAX_COOL_TEMP = 85.0
DEFAULT_MAX_AI_DELTA_F = 4.0

PRESENCE_ON_DEBOUNCE_MINUTES = 3
PRESENCE_OFF_DEBOUNCE_MINUTES = 15
INTRADAY_COOLDOWN_MINUTES = 5

# Days of week in HA schedule order (Monday = 0 .. Sunday = 6)
DAYS_OF_WEEK: tuple[str, ...] = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)
