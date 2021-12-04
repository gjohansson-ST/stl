"""SVENSKA TRYGGHETSLÖSNINGAR INTEGRATION FOR HOME ASSISTANT."""
import asyncio
from datetime import datetime, timedelta
import logging

import aiohttp
from aiohttp import ClientSession
import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_ARMING,
    STATE_ALARM_DISARMED,
    STATE_ALARM_DISARMING,
    STATE_ALARM_PENDING,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_APP_ID,
    CONF_CODE,
    CONF_PANEL,
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
    MIN_SCAN_INTERVAL,
    PLATFORMS,
    URL_EVENTS,
    URL_LOGIN,
    URL_PANEL_INFO,
    URL_PANEL_LOGIN,
    URL_SET_STATE,
    URL_STATUS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from config entries."""
    hass.data.setdefault(DOMAIN, {})

    websession = async_get_clientsession(hass)

    api = STLAlarmHub(
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        entry.data[CONF_APP_ID],
        entry.data[CONF_CODE],
        entry.data[CONF_PANEL],
        websession=websession,
    )

    async def async_update_data() -> None:
        """Fetch data from STL."""

        now = datetime.utcnow()
        hass.data[DOMAIN][entry.entry_id]["last_updated"] = now
        await api.fetch_info()

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
    }
    _LOGGER.debug("Connected to STL API")

    await coordinator.async_refresh()
    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    panel_data = await api.get_panel()
    if panel_data is None:
        _LOGGER.error("Platform not ready")
        raise ConfigEntryNotReady

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    device_registry = await dr.async_get_registry(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "visonic_" + str(entry.data[CONF_PANEL]))},
        manufacturer="Visonic",
        name="PowerMaster 360R - 1B7EEB",
        model="PowerMaster 360R",
        sw_version="7.0",
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    title = entry.title
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.debug("Unloaded entry for %s", title)
        return unload_ok
    return False


class STLAlarmHub(object):
    """Svensk Trygghetslosningar connectivity hub."""

    def __init__(
        self,
        username: str,
        password: str,
        app_id: str,
        code: str,
        panel_id: str,
        websession: ClientSession,
    ) -> None:
        """Initialize STL hub."""

        self._state = ""
        self._status: str = ""
        self._is_online: str = ""
        self._is_ready: str = ""
        self._changed_by: str = ""
        self._websession = websession
        self._username = username
        self._password = password
        self._app_id = app_id
        self._code = code
        self._panel: dict = {}
        self._panel_id = panel_id
        self._access_token: str = ""
        self._session_token: str = ""
        self._last_updated: datetime = datetime.utcnow() - timedelta(hours=2)
        self._last_updated_temp: datetime = datetime.utcnow() - timedelta(hours=2)
        self._timeout: int = 15

    async def get_panel(self) -> str:
        """Return panel information."""
        panel = self._panel

        if panel is None or panel == []:
            _LOGGER.debug("Failed to fetch panel")
            return None

        return str(panel["model"]) + str(panel["serial"])

    async def triggeralarm(self, command, code) -> None:
        """Change state of alarm."""

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
                URL_SET_STATE, json_data=message_json
            )
        elif command == "partial":
            message_json["state"] = "HOME"
            get_process_token = await self._request(
                URL_SET_STATE, json_data=message_json
            )
        else:
            message_json["state"] = "DISARM"
            get_process_token = await self._request(
                URL_SET_STATE, json_data=message_json
            )

        _LOGGER.debug("Process info: %s", get_process_token)

        """ TO BE USED LATER
        process_token_json = await get_process_token.json()
        process_token = process_token_json["process_token"]
        check_token = await self._request(
            url_process_status + "?process_tokens=" + str(process_token),
            json_data=message_json,
        )
        """
        await self.fetch_info()

    async def fetch_info(self) -> None:
        """Fetch info from API."""
        if not self._panel:
            response = await self._request(URL_PANEL_INFO)
            if not response:
                raise UpdateFailed
            self._panel = await response.json()

        response = await self._request(URL_STATUS)
        if response:
            json_data = await response.json()
            try:
                self._state = json_data["partitions"][0]["state"]
                if "status" in json_data["partitions"][0]:
                    self._status = json_data["partitions"][0]["status"]
                self._is_online = json_data["connected"]
                self._is_ready = json_data["partitions"][0]["ready"]
            except aiohttp.ClientConnectorError as error:
                _LOGGER.error(
                    "ClientError connecting to API: %s ", error, exc_info=True
                )
                self._status = None
            except aiohttp.ContentTypeError as error:
                _LOGGER.error("ContentTypeError connecting to API: %s ", error)
                self._status = None
            except asyncio.TimeoutError:
                _LOGGER.error("Timed out when connecting to API")
                self._status = None
            except asyncio.CancelledError:
                _LOGGER.error("Task was cancelled")
                self._status = None

        response = await self._request(URL_EVENTS)
        if response:
            json_data = await response.json()
            for users in json_data[::-1]:
                if users["label"] == "ARM" or users["label"] == "DISMARM":
                    self._changed_by = users["name"]
                    break
                self._changed_by = "unknown"

    async def _request(self, url, json_data=None, retry=3) -> dict:
        if self._access_token is None or self._session_token is None:
            result = await self._login()
            if not result:
                raise UpdateFailed

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

            if response.status in (200, 204):
                return response
            self._access_token = None
            self._session_token = None
            await asyncio.sleep(2)
            if retry > 0:
                return await self._request(url, json_data, retry=retry - 1)
            _LOGGER.error("Could not retrieve data after 3 attempts")

        except aiohttp.ClientConnectorError as error:
            _LOGGER.error("ClientError connecting to API: %s ", error, exc_info=True)

        except aiohttp.ContentTypeError as error:
            _LOGGER.error("ContentTypeError connecting to API: %s ", error)

        except asyncio.TimeoutError:
            _LOGGER.error("Timed out when connecting to API")

        except asyncio.CancelledError:
            _LOGGER.error("Task was cancelled")

        raise UpdateFailed

    async def _login(self) -> bool:
        """Login to retrieve access token."""

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
                    URL_LOGIN,
                    headers=message_headers,
                    json={
                        "email": self._username,
                        "password": self._password,
                        "app_id": self._app_id,
                    },
                )

                if response.status in (200, 204):
                    token_user = await response.json()
                    self._access_token = token_user["user_token"]
                    message_headers["User-Token"] = self._access_token

                    response = await self._websession.post(
                        URL_PANEL_LOGIN,
                        headers=message_headers,
                        json={
                            "user_code": self._code,
                            "app_type": "com.visonic.PowerMaxApp",
                            "app_id": self._app_id,
                            "panel_serial": self._panel_id,
                        },
                    )

                    if response.status in (200, 204):
                        token_session = await response.json()
                        self._session_token = token_session["session_token"]
                        return True

                self._access_token = None
                self._session_token = None
                raise UpdateFailed

        except aiohttp.ClientConnectorError as error:
            _LOGGER.error("ClientError connecting to API: %s ", error, exc_info=True)

        except aiohttp.ContentTypeError as error:
            _LOGGER.error("ContentTypeError connecting to API: %s ", error)

        except asyncio.TimeoutError:
            _LOGGER.error("Timed out when connecting to API")

        except asyncio.CancelledError:
            _LOGGER.error("Task was cancelled")

        return None

    @property
    def alarm_state(self):
        """Return state of alarm."""

        if self._state == "DISARM":
            return STATE_ALARM_DISARMED
        if self._state == "HOME" and self._status == "EXIT":
            return STATE_ALARM_ARMING
        if self._state == "AWAY" and self._status == "EXIT":
            return STATE_ALARM_ARMING
        if self._state == "HOME":
            return STATE_ALARM_ARMED_HOME
        if self._state == "AWAY":
            return STATE_ALARM_ARMED_AWAY
        if self._state == "ENTRY_DELAY":
            return STATE_ALARM_DISARMING
        return STATE_ALARM_PENDING

    @property
    def alarm_changed_by(self):
        """Return alarm changed by."""
        return self._changed_by

    @property
    def alarm_id(self):
        """Return panel id."""
        return self._panel_id

    @property
    def alarm_displayname(self):
        """Return friendly displayname."""
        return "Visonic " + str(self._panel_id)

    @property
    def alarm_isonline(self):
        """Return is alarm online."""
        return self._is_online

    @property
    def alarm_ready(self):
        """Return is alarm ready."""
        return self._is_ready
