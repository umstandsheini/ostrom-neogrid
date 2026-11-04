"""Binary sensors (read-only)."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity

from .const import DOMAIN
from .entity import OstromEntity, dig

BINARY = [
    ("vehicles", "charging", "Lädt", "chargeState.isCharging", BinarySensorDeviceClass.BATTERY_CHARGING),
    ("vehicles", "plugged_in", "Angesteckt", "chargeState.isPluggedIn", BinarySensorDeviceClass.PLUG),
    ("vehicles", "reachable", "Erreichbar", "isReachable", BinarySensorDeviceClass.CONNECTIVITY),
    ("vehicles", "optimized", "Optimiertes Laden", "optimizedCharging", None),
    ("vehicles", "vpp_registered", "NeoGrid registriert", "isVppRegistered", None),
    ("vehicles", "vpp_available", "NeoGrid verfügbar", "isVppAvailable", None),
    ("vehicles", "smart_charging", "Smart Charging", "smartChargingPolicy.isEnabled", None),
    ("chargers", "charging", "Lädt", "chargeState.isCharging", BinarySensorDeviceClass.BATTERY_CHARGING),
    ("chargers", "plugged_in", "Fahrzeug angesteckt", "chargeState.isPluggedIn", BinarySensorDeviceClass.PLUG),
    ("chargers", "reachable", "Erreichbar", "isReachable", BinarySensorDeviceClass.CONNECTIVITY),
    ("hvacs", "active", "Heizt", "isActive", BinarySensorDeviceClass.HEAT),
    ("hvacs", "reachable", "Erreichbar", "isReachable", BinarySensorDeviceClass.CONNECTIVITY),
]


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        OstromBinary(coordinator, kind, item, key, name, path, dc)
        for kind, key, name, path, dc in BINARY
        for item in coordinator.data.get(kind) or []
    )


class OstromBinary(OstromEntity, BinarySensorEntity):
    def __init__(self, coordinator, kind, item, key, name, path, device_class):
        super().__init__(coordinator, kind, item, key, name)
        self._path = path
        self._attr_device_class = device_class

    @property
    def is_on(self):
        value = dig(self.item, self._path) if self.item else None
        return None if value is None else bool(value)
