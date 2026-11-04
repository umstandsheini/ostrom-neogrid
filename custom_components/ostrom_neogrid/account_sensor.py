"""Contract / meter / billing sensors (hourly). Meter and consumption values are kWh (verified)."""
from __future__ import annotations

from datetime import date, datetime, timezone

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import UnitOfEnergy
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


def _latest_reading(d):
    rs = d.get("readings") or []
    return max(rs, key=lambda r: r["readAt"]) if rs else None


def _meter_last(d):
    r = _latest_reading(d)
    return r["value"] if r else None


def _credits(d):
    """NeoGrid (VPP) credit bookings, newest first. Amounts are EUR (0.7 == the 70 ct seen in the app)."""
    txs = (d.get("credits") or {}).get("transactions") or []
    got = [t for t in txs if t.get("type") == "CREDIT" and t.get("subType") == "VPP"]
    return sorted(got, key=lambda t: t["createdAt"], reverse=True)


def _last_credit(d):
    c = _credits(d)
    return c[0]["amount"] if c else None


def _last_credit_at(d):
    c = _credits(d)
    if not c:
        return None
    ts = datetime.fromisoformat(c[0]["createdAt"].replace("Z", "+00:00"))
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)  # naive stamps are treated as UTC


def _attrs_last_credit(d):
    c = _credits(d)
    return {"status": c[0].get("status"), "available_at": c[0].get("availableAt"),
            "previous": [{"at": t["createdAt"], "eur": t["amount"]} for t in c[1:6]]} if c else {}


def _credits_total(d):
    return round(sum(t["amount"] for t in _credits(d)), 2)


def _month_days(d):
    return ((d.get("consumption") or {}).get("month") or {}).get("consumption") or []


def _meter_estimated(d):
    """Last official reading + daily smart-meter consumption after that reading (None if there is a gap)."""
    r = _latest_reading(d)
    days = _month_days(d)
    if not r or not days:
        return None
    read_day = date.fromisoformat(r["readAt"][:10])
    first = date.fromisoformat(days[0]["date"][:10])
    if (first - read_day).days > 1:
        return None
    return round(r["value"] + sum(x["kwh"] for x in days if date.fromisoformat(x["date"][:10]) > read_day), 3)


def _yesterday(d):
    days = _month_days(d)
    return days[-1]["kwh"] if days else None


def _attrs_last(d):
    r = _latest_reading(d)
    return {"read_at": r["readAt"], "origin": r["origin"], "obis": r["obis"]} if r else {}


def _attrs_yesterday(d):
    days = _month_days(d)
    return {"date": days[-1]["date"]} if days else {}


def _g(*path):
    def f(d):
        for p in path:
            if not isinstance(d, dict):
                return None
            d = d.get(p)
        return d
    return f


KWH = UnitOfEnergy.KILO_WATT_HOUR
TI, TOT = SensorStateClass.TOTAL_INCREASING, SensorStateClass.TOTAL
ENERGY, MONEY = SensorDeviceClass.ENERGY, SensorDeviceClass.MONETARY
# key, name, value fn, unit, device_class, state_class, attrs fn
# EUR amounts: unit assumed from the field names, not yet verified against the app
SENSORS = [
    ("meter_last", "Zählerstand (letzte Ablesung)", _meter_last, KWH, ENERGY, TI, _attrs_last),
    ("meter_estimated", "Zählerstand (geschätzt)", _meter_estimated, KWH, ENERGY, TI, None),
    ("consumption_yesterday", "Verbrauch gestern", _yesterday, KWH, ENERGY, TOT, _attrs_yesterday),
    ("consumption_month", "Verbrauch Monat", _g("consumption", "month", "totalConsumption"), KWH, ENERGY, TOT, None),
    ("consumption_year", "Verbrauch Jahr", _g("consumption", "year", "totalConsumption"), KWH, ENERGY, TOT, None),
    ("monthly_payment", "Abschlag", _g("payment", "currentPayment"), "EUR", MONEY, None, None),
    ("balance_today", "Geschätzter Saldo", _g("graph", "estimatedBalanceForToday"), "EUR", MONEY, None, None),
    ("credits_invoice", "Guthaben Rechnung", _g("credits", "currentInvoiceCreditsAmount"), "EUR", MONEY, None, None),
    ("credits_market", "Guthaben Marktplatz", _g("credits", "currentMarketPlaceCreditsAmount"), "EUR", MONEY, None, None),
    ("last_credit", "NeoGrid letzte Gutschrift", _last_credit, "EUR", MONEY, None, _attrs_last_credit),
    ("last_credit_at", "NeoGrid letzte Gutschrift am", _last_credit_at, None, SensorDeviceClass.TIMESTAMP, None, None),
    ("credits_total", "NeoGrid Gutschriften gesamt", _credits_total, "EUR", MONEY, TOT, None),
    ("co2_saved", "CO₂ gespart", _g("emissions", "totalUserKgC02Offset"), "kg", None, TOT, None),
    ("solar_lifetime", "Solar Gesamtertrag", _g("solar", "totalLifetimeProduction"), KWH, ENERGY, TI, None),
]


