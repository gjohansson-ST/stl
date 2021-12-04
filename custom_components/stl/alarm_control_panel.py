"""Adds Alarm Panel for STL integration."""
import logging

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityDescription,
)
from homeassistant.components.alarm_control_panel.const import (
    SUPPORT_ALARM_ARM_AWAY,
    SUPPORT_ALARM_ARM_HOME,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ALARM_PENDING
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .__init__ import STLAlarmHub
from .const import CONF_PANEL, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set entry for Alarm Panel."""

    stl_hub: STLAlarmHub = hass.data[DOMAIN][entry.entry_id]["api"]
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    panel_id: str = entry.data[CONF_PANEL]
    description = AlarmControlPanelEntityDescription(
        key=panel_id, name=f"Alarm Panel {panel_id}"
    )
    async_add_entities([STLAlarmPanel(stl_hub, coordinator, description)])


class STLAlarmPanel(CoordinatorEntity, AlarmControlPanelEntity):
    """STL Alarm Panel."""

    def __init__(
        self,
        hub: STLAlarmHub,
        coordinator: DataUpdateCoordinator,
        description: AlarmControlPanelEntityDescription,
    ) -> None:
        """Initizialize STL Alarm Panel."""
        self._hub = hub
        super().__init__(coordinator)
        self._attr_name = description.name
        self._attr_unique_id = f"stl_panel_{str(description.key)}"
        self._attr_state = self._hub.alarm_state
        self._attr_changed_by = self._hub.alarm_changed_by
        self._attr_code_arm_required = False
        self._attr_code_format = None
        self._attr_supported_features = SUPPORT_ALARM_ARM_HOME | SUPPORT_ALARM_ARM_AWAY
        self._state: str = STATE_ALARM_PENDING
        self._changed_by: str = "unknown"
        self._displayname = self._hub.alarm_displayname
        self._isonline = self._hub.alarm_isonline
        self._isready = self._hub.alarm_ready
        self._panel_id = self._hub.alarm_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "manufacturer": "Visonic",
            "model": "PowerMaster 360R",
            "sw_version": "7.0",
            "via_device": (DOMAIN, f"visonic_{str(self._hub.alarm_id)}"),
        }

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional information."""
        return {
            "Display name": self._displayname,
            "Is Online": self._isonline,
            "Is Ready": self._isready,
            "Serial": self._panel_id,
        }

    async def async_alarm_arm_home(self, code=None) -> None:
        """Alarm home."""
        command = "partial"
        await self._hub.triggeralarm(command, code=code)

    async def async_alarm_disarm(self, code=None) -> None:
        """Alarm off."""
        command = "disarm"
        await self._hub.triggeralarm(command, code=code)

    async def async_alarm_arm_away(self, code=None) -> None:
        """Alarm away."""
        command = "full"
        await self._hub.triggeralarm(command, code=code)
