# Agent Instructions & Operational Constraints — HVAC Butler

## Project Overview
Start by reading [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md) for repository layout, module responsibilities, and test commands.

## Architectural Boundaries
- **Tier 3 Only:** `hvac-butler` operates strictly at the human context, weather, and occupancy intent layer. It must never implement dual-fuel physics, COP math, or hardware interlocks (those belong to Tier 1 `hvac-crossover` / Tier 2 `hvac-fusion`).
- **Native `schedule.*` Entities Only:** Never subclass Home Assistant's `Schedule` entity. Read native schedules via `schedule.get_schedule` and create/update native storage schedules via Home Assistant's `ScheduleStorageCollection`.
- **Integration-Agnostic with Progressive Enhancement:** Must work with standard HA `climate.*` entities, with automatic progressive enhancement (comfort boost, `schedule_editing` lock check, auto-discovery of spaces) when `hvac_fusion` is installed.

## Home Assistant Integration Invariants
- **Virtual Entity Polling Invariant:** All sensor/button entities must declare `_attr_should_poll = False`.
- **Translation Synchronization Invariant:** `strings.json` and `translations/en.json` must remain 100% identical at all times.

## Prompt Engineering Philosophy
- **Goals Over Prescriptions:** Lead prompts with clear goals and priority order; let the model reason over `Context` instead of prescribing scenario trees, numeric weather thresholds, or truth tables.
- **Domain Meaning Over Enumeration:** Do not enumerate self-describing JSON inputs, subfields, or trigger types in prose. Document only non-obvious *domain meaning* (authority/priority, gotchas, blind spots, physical/system mechanics) and strict output/guardrail contracts.

## Bug Handling Workflow
When presented with a bug:
1. **Diagnose** root cause.
2. **Present** findings clearly.
3. **Propose** fix options and wait for explicit user approval before editing code.
