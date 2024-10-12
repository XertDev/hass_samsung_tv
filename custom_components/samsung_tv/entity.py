from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import Entity, DeviceInfo
from homeassistant.helpers import device_registry

from .const import DOMAIN
from .const import CONF_MAC, CONF_NAME
from .coordinator import SamsungCoordinator


class SamsungEntity(CoordinatorEntity[SamsungCoordinator], Entity):
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, *, coordinator: SamsungCoordinator) -> None:
        super().__init__(coordinator)

        config_entry = coordinator.config_entry

        self._device = coordinator.device

        self._attr_unique_id = config_entry.unique_id or config_entry.entry_id
        self._attr_device_info = {
            "name": config_entry.data.get(CONF_NAME),
            "manufacturer": "Samsung",
        }

        if self.unique_id:
            self._attr_device_info["identifiers"] = {(DOMAIN, self.unique_id)}
        self._attr_device_info["connections"] = {
            (device_registry.CONNECTION_NETWORK_MAC, config_entry.data.get(CONF_MAC))
        }
