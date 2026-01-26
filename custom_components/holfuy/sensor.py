from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import (
    DOMAIN,
    CONF_WIND_UNIT,
    CONF_TEMP_UNIT,
    DEFAULT_WIND_UNIT,
    DEFAULT_TEMP_UNIT,
    CONF_STATION_IDS,
)

SENSOR_TYPES = {
    "wind_speed": ("Wind Speed", None),
    "wind_gust": ("Wind Gust", None),
    "wind_min": ("Wind Min", None),
    "wind_direction": ("Wind Direction", None),
    "temperature": ("Temperature", "temperature"),
}


async def async_setup_entry(hass, entry, async_add_entities):
    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = entry_data["coordinator"]
    stations = entry_data["stations"]

    sensors = []

    su = entry.data.get(CONF_WIND_UNIT, DEFAULT_WIND_UNIT)
    tu = entry.data.get(CONF_TEMP_UNIT, DEFAULT_TEMP_UNIT)
    temp_display_unit = "°C" if tu == "C" else "°F"

    for station in stations:
        for key, (name, device_class) in SENSOR_TYPES.items():
            if key == "temperature":
                unit = temp_display_unit
            elif key in ("wind_speed", "wind_gust", "wind_min"):
                unit = su
            else:
                unit = None
            sensors.append(HolfuySensor(coordinator, key, name, unit, device_class, station))

    async_add_entities(sensors)


class HolfuySensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, key, name, unit, device_class, station_id):
        super().__init__(coordinator)
        self._key = key
        self._name = name
        self._unit = unit
        self._device_class = device_class
        self._station_id = str(station_id)
        self._unique_id = f"{self._station_id}_{self._key}"

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        return f"Holfuy {self._name} ({self._station_id})"

    @property
    def state(self):
        data_map = self.coordinator.data or {}
        station_data = data_map.get(self._station_id)
        if not station_data:
            return None
        wind = station_data.get("wind", {}) if isinstance(station_data, dict) else {}
        if self._key == "wind_speed":
            return wind.get("speed")
        elif self._key == "wind_gust":
            return wind.get("gust")
        elif self._key == "wind_min":
            return wind.get("min")
        elif self._key == "wind_direction":
            return wind.get("direction")
        elif self._key == "temperature":
            return station_data.get("temperature")
        return None

    @property
    def unit_of_measurement(self):
        return self._unit

    @property
    def device_class(self):
        return self._device_class

    @property
    def extra_state_attributes(self):
        data_map = self.coordinator.data or {}
        station_data = data_map.get(self._station_id, {})
        return {
            "station_name": station_data.get("stationName"),
            "last_update": station_data.get("dateTime"),
        }

    @property
    def device_info(self):
        data_map = self.coordinator.data or {}
        station_data = data_map.get(self._station_id, {}) or {}
        station_name = station_data.get("stationName") or f"Holfuy {self._station_id}"
        return {
            "identifiers": {(DOMAIN, self._station_id)},
            "name": station_name,
            "manufacturer": "Holfuy",
            "model": "Weather Station",
        }