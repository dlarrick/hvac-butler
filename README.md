# HVAC Butler

[![CI](https://github.com/dlarrick/hvac-butler/actions/workflows/test.yml/badge.svg)](https://github.com/dlarrick/hvac-butler/actions/workflows/test.yml)
[![Validate](https://github.com/dlarrick/hvac-butler/actions/workflows/validate.yml/badge.svg)](https://github.com/dlarrick/hvac-butler/actions/workflows/validate.yml)
[![GitHub Release](https://img.shields.io/github/v/release/dlarrick/hvac-butler)](https://github.com/dlarrick/hvac-butler/releases)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/dlarrick/hvac-butler)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**An attentive AI butler for Home Assistant climate control, providing smart adaptive thermostat schedules with strict non-AI guardrails.**

Static thermostat schedules don't know that a howling windstorm makes 68°F feel drafty, that tomorrow morning's deep freeze needs an earlier warm-up, that nobody is home today because the alarm is armed away, or that someone just walked into a chilly guest room. HVAC Butler brings real-world context into Home Assistant climate control without giving up deterministic safety or local reliability.

## How It Works

1. **Nightly Planning (9:00 PM):** Reviews tomorrow's weather forecast, your occupied/unoccupied baseline routines, and persistent notes about your house and rooms (*"south-facing windows"*, *"woodstove in living room"*, *"dogs stay downstairs"*) to craft a tailored schedule for tonight and tomorrow.
2. **Attentive Intraday Adjustments:** Stays quiet during normal operation and wakes up only when reality changes — alarm armed away/disarmed or sustained presence/vacancy in a room — updating the remaining day's schedule and (when supported) issuing a gentle temporary comfort boost.
3. **Native Home Assistant Schedules & Shadow Mode:** Writes directly to native Home Assistant `schedule.*` helpers (`schedule.<space>_butler`) so you can inspect the Butler's proposed plan alongside your existing schedules before ever handing over control.
4. **Trust, but Verify:** Every AI proposal passes through deterministic Python guardrails that enforce hard temperature bounds, deadband separation, maximum deviation limits from your baselines, and automatic fallback to your baseline schedule if anything looks off.

## Dashboard Card

HVAC Butler automatically bundles and registers the **`custom:hvac-butler-card`** Lovelace card (no separate Marketplace frontend install or manual resource entry required). Add it from the Home Assistant card picker (under **By card**, or **By entity** on any HVAC Butler sensor) or with minimal YAML:

```yaml
type: custom:hvac-butler-card
```

- **Activity Timeline (All Spaces or Per-Space):** Switch between **All spaces** and any individual space from the header dropdown to inspect up to 7 days of Butler decisions (newest first), or click **Check Now** / **Run Plan** to trigger an on-demand intraday check or macro-plan.
- **Keyframes & Noise Reduction:** Daily `Plan` entries always stay visible as timeline anchors, while consecutive unchanged intraday checks automatically collapse into a single expandable row.
- **Deterministic Trigger Badges:** Each entry's primary badge (`Plan`, `Presence`, `Arm/Disarm`, `Manual Check`) is 100% deterministic and indicates **what triggered the evaluation**, not an AI result. Secondary badges (`Adjusted`, `Comfort Boost`, `Fallback`) reflect deterministic actions actually taken.
- **Full-Context Detail Modal:** Click any row to read the AI's verbatim commentary for the selected space (with before/after schedule diffs), plus the rest of the home's commentary from that same run and collapsible technical details.

## Installation

### Via Marketplace / HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=dlarrick&repository=hvac-butler&category=integration)

Or manually add as a Custom Repository in Marketplace (formerly HACS):
1. Ensure [Marketplace (HACS)](https://hacs.xyz/) is installed in Home Assistant.
2. In Marketplace, navigate to **Integrations** > **Custom repositories** (top-right menu).
3. Add `https://github.com/dlarrick/hvac-butler` with category **Integration**.
4. Download and restart Home Assistant.

### Manual Installation

Copy the `custom_components/hvac_butler` directory into your Home Assistant `<config_dir>/custom_components/` directory and restart Home Assistant.

## Configuration

HVAC Butler is configured entirely through the Home Assistant UI (**Settings → Devices & Services → Add Integration → HVAC Butler**):

1. **Initial Setup:** Select your Home Assistant `ai_task` entity, `weather` entity, and optional `alarm_control_panel` entity. If [HVAC Fusion](https://github.com/dlarrick/hvac-fusion) is installed, existing spaces are pre-populated automatically.
2. **Global Settings & Safety Bounds (Configure):** Add global house notes and set deterministic temperature limits (`min_heat_temp`, `max_heat_temp`, `min_cool_temp`, `max_cool_temp`, and `max_ai_delta_f`).
3. **Manage Spaces (Configure):** For each space, link its `climate.*` entity, occupied baseline `schedule.*`, optional unoccupied `schedule.*`, default mode, optional presence sensors, and room-specific notes (noting presence sensor types such as PIR motion, mmWave radar, or bed sensors helps the AI interpret occupancy behavior).

HVAC Butler automatically creates and maintains a native `schedule.<space>_butler` helper for each space (and registers a `"Butler"` preset on HVAC Fusion spaces). You can run in **shadow mode** for as long as you like by leaving your thermostats on your existing preset while reviewing Butler's proposed schedules and activity card.

## Compatibility

- **Bring Your Own AI Provider:** Uses Home Assistant's native `ai_task` integration (Gemini, OpenAI, Anthropic, Ollama, etc.) — no separate API keys to manage.
- **Works Standalone:** Compatible with standard Home Assistant `climate.*` entities and native `schedule.*` helpers.

### Better Together with [HVAC Fusion](https://github.com/dlarrick/hvac-fusion)

HVAC Butler works standalone with any Home Assistant climate entity, and pairs seamlessly with **[HVAC Fusion](https://github.com/dlarrick/hvac-fusion)** if you want:

- **Dual-Fuel & Multi-Source Optimization:** Automatically choose between heat pumps, mini-splits, boilers, or furnaces based on real-time COP and utility tariffs.
- **Visual Schedule Viewer & Editor:** Interactive 7-day weekly schedule editor (`custom:schedule-preset-card`) and 24-hour space timeline card (`custom:hvac-fusion-status-card`) for inspecting and editing your baseline and Butler schedules.
- **COP & AFUE-Based Cost Estimates:** Real-time hourly heating cost and baseline savings estimates modeled from your space envelope, equipment profiles, and fuel/electric rates.
- **More Automatic Butler Setup & Control:** HVAC Butler automatically discovers your HVAC Fusion spaces during setup, registers the `"Butler"` preset for you, respects schedule edit locks, and dispatches decaying temporary comfort boosts when someone enters a chilly or warm room.

## Planned Enhancements

- **Calendar Interpretation:** Read household calendars to anticipate events and travel (*"Cocktail party on the 12th"*, *"Maui trip 2/4–2/11; housesitter in guest room"*).
- **Rich Entity-Aware Space Descriptions:** Interpret natural-language room notes tied to Home Assistant entities (*"Guest room is used as a home office when Todd's tracked location is Home"*).
- **Day-Specific Natural-Language Instructions:** Give the Butler one-off instructions for a specific day or night (*"Guest Thursday night"*, *"Working from home Tuesday"*).
- **Weather-Scaled Adaptive Setbacks:** Automatically scale unoccupied setback depth with outdoor severity — deeper setbacks in extreme cold or heat where savings matter most, and shallower setbacks in mild weather for quicker recovery.
- **Thermal Envelope Calibration:** Learn your home's true thermal characteristics over time from Home Assistant energy and temperature history (for use with HVAC Fusion or standalone tuning).
