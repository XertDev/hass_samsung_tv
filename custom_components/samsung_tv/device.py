import asyncio
import base64
import dataclasses
import enum
import json
import logging
import urllib
from typing import Optional, Dict, Callable
from functools import partial
from urllib.parse import urlencode

import getmac

import socket
import aiohttp
from aiohttp import ClientSession, ClientConnectionError, ClientResponseError, ClientWebSocketResponse
from homeassistant.core import HomeAssistant

from .apps import SUPPORTED_APPS
from .const import WAIT_FOR_CONNECTION_TIMEOUT, KEY_POWER, WAIT_FOR_AUTH_TIMEOUT
from .errors import *

_LOGGING = logging.getLogger(__name__)


class PowerState(enum.Enum):
    STANDBY = "standby"
    ON = "on"


@dataclasses.dataclass(frozen=False)
class DeviceState:
    state: PowerState
    mac: str


class SamsungDevice:
    _name: str
    _host: str

    _device_state: Optional[DeviceState]
    _running_app: Optional[str]

    _hass: HomeAssistant
    _session: ClientSession
    _websocket: Optional[ClientWebSocketResponse]

    _token: Optional[str]
    _token_update_callback: Callable[[str], None]

    def __init__(self, host: str, name: str, session: ClientSession, hass: HomeAssistant):
        self._session = session
        self._hass = hass
        self._host = host
        self._name = name

        self._device_state = None
        self._running_app = None
        self._connected = asyncio.Event()
        self._websocket = None

        self._token = None
        self._token_update_callback = None

    def _process_response(self, response: str):
        _LOGGING.debug(f"Received: {response}")
        try:
            return json.loads(response)
        except json.JSONDecodeError as err:
            raise ApiError("Invalid TV response") from err

    def _format_rest_url(self, resource_path, protocol="http") -> str:
        return f"{protocol}://{self._host}:8001/api/v2/{resource_path}"

    async def _async_rest_request(self, subresource_path: str):
        url = self._format_rest_url(subresource_path)
        try:
            _LOGGING.debug(f"Request: {url}")
            res = self._session.get(url, verify_ssl=False)

            async with res as response:
                return self._process_response(await response.text())
        except aiohttp.ClientConnectionError as err:
            raise ApiError("Device request failed") from err

    async def _async_get_mac_from_host(self, host):
        ip = await self.hass.async_add_executor_job(
            partial(socket.gethostbyname, host)
        )
        mac = await self.hass.async_add_executor_job(
            partial(getmac.get_mac_address, ip=ip)
        )

        return mac

    async def _async_handle_ws(self):
        name = base64.b64encode(self._name.encode()).decode()
        name = urllib.parse.quote_plus(name)
        ws_url = f"wss://{self._host}:8002/api/v2/channels/samsung.remote.control?name={name}"

        if self._token:
            ws_url += f"&token={self._token}"
        try:
            _LOGGING.debug(f"Connecting to {ws_url}")
            self._websocket = await self._session.ws_connect(ws_url, heartbeat=30)
            _LOGGING.debug("Connecting established")

            async for msg in self._websocket:
                _LOGGING.debug(f"Received: {msg}")
                if msg.type == aiohttp.WSMsgType.TEXT:
                    payload = self._process_response(msg.data)
                    event = payload.get("event")
                    if event == "ms.channel.connect":
                        await self._async_handle_new_token(payload)
                        self._connected.set()

            _LOGGING.debug("Disconnected")
            self._websocket = None
        except (ClientConnectionError, ClientResponseError, TimeoutError):
            _LOGGING.exception('Failed to connect to Yandex Smart Home cloud')
        except Exception:
            _LOGGING.exception('Unexpected exception')

    async def _async_handle_new_token(self, data: Dict):
        if self._token_update_callback:
            response_data = data["data"]
            if "token" in response_data:
                token = response_data["token"]
                self._token_update_callback(token)

    async def _async_connect_ws(self):
        if self._websocket is not None and not self._websocket.closed:
            return

        self._connected = asyncio.Event()
        self._hass.loop.create_task(self._async_handle_ws())

        connection_timeout = WAIT_FOR_CONNECTION_TIMEOUT+WAIT_FOR_AUTH_TIMEOUT
        try:
            await asyncio.wait_for(self._connected.wait(), timeout=connection_timeout)
        except asyncio.TimeoutError:
            raise ConnectionFailed("TV connection timeout")

    async def _async_get_device_state(self) -> DeviceState:
        _LOGGING.debug("Get device info")

        device_info = await self._async_rest_request("")
        device_description = device_info["device"]
        mac = device_description["wifiMac"]
        state = PowerState(device_description["PowerState"])

        return DeviceState(state, mac)

    async def _async_check_running_app(self) -> Optional[str]:
        for app in SUPPORTED_APPS:
            app_id, app_name = app
            app_info = await self._async_rest_request(f"applications/{app_id}")
            if app_info["running"] and app_info["visible"]:
                return app_name
        return None

    def set_token(self, token: str):
        self._token = token

    def register_token_update_callback(self, callback: Callable[[str], None]):
        self._token_update_callback = callback

    async def async_update(self):
        device_state = await self._async_get_device_state()
        if device_state.mac == "none":
            if self._device_state is not None:
                device_state.mac = self._device_state.mac
            else:
                mac = await self.fetch_mac()
                assert mac is not None

                device_state.mac = mac
        self._device_state = device_state
        if self._device_state.state == PowerState.ON:
            self._running_app = await self._async_check_running_app()
        else:
            self._running_app = None

    async def _async_send_ws_message(self, message: str):
        if self._websocket is None or self._websocket.closed:
            await self._async_connect_ws()
        await self._websocket.send_str(message)

    async def async_click_key(self, key: str):
        await self._async_send_ws_message(json.dumps({
            "method": "ms.remote.control",
            "params": {
                "Cmd": "Click",
                "DataOfCmd": key,
                "Option": "false",
                "TypeOfRemote": "SendRemoteKey",
            }
        }))

    async def async_turn_on(self):
        await self.async_update()
        if self._device_state.state == PowerState.ON:
            return
        await self.async_click_key(KEY_POWER)

    async def async_turn_off(self):
        await self.async_update()
        if self._device_state.state == PowerState.STANDBY:
            return
        await self.async_click_key(KEY_POWER)

    async def async_toggle(self):
        await self.async_click_key(KEY_POWER)

    async def fetch_mac(self) -> str:
        if self._device_state is None:
            await self.async_update()
        return self._device_state.mac

    @property
    def name(self) -> str:
        return self._name

    @property
    def host(self) -> str:
        return self._host

    @property
    def is_on(self) -> bool:
        return self._device_state.state == PowerState.ON

    @property
    def running_app(self):
        return self._running_app
