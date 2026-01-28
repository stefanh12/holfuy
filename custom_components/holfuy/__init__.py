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
from . import repairs

_LOGGER = logging.getLogger(__name__)

# Update intervals
DEFAULT_UPDATE_INTERVAL = timedelta(minutes=2)
MAX_UPDATE_INTERVAL = timedelta(minutes=10)
MIN_UPDATE_INTERVAL = timedelta(minutes=1)


async def _fetch_json(session: aiohttp.ClientSession, url: str):
    """Fetch JSON from URL with error handling.
    
    Returns the JSON data on success, or raises UpdateFailed with error type encoded in message.
    Error message format: "error message|||error_type"
    """
    try:
        async with async_timeout.timeout(10):
            async with session.get(url) as resp:
                # Check for authentication errors
                if resp.status in (401, 403):
                    raise UpdateFailed(f"Authentication error {resp.status}: {resp.reason}|||auth")
                
                resp.raise_for_status()  # Raise exception for HTTP errors
                
                return await resp.json()
    except aiohttp.ContentTypeError as err:
        raise UpdateFailed(f"Invalid JSON response: {err}|||invalid_response")
    except aiohttp.ClientResponseError as err:
        raise UpdateFailed(f"HTTP error {err.status}: {err.message}|||http_error")
    except aiohttp.ClientError as err:
        raise UpdateFailed(f"Connection error: {err}|||connection")
    except asyncio.TimeoutError:
        raise UpdateFailed("Request timeout|||timeout")
    except Exception as err:
        raise UpdateFailed(f"Request failed: {err}|||unknown")


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


def _make_update_method(api_key: str, stations: list[str], tu: str, su: str, coordinator, hass: HomeAssistant, entry_id: str):
    """Create the update method with error tracking for throttling and repair issues."""
    consecutive_errors = 0
    station_error_counts = {station: 0 for station in stations}
    last_error_type = None

    async def async_update_data():
        nonlocal consecutive_errors, last_error_type

        try:
            # Try one combined request first
            async with aiohttp.ClientSession() as session:
                combined_url = _build_url(api_key, stations, tu, su, station=None)
                try:
                    response = await _fetch_json(session, combined_url)
                except UpdateFailed as err:
                    # Parse error type from message if present
                    error_str = str(err)
                    if "|||" in error_str:
                        error_msg, error_type = error_str.split("|||", 1)
                        
                        # Create appropriate repair issues
                        if error_type == "auth":
                            await repairs.async_create_auth_failure_issue(hass, entry_id)
                            raise UpdateFailed(error_msg)
                        elif error_type == "invalid_response":
                            await repairs.async_create_invalid_response_issue(hass, entry_id)
                            raise UpdateFailed(error_msg)
                    
                    _LOGGER.debug("Combined request failed: %s", err)
                    response = None

                parsed = _parse_combined_response(response, stations)
                if parsed is not None:
                    # Successful combined response parsed into mapping station -> data
                    consecutive_errors = 0
                    last_error_type = None
                    
                    # Reset station error counts
                    for station in stations:
                        station_error_counts[station] = 0
                    
                    # Restore normal update interval on success
                    if coordinator.update_interval != DEFAULT_UPDATE_INTERVAL:
                        coordinator.update_interval = DEFAULT_UPDATE_INTERVAL
                        _LOGGER.info("API calls successful, restored normal update interval")
                    
                    # Dismiss all repair issues on success
                    await repairs.async_delete_auth_failure_issue(hass, entry_id)
                    await repairs.async_delete_api_connection_failure_issue(hass, entry_id)
                    await repairs.async_delete_invalid_response_issue(hass, entry_id)
                    for station in stations:
                        await repairs.async_delete_station_inaccessible_issue(hass, entry_id, station)
                    
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
                auth_error = False
                invalid_response = False
                
                for station, res in zip(stations, results):
                    if isinstance(res, Exception):
                        _LOGGER.warning("Error fetching data for station %s: %s", station, res)
                        has_errors = True
                        
                        # Track station-specific errors
                        station_error_counts[station] += 1
                        
                        # Parse error type if present
                        error_str = str(res)
                        if "|||" in error_str:
                            error_msg, error_type = error_str.split("|||", 1)
                            
                            if error_type == "auth":
                                auth_error = True
                            elif error_type == "invalid_response":
                                invalid_response = True
                        
                        # Create repair issue for station if errors persist
                        if station_error_counts[station] >= 3:
                            await repairs.async_create_station_inaccessible_issue(hass, entry_id, station)
                        
                        continue
                    
                    # Success - store the data
                    mapping[str(station)] = res
                    # Clear station error count on success
                    station_error_counts[station] = 0
                    # Dismiss station issue if it exists
                    await repairs.async_delete_station_inaccessible_issue(hass, entry_id, station)

                # Handle authentication errors
                if auth_error:
                    await repairs.async_create_auth_failure_issue(hass, entry_id)
                    # Don't fail completely if we have partial data from other stations
                    if not mapping:
                        raise UpdateFailed("Authentication failed for all stations")
                
                # Handle invalid response errors
                if invalid_response:
                    await repairs.async_create_invalid_response_issue(hass, entry_id)
                    # Don't fail completely if we have partial data from other stations
                    if not mapping:
                        raise UpdateFailed("Invalid response format for all stations")

                # If we got at least some data, reset error counter
                if mapping:
                    consecutive_errors = 0
                    last_error_type = None
                    
                    if coordinator.update_interval != DEFAULT_UPDATE_INTERVAL:
                        coordinator.update_interval = DEFAULT_UPDATE_INTERVAL
                        _LOGGER.info("API calls successful, restored normal update interval")
                    
                    # Dismiss general API issues
                    await repairs.async_delete_auth_failure_issue(hass, entry_id)
                    await repairs.async_delete_api_connection_failure_issue(hass, entry_id)
                    await repairs.async_delete_invalid_response_issue(hass, entry_id)
                    
                    return mapping

                # All stations failed
                if has_errors:
                    raise UpdateFailed("All station requests failed")

                return mapping

        except Exception as err:
            consecutive_errors += 1
            
            # Parse error type from message if present
            error_str = str(err)
            if "|||" in error_str:
                error_msg, error_type = error_str.split("|||", 1)
                last_error_type = error_type
            else:
                # Try to detect error type from message
                if "auth" in error_str.lower() or "401" in error_str or "403" in error_str:
                    last_error_type = "auth"
                elif "timeout" in error_str.lower():
                    last_error_type = "timeout"
                elif "connection" in error_str.lower():
                    last_error_type = "connection"
                elif "invalid" in error_str.lower() and "json" in error_str.lower():
                    last_error_type = "invalid_response"

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
                    
                    # Create repair issue when reaching max throttle interval
                    if new_interval >= MAX_UPDATE_INTERVAL:
                        await repairs.async_create_api_connection_failure_issue(hass, entry_id)

            # Re-raise with clean error message
            if "|||" in error_str:
                error_msg, _ = error_str.split("|||", 1)
                raise UpdateFailed(f"Error fetching Holfuy data: {error_msg}")
            
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

    # Set the actual update method with coordinator reference for throttling and repair issues
    coordinator.update_method = _make_update_method(api_key, stations, tu, su, coordinator, hass, entry.entry_id)

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
        # Clean up all repair issues for this entry
        await repairs.async_delete_all_issues(hass, entry.entry_id)

    return unload_ok