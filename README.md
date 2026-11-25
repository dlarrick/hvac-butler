# HVAC Butler

**HVAC Butler uses AI reasoning to intelligently manage your home's heating and cooling — balancing comfort and economics the way an attentive butler would.**

Static thermostat schedules don't know that a howling windstorm makes 68°F feel drafty, that tomorrow morning's deep freeze needs an earlier warm-up, that nobody is home today because the alarm is armed away, or that someone just walked into a chilly guest room. HVAC Butler brings real-world context into Home Assistant climate control without giving up deterministic safety or local reliability.

## How It Works

1. **Nightly Planning (9:00 PM):** Reviews tomorrow's weather forecast, your occupied/unoccupied baseline routines, and persistent notes about your house and rooms (*"south-facing windows"*, *"woodstove in living room"*, *"dogs stay downstairs"*) to craft a tailored schedule for tonight and tomorrow.
2. **Attentive Intraday Adjustments:** Stays quiet during normal operation and wakes up only when reality changes — alarm armed away/disarmed or sustained presence/vacancy in a room — updating the remaining day's schedule and (when supported) issuing a gentle temporary comfort boost.
3. **Native Home Assistant Schedules & Shadow Mode:** Writes directly to native Home Assistant `schedule.*` helpers (`schedule.<space>_butler`) so you can inspect the Butler's proposed plan alongside your existing schedules before ever handing over control.
4. **Trust, but Verify:** Every AI proposal passes through deterministic Python guardrails that enforce hard temperature bounds, deadband separation, maximum deviation limits from your baselines, and automatic fallback to your baseline schedule if anything looks off.

## Dashboard Card

HVAC Butler automatically registers the **`custom:hvac-butler-card`** Lovelace card — add it from the Home Assistant card picker or with minimal YAML:

```yaml
type: custom:hvac-butler-card
```

- **Space-Scoped Activity Timeline:** Pick any configured space from the header dropdown to inspect up to 7 days of Butler decisions (newest first), or click **Run Plan** to trigger an on-demand macro-plan.
- **Keyframes & Noise Reduction:** Daily `Plan` entries always stay visible as timeline anchors, while consecutive unchanged intraday checks automatically collapse into a single expandable row.
- **Deterministic Trigger Badges:** Each entry's primary badge (`Plan`, `Presence`, `Arm/Disarm`) is 100% deterministic and indicates **what triggered the evaluation**, not an AI result. Secondary badges (`Adjusted`, `Comfort Boost`, `Fallback`) reflect deterministic actions actually taken.
- **Full-Context Detail Modal:** Click any row to read the AI's verbatim commentary for the selected space (with before/after schedule diffs), plus the rest of the home's commentary from that same run and collapsible technical details.

## Compatibility

- **Bring Your Own AI Provider:** Uses Home Assistant's native `ai_task` integration (Gemini, OpenAI, Anthropic, Ollama, etc.) — no separate API keys to manage.
- **Works Standalone:** Compatible with standard Home Assistant `climate.*` entities and native `schedule.*` helpers.
- **Progressive Enhancement with [HVAC Fusion](https://github.com/dlarrick/hvac-fusion):** Automatically discovers `hvac_fusion` spaces and dispatches decaying temporary comfort boosts when a space is actively following the `"Butler"` preset.

## Planned Enhancements

- **Calendar Interpretation:** Read household calendars to anticipate events and travel (*"Cocktail party on the 12th"*, *"Maui trip 2/4–2/11; housesitter in guest room"*).
- **Rich Entity-Aware Space Descriptions:** Interpret natural-language room notes tied to Home Assistant entities (*"Guest room is used as a home office when Todd's tracked location is Home"*).
- **Day-Specific Natural-Language Instructions:** Give the Butler one-off instructions for a specific day or night (*"Guest Thursday night"*, *"Working from home Tuesday"*).
- **Weather-Scaled Adaptive Setbacks:** Automatically scale unoccupied setback depth with outdoor severity — deeper setbacks in extreme cold or heat where savings matter most, and shallower setbacks in mild weather for quicker recovery.
- **Thermal Envelope Calibration:** Learn your home's true thermal characteristics over time from Home Assistant energy and temperature history (for use with HVAC Fusion or standalone tuning).
