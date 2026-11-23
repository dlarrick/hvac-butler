"""Unit tests for deterministic 'Trust, but Verify' guardrails."""

from __future__ import annotations

from custom_components.hvac_butler.guardrails import (
    GuardrailConfig,
    validate_and_clamp_blocks,
    validate_comfort_boost,
)
from custom_components.hvac_butler.schedule_utils import ScheduleBlock


def test_valid_plan_passes_cleanly() -> None:
    baseline = [
        ScheduleBlock(0, 390, "heat_cool", 62.0, 76.0),
        ScheduleBlock(390, 1320, "heat_cool", 68.0, 74.0),
        ScheduleBlock(1320, 1440, "heat_cool", 62.0, 76.0),
    ]
    ai_raw = [
        {
            "from": "00:00:00",
            "to": "06:00:00",
            "data": {"hvac_mode": "heat_cool", "heat_to": 61.0, "cool_to": 76.0},
        },
        {
            "from": "06:00:00",
            "to": "22:00:00",
            "data": {"hvac_mode": "heat_cool", "heat_to": 69.0, "cool_to": 74.0},
        },
        {
            "from": "22:00:00",
            "to": "24:00:00",
            "data": {"hvac_mode": "heat_cool", "heat_to": 62.0, "cool_to": 76.0},
        },
    ]
    res = validate_and_clamp_blocks(
        ai_raw, baseline, 0, 1440, GuardrailConfig(), outdoor_temp_f=25.0
    )
    assert res.used_fallback is False
    assert res.warnings is None
    assert len(res.blocks) == 3
    assert res.blocks[1].start_min == 360
    assert res.blocks[1].heat_to == 69.0


def test_directed_deadband_cold_vs_warm_outdoor() -> None:
    baseline = [ScheduleBlock(0, 1440, "heat_cool", 68.0, 72.0)]
    ai_raw = [
        {
            "from": "00:00:00",
            "to": "24:00:00",
            "data": {"hvac_mode": "heat_cool", "heat_to": 70.0, "cool_to": 71.0},
        }
    ]
    cfg = GuardrailConfig(min_deadband=3.0)

    # Cold outside (30°F): preserve heat_to=70, push cool_to -> 73
    cold_res = validate_and_clamp_blocks(
        ai_raw, baseline, 0, 1440, cfg, outdoor_temp_f=30.0
    )
    assert cold_res.used_fallback is False
    assert cold_res.blocks[0].heat_to == 70.0
    assert cold_res.blocks[0].cool_to == 73.0

    # Warm outside (85°F): preserve cool_to=71, push heat_to -> 68
    warm_res = validate_and_clamp_blocks(
        ai_raw, baseline, 0, 1440, cfg, outdoor_temp_f=85.0
    )
    assert warm_res.used_fallback is False
    assert warm_res.blocks[0].heat_to == 68.0
    assert warm_res.blocks[0].cool_to == 71.0


def test_delta_and_hard_bounds_clamping() -> None:
    baseline = [ScheduleBlock(1260, 1440, "heat_cool", 62.0, 76.0)]
    ai_raw = [
        {
            "from": "21:00:00",
            "to": "24:00:00",
            "data": {"hvac_mode": "heat_cool", "heat_to": 45.0, "cool_to": 95.0},
        }
    ]
    cfg = GuardrailConfig(
        min_heat_temp=50.0, max_cool_temp=85.0, max_ai_delta_f=4.0
    )
    res = validate_and_clamp_blocks(
        ai_raw, baseline, 1260, 1440, cfg, outdoor_temp_f=20.0
    )
    assert res.used_fallback is False
    assert res.blocks[0].heat_to == 58.0  # 62 - 4 (delta limit tighter than 50)
    assert res.blocks[0].cool_to == 80.0  # 76 + 4 (delta limit tighter than 85)


def test_structural_errors_trigger_baseline_fallback() -> None:
    baseline = [ScheduleBlock(1260, 1440, "heat_cool", 62.0, 76.0)]
    cfg = GuardrailConfig()

    # Gap between 22:00 and 23:00
    gapped = [
        {
            "from": "21:00:00",
            "to": "22:00:00",
            "data": {"hvac_mode": "heat_cool", "heat_to": 62.0, "cool_to": 76.0},
        },
        {
            "from": "23:00:00",
            "to": "24:00:00",
            "data": {"hvac_mode": "heat_cool", "heat_to": 62.0, "cool_to": 76.0},
        },
    ]
    res_gap = validate_and_clamp_blocks(gapped, baseline, 1260, 1440, cfg)
    assert res_gap.used_fallback is True
    assert res_gap.blocks == baseline

    # Overlap
    overlapping = [
        {
            "from": "21:00:00",
            "to": "23:00:00",
            "data": {"hvac_mode": "heat_cool", "heat_to": 62.0, "cool_to": 76.0},
        },
        {
            "from": "22:00:00",
            "to": "24:00:00",
            "data": {"hvac_mode": "heat_cool", "heat_to": 62.0, "cool_to": 76.0},
        },
    ]
    res_ov = validate_and_clamp_blocks(overlapping, baseline, 1260, 1440, cfg)
    assert res_ov.used_fallback is True
    assert res_ov.blocks == baseline


def test_validate_comfort_boost() -> None:
    assert validate_comfort_boost(None) is None
    assert validate_comfort_boost({"feeling": "invalid"}) is None
    clamped = validate_comfort_boost(
        {"feeling": "too_cold", "delta_f": 8.0, "duration_minutes": 300}
    )
    assert clamped == {
        "feeling": "too_cold",
        "delta_f": 4.0,
        "duration_minutes": 180,
        "decay": True,
    }


def test_supported_hvac_modes_coercion_for_heat_only_entity() -> None:
    """Heat-only climate entities must coerce unsupported 'heat_cool' proposals to 'heat'."""
    baseline = [ScheduleBlock(0, 1440, "heat", 68.0, None)]
    ai_raw = [
        {
            "from": "00:00:00",
            "to": "24:00:00",
            "data": {"hvac_mode": "heat_cool", "heat_to": 69.0, "cool_to": 74.0},
        }
    ]
    res = validate_and_clamp_blocks(
        ai_raw,
        baseline,
        0,
        1440,
        GuardrailConfig(),
        outdoor_temp_f=30.0,
        supported_hvac_modes={"heat", "off"},
    )
    assert res.used_fallback is False
    assert res.blocks[0].hvac_mode == "heat"
    assert res.blocks[0].heat_to == 69.0
    assert res.blocks[0].cool_to is None
    assert res.warnings is not None
