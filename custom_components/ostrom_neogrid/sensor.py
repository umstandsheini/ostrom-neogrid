"""Sensors."""
from __future__ import annotations

from datetime import datetime, timezone

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfLength, UnitOfPower, UnitOfTemperature, UnitOfTime
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .account_sensor import account_entities
from .const import DOMAIN
from .entity import OstromEntity, dig

TS = SensorDeviceClass.TIMESTAMP
# kind, key, name, path, unit, device_class
SENSORS = [
    ("vehicles", "battery", "Akku", "chargeState.batteryLevel", PERCENTAGE, SensorDeviceClass.BATTERY),
    ("vehicles", "range", "Reichweite", "chargeState.range", UnitOfLength.KILOMETERS, SensorDeviceClass.DISTANCE),
    ("vehicles", "charge_limit", "Ladelimit", "chargeState.chargeLimit", PERCENTAGE, None),
    ("vehicles", "power_delivery", "Ladezustand", "chargeState.powerDeliveryState", None, None),
    ("vehicles", "charge_rate", "Ladeleistung", "chargeState.chargeRate", UnitOfPower.KILO_WATT, SensorDeviceClass.POWER),
    # Enode reports the remaining charge time in minutes
    ("vehicles", "time_remaining", "Restladezeit", "chargeState.chargeTimeRemaining", UnitOfTime.MINUTES,
     SensorDeviceClass.DURATION),
    ("vehicles", "odometer", "Kilometerstand", "odometer.distance", UnitOfLength.KILOMETERS, SensorDeviceClass.DISTANCE),
    ("vehicles", "min_charge", "NeoGrid Mindestladung", "smartChargingPolicy.minimumChargeLimit", PERCENTAGE, None),
    ("vehicles", "last_seen", "Zuletzt gesehen", "lastSeen", None, TS),
    ("chargers", "power_delivery", "Ladezustand", "chargeState.powerDeliveryState", None, None),
    ("chargers", "charge_rate", "Ladeleistung", "chargeState.chargeRate", UnitOfPower.KILO_WATT, SensorDeviceClass.POWER),
    ("chargers", "max_current", "Max. Strom", "chargeState.maxCurrent", "A", SensorDeviceClass.CURRENT),
    ("chargers", "last_seen", "Zuletzt gesehen", "lastSeen", None, TS),
    ("hvacs", "temperature", "Temperatur", "currentTemperature", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
    ("hvacs", "heat_setpoint", "Solltemperatur Heizen", "heatSetpoint", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
    ("hvacs", "mode", "Modus", "mode", None, None),
    ("hvacs", "hold", "Hold", "holdType", None, None),
    ("hvacs", "last_seen", "Zuletzt gesehen", "lastSeen", None, TS),
]

GROUP_NAMES = {"grid": "Netz", "inverter": "Wechselrichter", "battery": "Speicher", "household": "Haushalt",
               "hvac": "Heizung", "vehicle": "Fahrzeug", "devices": "Geräte", "other": "Sonstige"}


def _parse_ts(value):
    if not value:
        return None
    ts = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        OstromSensor(coordinator, kind, item, key, name, path, unit, dc)
        for kind, key, name, path, unit, dc in SENSORS
        for item in coordinator.data.get(kind) or []
    ]
    entities.append(HouseholdPower(coordinator))
    for group in ((coordinator.data.get("energy_graph") or {}).get("deviceGroups") or []):
        entities.append(EnergyGroupPower(coordinator, group["name"]))
    for item in coordinator.data.get("vehicles") or []:
        entities.append(ExpectedCredit(coordinator, "vehicles", item, "expected_credit", "Erwartete NeoGrid-Gutschrift"))
    for item in coordinator.data.get("vehicles") or []:
        if item["id"] in (coordinator.data.get("vpp_sessions") or {}):
            entities.append(SessionSensor(coordinator, "vehicles", item, "vpp_session", "NeoGrid Sitzung"))
    entities.append(LastUpdate(coordinator, "api_last_ok", "Letzte erfolgreiche Abfrage", coordinator))
    entities.extend(account_entities(coordinator.account))
    if coordinator.account.data:
        entities.append(LastUpdate(coordinator, "account_last_ok", "Letzte Abfrage Vertragsdaten", coordinator.account))
    async_add_entities(entities)


class OstromSensor(OstromEntity, SensorEntity):
    def __init__(self, coordinator, kind, item, key, name, path, unit, device_class):
        super().__init__(coordinator, kind, item, key, name)
        self._path = path
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        if unit is not None:
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        value = dig(self.item, self._path) if self.item else None
        return _parse_ts(value) if self.device_class == TS else value


def _household_device() -> DeviceInfo:
    return DeviceInfo(identifiers={(DOMAIN, "energy_flow_0")}, name="Ostrom Haushalt")


class HouseholdPower(OstromEntity, SensorEntity):
    """Household power from /smart-devices/energy-flow (account level, not a device)."""

    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator):
        super().__init__(coordinator, "energy_flow", {"id": 0, "information": {"displayName": "Ostrom Haushalt"}},
                         "household_power", "Hausverbrauch")

    @property
    def native_value(self):
        return (self.coordinator.data.get("energy_flow") or {}).get("householdPowerKw")


