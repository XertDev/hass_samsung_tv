from homeassistant import exceptions


class ConnectionFailed(exceptions.HomeAssistantError):
    """Connection error."""


class AuthenticationFailed(exceptions.HomeAssistantError):
    """TV authentication failed."""

class ApiError(exceptions.HomeAssistantError):
    """Api error."""