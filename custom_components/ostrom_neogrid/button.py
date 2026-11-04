"""Buttons: start / stop charging per vehicle."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.exceptions import HomeAssistantError

from .api import OstromApiError, OstromAuthError
from .const import DOMAIN
from .entity import OstromEntity, dig

# key, name, action, capability
BUTTONS = [
    ("start_charging", "Laden starten", "START", "capabilities.startCharging.isCapable"),
    ("stop_charging", "Laden stoppen", "STOP", "capabilities.stopCharging.isCapable"),
]


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        ChargeButton(coordinator, "vehicles", item, key, name, action, cap)
        for item in coordinator.data.get("vehicles") or []
        for key, name, action, cap in BUTTONS
    )


class ChargeButton(OstromEntity, ButtonEntity):
    def __init__(self, coordinator, kind, item, key, name, action, capability):
        super().__init__(coordinator, kind, item, key, name)
        self._action = action
        self._capability = capability

    @property
    def available(self) -> bool:
        return super().available and bool(dig(self.item, self._capability)) if self.item else False

    async def async_press(self) -> None:
        try:
            await self.coordinator.api.control_charging(self._item_id, self._action)
        except (OstromApiError, OstromAuthError) as err:
            raise HomeAssistantError(f"{self._action} fehlgeschlagen: {err}") from err
        # the car reports its new state with a lag (the app polls every 2 s, up to 5 times)
        await self.coordinator.async_request_refresh()
