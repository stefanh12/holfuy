import logging
import asyncio
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import aiohttp
import async_timeout

from .const import (
    DOMAIN,
    API_URL,
    CONF_API_KEY,
    CONF_STATION_IDS,
    CONF_WIND_UNIT,
    CONF_TEMP_UNIT,
    DEFAULT_WIND_UNIT,
    DEFAULT_TEMP_UNIT,
)

_LOGGER = logging.getLogger(__name__)

# Update intervals
DEFAULT_UPDATE_INTERVAL = timedelta(minutes=2)
MAX_UPDATE_INTERVAL = timedelta(minutes=10)
MIN_UPDATE_INTERVAL = timedelta(minutes=1)


async def _fetch_json(session: aiohttp.ClientSession, url: str):
    async with async_timeout.timeout(10):
        async with session.get(url) as resp:
            return await resp.json()


def _build_url(api_key: str, stations: list[str], tu: str, su: str, station=None):
    # If station is provided, build URL for single station, else build combined
    if station is not None:
        s = station
    else:
        s = ",".join(stations)
    return API_URL.format(station=s, api_key=api_key, tu=tu, su=su)


def _parse_combined_response(response, stations: list[str]) -> dict | None:
    """Try to parse response into a mapping station_id -> station_data.

    Accepts multiple common shapes:
    - dict keyed by station id
    - dict containing 'stations' / 'data' list
    - list of station objects
    - if response looks like a single station dict, return None to indicate fallback
    """
    if response is None:
        return {}

    # If response is a dict keyed by station id (e.g. {"601": {...}, "602": {...}})
    if isinstance(response, dict):
        keys = list(response.keys())
        if keys and all(any(k == s or k == str(s) for s in stations) for k in keys):
            return {str(k): v for k, v in response.items()}

        # If response contains a 'stations' or 'data' list
        for list_key in ("stations", "data", "stationsData"):
            if list_key in response and isinstance(response[list_key], list):
                lst = response[list_key]
                mapping = {}
                for item in lst:
                    if not isinstance(item, dict):
                        continue
                    for id_key in ("station", "stationId", "id", "s"):
                        if id_key in item:
                            mapping[str(item[id_key])] = item
                            break
                if mapping:
                    return mapping

        # If response appears to be a single station (has wind/temperature fields) return None to indicate fallback
        if any(k in response for k in ("wind", "temperature", "stationName", "dateTime")):
            return None

    # If response is a list, map items by id
    if isinstance(response, list):
        mapping = {}
        for item in response:
            if not isinstance(item, dict):
                continue
            for id_key in ("station", "stationId", "id", "s"):
                if id_key in item:
                    mapping[str(item[id_key])] = item
                    break
        if mapping:
            return mapping

    # Unknown shape — indicate fallback required
    return None


def _make_update_method(api_key: str, stations: list[str], tu: str, su: str, coordinator):
    """Create the update method with error tracking for throttling."""
    consecutive_errors = 0

    async def async_update_data():
        nonlocal consecutive_errors

        try:
            # Try one combined request first
            async with aiohttp.ClientSession() as session:
                combined_url = _build_url(api_key, stations, tu, su, station=None)
                try:
                    response = await _fetch_json(session, combined_url)
                except Exception as err:
                    _LOGGER.debug("Combined request failed: %s", err)
                    response = None

                parsed = _parse_combined_response(response, stations)
                if parsed is not None:
                    # Successful combined response parsed into mapping station -> data
                    consecutive_errors = 0
                    # Restore normal update interval on success
                    if coordinator.update_interval != DEFAULT_UPDATE_INTERVAL:
                        coordinator.update_interval = DEFAULT_UPDATE_INTERVAL
                        _LOGGER.info("API calls successful, restored normal update interval")
                    return parsed

                # Fallback: if combined response couldn't be broken down, issue parallel requests per station
                tasks = []
                for station in stations:
                    url = _build_url(api_key, stations, tu, su, station=station)
                    tasks.append(_fetch_json(session, url))
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Map results to station ids
                mapping = {}
                has_errors = False
                for station, res in zip(stations, results):
                    if isinstance(res, Exception):
                        _LOGGER.warning("Error fetching data for station %s: %s", station, res)
                        has_errors = True
                        continue
                    mapping[str(station)] = res

                # If we got at least some data, reset error counter
                if mapping:
                    consecutive_errors = 0
                    if coordinator.update_interval != DEFAULT_UPDATE_INTERVAL:
                        coordinator.update_interval = DEFAULT_UPDATE_INTERVAL
                        _LOGGER.info("API calls successful, restored normal update interval")
                    return mapping

                # All stations failed
                if has_errors:
                    raise UpdateFailed("All station requests failed")

                return mapping

        except Exception as err:
            consecutive_errors += 1

            # Implement exponential backoff
            if consecutive_errors > 1:
                new_interval = min(
                    DEFAULT_UPDATE_INTERVAL * (2 ** (consecutive_errors - 1)),
                    MAX_UPDATE_INTERVAL
                )
                if coordinator.update_interval != new_interval:
                    coordinator.update_interval = new_interval
                    _LOGGER.warning(
                        "API errors detected (%d consecutive), throttling updates to %s",
                        consecutive_errors,
                        new_interval
                    )

            raise UpdateFailed(f"Error fetching Holfuy data: {err}")

    return async_update_data


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    api_key = entry.data.get(CONF_API_KEY)
    stations = entry.data.get(CONF_STATION_IDS, [])
    if not stations:
        _LOGGER.error("No station IDs configured for Holfuy entry %s", entry.entry_id)
        return False

    # Get user's preferred units from config entry
    su = entry.data.get(CONF_WIND_UNIT, DEFAULT_WIND_UNIT)
    tu = entry.data.get(CONF_TEMP_UNIT, DEFAULT_TEMP_UNIT)

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"Holfuy Weather ({entry.entry_id})",
        update_method=lambda: None,  # Placeholder, will be set below
        update_interval=DEFAULT_UPDATE_INTERVAL,
    )

    # Set the actual update method with coordinator reference for throttling
    coordinator.update_method = _make_update_method(api_key, stations, tu, su, coordinator)

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.error("Initial data fetch failed for Holfuy: %s", err)
        # allow setup to continue; coordinator will retry later

    # store coordinator and station list under entry
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "stations": [str(s) for s in stations],
    }

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload an entry: unload platforms and clear coordinator."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok