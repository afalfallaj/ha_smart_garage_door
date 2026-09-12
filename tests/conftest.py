"""Global test fixtures — sys.modules stubs for the `homeassistant` package.

We stub `homeassistant` instead of depending on the heavy, HA-core-version-pinned
`pytest-homeassistant-custom-component` package. Only the pieces this integration
actually imports are provided, as real minimal classes where behavior (attribute
access, inheritance) matters and MagicMock otherwise.
"""
from __future__ import annotations

import pathlib
import sys
from unittest.mock import MagicMock

# Make the repo root importable so tests can `import custom_components.smart_garage...`
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

# ---------------------------------------------------------------------------
# homeassistant.core
# ---------------------------------------------------------------------------


class _HomeAssistant:
    """Minimal stand-in for homeassistant.core.HomeAssistant."""

    def __init__(self) -> None:
        self.states = _StateMachine()
        self.services = MagicMock()
        self.config_entries = MagicMock()


class _State:
    """Minimal stand-in for homeassistant.core.State."""

    def __init__(self, state: str) -> None:
        self.state = state


class _StateMachine:
    """Minimal stand-in for homeassistant.core.StateMachine."""

    def __init__(self) -> None:
        self._states: dict[str, _State] = {}

    def get(self, entity_id: str) -> _State | None:
        return self._states.get(entity_id)

    def set(self, entity_id: str, state: str) -> None:
        self._states[entity_id] = _State(state)


_ha_core = MagicMock()
_ha_core.HomeAssistant = _HomeAssistant
_ha_core.State = _State
_ha_core.callback = lambda f: f  # passthrough decorator
_ha_core.Event = MagicMock()
_ha_core.EventStateChangedData = MagicMock()

# ---------------------------------------------------------------------------
# homeassistant.const
# ---------------------------------------------------------------------------

_ha_const = MagicMock()
_ha_const.STATE_ON = "on"
_ha_const.STATE_OFF = "off"
_ha_const.STATE_UNAVAILABLE = "unavailable"
_ha_const.SERVICE_TOGGLE = "toggle"
_ha_const.Platform = MagicMock()

# ---------------------------------------------------------------------------
# homeassistant.helpers.event — async_call_later is captured so tests can fire
# the scheduled callback manually instead of waiting on a real event loop timer
# ---------------------------------------------------------------------------

_ha_event = MagicMock()
_ha_event.async_track_state_change_event = MagicMock(return_value=MagicMock())
_ha_event.async_call_later = MagicMock(return_value=MagicMock())

# ---------------------------------------------------------------------------
# homeassistant.helpers.dispatcher
# ---------------------------------------------------------------------------

_ha_dispatcher = MagicMock()
_ha_dispatcher.async_dispatcher_send = MagicMock()
_ha_dispatcher.async_dispatcher_connect = MagicMock(return_value=MagicMock())

# ---------------------------------------------------------------------------
# homeassistant.helpers.config_validation — only what config_flow.py uses
# ---------------------------------------------------------------------------


def _cv_entity_id(value: str) -> str:
    if not isinstance(value, str) or "." not in value:
        raise ValueError(f"Invalid entity id: {value}")
    return value


_ha_cv = MagicMock()
_ha_cv.entity_id = _cv_entity_id

# ---------------------------------------------------------------------------
# homeassistant.config_entries — just enough of ConfigFlow/OptionsFlow/ConfigEntry
# for SmartGarageConfigFlow to subclass and exercise, without depending on the
# real flow-manager machinery.
# ---------------------------------------------------------------------------


class _ConfigEntry:
    """Minimal stand-in for homeassistant.config_entries.ConfigEntry."""

    def __init__(self, data=None, options=None, entry_id="test_entry") -> None:
        self.data = data or {}
        self.options = options or {}
        self.entry_id = entry_id
        self.title = self.data.get("name", "")
        self.runtime_data = None

    def add_update_listener(self, _listener):
        return MagicMock()

    def async_on_unload(self, _unsub):
        return None


