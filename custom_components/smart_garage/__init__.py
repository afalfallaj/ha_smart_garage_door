"""Smart Garage Door Integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .garage import SmartGarageStateTracker

_LOGGER = logging.getLogger(__name__)

type SmartGarageConfigEntry = ConfigEntry[SmartGarageStateTracker]

# Sensor first, then cover - both are independent views over the tracker, but
# creating the sensor entity first keeps device registration order stable.
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.COVER]


async def async_setup_entry(hass: HomeAssistant, entry: SmartGarageConfigEntry) -> bool:
    """Set up Smart Garage from a config entry."""
    _LOGGER.debug("Setting up Smart Garage from config entry: %s", entry.title)

    tracker = SmartGarageStateTracker(hass, entry)
    tracker.async_setup()
    entry.runtime_data = tracker

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info("Successfully set up Smart Garage: %s", entry.title)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: SmartGarageConfigEntry) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: SmartGarageConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        entry.runtime_data.async_unload()
        _LOGGER.debug("Successfully unloaded Smart Garage: %s", entry.title)
    else:
        _LOGGER.error("Failed to unload Smart Garage: %s", entry.title)

    return unload_ok


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: SmartGarageConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Allow manually deleting any device under this entry from the UI.

    sensor.py/cover.py always recreate today's device via device_info on the next
    reload, so deleting it manually is harmless - including for pre-v2.0.0 leftover
    devices left over from before sensor.py/cover.py shared one device.
    """
    return True
