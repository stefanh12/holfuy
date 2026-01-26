from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfSpeed,
    UnitOfTemperature,
    DEGREE,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import (
    DOMAIN,
    CONF_WIND_UNIT,
    CONF_TEMP_UNIT,
    DEFAULT_WIND_UNIT,
    DEFAULT_TEMP_UNIT,
)

SENSOR_TYPES = {
    "wind_speed": {
        "name": "Wind Speed",
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:weather-windy",
    },
    "wind_gust": {
        "name": "Wind Gust",
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:weather-windy",
    },
    "wind_min": {
        "name": "Wind Min",
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:weather-windy",
    },
    "wind_direction": {
        "name": "Wind Direction",
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:compass",
    },
    "temperature": {
        "name": "Temperature",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:thermometer",
    },
}

# Map custom wind units to HA standard units
WIND_UNIT_MAP = {
    "m/s": UnitOfSpeed.METERS_PER_SECOND,
    "km/h": UnitOfSpeed.KILOMETERS_PER_HOUR,
    "mph": UnitOfSpeed.MILES_PER_HOUR,
    "knots": UnitOfSpeed.KNOTS,
}

TEMP_UNIT_MAP = {
    "C": UnitOfTemperature.CELSIUS,
    "F": UnitOfTemperature.FAHRENHEIT,
}


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Holfuy sensors from a config entry."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = entry_data["coordinator"]
    stations = entry_data["stations"]

    sensors = []

    # Get user-configured units
    su = entry.data.get(CONF_WIND_UNIT, DEFAULT_WIND_UNIT)
    tu = entry.data.get(CONF_TEMP_UNIT, DEFAULT_TEMP_UNIT)

    # Map to HA standard units for display
    wind_unit = WIND_UNIT_MAP.get(su, UnitOfSpeed.METERS_PER_SECOND)
    temp_unit = TEMP_UNIT_MAP.get(tu, UnitOfTemperature.CELSIUS)

    for station in stations:
        for key, sensor_config in SENSOR_TYPES.items():
            if key == "temperature":
                unit = temp_unit
            elif key in ("wind_speed", "wind_gust", "wind_min"):
                unit = wind_unit
            elif key == "wind_direction":
                unit = DEGREE
            else:
                unit = None
            sensors.append(HolfuySensor(coordinator, key, sensor_config, unit, station))

    async_add_entities(sensors)


class HolfuySensor(CoordinatorEntity, SensorEntity):
    """Representation of a Holfuy sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, key, sensor_config, unit, station_id):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._key = key
        self._sensor_config = sensor_config
        self._station_id = str(station_id)
        self._attr_unique_id = f"{DOMAIN}_{self._station_id}_{self._key}"

        # Set device class and state class from config
        self._attr_device_class = sensor_config.get("device_class")
        self._attr_state_class = sensor_config.get("state_class")
        self._attr_icon = sensor_config.get("icon")
        self._attr_name = sensor_config["name"]

        # Set the native unit - this is what the API returns in
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self):
        """Return the state of the sensor."""
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
    def extra_state_attributes(self):
        """Return additional state attributes."""
        data_map = self.coordinator.data or {}
        station_data = data_map.get(self._station_id, {})
        return {
            "station_name": station_data.get("stationName"),
            "last_update": station_data.get("dateTime"),
        }

    @property
    def device_info(self):
        """Return device information."""
        data_map = self.coordinator.data or {}
        station_data = data_map.get(self._station_id, {}) or {}
        station_name = station_data.get("stationName") or f"Station {self._station_id}"
        return {
            "identifiers": {(DOMAIN, self._station_id)},
            "name": station_name,
            "manufacturer": "Holfuy",
            "model": "Weather Station",
        }