"""Config flow for Smart Garage Door integration."""
from __future__ import annotations

import logging
from typing import Any, Mapping

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)

from .const import (
    ATTR_CLOSED_SENSOR,
    ATTR_MOTION_DURATION,
    ATTR_OPEN_SENSOR,
    ATTR_SENSOR_DEBOUNCE_MS,
    ATTR_TOGGLE_ENTITY,
    DEFAULT_MOTION_DURATION,
    DEFAULT_SENSOR_DEBOUNCE_MS,
    DOMAIN,
    STEP_RECONFIGURE,
    STEP_USER,
    TOGGLE_DOMAINS,
)

_LOGGER = logging.getLogger(__name__)


def validate_toggle_entity(value: str) -> str:
    """Validate that the toggle entity is a switch or light."""
    entity_id = cv.entity_id(value)
    domain = entity_id.split(".")[0]
    if domain not in TOGGLE_DOMAINS:
        raise vol.Invalid(f"Toggle entity must be from domains: {TOGGLE_DOMAINS}, got: {domain}")
    return entity_id


def _garage_data_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    """Build the name/sensors/toggle schema, prefilled with `defaults` if given."""
    defaults = defaults or {}

    def _marker(key: str, fallback: Any = None) -> vol.Marker:
        if key in defaults:
            return vol.Required(key, default=defaults[key])
        if fallback is not None:
            return vol.Required(key, default=fallback)
        return vol.Required(key)

    return vol.Schema(
        {
            _marker("name", fallback="Garage Door"): TextSelector(),
            _marker(ATTR_OPEN_SENSOR): EntitySelector(
                EntitySelectorConfig(domain="binary_sensor")
            ),
            _marker(ATTR_CLOSED_SENSOR): EntitySelector(
                EntitySelectorConfig(domain="binary_sensor")
            ),
            _marker(ATTR_TOGGLE_ENTITY): EntitySelector(
                EntitySelectorConfig(domain=TOGGLE_DOMAINS)
            ),
        }
    )


class SmartGarageConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Smart Garage Door."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                validate_toggle_entity(user_input[ATTR_TOGGLE_ENTITY])

                unique_id = user_input["name"].lower().replace(" ", "_")
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(title=user_input["name"], data=user_input)
            except vol.Invalid:
                errors[ATTR_TOGGLE_ENTITY] = "invalid_toggle_entity"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id=STEP_USER,
            data_schema=_garage_data_schema(),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user fix a wrong sensor/toggle-entity pick without re-adding the integration."""
        reconfigure_entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                validate_toggle_entity(user_input[ATTR_TOGGLE_ENTITY])

                return self.async_update_reload_and_abort(
                    reconfigure_entry,
                    title=user_input["name"],
                    data_updates=user_input,
                )
            except vol.Invalid:
                errors[ATTR_TOGGLE_ENTITY] = "invalid_toggle_entity"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id=STEP_RECONFIGURE,
            data_schema=_garage_data_schema(reconfigure_entry.data),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SmartGarageOptionsFlow:
        """Get the options flow for this handler."""
        return SmartGarageOptionsFlow()


class SmartGarageOptionsFlow(config_entries.OptionsFlow):
    """Handle tunables (motion duration, sensor debounce) for an existing garage door."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options
        data = self.config_entry.data

        schema = vol.Schema(
            {
                vol.Optional(
                    ATTR_MOTION_DURATION,
                    default=current.get(
                        ATTR_MOTION_DURATION,
                        data.get(ATTR_MOTION_DURATION, DEFAULT_MOTION_DURATION),
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        mode=NumberSelectorMode.BOX,
                        min=5,
                        max=120,
                        unit_of_measurement="seconds",
                    )
                ),
                vol.Optional(
                    ATTR_SENSOR_DEBOUNCE_MS,
                    default=current.get(
                        ATTR_SENSOR_DEBOUNCE_MS,
                        data.get(ATTR_SENSOR_DEBOUNCE_MS, DEFAULT_SENSOR_DEBOUNCE_MS),
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        mode=NumberSelectorMode.BOX,
                        min=50,
                        max=2000,
                        unit_of_measurement="ms",
                    )
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
