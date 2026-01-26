# Holfuy Weather Integration for Home Assistant

This custom component integrates **Holfuy weather station data** into Home Assistant using the Holfuy API.

## About Holfuy

Holfuy is a network of real-time weather stations specifically designed for aviation, paragliding, hang gliding, and outdoor sports enthusiasts. The service provides:

- **Live wind data** from weather stations located at popular flying sites and outdoor locations worldwide
- **Real-time measurements** including wind speed, wind gusts, wind direction, and temperature
- **Reliable data** used by pilots and outdoor enthusiasts for safety and activity planning
- **API access** for developers to integrate station data into their applications

Instructions on how to obtain an API key can be found here: https://api.holfuy.com/

**To use the integration you need an API key from Holfuy!** You need to contact Holfuy to obtain the key and the key is valid for up to 3 stations.

## How It Works

This integration:

- **Polls the Holfuy API** at regular intervals to fetch real-time weather data from your configured stations
- **Supports multiple stations** (up to 3) in a single API call for efficient polling
- **Creates individual sensors** for each station and each measurement type (wind speed, gust, min, direction, temperature)
- **Uses a DataUpdateCoordinator** for efficient background updates and automatic error handling
- **Configurable units** - Choose your preferred wind speed unit (m/s, knots, km/h, mph) and temperature unit (°C, °F)
- **Config flow integration** - Easy setup through the Home Assistant UI with validation of station IDs
- **Live API validation** - Validates API key and station IDs during setup by making actual API calls

### Technical Details

- API requests include unit parameters (`tu` for temperature, `su` for wind speed)
- Attempts combined API calls first for efficiency, falls back to individual station requests if needed
- Handles various API response formats (dict, list, combined or individual station data)
- Station IDs are validated (0-65000 range) and duplicates are automatically removed
- **API key and station validation** - During setup, the integration tests each station ID with your API key to ensure they are valid and accessible
- Configuration is stored in Home Assistant config entries and can be modified via Options Flow

## Features

- Fetches real-time data from Holfuy stations:
  - Wind Speed
  - Wind Gust
  - Wind Min
  - Wind Direction
  - Temperature
- Includes station name and last update timestamp as attributes
- Uses **DataUpdateCoordinator** for efficient updates
- Configurable units for wind speed and temperature
- **Real-time validation** during setup:
  - API key verification
  - Station ID accessibility checks
  - Comprehensive error messages for invalid configurations
- Supports 17+ languages including English, Spanish, German, French, Swedish, Norwegian, Danish, Finnish, Dutch, Italian, Polish, Portuguese, Greek, Czech, Ukrainian, Romanian, and Japanese

## Installation via HACS

1. Go to **HACS → Integrations → Custom Repositories**.
2. Add your repository URL:
   `https://github.com/stefanh12/holfuy-homeassistant`
3. Select **Integration**.
4. Restart Home Assistant.
5. Install the integration via HACS.

## Manual Installation

1. Copy `custom_components/holfuy` to your Home Assistant `custom_components` folder.
2. Restart Home Assistant.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration → Holfuy**.
2. Enter:**validate your credentials** by testing the API key and each station ID:
   - Verifies the API key is valid and authorized
   - Confirms each station ID is accessible with your API key
   - Displays specific error messages if validation fails (invalid API key, inaccessible stations, connection issues, etc.)
3. Once validated, sensors will be created for each station.
4. You can modify the configuration later via **Devices & Services → Holfuy → Configure**.

### Validation Errors

During setup, you may encounter these validation errors:

- **Invalid API key** - The API key is not recognized or unauthorized
- **Invalid station ID** - One or more station IDs are not accessible with your API key
- **Cannot connect** - Unable to reach the Holfuy API (check your internet connection)
- **Timeout** - API request took too long (try again)
- **Invalid station IDs format** - Station IDs must be integers between 0 and 65000
  - **Station IDs** (comma-separated, e.g., `601, 1435, 2045`) - up to 3 stations
  - **Wind Speed Unit** (m/s, knots, km/h, or mph)
  - **Temperature Unit** (°C or °F)

3. The integration will validate your station IDs and create sensors for each station.
4. You can modify the configuration later via **Devices & Services → Holfuy → Configure**.

## Example Sensors

- `sensor.holfuy_wind_speed`
- `sensor.holfuy_temperature`

## 🌍 Lovelace Dashboard Example

You can visualize wind direction and speed using the https://github.com/tomvanswam/compass-card/ in your Lovelace dashboard.

### Example YAML:

```yaml
type: custom:compass-card
header:
title:
 value: Wind
indicator_sensors:
- sensor: sensor.holfuy_station_direction
 indicator:
   image: arrow_inward
value_sensors:
- sensor: sensor.holfuy_station_speed
- sensor: sensor.holfuy_station_gust
```

## Credits

Developed for Home Assistant using Holfuy API.
