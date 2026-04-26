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
from homeassistant.helpers.entity import EntityCategory
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
        sensors.append(HolfuyApiStatusSensor(coordinator, station))

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
        if not self.coordinator.data:
            return None

        data_map = self.coordinator.data
        if not isinstance(data_map, dict):
            return None

        station_data = data_map.get(self._station_id)
        if not station_data or not isinstance(station_data, dict):
            return None

        try:
            if self._key in ("wind_speed", "wind_gust", "wind_min", "wind_direction"):
                wind = station_data.get("wind")
                if not wind or not isinstance(wind, dict):
                    return None

                if self._key == "wind_speed":
                    value = wind.get("speed")
                elif self._key == "wind_gust":
                    value = wind.get("gust")
                elif self._key == "wind_min":
                    value = wind.get("min")
                elif self._key == "wind_direction":
                    value = wind.get("direction")
                else:
                    return None

                # Validate numeric value
                if value is not None and not isinstance(value, (int, float)):
                    return None
                return value

            elif self._key == "temperature":
                value = station_data.get("temperature")
                # Validate numeric value
                if value is not None and not isinstance(value, (int, float)):
                    return None
                return value

        except (KeyError, TypeError, AttributeError):
            return None

        return None

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        try:
            if not self.coordinator.data or not isinstance(self.coordinator.data, dict):
                return {}

            station_data = self.coordinator.data.get(self._station_id)
            if not station_data or not isinstance(station_data, dict):
                return {}

            return {
                "station_name": station_data.get("stationName"),
                "last_update": station_data.get("dateTime"),
            }
        except (KeyError, TypeError, AttributeError):
            return {}

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


class HolfuyApiStatusSensor(CoordinatorEntity, SensorEntity):
    """Diagnostic entity reporting API status for a station."""

    _attr_has_entity_name = True
    _attr_name = "API Status"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:api"

    def __init__(self, coordinator, station_id):
        """Initialize the API status sensor."""
        super().__init__(coordinator)
        self._station_id = str(station_id)
        self._attr_unique_id = f"{DOMAIN}_{self._station_id}_api_status"

    @property
    def available(self):
        """Always keep the diagnostic entity available to show failure state."""
        return True

    @property
    def native_value(self):
        """Return API status for this station and latest coordinator update."""
        if not self.coordinator.last_update_success:
            return "error"

        data_map = self.coordinator.data
        if not isinstance(data_map, dict):
            return "no_data"

        if self._station_id not in data_map:
            return "station_unavailable"

        return "ok"

    @property
    def extra_state_attributes(self):
        """Return details helpful for diagnostics."""
        attrs = {
            "station_id": self._station_id,
            "last_update_success": self.coordinator.last_update_success,
            "update_interval_seconds": int(self.coordinator.update_interval.total_seconds()),
        }

        if self.coordinator.last_exception is not None:
            attrs["last_error"] = str(self.coordinator.last_exception)

        data_map = self.coordinator.data
        if isinstance(data_map, dict) and self._station_id in data_map:
            station_data = data_map.get(self._station_id) or {}
            if isinstance(station_data, dict):
                attrs["last_station_update"] = station_data.get("dateTime")

        return attrs

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