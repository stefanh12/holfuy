from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, CONF_WIND_UNIT, CONF_TEMP_UNIT, DEFAULT_WIND_UNIT, DEFAULT_TEMP_UNIT, CONF_STATION_ID

# Keep sensor type names and device class where applicable; units will be set per-entry
SENSOR_TYPES = {
    "wind_speed": ("Wind Speed", None),
    "wind_gust": ("Wind Gust", None),
    "wind_min": ("Wind Min", None),
    "wind_direction": ("Wind Direction", None),
    "temperature": ("Temperature", "temperature"),
}


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    sensors = []

    # Get configured units for this entry (fallback to defaults)
    su = entry.data.get(CONF_WIND_UNIT, DEFAULT_WIND_UNIT)
    tu = entry.data.get(CONF_TEMP_UNIT, DEFAULT_TEMP_UNIT)

    # Map temperature unit to display unit
    temp_display_unit = "°C" if tu == "C" else "°F"

    # For wind sensors use su directly (API and display strings use same values like "m/s", "km/h", "knots", "mph")
    wind_unit_display = su

    station_id = entry.data.get(CONF_STATION_ID)

    for key, (name, device_class) in SENSOR_TYPES.items():
        if key == "temperature":
            unit = temp_display_unit
        elif key in ("wind_speed", "wind_gust", "wind_min"):
            unit = wind_unit_display
        else:
            unit = None

        sensors.append(HolfuySensor(coordinator, key, name, unit, device_class, station_id))

    async_add_entities(sensors)


class HolfuySensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, key, name, unit, device_class, station_id):
        super().__init__(coordinator)
        self._key = key
        self._name = name
        self._unit = unit
        self._device_class = device_class
        self._station_id = str(station_id)
        # stable unique id for the entity
        self._unique_id = f"{self._station_id}_{self._key}"

    @property
    def unique_id(self):
        return self._unique_id

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

    @property
    def device_info(self):
        """Return device information for this entity.

        Entities that return the same identifiers will be grouped under the same device.
        """
        data = self.coordinator.data or {}
        station_name = data.get("stationName") or f"Holfuy {self._station_id}"
        return {
            "identifiers": {(DOMAIN, self._station_id)},  # unique device identifier
            "name": station_name,
            "manufacturer": "Holfuy",
            "model": "Weather Station",
        }