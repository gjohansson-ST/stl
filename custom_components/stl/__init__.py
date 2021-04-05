"""SVENSKA TRYGGHETSLÖSNINGAR INTEGRATION FOR HOME ASSISTANT"""
import logging
import json
import asyncio
import aiohttp
import async_timeout
from datetime import datetime, timedelta
import voluptuous as vol
from homeassistant import exceptions
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
from homeassistant.helpers import discovery
from homeassistant.exceptions import (
    PlatformNotReady,
    ConfigEntryNotReady,
    HomeAssistantError,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_DISARMED,
    STATE_ALARM_PENDING,
    STATE_ALARM_ARMING,
    STATE_ALARM_DISARMING,
)
from homeassistant.const import (
    STATE_LOCKED,
    STATE_UNKNOWN,
    STATE_UNLOCKED,
)

from .const import (
    DOMAIN,
    DEPENDENCIES,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_APP_ID,
    CONF_PANEL,
    CONF_CODE,
    MIN_SCAN_INTERVAL,
    API_URL,
)

url_base = API_URL
url_panel_login = url_base + "/panel/login"
url_login = url_base + "/auth"
url_status = url_base + "/status"
url_alarms = url_base + "/alarms"
url_alerts = url_base + "/alerts"
url_troubles = url_base + "/troubles"

url_panel_info = url_base + "/panel_info"
url_events = url_base + "/events"
url_wakeup_sms = url_base + "/wakeup_sms"
url_all_devices = url_base + "/devices"
url_set_state = url_base + "/set_state"
url_locations = url_base + "/locations"
url_process_status = url_base + "/process_status"

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_CODE, default=""): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    """ No setup from yaml """
    return True


async def async_setup_entry(hass, entry):
    """ Setup from config entries """
    hass.data.setdefault(DOMAIN, {})
    title = entry.title

    websession = async_get_clientsession(hass)

    api = STLAlarmHub(
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        entry.data[CONF_APP_ID],
        entry.data[CONF_CODE],
        entry.data[CONF_PANEL],
        websession=websession,
    )

    async def async_update_data():
        """ Fetch data from STL """

        now = datetime.utcnow()
        hass.data[DOMAIN][entry.entry_id]["last_updated"] = now
        _LOGGER.debug("UPDATE_INTERVAL = %s", MIN_SCAN_INTERVAL)
        _LOGGER.debug(
            "last updated = %s", hass.data[DOMAIN][entry.entry_id]["last_updated"]
        )
        await api.fetch_info()

        return True

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="stl_api",
        update_method=async_update_data,
        update_interval=timedelta(seconds=MIN_SCAN_INTERVAL),
    )

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "last_updated": datetime.utcnow() - timedelta(hours=2),
        "data_listener": [entry.add_update_listener(update_listener)],
    }
    _LOGGER.debug("Connected to STL API")

    await coordinator.async_refresh()
    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    panel_data = await api.get_panel()
    if panel_data is None:
        _LOGGER.error("Platform not ready")
        raise ConfigEntryNotReady

    else:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, "alarm_control_panel")
        )

    device_registry = await dr.async_get_registry(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "visonic_" + str(api._panel_id))},
        manufacturer="Visonic",
        name="1B7EEB",
        model="PowerMaster 360R",
        sw_version="7.0",
    )

    return True


async def update_listener(hass, entry):
    """Update when config_entry options update."""


async def async_unload_entry(hass, entry):
    """Unload a config entry."""

    Platforms = ["alarm_control_panel"]

    for listener in hass.data[DOMAIN][entry.entry_id]["data_listener"]:
        listener()

    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in Platforms
            ]
        )
    )

    title = entry.title
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.debug("Unloaded entry for %s", title)
        return unload_ok
    return False


