"""Thermostats (Bosch via Enode): on/off and target temperature.

Writes use the app's `permanent-hold` call, which sets a fixed mode + setpoint (the thermostats
already report holdType PERMANENT). Returning to the device schedule (mode SCHEDULE) is not exposed:
how the app undoes a hold is not known yet.
"""
from __future__ import annotations

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.exceptions import HomeAssistantError

from .api import OstromApiError, OstromAuthError
from .const import DOMAIN
from .entity import OstromEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        OstromThermostat(coordinator, "hvacs", item, "thermostat", "Thermostat")
        for item in coordinator.data.get("hvacs") or []
    )


class OstromThermostat(OstromEntity, ClimateEntity):
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
    )
    _attr_target_temperature_step = 0.5
    _attr_min_temp = 5
    _attr_max_temp = 30
    _enable_turn_on_off_backwards_compat = False

    @property
    def current_temperature(self):
        return (self.item or {}).get("currentTemperature")

    @property
    def target_temperature(self):
        return (self.item or {}).get("heatSetpoint")

    @property
    def hvac_mode(self):
        mode = (self.item or {}).get("mode")
        if mode == "HEAT":
            return HVACMode.HEAT
        return HVACMode.OFF if mode == "OFF" else None

    @property
    def hvac_action(self):
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        return HVACAction.HEATING if (self.item or {}).get("isActive") else HVACAction.IDLE

    @property
    def extra_state_attributes(self):
        return {"hold_type": (self.item or {}).get("holdType")}

    async def _write(self, **changes) -> None:
        try:
            await self.coordinator.api.update_hvac(self.item, **changes)
        except (OstromApiError, OstromAuthError) as err:
            raise HomeAssistantError(f"Heizung konnte nicht gesetzt werden: {err}") from err
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs) -> None:
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is not None:
            await self._write(mode="HEAT", heatSetpoint=float(temp))

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        await self._write(mode="HEAT" if hvac_mode == HVACMode.HEAT else "OFF")
