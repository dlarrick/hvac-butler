"""Deterministic 'Trust, but Verify' guardrails for AI-generated climate plans."""

from __future__ import annotations

from dataclasses import dataclass
import itertools
from typing import Any

from .const import (
    DEFAULT_MAX_AI_DELTA_F,
    DEFAULT_MAX_COOL_TEMP,
    DEFAULT_MAX_HEAT_TEMP,
    DEFAULT_MIN_COOL_TEMP,
    DEFAULT_MIN_HEAT_TEMP,
    HEATING_REGIME_OUTDOOR_THRESHOLD_F,
    MIN_DEADBAND_F,
)
from .schedule_utils import ScheduleBlock, parse_ha_blocks, slice_blocks_to_window


@dataclass(slots=True)
class GuardrailConfig:
    """Hard safety bounds and deviation limits applied to every AI plan."""

    min_heat_temp: float = DEFAULT_MIN_HEAT_TEMP
    max_heat_temp: float = DEFAULT_MAX_HEAT_TEMP
    min_cool_temp: float = DEFAULT_MIN_COOL_TEMP
    max_cool_temp: float = DEFAULT_MAX_COOL_TEMP
    min_deadband: float = MIN_DEADBAND_F
    max_ai_delta_f: float = DEFAULT_MAX_AI_DELTA_F


@dataclass(slots=True)
class ValidationResult:
    """Output of guardrail validation for a space's time window."""

    blocks: list[ScheduleBlock]
    used_fallback: bool = False
    warnings: list[str] | None = None
    fallback_reason: str | None = None


def _clamp(val: float, low: float, high: float) -> float:
    return max(low, min(high, val))


def _find_baseline_reference(
    block: ScheduleBlock, baseline_blocks: list[ScheduleBlock]
) -> ScheduleBlock | None:
    """Return the baseline block with the largest time overlap against `block`."""
    best: ScheduleBlock | None = None
    best_overlap = 0
    for base in baseline_blocks:
        overlap = min(block.end_min, base.end_min) - max(
            block.start_min, base.start_min
        )
        if overlap > best_overlap:
            best_overlap = overlap
            best = base
    return best


def _coerce_supported_mode(
    mode: str,
    baseline_ref: ScheduleBlock | None,
    supported_hvac_modes: set[str] | None,
    outdoor_temp_f: float | None,
    warnings: list[str],
) -> str:
    """Ensure the block's hvac_mode is supported by the target climate entity."""
    if not supported_hvac_modes or mode in supported_hvac_modes:
        return mode

    # Prefer the overlapping baseline block's mode if supported
    if baseline_ref and baseline_ref.hvac_mode in supported_hvac_modes:
        warnings.append(
            f"Coerced unsupported mode '{mode}' -> '{baseline_ref.hvac_mode}' (baseline)"
        )
        return baseline_ref.hvac_mode

    # Pick sensible fallback from supported modes based on regime
    is_heating_regime = (
        outdoor_temp_f is None or outdoor_temp_f < HEATING_REGIME_OUTDOOR_THRESHOLD_F
    )
    preference = (
        ("heat_cool", "heat", "cool", "off")
        if is_heating_regime
        else ("heat_cool", "cool", "heat", "off")
    )
    for candidate in preference:
        if candidate in supported_hvac_modes:
            warnings.append(f"Coerced unsupported mode '{mode}' -> '{candidate}'")
            return candidate
    return mode


def _enforce_block_bounds(
    block: ScheduleBlock,
    baseline_ref: ScheduleBlock | None,
    config: GuardrailConfig,
    outdoor_temp_f: float | None,
    warnings: list[str],
    supported_hvac_modes: set[str] | None = None,
) -> ScheduleBlock:
    """Clamp delta vs baseline, enforce hard bounds, and apply directed deadband."""
    mode = _coerce_supported_mode(
        block.hvac_mode, baseline_ref, supported_hvac_modes, outdoor_temp_f, warnings
    )
    if mode == "off":
        return ScheduleBlock(
            start_min=block.start_min,
            end_min=block.end_min,
            hvac_mode="off",
            heat_to=None,
            cool_to=None,
        )

    heat = block.heat_to
    cool = block.cool_to

    # Fill missing setpoint from baseline if needed
    if mode in ("heat_cool", "heat") and heat is None:
        heat = (
            baseline_ref.heat_to
            if baseline_ref and baseline_ref.heat_to is not None
            else config.min_heat_temp
        )
    if mode in ("heat_cool", "cool") and cool is None:
        cool = (
            baseline_ref.cool_to
            if baseline_ref and baseline_ref.cool_to is not None
            else config.max_cool_temp
        )

    # Strip unused setpoint on single-mode entities
    if mode == "heat":
        cool = None
    elif mode == "cool":
        heat = None

    # 1. Clamp deviation vs active baseline within +/- max_ai_delta_f
    if baseline_ref is not None:
        if heat is not None and baseline_ref.heat_to is not None:
            clamped_h = _clamp(
                heat,
                baseline_ref.heat_to - config.max_ai_delta_f,
                baseline_ref.heat_to + config.max_ai_delta_f,
            )
            if clamped_h != heat:
                warnings.append(
                    f"Clamped heat_to {heat:.1f} -> {clamped_h:.1f} (delta limit ±{config.max_ai_delta_f:.1f})"
                )
                heat = clamped_h
        if cool is not None and baseline_ref.cool_to is not None:
            clamped_c = _clamp(
                cool,
                baseline_ref.cool_to - config.max_ai_delta_f,
                baseline_ref.cool_to + config.max_ai_delta_f,
            )
            if clamped_c != cool:
                warnings.append(
                    f"Clamped cool_to {cool:.1f} -> {clamped_c:.1f} (delta limit ±{config.max_ai_delta_f:.1f})"
                )
                cool = clamped_c

    # 2. Clamp to hard safety bounds
    if heat is not None:
        clamped_h = _clamp(heat, config.min_heat_temp, config.max_heat_temp)
        if clamped_h != heat:
            warnings.append(
                f"Clamped heat_to {heat:.1f} -> {clamped_h:.1f} (hard bounds)"
            )
            heat = clamped_h
    if cool is not None:
        clamped_c = _clamp(cool, config.min_cool_temp, config.max_cool_temp)
        if clamped_c != cool:
            warnings.append(
                f"Clamped cool_to {cool:.1f} -> {clamped_c:.1f} (hard bounds)"
            )
            cool = clamped_c

    # 3. Directed deadband enforcement for heat_cool
    if mode == "heat_cool" and heat is not None and cool is not None:
        if cool - heat < config.min_deadband:
            is_heating_regime = (
                outdoor_temp_f is None
                or outdoor_temp_f < HEATING_REGIME_OUTDOOR_THRESHOLD_F
            )
            if is_heating_regime:
                # Cold outside: preserve AI heat_to, push cool_to upward
                cool = min(config.max_cool_temp, heat + config.min_deadband)
                if cool - heat < config.min_deadband:
                    heat = max(config.min_heat_temp, cool - config.min_deadband)
            else:
                # Warm outside: preserve AI cool_to, push heat_to downward
                heat = max(config.min_heat_temp, cool - config.min_deadband)
                if cool - heat < config.min_deadband:
                    cool = min(config.max_cool_temp, heat + config.min_deadband)
            warnings.append(
                f"Enforced {config.min_deadband:.1f}°F deadband -> heat={heat:.1f}, cool={cool:.1f}"
            )

    return ScheduleBlock(
        start_min=block.start_min,
        end_min=block.end_min,
        hvac_mode=mode,
        heat_to=round(heat, 1) if heat is not None else None,
        cool_to=round(cool, 1) if cool is not None else None,
    )


