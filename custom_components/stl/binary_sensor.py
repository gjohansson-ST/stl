"""Adds Binary Sensor for STL integration."""
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
    DEVICE_CLASS_DOOR,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.const import STATE_ON

from .__init__ import STLAlarmHub
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set entry for Alarm Panel."""

    stl_hub: STLAlarmHub = hass.data[DOMAIN][entry.entry_id]["api"]
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    add_entities: list = []
    devices = stl_hub.get_door_sensors()
    for device in devices:
        description = BinarySensorEntityDescription(
            key=device["id"], name=device["name"], device_class=DEVICE_CLASS_DOOR
        )
        add_entities.append(STLBinarySensor(stl_hub, coordinator, description))
    async_add_entities(add_entities)


class STLBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """STL Binary Sensor."""

    def __init__(
        self,
        hub: STLAlarmHub,
        coordinator: DataUpdateCoordinator,
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initizialize STL Alarm Panel."""
        self._hub = hub
        super().__init__(coordinator)
        self._attr_name = description.name
        self._attr_unique_id = f"stl_door_{str(description.key)}"
        self._attr_state = self._hub.alarm_state
        self._id = description.key

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self._attr_name,
            "manufacturer": "Visonic",
            "model": "PowerMaster 360R",
            "sw_version": "7.0",
            "via_device": (DOMAIN, f"visonic_{str(self._hub.alarm_id)}"),
        }

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        _devices = self._hub.get_door_sensors()
        for device in _devices:
            if device["id"] == self._id:
                return device["status"] == STATE_ON
        return False
