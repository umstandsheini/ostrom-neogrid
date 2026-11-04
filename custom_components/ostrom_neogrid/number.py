"""Target state of charge (NeoGrid) per vehicle."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode, RestoreNumber
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.const import PERCENTAGE
from homeassistant.exceptions import HomeAssistantError

from .api import OstromApiError, OstromAuthError
from .const import DOMAIN
from .entity import OstromEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        TargetChargeNumber(coordinator, "vehicles", item, "target_soc", "Ziel-Ladestand")
        for item in coordinator.data.get("vehicles") or []
    ]
    if coordinator.account.data:
        cid = coordinator.account.data["contract_id"]
        entities += [
            SettingNumber(coordinator, cid, "factor", "NeoGrid Aktionsfaktor", 1, 10, 0.5, 1.0, None),
            SettingNumber(coordinator, cid, "base_ct", "NeoGrid Basis-Gutschrift", 0, 20, 0.1, 3.4, "ct/kWh"),
        ]
    async_add_entities(entities)


class SettingNumber(RestoreNumber):
    """User-set inputs for the expected-credit estimate (kept across restarts)."""

    _attr_has_entity_name = True
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, cid, key, name, lo, hi, step, default, unit):
        self._coordinator, self._key, self._default = coordinator, key, default
        self._attr_unique_id = f"contract_{cid}_setting_{key}"
        self._attr_name = name
        self._attr_native_min_value, self._attr_native_max_value, self._attr_native_step = lo, hi, step
        self._attr_native_unit_of_measurement = unit
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, f"contract_{cid}")}, name="Ostrom Vertrag")
        self._attr_native_value = default

    async def async_added_to_hass(self) -> None:
        if (last := await self.async_get_last_number_data()) and last.native_value is not None:
            self._attr_native_value = last.native_value
        self._coordinator.settings[self._key] = float(self._attr_native_value)

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self._coordinator.settings[self._key] = float(value)
        self.async_write_ha_state()
        self._coordinator.async_update_listeners()  # recompute the estimate


class TargetChargeNumber(OstromEntity, NumberEntity):
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_native_min_value = 10
    _attr_native_max_value = 100
    _attr_native_step = 5
    _attr_mode = NumberMode.SLIDER

    @property
    def native_value(self):
        return (self.item or {}).get("batteryLevelNeeded")

    async def async_set_native_value(self, value: float) -> None:
        try:
            await self.coordinator.api.update_vehicle(self.item, batteryLevelNeeded=int(value))
        except (OstromApiError, OstromAuthError) as err:
            raise HomeAssistantError(f"Ziel-Ladestand konnte nicht gesetzt werden: {err}") from err
        await self.coordinator.async_request_refresh()
