"""Ostrom NeoGrid integration."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import OstromApi, OstromApiError, OstromAuthError
from .const import DOMAIN, EVENT_CREDIT, SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.SWITCH, Platform.NUMBER, Platform.TIME,
             Platform.BUTTON, Platform.CLIMATE]


def _vpp_credits(data: dict | None) -> list[dict]:
    txs = ((data or {}).get("credits") or {}).get("transactions") or []
    return [t for t in txs if t.get("type") == "CREDIT" and t.get("subType") == "VPP"]


def _make_coordinator(hass: HomeAssistant, name: str, fetch, interval: timedelta) -> DataUpdateCoordinator:
    async def _update():
        try:
            data = await fetch()
        except OstromAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err  # starts the reauth flow (password prompt in HA)
        except OstromApiError as err:
            raise UpdateFailed(str(err)) from err
        coordinator.last_ok = datetime.now(timezone.utc)
        return data

    coordinator = DataUpdateCoordinator(hass, _LOGGER, name=name, update_method=_update, update_interval=interval)
    coordinator.last_ok = None
    return coordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # own session: the API sets cookies we do not want shared with other integrations
    api = OstromApi(async_create_clientsession(hass), entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])

    coordinator = _make_coordinator(hass, DOMAIN, api.fetch_all, timedelta(seconds=SCAN_INTERVAL_SECONDS))
    await coordinator.async_config_entry_first_refresh()
    coordinator.api = api
    # user settings for the "expected credit" estimate (restored by the number entities)
    coordinator.settings = {"factor": 1.0, "base_ct": 3.4}

    # meter / billing data changes at most daily, so poll it hourly
    coordinator.account = _make_coordinator(hass, f"{DOMAIN}_account", api.fetch_account, timedelta(hours=1))
    await coordinator.account.async_config_entry_first_refresh()

    # new NeoGrid credit -> bus event + notification (the first refresh is only the baseline)
    seen = {t["id"] for t in _vpp_credits(coordinator.account.data)}

    @callback
    def _check_credits() -> None:
        for t in _vpp_credits(coordinator.account.data):
            if t["id"] in seen:
                continue
            seen.add(t["id"])
            hass.bus.async_fire(EVENT_CREDIT, {"amount": t["amount"], "created_at": t["createdAt"],
                                               "status": t.get("status"), "entry_id": entry.entry_id})
            persistent_notification.async_create(
                hass, f"Neue NeoGrid-Gutschrift: {t['amount']:.2f} €", title="NeoGrid",
                notification_id=f"{DOMAIN}_credit_{t['id']}")

    entry.async_on_unload(coordinator.account.async_add_listener(_check_credits))

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return ok
