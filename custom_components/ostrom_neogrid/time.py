"""Departure time ("ready until") per vehicle."""
from __future__ import annotations

from datetime import time as dtime

from homeassistant.components.time import TimeEntity
from homeassistant.exceptions import HomeAssistantError

from .api import OstromApiError, OstromAuthError
from .const import DOMAIN
from .entity import OstromEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        DepartureTime(coordinator, "vehicles", item, "ready_until", "Fertig bis")
        for item in coordinator.data.get("vehicles") or []
    ]
    entities += [
        ChargerDepartureTime(coordinator, "chargers", item, "ready_until", "Fertig bis")
        for item in coordinator.data.get("chargers") or []
    ]
    async_add_entities(entities)


class DepartureTime(OstromEntity, TimeEntity):
    @property
    def native_value(self):
        raw = (self.item or {}).get("requiredForUseAt")
        if not raw:
            return None
        try:
            hh, mm = str(raw).split(":")[:2]  # the app uses "HH:mm"
            return dtime(int(hh), int(mm))
        except ValueError:
            return None

    async def async_set_value(self, value: dtime) -> None:
        try:
            await self.coordinator.api.update_vehicle(self.item, requiredForUseAt=value.strftime("%H:%M"))
        except (OstromApiError, OstromAuthError) as err:
            raise HomeAssistantError(f"Uhrzeit konnte nicht gesetzt werden: {err}") from err
        await self.coordinator.async_request_refresh()


class ChargerDepartureTime(DepartureTime):
    async def async_set_value(self, value: dtime) -> None:
        try:
            await self.coordinator.api.update_charger(self.item, requiredForUseAt=value.strftime("%H:%M"))
        except (OstromApiError, OstromAuthError) as err:
            raise HomeAssistantError(f"Uhrzeit konnte nicht gesetzt werden: {err}") from err
        await self.coordinator.async_request_refresh()
