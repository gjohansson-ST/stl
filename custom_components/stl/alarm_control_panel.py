"""Adds Alarm Panel for STL integration."""
import logging
from datetime import timedelta
from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    FORMAT_NUMBER,
)
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    UpdateFailed,
)
from homeassistant.components.alarm_control_panel.const import (
    SUPPORT_ALARM_ARM_AWAY,
    SUPPORT_ALARM_ARM_HOME,
)
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_DISARMED,
    STATE_ALARM_PENDING,
    STATE_ALARM_ARMING,
    STATE_ALARM_DISARMING,
)
from .const import (
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """ No setup from yaml """
    return True


async def async_setup_entry(hass, entry, async_add_entities):

    stl_hub = hass.data[DOMAIN][entry.entry_id]["api"]
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities([STLAlarmPanel(stl_hub, coordinator)])

    return True


class STLAlarmAlarmDevice(AlarmControlPanelEntity):
    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "manufacturer": "Visonic",
            "model": "PowerMaster 360R",
            "sw_version": "7.0",
            "via_device": (DOMAIN, f"visonic_{str(self._hub.alarm_id)}"),
        }


class STLAlarmPanel(CoordinatorEntity, STLAlarmAlarmDevice):
    def __init__(self, hub, coordinator):
        self._hub = hub
        super().__init__(coordinator)
        self._state = STATE_ALARM_PENDING
        self._changed_by = None
        self._displayname = self._hub.alarm_displayname
        self._isonline = self._hub.alarm_isonline
        self._isready = self._hub.alarm_ready
        self._panel_id = self._hub.alarm_id

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        return f"stl_panel_{str(self._hub.alarm_id)}"

    @property
    def name(self):
        return f"STL {self._hub.alarm_id}"

    @property
    def changed_by(self):
        return self._hub.alarm_changed_by

    @property
    def supported_features(self) -> int:
        return SUPPORT_ALARM_ARM_HOME | SUPPORT_ALARM_ARM_AWAY

    @property
    def code_arm_required(self):
        return False

    @property
    def state(self):
        return self._hub.alarm_state

    @property
    def code_format(self):
        """Return one or more digits/characters."""
        return None

    @property
    def device_state_attributes(self):
        return {
            "Display name": self._displayname,
            "Is Online": self._isonline,
            "Is Ready": self._isready,
            "Serial": self._panel_id,
        }

    async def async_alarm_arm_home(self, code=None):
        command = "partial"

        _LOGGER.debug("Trying to arm home")
        await self._hub.triggeralarm(command, code=code)

    async def async_alarm_disarm(self, code=None):
        command = "disarm"

        _LOGGER.debug("Trying to disarm")
        await self._hub.triggeralarm(command, code=code)

    async def async_alarm_arm_away(self, code=None):
        command = "full"

        _LOGGER.debug("Trying to arm away")
        await self._hub.triggeralarm(command, code=code)
