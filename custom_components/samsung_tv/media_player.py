from homeassistant.components.media_player import MediaPlayerEntity, MediaPlayerState, MediaPlayerDeviceClass
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SamsungConfigEntry
from .device import SamsungDevice
from .coordinator import SamsungCoordinator
from .entity import SamsungEntity
from .const import BASE_PLAYER_SUPPORTED_FEATURES
from .const import KEY_MUTE, KEY_VOLUME_UP, KEY_VOLUME_DOWN


async def async_setup_entry(
        hass: HomeAssistant,
        entry: SamsungConfigEntry,
        async_add_entities: AddEntitiesCallback
) -> None:

    coordinator = entry.runtime_data
    async_add_entities([SamsungMediaPlayer(coordinator)])


class SamsungMediaPlayer(SamsungEntity, MediaPlayerEntity):
    _attr_device_class = MediaPlayerDeviceClass.TV

    def __init__(self, coordinator: SamsungCoordinator):
        super().__init__(coordinator=coordinator)

        self._attr_supported_features = BASE_PLAYER_SUPPORTED_FEATURES

    @callback
    def _handle_coordinator_update(self) -> None:
        device = self.coordinator.device
        if device.is_on:
            if device.running_app:
                self._attr_state = MediaPlayerState.PLAYING
                if device.running_app:
                    self._attr_app_name = device.running_app
                else:
                    self._attr_app_name = None
            else:
                self._attr_state = MediaPlayerState.ON
        else:
            self._attr_state = MediaPlayerState.OFF
        self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        device: SamsungDevice = self.coordinator.device
        await device.async_turn_on()

    async def async_turn_off(self) -> None:
        device: SamsungDevice = self.coordinator.device
        await device.async_turn_off()

    async def async_toggle(self) -> None:
        device: SamsungDevice = self.coordinator.device
        await device.async_toggle()

    async def async_mute_volume(self, mute: bool) -> None:
        device: SamsungDevice = self.coordinator.device
        await device.async_click_key(KEY_MUTE)

    async def async_volume_up(self) -> None:
        device: SamsungDevice = self.coordinator.device
        await device.async_click_key(KEY_VOLUME_UP)

    async def async_volume_down(self) -> None:
        device: SamsungDevice = self.coordinator.device
        await device.async_click_key(KEY_VOLUME_DOWN)
