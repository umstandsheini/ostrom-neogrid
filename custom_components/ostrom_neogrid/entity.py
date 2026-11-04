"""Shared base entity: one HA device per Ostrom device, values looked up by id."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .const import DOMAIN


class OstromEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: DataUpdateCoordinator, kind: str, item: dict, key: str, name: str) -> None:
        super().__init__(coordinator)
        self._kind = kind  # "vehicles" | "chargers" | "hvacs"
        self._item_id = item["id"]
        info = item.get("information") or {}
        self._attr_unique_id = f"{kind}_{self._item_id}_{key}"
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{kind}_{self._item_id}")},
            name=device_name(item, _siblings(coordinator.data.get(kind)), kind),
            manufacturer=info.get("brand") or item.get("vendor"),
            model=info.get("model"),
        )

    @property
    def item(self) -> dict | None:
        for it in self.coordinator.data.get(self._kind) or []:
            if it["id"] == self._item_id:
                return it
        return None


def _siblings(value) -> list[dict]:
    """Only device lists count; e.g. "energy_flow" is a single object, not a list of devices."""
    return value if isinstance(value, list) else []


def _base_name(item: dict, fallback: str) -> str:
    info = item.get("information") or {}
    return info.get("displayName") or " ".join(filter(None, [info.get("brand"), info.get("model")])) or fallback


def device_name(item: dict, siblings: list[dict], fallback: str) -> str:
    """Name from Ostrom; if several devices share it, add the model year or the last 4 VIN characters."""
    base = _base_name(item, fallback)
    same = [s for s in siblings if _base_name(s, fallback) == base]
    if len(same) < 2:
        return base
    info = item.get("information") or {}
    years = [(s.get("information") or {}).get("year") for s in same]
    if info.get("year") and years.count(info["year"]) == 1:
        return f"{base} {info['year']}"
    vin = info.get("vin")
    return f"{base} (…{vin[-4:]})" if vin else f"{base} #{item['id']}"


def dig(obj, path: str):
    """'chargeState.batteryLevel' -> nested lookup, None if anything is missing."""
    for part in path.split("."):
        if not isinstance(obj, dict):
            return None
        obj = obj.get(part)
    return obj
