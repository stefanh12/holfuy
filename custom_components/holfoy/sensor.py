
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

SENSOR_TYPES = {
    "wind_speed": ("Wind Speed", "m/s", None),
    "wind_gust": ("Wind Gust", "m/s", None),
    "wind_min": ("Wind Min", "m/s", None),
    "wind_direction": ("Wind Direction", "°", None),
    "temperature": ("Temperature", "°C", "temperature"),
}

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    sensors = []
    for key, (name, unit, device_class) in SENSOR_TYPES.items():
        sensors.append(HolfuySensor(coordinator, key, name, unit, device_class))
    async_add_entities(sensors)

class HolfuySensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, key, name, unit, device_class):
        super().__init__(coordinator)
        self._key = key
        self._name = name
        self._unit = unit
        self._device_class = device_class

    @property
    def name(self):
        return f"Holfuy {self._name}"

    @property
    def state(self):
        data = self.coordinator.data
        if not data:
            return None
        wind = data.get("wind", {})
        if self._key == "wind_speed":
            return wind.get("speed")
        elif self._key == "wind_gust":
            return wind.get("gust")
        elif self._key == "wind_min":
            return wind.get("min")
        elif self._key == "wind_direction":
            return wind.get("direction")
        elif self._key == "temperature":
            return data.get("temperature")

    @property
    def unit_of_measurement(self):
        return self._unit

    @property
    def device_class(self):
        return self._device_class

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        return {
            "station_name": data.get("stationName"),
            "last_update": data.get("dateTime"),
        }
