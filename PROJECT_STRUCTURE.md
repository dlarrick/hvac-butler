# HVAC Butler — Project Structure & Architecture

`hvac-butler` is a Home Assistant custom component (Tier 3 Context & Intent Supervisor) designed to operate independently of Tier 1 (`hvac-crossover`) and Tier 2 (`hvac-fusion`) via standard Home Assistant interfaces (`ai_task.*`, `schedule.*`, `climate.*`, `weather.*`, `alarm_control_panel.*`, `binary_sensor.*`).

## 1. Directory Structure

```text
hvac-butler/
├── .gitignore
├── AGENTS.md                           # AI operational rules and architectural invariants
├── LICENSE                             # MIT License
├── PROJECT_STRUCTURE.md                # Permanent repository layout and architecture map
├── README.md                           # Project overview
├── hacs.json                           # HACS integration metadata
├── pytest.ini                          # Pytest runner configuration
├── requirements-test.txt               # Test dependencies
├── custom_components/
│   └── hvac_butler/
│       ├── const.py                    # Domain constants, config keys, and baked-in defaults
│       ├── guardrails.py               # Deterministic 'Trust, but Verify' validator & clamping
│       ├── manifest.json               # Home Assistant integration manifest
│       ├── prompts.py                  # Pure-Python prompt & compact context builders
│       └── schedule_utils.py           # Schedule block parsing, slicing, merging, HA payloads
└── tests/
    ├── test_guardrails.py              # Directed deadband, hard bounds, delta clamp, fallback tests
    ├── test_prompts.py                 # Forecast condensation, nightly/intraday prompt tests
    └── test_schedule_utils.py          # Time parsing, slicing, merging, 7-day payload tests
```

## 2. Developer Quick Reference

```bash
# Run pure-Python core tests
PYTHONPATH=. ./venv/bin/pytest
```
