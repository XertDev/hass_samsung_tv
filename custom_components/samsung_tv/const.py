import logging

from homeassistant.components.media_player import MediaPlayerEntityFeature

LOGGER = logging.getLogger(__package__)

NAME = "samsung_tv"
DOMAIN = "samsung_tv"

CONF_HOST = "host"
CONF_NAME = "name"
CONF_POLLING_RATE = "polling_rate"

CONF_MAC = "mac"

KEY_POWER = "KEY_POWER"

DEFAULT_POLLING_RATE = 10

WAIT_FOR_CONNECTION_TIMEOUT = 10
WAIT_FOR_AUTH_TIMEOUT = 60

BASE_PLAYER_SUPPORTED_FEATURES = (
    MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.TURN_ON
)
