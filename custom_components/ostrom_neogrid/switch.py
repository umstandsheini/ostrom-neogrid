"""Switches: NeoGrid on/off per vehicle."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.exceptions import HomeAssistantError

from .api import OstromApiError, OstromAuthError
from .const import DOMAIN
from .entity import OstromEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        VehicleNeoGridSwitch(coordinator, "vehicles", item, "neogrid_switch", "NeoGrid")
        for item in coordinator.data.get("vehicles") or []
    ]
    entities += [
        ChargerOptimizedSwitch(coordinator, "chargers", item, "optimized_switch", "Optimiertes Laden")
        for item in coordinator.data.get("chargers") or []
    ]
    async_add_entities(entities)


class ChargerOptimizedSwitch(OstromEntity, SwitchEntity):
    """Optimised (grid-friendly) charging on the wallbox itself."""

    @property
    def is_on(self):
        value = (self.item or {}).get("optimizedCharging")
        return None if value is None else bool(value)

    async def _set(self, enabled: bool) -> None:
        try:
            await self.coordinator.api.update_charger(self.item, optimizedCharging=enabled)
        except (OstromApiError, OstromAuthError) as err:
            raise HomeAssistantError(f"Wallbox konnte nicht geschaltet werden: {err}") from err
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._set(False)


class VehicleNeoGridSwitch(OstromEntity, SwitchEntity):
    @property
    def available(self) -> bool:
        return super().available and self.item is not None and self.item.get("isVppAvailable") is not False

    @property
    def is_on(self):
        value = (self.item or {}).get("isVppEnabled")
        return None if value is None else bool(value)

    async def _set(self, enabled: bool) -> None:
        try:
            await self.coordinator.api.update_vehicle(self.item, isVppEnabled=enabled)
        except (OstromApiError, OstromAuthError) as err:
            raise HomeAssistantError(f"NeoGrid konnte nicht geschaltet werden: {err}") from err
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._set(False)
