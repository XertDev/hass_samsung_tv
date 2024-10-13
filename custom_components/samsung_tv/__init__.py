from homeassistant.const import CONF_NAME, CONF_HOST, Platform, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import CONF_POLLING_RATE
from .coordinator import SamsungCoordinator
from .device import SamsungDevice

PLATFORMS = [Platform.MEDIA_PLAYER, Platform.REMOTE]

type SamsungConfigEntry = ConfigEntry[SamsungCoordinator]

async def async_setup_entry(hass: HomeAssistant, entry: SamsungConfigEntry) -> bool:
    """Set up Samsung TV from config entry."""
    session = async_create_clientsession(hass, verify_ssl=False)

    samsung_device = SamsungDevice(entry.data[CONF_HOST], entry.data[CONF_NAME], session, hass)
    mac = await samsung_device.fetch_mac()
    samsung_coordinator = SamsungCoordinator(hass, samsung_device, mac, entry.data[CONF_POLLING_RATE])

    entry.runtime_data = samsung_coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def stop_device(event=None) -> None:
        await samsung_device.async_close()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_device),
    )
    entry.async_on_unload(stop_device)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return True
