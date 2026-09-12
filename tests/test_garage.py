"""Tests for SmartGarageStateTracker's derived-state logic (custom_components/smart_garage/garage.py).

Covers the 9-branch priority logic that CLAUDE.md/AGENTS.md calls out as hard-won
through iteration against real hardware, so a refactor doesn't silently change behavior.
"""
from __future__ import annotations

from datetime import timedelta

from custom_components.smart_garage.garage import SmartGarageStateTracker

from conftest import _ConfigEntry, _HomeAssistant  # type: ignore[import]

OPEN_SENSOR = "binary_sensor.garage_open"
CLOSED_SENSOR = "binary_sensor.garage_closed"
TOGGLE_ENTITY = "switch.garage_opener"


def _make_tracker(motion_duration: int = 35) -> SmartGarageStateTracker:
    hass = _HomeAssistant()
    entry = _ConfigEntry(
        data={
            "name": "Test Garage",
            "open_sensor": OPEN_SENSOR,
            "closed_sensor": CLOSED_SENSOR,
            "toggle_entity": TOGGLE_ENTITY,
            "motion_duration": motion_duration,
        }
    )
    tracker = SmartGarageStateTracker(hass, entry)
    # All three tracked entities must exist for the tracker to be "available".
    hass.states.set(TOGGLE_ENTITY, "off")
    return tracker


def test_open_sensor_on_is_open() -> None:
    tracker = _make_tracker()
    tracker.hass.states.set(OPEN_SENSOR, "on")
    tracker.hass.states.set(CLOSED_SENSOR, "off")

    tracker._update_state()

    assert tracker.state == "open"
    assert tracker.available is True


def test_closed_sensor_on_is_closed() -> None:
    tracker = _make_tracker()
    tracker.hass.states.set(OPEN_SENSOR, "off")
    tracker.hass.states.set(CLOSED_SENSOR, "on")

    tracker._update_state()

    assert tracker.state == "closed"


def test_both_sensors_on_is_unavailable() -> None:
    tracker = _make_tracker()
    tracker.hass.states.set(OPEN_SENSOR, "on")
    tracker.hass.states.set(CLOSED_SENSOR, "on")

    tracker._update_state()

    assert tracker.state == "unavailable"


def test_missing_entity_is_unavailable() -> None:
    tracker = _make_tracker()
    tracker.hass.states.set(OPEN_SENSOR, "off")
    # closed_sensor state never set -> missing

    tracker._update_state()

    assert tracker.state == "unavailable"
    assert tracker.available is False


def test_motion_from_open_reports_closing_then_settles_closed() -> None:
    tracker = _make_tracker()

    tracker.hass.states.set(OPEN_SENSOR, "on")
    tracker.hass.states.set(CLOSED_SENSOR, "off")
    tracker._update_state()
    assert tracker.state == "open"

    tracker.hass.states.set(OPEN_SENSOR, "off")
    tracker._update_state()
    assert tracker.state == "closing"

    tracker.hass.states.set(CLOSED_SENSOR, "on")
    tracker._update_state()
    assert tracker.state == "closed"
    assert tracker._motion_start_time is None


def test_motion_from_closed_reports_opening() -> None:
    tracker = _make_tracker()

    tracker.hass.states.set(OPEN_SENSOR, "off")
    tracker.hass.states.set(CLOSED_SENSOR, "on")
    tracker._update_state()
    assert tracker.state == "closed"

    tracker.hass.states.set(CLOSED_SENSOR, "off")
    tracker._update_state()
    assert tracker.state == "opening"


def test_motion_timeout_without_definite_reading_goes_unavailable() -> None:
    tracker = _make_tracker(motion_duration=35)

    tracker.hass.states.set(OPEN_SENSOR, "on")
    tracker.hass.states.set(CLOSED_SENSOR, "off")
    tracker._update_state()

    tracker.hass.states.set(OPEN_SENSOR, "off")
    tracker._update_state()
    assert tracker.state == "closing"

    # Simulate the motion window having expired without a sensor ever firing.
    tracker._motion_start_time = tracker._motion_start_time - timedelta(
        seconds=tracker.motion_duration + 1
    )
    tracker._update_state()

    assert tracker.state == "unavailable"
