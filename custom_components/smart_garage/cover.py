"""Cover platform for Smart Garage integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.const import SERVICE_TOGGLE
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
    ICON_GARAGE,
    ICON_GARAGE_ALERT,
    ICON_GARAGE_OPEN,
    STATE_CLOSED,
    STATE_CLOSING,
    STATE_OPEN,
    STATE_OPENING,
)
from .garage import SmartGarageStateTracker

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartGarageConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Smart Garage cover from a config entry."""
    async_add_entities([SmartGarageCover(entry.runtime_data)])


class SmartGarageCover(CoverEntity):
    """A controllable view of a SmartGarageStateTracker's derived state."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_name = None
    _attr_device_class = CoverDeviceClass.GARAGE
    _attr_supported_features = (
        CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
    )

    def __init__(self, tracker: SmartGarageStateTracker) -> None:
        """Initialize the cover."""
        self._tracker = tracker
        self._toggle_domain = tracker.toggle_entity.split(".")[0]
        slug = tracker.name.lower().replace(" ", "_")
        self._attr_unique_id = f"{DOMAIN}_{slug}_cover"

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
        self._attr_available = self._tracker.available

    @property
    def is_closed(self) -> bool | None:
        """Return true if cover is closed, else False."""
        if self._tracker.state == STATE_CLOSED:
            return True
        if self._tracker.state == STATE_OPEN:
            return False
        return None

    @property
    def is_opening(self) -> bool:
        """Return true if cover is opening."""
        return self._tracker.state == STATE_OPENING

    @property
    def is_closing(self) -> bool:
        """Return true if cover is closing."""
        return self._tracker.state == STATE_CLOSING

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""
        if self._tracker.state in (STATE_OPENING, STATE_CLOSING):
            return ICON_GARAGE_ALERT
        if self._tracker.state == STATE_OPEN:
            return ICON_GARAGE_OPEN
        return ICON_GARAGE

    async def _call_toggle_service(self) -> None:
        """Toggle the garage door entity (switch or light)."""
        try:
            await self.hass.services.async_call(
                self._toggle_domain,
                SERVICE_TOGGLE,
                {"entity_id": self._tracker.toggle_entity},
                blocking=True,
            )
        except Exception:
            _LOGGER.exception(
                "Failed to call %s.%s for %s",
                self._toggle_domain,
                SERVICE_TOGGLE,
                self._tracker.toggle_entity,
            )

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        if self._tracker.state != STATE_CLOSED:
            _LOGGER.warning(
                "Cannot open %s: current state is %s, expected %s",
                self._tracker.name,
                self._tracker.state,
                STATE_CLOSED,
            )
            return
        await self._call_toggle_service()

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        if self._tracker.state != STATE_OPEN:
            _LOGGER.warning(
                "Cannot close %s: current state is %s, expected %s",
                self._tracker.name,
                self._tracker.state,
                STATE_OPEN,
            )
            return
        await self._call_toggle_service()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        if self._tracker.state not in (STATE_OPENING, STATE_CLOSING):
            _LOGGER.warning(
                "Cannot stop %s: current state is %s, expected opening or closing",
                self._tracker.name,
                self._tracker.state,
            )
            return
        await self._call_toggle_service()

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
            "toggle_domain": self._toggle_domain,
            "garage_state": self._tracker.state,
        }
