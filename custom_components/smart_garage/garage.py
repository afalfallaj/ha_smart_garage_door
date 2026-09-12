"""Shared state tracking for a single Smart Garage Door config entry.

Owns the sensor-fusion logic (open/closed binary sensors + toggle entity) so the
sensor and cover entities are simple, independent views over one signal instead of
depending on each other's existence at startup.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.const import STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_CLOSED_SENSOR,
    ATTR_MOTION_DURATION,
    ATTR_OPEN_SENSOR,
    ATTR_SENSOR_DEBOUNCE_MS,
    ATTR_TOGGLE_ENTITY,
    DEFAULT_MOTION_DURATION,
    DEFAULT_SENSOR_DEBOUNCE_MS,
    STATE_CLOSED,
    STATE_CLOSING,
    STATE_OPEN,
    STATE_OPENING,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)


class SmartGarageStateTracker:
    """Derives and broadcasts one garage door's state."""

    def __init__(self, hass: HomeAssistant, entry: "ConfigEntry") -> None:
        """Initialize the tracker."""
        self.hass = hass
        self.entry = entry
        self.name: str = entry.data["name"]
        self.open_sensor: str = entry.data[ATTR_OPEN_SENSOR]
        self.closed_sensor: str = entry.data[ATTR_CLOSED_SENSOR]
        self.toggle_entity: str = entry.data[ATTR_TOGGLE_ENTITY]

        self.signal = f"smart_garage_update_{entry.entry_id}"

        self.state: str = STATE_UNAVAILABLE
        self.available: bool = False

        self._previous_state: str | None = None
        self._motion_start_time = None
        self._motion_timeout_unsub: Any = None
        self._debounce_unsub: Any = None
        self._unsub_state_change: Any = None

    @property
    def motion_duration(self) -> int:
        """Return the configured motion duration in seconds."""
        return self.entry.options.get(
            ATTR_MOTION_DURATION,
            self.entry.data.get(ATTR_MOTION_DURATION, DEFAULT_MOTION_DURATION),
        )

    @property
    def sensor_debounce_ms(self) -> int:
        """Return the configured sensor debounce in milliseconds."""
        return self.entry.options.get(
            ATTR_SENSOR_DEBOUNCE_MS,
            self.entry.data.get(ATTR_SENSOR_DEBOUNCE_MS, DEFAULT_SENSOR_DEBOUNCE_MS),
        )

    @callback
    def async_setup(self) -> None:
        """Start tracking the underlying entities and compute the initial state."""
        self._unsub_state_change = async_track_state_change_event(
            self.hass,
            [self.open_sensor, self.closed_sensor, self.toggle_entity],
            self._handle_state_change,
        )
        self._update_state()

    @callback
    def async_unload(self) -> None:
        """Stop tracking and cancel any pending timers."""
        if self._unsub_state_change:
            self._unsub_state_change()
            self._unsub_state_change = None
        self._clear_debounce()
        self._clear_motion_tracking()

    @callback
    def _handle_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Debounce and react to a tracked entity's state change."""
        self._clear_debounce()

        @callback
        def _run_update(_now: Any = None) -> None:
            self._debounce_unsub = None
            self._update_state()

        self._debounce_unsub = async_call_later(
            self.hass, self.sensor_debounce_ms / 1000.0, _run_update
        )

    def _clear_debounce(self) -> None:
        if self._debounce_unsub:
            self._debounce_unsub()
            self._debounce_unsub = None

    @callback
    def _update_state(self) -> None:
        """Recompute the derived state and notify listeners if it changed."""
        open_sensor_state = self.hass.states.get(self.open_sensor)
        closed_sensor_state = self.hass.states.get(self.closed_sensor)
        toggle_entity_state = self.hass.states.get(self.toggle_entity)

        if not open_sensor_state or not closed_sensor_state or not toggle_entity_state:
            _LOGGER.debug(
                "Garage '%s': waiting on entities open=%s closed=%s toggle=%s",
                self.name,
                bool(open_sensor_state),
                bool(closed_sensor_state),
                bool(toggle_entity_state),
            )
            self.state = STATE_UNAVAILABLE
            self.available = False
            async_dispatcher_send(self.hass, self.signal)
            return

        if (
            open_sensor_state.state == STATE_UNAVAILABLE
            or closed_sensor_state.state == STATE_UNAVAILABLE
        ):
            self.state = STATE_UNAVAILABLE
            self.available = False
            async_dispatcher_send(self.hass, self.signal)
            return

        self.available = True

        if self.state != STATE_UNAVAILABLE:
            self._previous_state = self.state

        open_sensor_on = open_sensor_state.state == STATE_ON
        closed_sensor_on = closed_sensor_state.state == STATE_ON
        both_sensors_off = not open_sensor_on and not closed_sensor_on

        was_in_definite_state = self._previous_state in (STATE_OPEN, STATE_CLOSED)
        if both_sensors_off and was_in_definite_state and not self._motion_start_time:
            self._motion_start_time = dt_util.utcnow()
            _LOGGER.debug(
                "Motion started for '%s': previous_state=%s", self.name, self._previous_state
            )
            self._schedule_motion_timeout()

        new_state = self._determine_garage_state(open_sensor_on, closed_sensor_on, both_sensors_off)

        if new_state in (STATE_OPEN, STATE_CLOSED):
            self._clear_motion_tracking()

        self.state = new_state
        _LOGGER.debug("Garage '%s' determined state: %s", self.name, new_state)
        async_dispatcher_send(self.hass, self.signal)

    def _determine_garage_state(
        self, open_sensor_on: bool, closed_sensor_on: bool, both_sensors_off: bool
    ) -> str:
        """Determine garage door state (see AGENTS.md for the full priority rationale)."""
        # 1. Both sensors on - impossible state
        if open_sensor_on and closed_sensor_on:
            return STATE_UNAVAILABLE

        # 2. Open sensor on - door is open
        if open_sensor_on:
            return STATE_OPEN

        # 3. Closed sensor on - door is closed
        if closed_sensor_on:
            return STATE_CLOSED

        # 4. Both sensors off + previous state was open + in motion = closing
        if both_sensors_off and self._previous_state == STATE_OPEN and self._is_in_motion():
            return STATE_CLOSING

        # 5. Both sensors off + previous state was closed + in motion = opening
        if both_sensors_off and self._previous_state == STATE_CLOSED and self._is_in_motion():
            return STATE_OPENING

        # 6. Failed transitions: motion expired without reaching open/closed
        if both_sensors_off and self._previous_state == STATE_OPENING and not self._is_in_motion():
            _LOGGER.warning(
                "Garage '%s' was opening but motion expired without reaching open state",
                self.name,
            )
            return STATE_UNAVAILABLE

        if both_sensors_off and self._previous_state == STATE_CLOSING and not self._is_in_motion():
            _LOGGER.warning(
                "Garage '%s' was closing but motion expired without reaching closed state",
                self.name,
            )
            return STATE_UNAVAILABLE

        # 7. Both sensors off + previous stable state + not in motion = hold it
        if (
            both_sensors_off
            and self._previous_state in (STATE_OPEN, STATE_CLOSED)
            and not self._is_in_motion()
        ):
            return self._previous_state

        # 8. Still transitioning and still within the motion window = hold it
        if (
            both_sensors_off
            and self._previous_state in (STATE_OPENING, STATE_CLOSING)
            and self._is_in_motion()
        ):
            return self._previous_state

        # 9. Everything else
        return STATE_UNAVAILABLE

    def _is_in_motion(self) -> bool:
        """Return whether the door is still within its motion window."""
        if not self._motion_start_time:
            return False

        elapsed = (dt_util.utcnow() - self._motion_start_time).total_seconds()
        within_duration = elapsed < self.motion_duration

        if not within_duration:
            self._clear_motion_tracking()

        return within_duration

    def _schedule_motion_timeout(self) -> None:
        """Schedule a forced re-check once the motion window expires."""
        if self._motion_timeout_unsub:
            self._motion_timeout_unsub()

        @callback
        def _check_motion_timeout(_now: Any) -> None:
            self._motion_timeout_unsub = None
            self._update_state()

        self._motion_timeout_unsub = async_call_later(
            self.hass, self.motion_duration, _check_motion_timeout
        )

    def _clear_motion_tracking(self) -> None:
        self._motion_start_time = None
        if self._motion_timeout_unsub:
            self._motion_timeout_unsub()
            self._motion_timeout_unsub = None
