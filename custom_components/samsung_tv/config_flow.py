from typing import Optional, Any
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant import data_entry_flow
from homeassistant.helpers import device_registry
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import DOMAIN, CONF_MAC
from .const import CONF_HOST, CONF_POLLING_RATE, CONF_NAME
from .const import DEFAULT_POLLING_RATE

from .device import SamsungDevice

from .errors import *

_LOGGER = logging.getLogger(__name__)

STEP_TV_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(
            CONF_HOST,
            description="The hostname or IP address of your samsung TV ",
        ): str,
        vol.Required(
            CONF_NAME,
            description="Name of your device",
        ): str,
        vol.Optional(
            CONF_POLLING_RATE,
            description="Polling rate in seconds (e.g. 0.1 = 100ms)",
            default=DEFAULT_POLLING_RATE,
        ): vol.All(vol.Coerce(float), vol.Clamp(min=5))
    }
)


def step_options(entry: config_entries.ConfigEntry) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_HOST,
                description="The IP address of yout samsung TV (must be static)",
                default=entry.data[CONF_HOST]
            ): str,
            vol.Optional(
                CONF_POLLING_RATE,
                description="Polling rate in seconds (e.g. 0.1 = 100ms)",
                default=entry.data.get(CONF_POLLING_RATE, DEFAULT_POLLING_RATE),
            ): vol.All(vol.Coerce(float), vol.Clamp(min=5))
        }
    )


@config_entries.HANDLERS.register(DOMAIN)
class SamsungTVConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow for Samsung TV."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        super().__init__()

    async def async_step_user(
        self, user_input: Optional[dict[str, Any]] = None
    ) -> data_entry_flow.FlowResult:
        """Handle the initial step."""
        self.hass.data.setdefault(DOMAIN, {})

        errors = {}

        if user_input is not None:
            try:
                device = await self._async_device_connect(user_input)
                mac = await device.fetch_mac()
                await self.async_set_unique_id(device_registry.format_mac(mac))
                self._abort_if_unique_id_configured()
                self._async_abort_entries_match({CONF_HOST: device.host})

                return await self._async_create_config_entry(device, user_input)
            except ConnectionFailed as err:
                errors["base"] = "connection_failed"
                _LOGGER.exception(f"Failed to setup. Connection failed: {str(err)}")
            except AuthenticationFailed as err:
                errors["base"] = "authentication_failed"
                _LOGGER.exception(f"Failed to setup. Authentication failed: {str(err)}")

        return self.async_show_form(
            step_id="user", data_schema=STEP_TV_DATA_SCHEMA, errors=errors
        )

    async def _async_device_connect(
            self,
            config: dict[str, Any],
    ) -> SamsungDevice:
        host = config[CONF_HOST]
        name = config[CONF_NAME]

        session = async_create_clientsession(self.hass)

        device = SamsungDevice(host, name, session, self.hass)
        await device.async_update()

        return device

    async def _async_create_config_entry(self, device: SamsungDevice, options: dict[str, Any]):
        return self.async_create_entry(
            title=device.name,
            data=options
            | {
                CONF_MAC: await device.fetch_mac()
            }
        )
