"""Adds config flow for Sector integration."""
import logging
import uuid

import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_APP_ID,
    CONF_CODE,
    CONF_PANEL,
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
    URL_LOGIN,
    URL_PANEL_LOGIN,
)

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
    hass: HomeAssistant,
    username: str,
    password: str,
    app_id: str,
    code: str,
    panel_id: str,
) -> None:
    """Validate the user input allows us to connect."""

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
        URL_LOGIN,
        headers=message_headers,
        json={
            "email": username,
            "password": password,
            "app_id": app_id,
        },
    )
    if login.status in (200, 204):
        token_user = await login.json()
        message_headers["User-Token"] = token_user["user_token"]
    else:
        raise CannotConnect

    session = await websession.post(
        URL_PANEL_LOGIN,
        headers=message_headers,
        json={
            "user_code": code,
            "app_type": "com.visonic.PowerMaxApp",
            "app_id": app_id,
            "panel_serial": panel_id,
        },
    )

    if session.status in (200, 204):
        token_session = await session.json()
        message_headers["Session-Token"] = token_session["session_token"]
    else:
        raise CannotConnect


class STLConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sector integration."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            username: str = user_input[CONF_USERNAME].replace(" ", "")
            password: str = user_input[CONF_PASSWORD].replace(" ", "")
            app_id: str = user_input[CONF_APP_ID].replace(" ", "")
            code: str = user_input[CONF_CODE].replace(" ", "")
            panel_id: str = user_input[CONF_PANEL].replace(" ", "")

            try:
                await validate_input(
                    self.hass, username, password, app_id, code, panel_id
                )
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

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""
