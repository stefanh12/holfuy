import re
import asyncio
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
import aiohttp
import async_timeout
from .const import (
    DOMAIN,
    CONF_STATION_IDS,
    CONF_WIND_UNIT,
    CONF_TEMP_UNIT,
    DEFAULT_WIND_UNIT,
    DEFAULT_TEMP_UNIT,
    API_URL,
)

_LOGGER = logging.getLogger(__name__)

WIND_UNIT_OPTIONS = ["knots", "km/h", "m/s", "mph"]
TEMP_UNIT_OPTIONS = ["C", "F"]
MAX_STATIONS = 3
MAX_STATION_ID = 65000


async def _validate_api_key_and_stations(api_key: str, stations: list[str], tu: str, su: str):
    """Validate API key and stations by making test API calls.

    Returns a dict with validation results:
    - {"valid": True} if all successful
    - {"valid": False, "error": "error_key"} if validation fails
    """
    if not api_key or not api_key.strip():
        return {"valid": False, "error": "invalid_api_key"}

    if not stations:
        return {"valid": False, "error": "invalid_station_ids"}

    # Test each station ID with the API key
    async with aiohttp.ClientSession() as session:
        for station in stations:
            url = API_URL.format(station=station, api_key=api_key, tu=tu, su=su)
            try:
                async with async_timeout.timeout(10):
                    async with session.get(url) as resp:
                        if resp.status == 401 or resp.status == 403:
                            return {"valid": False, "error": "invalid_api_key"}
                        if resp.status != 200:
                            return {"valid": False, "error": "cannot_connect"}

                        try:
                            data = await resp.json()
                        except (aiohttp.ContentTypeError, ValueError):
                            return {"valid": False, "error": "invalid_response"}

                        # Check if the response indicates an error
                        if isinstance(data, dict):
                            # Some APIs return error messages in the response
                            if data.get("error") or data.get("status") == "error":
                                # Could be invalid station or API key
                                error_msg = str(data.get("error", data.get("message", ""))).lower()
                                if "api" in error_msg or "key" in error_msg or "auth" in error_msg:
                                    return {"valid": False, "error": "invalid_api_key"}
                                else:
                                    return {"valid": False, "error": "invalid_station_id", "station": station}
            except aiohttp.ClientError:
                return {"valid": False, "error": "cannot_connect"}
            except asyncio.TimeoutError:
                return {"valid": False, "error": "timeout"}
            except ValueError:
                return {"valid": False, "error": "invalid_response"}
            except Exception as err:
                _LOGGER.exception("Unexpected error during validation: %s", err)
                return {"valid": False, "error": "unknown"}

    return {"valid": True}


def _normalize_station_input(value: str):
    """Extract integers from the provided string, trim duplicates and validate.

    Accepts inputs like:
      - "601,602"
      - "601, 602"
      - "601;602"
      - "[601,602]"
      - "601\n602"
      - "601 602"
    Returns a list of station id strings.
    Raises vol.Invalid("invalid_station_ids") on validation errors.
    """
    if not isinstance(value, str) or not value.strip():
        raise vol.Invalid("invalid_station_ids")

    # Find all integer substrings
    parts = re.findall(r"\d+", value)
    if not parts:
        raise vol.Invalid("invalid_station_ids")

    # Trim duplicates while preserving order
    seen = set()
    unique_parts = []
    for p in parts:
        if p in seen:
            continue
        seen.add(p)
        unique_parts.append(p)

    if len(unique_parts) > MAX_STATIONS:
        raise vol.Invalid("invalid_station_ids")

    normalized = []
    for p in unique_parts:
        n = int(p)
        if n < 0 or n > MAX_STATION_ID:
            raise vol.Invalid("invalid_station_ids")
        normalized.append(str(n))  # store as string for consistency

    return normalized


class HolfuyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        """Handle the initial config flow."""
        schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): str,
                vol.Required(CONF_STATION_IDS, default=""): str,
                vol.Required(CONF_WIND_UNIT, default=DEFAULT_WIND_UNIT): vol.In(WIND_UNIT_OPTIONS),
                vol.Required(CONF_TEMP_UNIT, default=DEFAULT_TEMP_UNIT): vol.In(TEMP_UNIT_OPTIONS),
            }
        )

        if user_input is not None:
            station_input = user_input.pop(CONF_STATION_IDS)
            try:
                stations = _normalize_station_input(station_input)
            except vol.Invalid:
                # Use a translation key for the error so strings.json can provide the message
                return self.async_show_form(step_id="user", data_schema=schema, errors={"base": "invalid_station_ids"})

            # Validate API key and stations by making test API calls
            api_key = user_input[CONF_API_KEY]
            # Always use standard units for API requests
            tu = "C"
            su = "m/s"

            validation_result = await _validate_api_key_and_stations(api_key, stations, tu, su)
            if not validation_result["valid"]:
                error_key = validation_result["error"]
                if error_key == "invalid_station_id":
                    # Include specific station ID in error if available
                    station = validation_result.get("station")
                    error_key = f"invalid_station_id_{station}" if station else "invalid_station_id"
                return self.async_show_form(step_id="user", data_schema=schema, errors={"base": error_key})

            data = {**user_input, CONF_STATION_IDS: stations}
            return self.async_create_entry(title="Holfuy", data=data)

        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return options flow handler."""
        return HolfuyOptionsFlow(config_entry)


class HolfuyOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        """Store the provided config_entry without overwriting the base property."""
        super().__init__()
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options for the integration."""
        existing = self._config_entry.data

        stations_default = ",".join(existing.get(CONF_STATION_IDS, []))

        schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY, default=existing.get(CONF_API_KEY, "")): str,
                vol.Required(CONF_STATION_IDS, default=stations_default): str,
                vol.Required(
                    CONF_WIND_UNIT,
                    default=existing.get(CONF_WIND_UNIT, DEFAULT_WIND_UNIT),
                ): vol.In(WIND_UNIT_OPTIONS),
                vol.Required(
                    CONF_TEMP_UNIT,
                    default=existing.get(CONF_TEMP_UNIT, DEFAULT_TEMP_UNIT),
                ): vol.In(TEMP_UNIT_OPTIONS),
            }
        )

        if user_input is not None:
            station_input = user_input.pop(CONF_STATION_IDS)
            try:
                stations = _normalize_station_input(station_input)
            except vol.Invalid:
                return self.async_show_form(step_id="init", data_schema=schema, errors={"base": "invalid_station_ids"})

            # Validate API key and stations by making test API calls
            api_key = user_input[CONF_API_KEY]
            tu = user_input.get(CONF_TEMP_UNIT, DEFAULT_TEMP_UNIT)
            su = user_input.get(CONF_WIND_UNIT, DEFAULT_WIND_UNIT)

            validation_result = await _validate_api_key_and_stations(api_key, stations, tu, su)
            if not validation_result["valid"]:
                error_key = validation_result["error"]
                if error_key == "invalid_station_id":
                    station = validation_result.get("station")
                    error_key = f"invalid_station_id_{station}" if station else "invalid_station_id"
                return self.async_show_form(step_id="init", data_schema=schema, errors={"base": error_key})

            new_data = {**self._config_entry.data, **user_input, CONF_STATION_IDS: stations}
            self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(step_id="init", data_schema=schema)