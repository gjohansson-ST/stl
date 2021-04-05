"""Adds config flow for Sector integration."""
import logging

import voluptuous as vol
import aiohttp
import uuid

import homeassistant.helpers.config_validation as cv
from homeassistant import config_entries, core, exceptions
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_CODE,
    CONF_APP_ID,
    CONF_PANEL,
    MIN_SCAN_INTERVAL,
    API_URL,
)

url_base = API_URL
url_panel_login = url_base + "/panel/login"
url_login = url_base + "/auth"

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_CODE): cv.string,
        vol.Required(CONF_PANEL): cv.string,
        vol.Required(CONF_APP_ID, default=str(uuid.uuid4())): cv.string,
    }
)


async def validate_input(
    hass: core.HomeAssistant, username, password, app_id, code, panel_id
):
    """Validate the user input allows us to connect."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.data["username"] == username:
            raise AlreadyConfigured

    message_headers = {
        "Content-Type": "application/json",
        "Connection": "keep-alive",
        "Accept": "*/*",
        "User-Agent": "Visonic GO/2.8.62.91 CFNetwork/901.1 Darwin/17.6.0",
        "Accept-Language": "en-us",
        "Accept-Encoding": "br, gzip, deflate",
    }

    websession = async_get_clientsession(hass)
    login = await websession.post(
        url_login,
        headers=message_headers,
        json={
            "email": username,
            "password": password,
            "app_id": app_id,
        },
    )
    if login.status == 200 or login.status == 204:
        token_user = await login.json()
        message_headers["User-Token"] = token_user["user_token"]
    else:
        raise CannotConnect

    session = await websession.post(
        url_panel_login,
        headers=message_headers,
        json={
            "user_code": code,
            "app_type": "com.visonic.PowerMaxApp",
            "app_id": app_id,
            "panel_serial": panel_id,
        },
    )

    if session.status == 200 or session.status == 204:
        token_session = await session.json()
        message_headers["Session-Token"] = token_session["session_token"]
    else:
        raise CannotConnect

    return True


class STLConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sector integration."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME].replace(" ", "")
            password = user_input[CONF_PASSWORD].replace(" ", "")
            app_id = user_input[CONF_APP_ID].replace(" ", "")
            code = user_input[CONF_CODE].replace(" ", "")
            panel_id = user_input[CONF_PANEL].replace(" ", "")

            try:
                await validate_input(
                    self.hass, username, password, app_id, code, panel_id
                )

            except AlreadyConfigured:
                return self.async_abort(reason="already_configured")
            except CannotConnect:
                return self.async_show_form(
                    step_id="user",
                    data_schema=DATA_SCHEMA,
                    errors={"base": "auth_error"},
                    description_placeholders={},
                )

            unique_id = "stl_" + panel_id
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=unique_id,
                data={
                    CONF_USERNAME: username,
                    CONF_PASSWORD: password,
                    CONF_CODE: code,
                    CONF_APP_ID: app_id,
                    CONF_PANEL: panel_id,
                },
            )
            _LOGGER.info("Login succesful. Config entry created.")

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class AlreadyConfigured(exceptions.HomeAssistantError):
    """Error to indicate host is already configured."""
