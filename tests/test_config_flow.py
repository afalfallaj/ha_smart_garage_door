"""Tests for custom_components/smart_garage/config_flow.py."""
from __future__ import annotations

import pytest
import voluptuous as vol

from custom_components.smart_garage.config_flow import (
    SmartGarageConfigFlow,
    SmartGarageOptionsFlow,
    validate_toggle_entity,
)

from conftest import _ConfigEntry  # type: ignore[import]


def test_validate_toggle_entity_accepts_switch() -> None:
    assert validate_toggle_entity("switch.garage_opener") == "switch.garage_opener"


def test_validate_toggle_entity_accepts_light() -> None:
    assert validate_toggle_entity("light.shelly_relay") == "light.shelly_relay"


def test_validate_toggle_entity_rejects_other_domains() -> None:
    with pytest.raises(vol.Invalid):
        validate_toggle_entity("sensor.not_a_toggle")


@pytest.mark.asyncio
async def test_user_step_creates_entry_for_valid_input() -> None:
    flow = SmartGarageConfigFlow()

    result = await flow.async_step_user(
        {
            "name": "Main Garage",
            "open_sensor": "binary_sensor.open",
            "closed_sensor": "binary_sensor.closed",
            "toggle_entity": "switch.opener",
        }
    )

    assert result["type"] == "create_entry"
    assert result["title"] == "Main Garage"
    assert result["data"]["toggle_entity"] == "switch.opener"


@pytest.mark.asyncio
async def test_user_step_shows_form_with_no_input() -> None:
    flow = SmartGarageConfigFlow()

    result = await flow.async_step_user(None)

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}


@pytest.mark.asyncio
async def test_user_step_rejects_invalid_toggle_domain() -> None:
    flow = SmartGarageConfigFlow()

    result = await flow.async_step_user(
        {
            "name": "Main Garage",
            "open_sensor": "binary_sensor.open",
            "closed_sensor": "binary_sensor.closed",
            "toggle_entity": "sensor.not_a_toggle",
        }
    )

    assert result["type"] == "form"
    assert result["errors"]["toggle_entity"] == "invalid_toggle_entity"


@pytest.mark.asyncio
async def test_reconfigure_step_updates_existing_entry() -> None:
    entry = _ConfigEntry(
        data={
            "name": "Main Garage",
            "open_sensor": "binary_sensor.open",
            "closed_sensor": "binary_sensor.closed",
            "toggle_entity": "switch.opener",
        }
    )
    flow = SmartGarageConfigFlow()
    flow._reconfigure_entry = entry

    result = await flow.async_step_reconfigure(
        {
            "name": "Main Garage",
            "open_sensor": "binary_sensor.open_v2",
            "closed_sensor": "binary_sensor.closed",
            "toggle_entity": "switch.opener",
        }
    )

    assert result["type"] == "abort"
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["open_sensor"] == "binary_sensor.open_v2"


@pytest.mark.asyncio
async def test_options_flow_prefills_existing_values() -> None:
    entry = _ConfigEntry(data={"name": "Main Garage", "motion_duration": 40})
    options_flow = SmartGarageOptionsFlow()
    options_flow.config_entry = entry

    result = await options_flow.async_step_init(None)

    assert result["type"] == "form"
    assert result["step_id"] == "init"
