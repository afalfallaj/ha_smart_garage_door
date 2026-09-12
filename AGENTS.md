# Smart Garage Door — Project Summary

A Home Assistant custom component (HACS integration, domain `smart_garage`) that turns two binary
door sensors + a switch/light relay into a proper `cover.*` entity with correct open/closed/opening/closing
states. Built for Shelly-style relays that expose their output as a `light` entity.

Config-entry (UI) setup only — YAML configuration was removed in v2.0.0 (it depended on
`hass.helpers.discovery.async_load_platform`, which HA core removed in 2024.11).

## Layout

- `custom_components/smart_garage/`
  - `__init__.py` — sets up the config entry: builds a `SmartGarageStateTracker`, stores it on
    `entry.runtime_data`, forwards to the `sensor`/`cover` platforms, and reloads the entry when
    options change.
  - `garage.py` — `SmartGarageStateTracker`: the state machine. Tracks the open/closed binary
    sensors + toggle entity, derives `open|closed|opening|closing|unavailable`, and broadcasts
    changes via `async_dispatcher_send` on a per-entry signal. Owned once per config entry — not
    per platform.
  - `sensor.py` / `cover.py` — thin, independent views over the tracker. Each subscribes to the
    tracker's dispatcher signal in `async_added_to_hass`; neither depends on the other existing or
    on any startup retry/backoff loop (that polling anti-pattern was removed in the v2.0.0
    refactor — see below).
  - `config_flow.py` — UI config flow: initial setup (`async_step_user`), editing an existing
    garage's sensors/toggle entity (`async_step_reconfigure`), and tunable options — motion
    duration, sensor debounce — via `SmartGarageOptionsFlow`.
  - `const.py` — domain, attribute keys, state strings, defaults (`DEFAULT_MOTION_DURATION=35s`,
    `DEFAULT_SENSOR_DEBOUNCE_MS=300ms`).
  - `strings.json` + `translations/en.json` — must be kept in sync manually; HA does not
    auto-generate a custom integration's `translations/` from `strings.json`.
  - `manifest.json` — `quality_scale: custom`, `loggers: [...]` for the "Enable debug logging" UI
    toggle.
  - `brand/` — icon/logo assets HACS/HA use instead of falling back to a generic icon
    (`icon.png`, `icon@2x.png`, `logo.png`, `logo.svg`, `logo@2x.png`, `dark_*` variants — same set
    as `ha_gimdow_ble`). Rendered from the open-source `mdi:garage` glyph (Apache 2.0, see
    `brand/SOURCE.md`) — not dedicated artwork, swap in a real logo whenever you want one.
- `tests/` — stubs `homeassistant` via `sys.modules` (see `tests/conftest.py`) instead of pulling in
  `pytest-homeassistant-custom-component`, so tests don't need to track HA core's release cadence.
  Covers `garage.py`'s state machine and `config_flow.py`'s validation/flow steps.
- `.github/workflows/validate.yml` — hassfest + HACS validation + `pytest` on push/PR.
- `README.md` — user-facing docs. Treat as the source of truth for documented behavior.

## Core state machine (garage.py)

Inputs: `open_sensor` (binary_sensor), `closed_sensor` (binary_sensor), previous derived state, and a
"motion start" timestamp set whenever both sensors go off right after being in a definite `open`/`closed` state.

Priority order in `_determine_garage_state`:
1. Both sensors ON → `unavailable` (impossible/malfunction)
2. Open sensor ON → `open`
3. Closed sensor ON → `closed`
4. Both OFF, was `open`, within `motion_duration` → `closing`
5. Both OFF, was `closed`, within `motion_duration` → `opening`
6. Both OFF, was `opening`/`closing` but motion timer expired without reaching a definite state → `unavailable`
7. Both OFF, was a stable state, not in motion → hold the previous stable state (handles transient sensor blips)
8. Both OFF, still mid-transition and still within the motion window → hold `opening`/`closing`
9. Anything else → `unavailable`

Motion timing is enforced two ways: lazily via `_is_in_motion()` (checked whenever state is recomputed) and
proactively via a scheduled `async_call_later` (`_schedule_motion_timeout`), so a door that never reports a
definite end sensor still flips to `unavailable` after `motion_duration` seconds even with no further sensor events.

State changes on the tracked entities are debounced (`sensor_debounce_ms`, default 300ms, configurable via
the options flow) via `async_call_later` before `_update_state` runs — added specifically to avoid reacting
to sensor chatter/flicker.

## v2.0.0 architecture change (from the deprecation/standards audit)

The original design had `sensor.py` own this state machine directly and `cover.py` poll for the
sensor *entity* to exist (manual `asyncio.sleep` retry loops with backoff, plus a periodic
availability check) — an ordering dependency between platforms. That's gone: the tracker is now
created once in `async_setup_entry` and shared via `entry.runtime_data`, and both entities are pure
reactive views over it. If you're tempted to add polling/retry logic back for a "not found yet"
problem, it's almost certainly solvable by moving the shared logic further up into the tracker
instead.

## Recent history / trajectory

Git log (pre-v2.0.0) shows heavy iteration specifically on the state-detection logic (many "improve
sensor state" commits) before settling on the current 9-branch priority list, followed by a
debounce-timer addition to smooth out noisy sensor input. If asked to touch state logic again,
assume correctness here has been hard-won through trial and error against real (noisy) hardware —
prefer additive/targeted changes over rewrites, and check `_determine_garage_state`'s comments for
the reasoning behind each branch.

## Requirements

Home Assistant 2025.8.0+ (see `hacs.json`), no external Python dependencies
(`requirements: []` in manifest).