class EnergyGroupPower(CoordinatorEntity, SensorEntity):
    """Power per device group from /smart-devices/energy-flow/graph (whole kW only)."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, group: str):
        super().__init__(coordinator)
        self._group = group
        self._attr_unique_id = f"energy_group_{group}"
        self._attr_name = f"Leistung {GROUP_NAMES.get(str(group).lower(), group)}"
        self._attr_device_info = _household_device()

    def _row(self):
        for g in (self.coordinator.data.get("energy_graph") or {}).get("deviceGroups") or []:
            if g.get("name") == self._group:
                return g
        return None

    @property
    def native_value(self):
        return (self._row() or {}).get("powerKw")

    @property
    def extra_state_attributes(self):
        return {"status": (self._row() or {}).get("status")}


class ExpectedCredit(OstromEntity, SensorEntity):
    """Rough estimate: kWh still needed to the target level x base credit (ct/kWh) x campaign factor.

    The base value (~3.4 ct/kWh) and the factor are user inputs (number entities); this is an
    estimate from past credits, not something Ostrom publishes.
    """

    _attr_native_unit_of_measurement = "EUR"
    _attr_device_class = SensorDeviceClass.MONETARY

    def _needed_kwh(self):
        v = self.item or {}
        cs = v.get("chargeState") or {}
        target = v.get("batteryLevelNeeded") or cs.get("chargeLimit")
        level, cap = cs.get("batteryLevel"), cs.get("batteryCapacity")
        if None in (target, level, cap):
            return None
        return max(0.0, (target - level) / 100 * cap)

    @property
    def native_value(self):
        kwh = self._needed_kwh()
        if kwh is None:
            return None
        s = self.coordinator.settings
        return round(kwh * s["base_ct"] * s["factor"] / 100, 2)

    @property
    def extra_state_attributes(self):
        kwh = self._needed_kwh()
        s = self.coordinator.settings
        return {"needed_kwh": None if kwh is None else round(kwh, 1), "base_ct_per_kwh": s["base_ct"],
                "factor": s["factor"], "neogrid_enabled": (self.item or {}).get("isVppEnabled"),
                "note": "Schätzung aus bisherigen Gutschriften"}


class LastUpdate(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = TS
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, main, key, name, source):
        super().__init__(source)
        self._attr_unique_id = f"diag_{key}"
        self._attr_name = name
        self._source = source
        self._attr_device_info = _household_device()

    @property
    def native_value(self):
        return getattr(self._source, "last_ok", None)


class SessionSensor(OstromEntity, SensorEntity):
    """Latest NeoGrid session from the VPP host. Field names (status, ineligibilityReason) are taken
    from the app code; the live answer so far was only {"session": null}, so this is best effort."""

    _SKIP = ("lat", "lon", "address", "street", "zip", "city", "location")

    def _session(self):
        return ((self.coordinator.data.get("vpp_sessions") or {}).get(self._item_id) or {}).get("session")

    @property
    def native_value(self):
        ses = self._session()
        if ses is None:
            return "keine"
        return str(ses.get("status") or "aktiv")

    @property
    def extra_state_attributes(self):
        ses = self._session() or {}
        attrs = {k: v for k, v in ses.items() if not any(x in k.lower() for x in self._SKIP)}
        if ses.get("ineligibilityReason"):
            attrs["ineligibility_reason"] = ses["ineligibilityReason"]
        return attrs
