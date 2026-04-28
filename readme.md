[![Validate with hassfest](https://github.com/stefanh12/holfuy/actions/workflows/hassfest.yaml/badge.svg)](https://github.com/stefanh12/holfuy/actions/workflows/hassfest.yaml)
[![HACS Action](https://github.com/stefanh12/holfuy/actions/workflows/hacs-validate.yml/badge.svg)](https://github.com/stefanh12/holfuy/actions/workflows/hacs-validate.yml)
[![Release](https://github.com/stefanh12/holfuy/actions/workflows/release.yml/badge.svg)](https://github.com/stefanh12/holfuy/actions/workflows/release.yml)
[![Dependabot Updates](https://github.com/stefanh12/holfuy/actions/workflows/dependabot/dependabot-updates/badge.svg)](https://github.com/stefanh12/holfuy/actions/workflows/dependabot/dependabot-updates)
# Holfuy Weather Integration for Home Assistant

This custom component integrates **Holfuy weather station data** into Home Assistant using the Holfuy API.

## About Holfuy

Holfuy is a network of real-time weather stations specifically designed for aviation, paragliding, hang gliding, and outdoor sports enthusiasts. The service provides:

- **Live wind data** from weather stations located at popular flying sites and outdoor locations worldwide
- **Real-time measurements** including wind speed, wind gusts, wind direction, and temperature
- **Reliable data** Uses high quality hardware

Instructions on how to obtain an API key can be found here: https://api.holfuy.com/
This integration is not created by Holfuy but it has been reviewed by the Holfuy team.

**To use the integration you need an API key from Holfuy!** 


## Features

- **Supports multiple stations** (up to 3) in a single API call for efficient polling
- Fetches real-time data from Holfuy stations:
  - Wind Speed
  - Wind Gust
  - Wind Min
  - Wind Direction
  - Temperature
- Includes station name and last update timestamp as attributes
- Uses **DataUpdateCoordinator** for efficient updates
- **Intelligent error handling**:
  - Automatic API throttling with exponential backoff on errors
  - Self-recovery when API becomes available again
    **Configurable units** - Select your preferred wind speed (m/s, knots, km/h, mph) and temperature units (°C, °F)
  - Units are set during integration setup and can be changed via Options
  - **Important for Sweden and other regions**: Choose m/s for wind speed since Home Assistant's default Metric system shows km/h
  - Wind sensors display in the exact unit you select from the API
  - Temperature sensors use device class for proper display in Home Assistant
- Configurable units for wind speed and temperature
- **Real-time validation** during setup:
  - API key verification
  - Station ID accessibility checks
  - Comprehensive error messages for invalid configurations
- Supports 17+ languages including English, Spanish, German, French, Swedish, Norwegian, Danish, Finnish, Dutch, Italian, Polish, Portuguese, Greek, Czech, Ukrainian, Romanian, and Japanese

## Installation via HACS

1. Go to **HACS → Integrations → Custom Repositories**.
2. Add your repository URL:
   `https://github.com/stefanh12/holfuy`
3. Select **Integration**.
4. Restart Home Assistant.
5. Install the integration via HACS.

## Manual Installation

1. Copy `custom_components/holfuy` to your Home Assistant `custom_components` folder.
2. Restart Home Assistant.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration → Holfuy**.
2. Enter:
   - **API Key** - Your Holfuy API key
   - **Station IDs** (comma-separated, e.g., `601, 1435, 2045`) - up to 3 stations
   - **Wind Speed Unit** - Choose m/s, knots, km/h, or mph
3. Once validated, sensors will be created for each station in your selected units.
4. You can modify the configuration (including units)your credentials\*\* by testing the API key and each station ID:
   - Verifies the API key is valid and authorized
   - Confirms each station ID is accessible with your API key
   - Displays specific error messages if validation fails (invalid API key, inaccessible stations, connection issues, etc.)
5. Once validated, sensors will be created for each station.
6. You can modify the configuration later via **Devices & Services → Holfuy → Configure**.

### Validation Errors

During setup, you may encounter these validation errors:

- **Invalid API key** - The API key is not recognized or unauthorized
- **Invalid station ID** - One or more station IDs are not accessible with your API key
- **Cannot connect** - Unable to reach the Holfuy API (check your internet connection)
- **Timeout** - API request took too long (try again)
- **Invalid station IDs format** - Station IDs must be integers between 0 and 65000

### Unit Selection

When setting up the integration, you'll choose units for:

- **Wind Speed**: m/s, knots, km/h, or mph
- **Temperature**: °C or °F

**Regional Note**: If you're in Sweden or other regions that use m/s for wind speed, be sure to select **m/s** during setup. Home Assistant's default Metric system uses km/h for wind, so selecting your preferred unit ensures the data displays correctly.

You can change units anytime via **Settings → Devices & Services → Holfuy → Configure**.


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