class STLAlarmHub(object):
    """ Svensk Trygghetslosningar connectivity hub """

    def __init__(self, username, password, app_id, code, panel_id, websession):

        self._state = None
        self._status = None
        self._is_online = None
        self._is_ready = None
        self._changed_by = None
        self._websession = websession
        self._username = username
        self._password = password
        self._app_id = app_id
        self._code = code
        self._panel = []
        self._panel_id = panel_id
        self._access_token = None
        self._session_token = None
        self._last_updated = datetime.utcnow() - timedelta(hours=2)
        self._last_updated_temp = datetime.utcnow() - timedelta(hours=2)
        self._timeout = 15

    async def get_panel(self):
        panel = self._panel

        if panel is None or panel == []:
            _LOGGER.debug("Failed to fetch panel")
            return None

        return str(panel["model"]) + str(panel["serial"])

    async def triggeralarm(self, command, code):

        headers = {
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Accept": "*/*",
            "User-Agent": "Visonic GO/2.8.62.91 CFNetwork/901.1 Darwin/17.6.0",
            "Accept-Language": "en-us",
            "Accept-Encoding": "br, gzip, deflate",
        }
        headers["User-Token"] = self._access_token
        headers["Session-Token"] = self._session_token

        message_json = {
            "partition": -1,
        }

        if command == "full":
            message_json["state"] = "AWAY"
            get_process_token = await self._request(
                url_set_state, json_data=message_json
            )
        elif command == "partial":
            message_json["state"] = "HOME"
            get_process_token = await self._request(
                url_set_state, json_data=message_json
            )
        else:
            message_json["state"] = "DISARM"
            get_process_token = await self._request(
                url_set_state, json_data=message_json
            )

        """ TO BE USED LATER
        process_token_json = await get_process_token.json()
        process_token = process_token_json["process_token"]
        check_token = await self._request(
            url_process_status + "?process_tokens=" + str(process_token),
            json_data=message_json,
        )
        """

        _LOGGER.debug("triggeralarm complete with command %s", command)

        await self.fetch_info()

    async def fetch_info(self):
        """ Fetch info from API """
        if self._panel == []:
            response = await self._request(url_panel_info)
            if response is None:
                return None
            self._panel = await response.json()

        response = await self._request(url_status)
        if response is not None:
            json_data = await response.json()
            self._state = json_data["partitions"][0]["state"]
            try:
                self._status = json_data["partitions"][0]["status"]
            except:
                self._status = None
            self._is_online = json_data["connected"]
            self._is_ready = json_data["partitions"][0]["ready"]
            _LOGGER.debug("self._state = %s", self._state)

        response = await self._request(url_events)
        if response is not None:
            json_data = await response.json()
            for users in json_data[::-1]:
                if users["label"] == "ARM" or users["label"] == "DISMARM":
                    self._changed_by = users["name"]
                    break
                else:
                    self._changed_by = "unknown"
            _LOGGER.debug("self._changed_by = %s", self._changed_by)

    async def _request(self, url, json_data=None, retry=3):
        if self._access_token is None or self._session_token is None:
            result = await self._login()
            if result is None:
                return None

        message_headers = {
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Accept": "*/*",
            "User-Agent": "Visonic GO/2.8.62.91 CFNetwork/901.1 Darwin/17.6.0",
            "Accept-Language": "en-us",
            "Accept-Encoding": "br, gzip, deflate",
        }
        message_headers["User-Token"] = self._access_token
        message_headers["Session-Token"] = self._session_token

        try:
            with async_timeout.timeout(self._timeout):
                if json_data:
                    response = await self._websession.post(
                        url, json=json_data, headers=message_headers
                    )
                else:
                    response = await self._websession.get(url, headers=message_headers)

            if response.status == 200 or response.status == 204:
                _LOGGER.debug(f"Info retrieved successfully URL: {url}")
                _LOGGER.debug(f"request status: {response.status}")
                return response
            else:
                self._access_token = None
                self._session_token = None
                await asyncio.sleep(2)
                if retry > 0:
                    return await self._request(url, json_data, retry=retry - 1)
                else:
                    _LOGGER.error("Could not retrieve data after 3 attempts")

        except aiohttp.ClientConnectorError as e:
            _LOGGER.error("ClientError connecting to API: %s ", e, exc_info=True)

        except aiohttp.ContentTypeError as e:
            _LOGGER.error("ContentTypeError connecting to API: %s ", e)

        except asyncio.TimeoutError:
            _LOGGER.error("Timed out when connecting to API")

        except asyncio.CancelledError:
            _LOGGER.error("Task was cancelled")

        return None

    async def _login(self):
        """ Login to retrieve access token """
        message_headers = {
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Accept": "*/*",
            "User-Agent": "Visonic GO/2.8.62.91 CFNetwork/901.1 Darwin/17.6.0",
            "Accept-Language": "en-us",
            "Accept-Encoding": "br, gzip, deflate",
        }
        try:
            with async_timeout.timeout(self._timeout):
                response = await self._websession.post(
                    url_login,
                    headers=message_headers,
                    json={
                        "email": self._username,
                        "password": self._password,
                        "app_id": self._app_id,
                    },
                )

                if response.status == 200 or response.status == 204:
                    token_user = await response.json()
                    self._access_token = token_user["user_token"]
                    message_headers["User-Token"] = self._access_token
                else:
                    self._access_token = None
                    _LOGGER.error("Could not retrieve login info")
                    return None

                response = await self._websession.post(
                    url_panel_login,
                    headers=message_headers,
                    json={
                        "user_code": self._code,
                        "app_type": "com.visonic.PowerMaxApp",
                        "app_id": self._app_id,
                        "panel_serial": self._panel_id,
                    },
                )

                if response.status == 200 or response.status == 204:
                    token_session = await response.json()
                    self._session_token = token_session["session_token"]
                else:
                    self._session_token = None
                    _LOGGER.error("Could not retrieve session info")
                    return None

                return True

        except aiohttp.ClientConnectorError as e:
            _LOGGER.error("ClientError connecting to API: %s ", e, exc_info=True)

        except aiohttp.ContentTypeError as c:
            _LOGGER.error("ContentTypeError connecting to API: %s ", c)

        except asyncio.TimeoutError:
            _LOGGER.error("Timed out when connecting to API")

        except asyncio.CancelledError:
            _LOGGER.error("Task was cancelled")

        return None

    @property
    def alarm_state(self):

        state = self._state
        status = self._status

        if state == "DISARM":
            return STATE_ALARM_DISARMED
        elif state == "HOME" and status == "EXIT":
            return STATE_ALARM_ARMING
        elif state == "AWAY" and status == "EXIT":
            return STATE_ALARM_ARMING
        elif state == "HOME":
            return STATE_ALARM_ARMED_HOME
        elif state == "AWAY":
            return STATE_ALARM_ARMED_AWAY
        elif state == "ENTRY_DELAY":
            return STATE_ALARM_DISARMING
        else:
            return STATE_ALARM_PENDING

    @property
    def alarm_changed_by(self):
        return self._changed_by

    @property
    def alarm_id(self):
        return self._panel_id

    @property
    def alarm_displayname(self):
        return "Visonic " + str(self._panel_id)

    @property
    def alarm_isonline(self):
        return self._is_online

    @property
    def alarm_ready(self):
        return self._is_ready


class UnauthorizedError(HomeAssistantError):
    """Exception to indicate an error in authorization."""


class CannotConnectError(HomeAssistantError):
    """Exception to indicate an error in client connection."""


class OperationError(HomeAssistantError):
    """Exception to indicate an error in operation."""
