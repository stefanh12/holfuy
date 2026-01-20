
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from .const import DOMAIN, CONF_STATION_ID

class HolfuyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="Holfuy", data=user_input)

        schema = vol.Schema({
            vol.Required(CONF_API_KEY): str,
            vol.Required(CONF_STATION_ID): str
        })
        return self.async_show_form(step_id="user", data_schema=schema)