def account_entities(account):
    if not account.data:
        return []
    entities = [AccountSensor(account, *spec) for spec in SENSORS]
    for vid in account.data.get("vehicle_stats") or {}:
        entities += [VehicleStatsSensor(account, vid, *spec) for spec in STATS_SENSORS]
    return entities


class AccountSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, key, name, fn, unit, device_class, state_class, attrs):
        super().__init__(coordinator)
        cid = coordinator.data["contract_id"]
        self._fn, self._attrs = fn, attrs
        self._attr_unique_id = f"contract_{cid}_{key}"
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"contract_{cid}")}, name="Ostrom Vertrag", manufacturer="Ostrom")

    @property
    def native_value(self):
        return self._fn(self.coordinator.data)

    @property
    def extra_state_attributes(self):
        return self._attrs(self.coordinator.data) if self._attrs else None


# --- NeoGrid charging statistics per vehicle (from interval-charging-session-statistics) -------------
# Money in that endpoint is in cent (neogridCredits 70.11 matched the 0.70 EUR booking).

def _neogrid_days(st):
    """[(date, neogrid_kwh, credits_ct)] for days that have at least one NeoGrid session."""
    out = []
    for day in st.get("days") or []:
        kwh = sum(x.get("kwhSum") or 0 for x in day.get("sessions") or [] if x.get("type") == "neogrid")
        if kwh > 0:
            out.append((day["date"], round(kwh, 3), day.get("neogridCredits") or 0))
    return out


def _st_neogrid_kwh(st):
    return round(sum(k for _, k, _ in _neogrid_days(st)), 3)


def _st_credits_eur(st):
    return round((st.get("neogridCredits") or 0) / 100, 2)


def _st_benefit(st):
    kwh = _st_neogrid_kwh(st)
    return round((st.get("neogridCredits") or 0) / kwh, 2) if kwh else None


def _st_last_day_kwh(st):
    days = _neogrid_days(st)
    return days[-1][1] if days else None


def _st_last_day_attrs(st):
    days = _neogrid_days(st)
    if not days:
        return {}
    d, kwh, credits = days[-1]
    return {"date": d, "credits_eur": round(credits / 100, 2),
            "benefit_ct_per_kwh": round(credits / kwh, 2) if kwh else None,
            "recent_days": [{"date": a, "kwh": b, "credits_eur": round(c / 100, 2)} for a, b, c in days[-7:]]}


def _month_start():
    from datetime import datetime
    return datetime.combine(date.today().replace(day=1), datetime.min.time()).astimezone()


CT_KWH = "ct/kWh"
# key, name, value fn, unit, device_class, state_class, attrs fn
STATS_SENSORS = [
    ("neogrid_kwh_month", "NeoGrid geladen (Monat)", _st_neogrid_kwh, KWH, ENERGY, TOT, None),
    ("neogrid_credits_month", "NeoGrid Gutschrift (Monat)", _st_credits_eur, "EUR", MONEY, TOT, None),
    ("neogrid_benefit", "NeoGrid Vorteil pro kWh", _st_benefit, CT_KWH, None, None, None),
    ("neogrid_last_day", "NeoGrid letzter Ladetag", _st_last_day_kwh, KWH, ENERGY, None, _st_last_day_attrs),
    ("charged_month", "Geladen (Monat)", _g("energyCharged"), KWH, ENERGY, TOT, None),
    ("avg_cost", "Ø Ladepreis effektiv", _g("averageCostKWh"), CT_KWH, None, None, None),
]


class VehicleStatsSensor(CoordinatorEntity, SensorEntity):
    """Attached to the existing vehicle device (same identifiers as in entity.py)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, vehicle_id, key, name, fn, unit, device_class, state_class, attrs):
        super().__init__(coordinator)
        self._vid, self._fn, self._attrs = vehicle_id, fn, attrs
        self._attr_unique_id = f"vehicles_{vehicle_id}_{key}"
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, f"vehicles_{vehicle_id}")})
        if state_class == TOT:
            self._attr_last_reset = _month_start()

    @property
    def _stats(self):
        return (self.coordinator.data.get("vehicle_stats") or {}).get(self._vid) or {}

    @property
    def native_value(self):
        return self._fn(self._stats) if self._stats else None

    @property
    def extra_state_attributes(self):
        return self._attrs(self._stats) if self._attrs and self._stats else None
