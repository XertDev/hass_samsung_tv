from typing import Any, Iterable

from homeassistant.components.remote import RemoteEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SamsungConfigEntry, SamsungDevice
from .entity import SamsungEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SamsungConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities([SamsungRemote(coordinator=coordinator)])


class SamsungRemote(SamsungEntity, RemoteEntity):
    _attr_name = None

    @callback
    def _handle_coordinator_update(self) -> None:
        device = self.coordinator.device
        self._attr_is_on = device.is_on
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        device: SamsungDevice = self.coordinator.device
        await device.async_turn_off()

    async def async_turn_on(self, **kwargs: Any) -> None:
        device: SamsungDevice = self.coordinator.device
        await device.async_turn_on()

    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        device: SamsungDevice = self.coordinator.device
        for key in command:
            await device.async_click_key(key)