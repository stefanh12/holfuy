"""Repair issue management for Holfuy integration."""
import logging
from homeassistant.helpers import issue_registry as ir
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Repair issue IDs
ISSUE_AUTH_FAILURE = "auth_failure"
ISSUE_STATION_INACCESSIBLE = "station_inaccessible_{station_id}"
ISSUE_API_CONNECTION_FAILURE = "api_connection_failure"
ISSUE_INVALID_RESPONSE = "invalid_response"


async def async_create_auth_failure_issue(hass: HomeAssistant, entry_id: str) -> None:
    """Create a repair issue for authentication failure (401/403 errors)."""
    issue_id = f"{entry_id}_{ISSUE_AUTH_FAILURE}"
    
    # Check if issue already exists
    issue_reg = ir.async_get(hass)
    existing = issue_reg.async_get_issue(DOMAIN, issue_id)
    if existing:
        _LOGGER.debug("Auth failure repair issue already exists for entry %s", entry_id)
        return
    
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=True,
        severity=ir.IssueSeverity.CRITICAL,
        translation_key="auth_failure",
    )
    _LOGGER.warning("Created repair issue for authentication failure (entry: %s)", entry_id)


async def async_create_station_inaccessible_issue(
    hass: HomeAssistant, entry_id: str, station_id: str
) -> None:
    """Create a repair issue for an inaccessible station."""
    issue_id = f"{entry_id}_{ISSUE_STATION_INACCESSIBLE.format(station_id=station_id)}"
    
    # Check if issue already exists
    issue_reg = ir.async_get(hass)
    existing = issue_reg.async_get_issue(DOMAIN, issue_id)
    if existing:
        _LOGGER.debug("Station inaccessible issue already exists for station %s", station_id)
        return
    
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="station_inaccessible",
        translation_placeholders={
            "station_id": station_id,
        },
    )
    _LOGGER.warning("Created repair issue for inaccessible station %s (entry: %s)", station_id, entry_id)


async def async_create_api_connection_failure_issue(hass: HomeAssistant, entry_id: str) -> None:
    """Create a repair issue for persistent API connection failures."""
    issue_id = f"{entry_id}_{ISSUE_API_CONNECTION_FAILURE}"
    
    # Check if issue already exists
    issue_reg = ir.async_get(hass)
    existing = issue_reg.async_get_issue(DOMAIN, issue_id)
    if existing:
        _LOGGER.debug("API connection failure issue already exists for entry %s", entry_id)
        return
    
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="api_connection_failure",
    )
    _LOGGER.warning("Created repair issue for persistent API connection failures (entry: %s)", entry_id)


async def async_create_invalid_response_issue(hass: HomeAssistant, entry_id: str) -> None:
    """Create a repair issue for invalid API response format."""
    issue_id = f"{entry_id}_{ISSUE_INVALID_RESPONSE}"
    
    # Check if issue already exists
    issue_reg = ir.async_get(hass)
    existing = issue_reg.async_get_issue(DOMAIN, issue_id)
    if existing:
        _LOGGER.debug("Invalid response issue already exists for entry %s", entry_id)
        return
    
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="invalid_response",
    )
    _LOGGER.warning("Created repair issue for invalid API response (entry: %s)", entry_id)


async def async_delete_issue(hass: HomeAssistant, issue_id: str) -> None:
    """Delete a repair issue."""
    try:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        _LOGGER.info("Deleted repair issue: %s", issue_id)
    except KeyError:
        # Issue doesn't exist, which is fine
        _LOGGER.debug("Repair issue %s does not exist", issue_id)


async def async_delete_auth_failure_issue(hass: HomeAssistant, entry_id: str) -> None:
    """Delete the authentication failure repair issue."""
    issue_id = f"{entry_id}_{ISSUE_AUTH_FAILURE}"
    await async_delete_issue(hass, issue_id)


async def async_delete_station_inaccessible_issue(
    hass: HomeAssistant, entry_id: str, station_id: str
) -> None:
    """Delete the station inaccessible repair issue."""
    issue_id = f"{entry_id}_{ISSUE_STATION_INACCESSIBLE.format(station_id=station_id)}"
    await async_delete_issue(hass, issue_id)


async def async_delete_api_connection_failure_issue(hass: HomeAssistant, entry_id: str) -> None:
    """Delete the API connection failure repair issue."""
    issue_id = f"{entry_id}_{ISSUE_API_CONNECTION_FAILURE}"
    await async_delete_issue(hass, issue_id)


async def async_delete_invalid_response_issue(hass: HomeAssistant, entry_id: str) -> None:
    """Delete the invalid response repair issue."""
    issue_id = f"{entry_id}_{ISSUE_INVALID_RESPONSE}"
    await async_delete_issue(hass, issue_id)


async def async_delete_all_issues(hass: HomeAssistant, entry_id: str) -> None:
    """Delete all repair issues for an entry."""
    await async_delete_auth_failure_issue(hass, entry_id)
    await async_delete_api_connection_failure_issue(hass, entry_id)
    await async_delete_invalid_response_issue(hass, entry_id)
    
    # Delete station-specific issues - we need to check what stations exist
    # Since we don't have the station list here, we'll try to get it from hass.data
    if DOMAIN in hass.data and entry_id in hass.data[DOMAIN]:
        stations = hass.data[DOMAIN][entry_id].get("stations", [])
        for station_id in stations:
            await async_delete_station_inaccessible_issue(hass, entry_id, station_id)