class _FlowHandlerBase:
    """Shared bits of homeassistant.config_entries.ConfigFlow/OptionsFlow."""

    def async_show_form(self, *, step_id, data_schema=None, errors=None):
        return {"type": "form", "step_id": step_id, "data_schema": data_schema, "errors": errors or {}}

    def async_create_entry(self, *, title=None, data=None):
        return {"type": "create_entry", "title": title, "data": data}

    def async_abort(self, *, reason):
        return {"type": "abort", "reason": reason}


class _ConfigFlow(_FlowHandlerBase):
    """Minimal stand-in for homeassistant.config_entries.ConfigFlow."""

    def __init_subclass__(cls, *, domain=None, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.domain = domain

    async def async_set_unique_id(self, unique_id):
        self._unique_id = unique_id

    def _abort_if_unique_id_configured(self):
        return None

    def _get_reconfigure_entry(self) -> _ConfigEntry:
        return self._reconfigure_entry

    def async_update_reload_and_abort(
        self, entry, *, title=None, data=None, data_updates=None
    ):
        if data is not None:
            entry.data = data
        if data_updates is not None:
            entry.data = {**entry.data, **data_updates}
        if title is not None:
            entry.title = title
        return {"type": "abort", "reason": "reconfigure_successful"}


class _OptionsFlow(_FlowHandlerBase):
    """Minimal stand-in for homeassistant.config_entries.OptionsFlow."""

    config_entry: _ConfigEntry


_ha_config_entries = MagicMock()
_ha_config_entries.ConfigEntry = _ConfigEntry
_ha_config_entries.ConfigFlow = _ConfigFlow
_ha_config_entries.OptionsFlow = _OptionsFlow
_ha_config_entries.ConfigFlowResult = dict

# ---------------------------------------------------------------------------
# homeassistant.util.dt needs a real utcnow() so motion-duration math works
# ---------------------------------------------------------------------------

import datetime as _dt  # noqa: E402

_ha_util_dt = MagicMock()
_ha_util_dt.utcnow = lambda: _dt.datetime.now(_dt.timezone.utc)

_ha_util = MagicMock()
_ha_util.dt = _ha_util_dt  # `from homeassistant.util import dt` resolves via this attribute

_ha_helpers_entity = MagicMock()
_ha_helpers_entity_platform = MagicMock()
_ha_helpers_selector = MagicMock()

# For "from package import submodule" (rather than "from package.submodule import
# name"), Python resolves the submodule via getattr() on the already-imported
# parent package. A bare MagicMock() parent auto-vivifies any attribute access,
# silently returning a *different* mock than the one registered in sys.modules
# for the dotted path — so every submodule accessed that way must also be set
# explicitly as an attribute on its parent mock.
_ha_helpers = MagicMock()
_ha_helpers.event = _ha_event
_ha_helpers.dispatcher = _ha_dispatcher
_ha_helpers.config_validation = _ha_cv
_ha_helpers.entity = _ha_helpers_entity
_ha_helpers.entity_platform = _ha_helpers_entity_platform
_ha_helpers.selector = _ha_helpers_selector

_ha_top = MagicMock()
_ha_top.config_entries = _ha_config_entries  # `from homeassistant import config_entries`

sys.modules.update(
    {
        "homeassistant": _ha_top,
        "homeassistant.core": _ha_core,
        "homeassistant.const": _ha_const,
        "homeassistant.config_entries": _ha_config_entries,
        "homeassistant.helpers": _ha_helpers,
        "homeassistant.helpers.event": _ha_event,
        "homeassistant.helpers.dispatcher": _ha_dispatcher,
        "homeassistant.helpers.config_validation": _ha_cv,
        "homeassistant.helpers.entity": _ha_helpers_entity,
        "homeassistant.helpers.entity_platform": _ha_helpers_entity_platform,
        "homeassistant.helpers.selector": _ha_helpers_selector,
        "homeassistant.components": MagicMock(),
        "homeassistant.components.sensor": MagicMock(),
        "homeassistant.components.cover": MagicMock(),
        "homeassistant.util": _ha_util,
        "homeassistant.util.dt": _ha_util_dt,
    }
)