def validate_and_clamp_blocks(
    ai_raw_blocks: list[dict[str, Any]] | None,
    baseline_blocks: list[ScheduleBlock],
    window_start_min: int,
    window_end_min: int,
    config: GuardrailConfig,
    outdoor_temp_f: float | None = None,
    supported_hvac_modes: set[str] | None = None,
) -> ValidationResult:
    """Validate AI-proposed schedule blocks; fall back cleanly to baseline on structural error."""
    baseline_window = slice_blocks_to_window(
        baseline_blocks, window_start_min, window_end_min
    )

    if not ai_raw_blocks:
        return ValidationResult(
            blocks=baseline_window,
            used_fallback=True,
            fallback_reason="AI returned empty or missing schedule blocks",
        )

    try:
        parsed = parse_ha_blocks(ai_raw_blocks)
    except (ValueError, KeyError, TypeError) as err:
        return ValidationResult(
            blocks=baseline_window,
            used_fallback=True,
            fallback_reason=f"Malformed AI schedule block: {err}",
        )

    # Structural check: exact contiguous coverage of [window_start_min, window_end_min] with no overlaps or gaps
    if parsed[0].start_min != window_start_min:
        return ValidationResult(
            blocks=baseline_window,
            used_fallback=True,
            fallback_reason=(
                f"AI blocks start at {parsed[0].start_min}m, expected {window_start_min}m"
            ),
        )
    if parsed[-1].end_min != window_end_min:
        return ValidationResult(
            blocks=baseline_window,
            used_fallback=True,
            fallback_reason=(
                f"AI blocks end at {parsed[-1].end_min}m, expected {window_end_min}m"
            ),
        )
    for prev, curr in itertools.pairwise(parsed):
        if curr.start_min < prev.end_min:
            return ValidationResult(
                blocks=baseline_window,
                used_fallback=True,
                fallback_reason=(
                    f"Overlapping AI blocks at {prev.end_min}m / {curr.start_min}m"
                ),
            )
        if curr.start_min > prev.end_min:
            return ValidationResult(
                blocks=baseline_window,
                used_fallback=True,
                fallback_reason=(
                    f"Gap in AI blocks between {prev.end_min}m and {curr.start_min}m"
                ),
            )

    warnings: list[str] = []
    clamped: list[ScheduleBlock] = []
    for blk in parsed:
        ref = _find_baseline_reference(blk, baseline_window)
        clamped.append(
            _enforce_block_bounds(
                blk, ref, config, outdoor_temp_f, warnings, supported_hvac_modes
            )
        )

    return ValidationResult(
        blocks=clamped,
        used_fallback=False,
        warnings=warnings or None,
    )


def validate_comfort_boost(raw_boost: dict[str, Any] | None) -> dict[str, Any] | None:
    """Validate and clamp an optional AI comfort_boost proposal."""
    if not raw_boost or not isinstance(raw_boost, dict):
        return None
    feeling = str(raw_boost.get("feeling", "")).lower()
    if feeling not in ("too_cold", "too_hot"):
        return None
    try:
        delta_f = float(raw_boost.get("delta_f", 2.0))
        duration = int(raw_boost.get("duration_minutes", 60))
    except (ValueError, TypeError):
        return None
    return {
        "feeling": feeling,
        "delta_f": round(_clamp(abs(delta_f), 0.5, 4.0), 1),
        "duration_minutes": int(_clamp(duration, 15, 180)),
        "decay": True,
    }
