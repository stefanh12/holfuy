import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from .const import (
    DOMAIN,
    CONF_STATION_ID,
    CONF_WIND_UNIT,
    CONF_TEMP_UNIT,
    DEFAULT_WIND_UNIT,
    DEFAULT_TEMP_UNIT,
)

WIND_UNIT_OPTIONS = ["knots", "km/h", "m/s", "mph"]
TEMP_UNIT_OPTIONS = ["C", "F"]


class HolfuyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        """Handle the initial config flow."""
        if user_input is not None:
            # Save the chosen units together with API key and station
            return self.async_create_entry(title="Holfuy", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): str,
                vol.Required(CONF_STATION_ID): str,
                vol.Required(CONF_WIND_UNIT, default=DEFAULT_WIND_UNIT): vol.In(WIND_UNIT_OPTIONS),
                vol.Required(CONF_TEMP_UNIT, default=DEFAULT_TEMP_UNIT): vol.In(TEMP_UNIT_OPTIONS),
            }
        )
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
        if user_input is not None:
            # Merge existing data with new values and update the entry
            new_data = {**self._config_entry.data, **user_input}
            self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)
            return self.async_create_entry(title="", data={})

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_API_KEY, default=self._config_entry.data.get(CONF_API_KEY, "")
                ): str,
                vol.Required(
                    CONF_STATION_ID, default=self._config_entry.data.get(CONF_STATION_ID, "")
                ): str,
                vol.Required(
                    CONF_WIND_UNIT,
                    default=self._config_entry.data.get(CONF_WIND_UNIT, DEFAULT_WIND_UNIT),
                ): vol.In(WIND_UNIT_OPTIONS),
                vol.Required(
                    CONF_TEMP_UNIT,
                    default=self._config_entry.data.get(CONF_TEMP_UNIT, DEFAULT_TEMP_UNIT),
                ): vol.In(TEMP_UNIT_OPTIONS),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)