"""Sensor platform for Smart Garage integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SmartGarageConfigEntry
from .const import (
    ATTR_CLOSED_SENSOR,
    ATTR_MOTION_DURATION,
    ATTR_OPEN_SENSOR,
    ATTR_TOGGLE_ENTITY,
    DOMAIN,
)
from .garage import SmartGarageStateTracker

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartGarageConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Smart Garage sensor from a config entry."""
    async_add_entities([SmartGarageSensor(entry.runtime_data)])


class SmartGarageSensor(SensorEntity):
    """A read-only view of a SmartGarageStateTracker's derived state."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_translation_key = "state"

    def __init__(self, tracker: SmartGarageStateTracker) -> None:
        """Initialize the sensor."""
        self._tracker = tracker
        slug = tracker.name.lower().replace(" ", "_")
        self._attr_unique_id = f"{DOMAIN}_{slug}_state"
        self.entity_id = f"sensor.{DOMAIN}_{slug}_state"

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self._tracker.signal, self._handle_update)
        )
        self._refresh()

    @callback
    def _handle_update(self) -> None:
        self._refresh()
        self.async_write_ha_state()

    def _refresh(self) -> None:
        self._attr_native_value = self._tracker.state
        self._attr_available = self._tracker.available

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this garage door."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._tracker.entry.entry_id)},
            name=self._tracker.name,
            manufacturer="Smart Garage",
            model="Garage Door",
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            ATTR_OPEN_SENSOR: self._tracker.open_sensor,
            ATTR_CLOSED_SENSOR: self._tracker.closed_sensor,
            ATTR_TOGGLE_ENTITY: self._tracker.toggle_entity,
            ATTR_MOTION_DURATION: self._tracker.motion_duration,
        }
