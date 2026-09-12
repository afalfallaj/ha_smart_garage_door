# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## 2.0.0

Deprecation and Home Assistant/HACS standards audit. Breaking changes for anyone still using YAML
configuration.

### Breaking changes

- **Removed YAML configuration support** (`smart_garage:` in `configuration.yaml`). It relied on
  `hass.helpers.discovery.async_load_platform`, which Home Assistant core removed in 2024.11, so it
  no longer worked regardless. Its `opening_duration` schema key also never matched the
  `motion_duration` key the rest of the integration read, so YAML config was doubly broken. Use the
  UI config flow instead (**Settings → Devices & Services → Add Integration**).
- Raised the minimum supported Home Assistant version to 2025.8.0 (see `hacs.json`).

### Added

- **Reconfigure flow**: fix a garage door's name/sensors/toggle entity from the integration entry
  without deleting and re-adding it.
- **Options flow**: edit `motion_duration` and `sensor_debounce_ms` after setup; the entry reloads
  automatically when saved.
- Entity translations (`translation_key`, `has_entity_name`) so entity names follow the device name
  instead of being hardcoded strings.
- `manifest.json` now declares `quality_scale` and `loggers`.
- CI: hassfest + HACS validation + test suite on push/PR (`.github/workflows/validate.yml`).
- A `tests/` suite covering the state-machine logic and config/options/reconfigure flows.

### Changed

- Replaced the sensor↔cover polling/order-dependency (manual `asyncio.sleep` retry loops waiting
  for the other platform's entity to exist) with a single `SmartGarageStateTracker` per config
  entry, stored on `entry.runtime_data` and shared via `async_dispatcher_send`/`async_dispatcher_connect`.
  Neither entity depends on the other existing anymore.
- Replaced manual `hass.loop.call_later`/`async_track_point_in_time` timer bookkeeping with the
  `async_call_later` helper.

## 1.0.0

Initial release: UI + YAML configuration, sensor-derived garage door state, cover entity, debounce
timer for noisy sensors.
