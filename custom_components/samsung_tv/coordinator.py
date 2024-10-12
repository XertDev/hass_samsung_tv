from datetime import timedelta

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import LOGGER
from .const import DOMAIN
from .device import SamsungDevice


class SamsungCoordinator(DataUpdateCoordinator):
    _device: SamsungDevice
    _mac: str

    def __init__(self, hass: HomeAssistant, device: SamsungDevice, mac: str, polling_rate: float) -> None:
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=polling_rate)
        )

        self._device = device
        self._mac = mac
        self._device.register_token_update_callback(self._on_token_updated)
        if "token" in self.config_entry.data:
            token = self.config_entry.data["token"]
            device.set_token(token)

    @property
    def device(self) -> SamsungDevice:
        return self._device

    @property
    def mac(self) -> str:
        return self._mac

    @callback
    def _on_token_updated(self, token) -> None:
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data={
                **self.config_entry.data,
                "token": token
            }
        )

    async def _async_update_data(self) -> None:
        if self.hass.is_stopping:
            return

        await self._device.async_update()
