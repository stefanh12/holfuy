
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.helpers import config_validation as cv
from .const import DOMAIN, CONF_STATION_ID

class HolfuyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Holfuy."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate the input
            api_key = user_input.get(CONF_API_KEY, "").strip()
            station_id = user_input.get(CONF_STATION_ID, "").strip()

            if not api_key:
                errors[CONF_API_KEY] = "required"
            if not station_id:
                errors[CONF_STATION_ID] = "required"

            if not errors:
                # Create a unique ID based on station ID
                await self.async_set_unique_id(station_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Holfuy Station {station_id}",
                    data={CONF_API_KEY: api_key, CONF_STATION_ID: station_id}
                )

        # Show the form
        schema = vol.Schema({
            vol.Required(CONF_API_KEY): str,
            vol.Required(CONF_STATION_ID): str
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors
        )
