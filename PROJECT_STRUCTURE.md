# HVAC Butler — Project Structure & Architecture

`hvac-butler` is a Home Assistant custom component (Tier 3 Context & Intent Supervisor) designed to operate independently of Tier 1 (`hvac-crossover`) and Tier 2 (`hvac-fusion`) via standard Home Assistant interfaces (`ai_task.*`, `schedule.*`, `climate.*`, `weather.*`, `alarm_control_panel.*`, `binary_sensor.*`).

## 1. Directory Structure

```text
hvac-butler/
├── .github/
│   └── workflows/
│       ├── test.yml                    # GitHub Actions CI (pre-commit ruff & pytest)
│       └── validate.yml                # GitHub Actions CI (HACS & Home Assistant Hassfest validation)
├── .gitignore
├── .pre-commit-config.yaml             # Pre-commit hooks (ruff lint/format, yaml, whitespace)
├── AGENTS.md                           # AI operational rules and architectural invariants
├── LICENSE                             # MIT License
├── PROJECT_STRUCTURE.md                # Permanent repository layout and architecture map
├── README.md                           # Project overview and planned enhancements
├── hacs.json                           # HACS integration metadata
├── pytest.ini                          # Pytest runner configuration
├── requirements-test.txt               # Test dependencies
├── custom_components/
│   └── hvac_butler/
│       ├── brand/                      # Brand assets (icon.png, icon@2x.png, logo.png, logo@2x.png)
│       ├── frontend/                   # Built Lovelace card bundle (hvac-butler-cards.js)
│       ├── __init__.py                 # Integration entry setup/unload, frontend & WebSocket registration
│       ├── button.py                   # On-demand "Run nightly plan now" & "Run intraday check now" buttons
│       ├── calendar.py                 # Standard HA CalendarEntity (calendar.hvac_butler_notes, delete-only UI)
│       ├── calendar_store.py           # HA Store-backed Butler calendar events, day_notes & boundary triggers
│       ├── config_flow.py              # Initial onboarding & 2-menu Options Flow (with hvac_fusion auto-discovery)
│       ├── const.py                    # Domain constants, config keys, and baked-in defaults
│       ├── coordinator.py              # Nightly 21:00 macro-planner & event-driven intraday coordinator
│       ├── frontend_loader.py          # Content-hashed auto-registration for hvac-butler-cards.js
│       ├── guardrails.py               # Deterministic 'Trust, but Verify' validator & clamping
│       ├── heuristics.py               # Pure-Python deterministic non-AI fallback planners
│       ├── journal.py                  # HA Store-backed 7-day versioned rolling activity journal
│       ├── manifest.json               # Home Assistant integration manifest
│       ├── prompts.py                  # Pure-Python prompt & compact context builders
│       ├── schedule_store.py           # Native HA schedule.get_schedule reader & ScheduleStorageCollection writer
│       ├── schedule_utils.py           # Schedule block parsing, slicing, merging, HA payloads
│       ├── sensor.py                   # Observability sensors (status, daily_plan_summary, intraday_explanation)
│       ├── strings.json                # Source UI translation strings
│       ├── translations/
│       │   └── en.json                 # English UI translation strings (mirrors strings.json)
│       └── websocket_api.py            # WebSocket API (hvac_butler/journal, hvac_butler/run_plan)
├── frontend/                           # Vite + Lit + TypeScript source for custom:hvac-butler-card
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── src/
│       ├── assets/
│       │   └── butler-head.ts          # Extracted circular Butler head avatar data URI
│       ├── components/
│       │   ├── butler-brief-modal.ts   # "Call Butler" interactive Q&A briefing modal
│       │   ├── butler-detail-modal.ts  # Full-context modal (selected space + diffs, other spaces, raw JSON)
│       │   └── butler-timeline-view.ts # Pinned latest Plan bar + scrollable space-scoped timeline
│       ├── utils/
│       │   └── timeline.ts             # Grouping, timestamp formatting, deterministic block diff helpers
│       ├── hvac-butler-card.ts         # Main card shell (compact header, Call Butler, space selector, actions)
│       ├── index.ts                    # Card registration & HA card picker metadata
│       └── types.ts                    # Versioned journal, briefing & HA TypeScript types
└── tests/
    ├── conftest.py                     # Pytest Home Assistant harness fixtures
    ├── test_calendar.py                # Calendar store, CalendarEntity, Call Butler briefing & day_notes tests
    ├── test_config_flow.py             # Onboarding, hvac_fusion pre-population, 2-menu Options Flow tests
    ├── test_coordinator.py             # End-to-end nightly plan, native schedule write, intraday & shadow-mode tests
    ├── test_guardrails.py              # Directed deadband, hard bounds, mode coercion, delta clamp, fallback tests
    ├── test_heuristics.py              # Deterministic non-AI heuristic fallback & LLM outage degradation tests
    ├── test_journal.py                 # Journal persistence, pruning, schema versioning, and WebSocket API tests
    ├── test_prompts.py                 # Forecast condensation, nightly/intraday prompt tests
    └── test_schedule_utils.py          # Time parsing, slicing, merging, 7-day payload tests
```

## 2. Developer Quick Reference

```bash
# Run Python test suite
PYTHONPATH=. ./venv/bin/pytest

# Typecheck and build frontend card bundle
npm --prefix frontend run typecheck && npm --prefix frontend run build
```
