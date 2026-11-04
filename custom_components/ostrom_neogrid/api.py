"""Client for the private Ostrom app API (reverse engineered from app 6.4.0)."""
from __future__ import annotations

import json as json_module
from datetime import date

import aiohttp

from .const import API_URL, VPP_URL


class OstromAuthError(Exception):
    """Login failed or session expired."""


class OstromApiError(Exception):
    """Any other API failure."""


class OstromApi:
    def __init__(self, session: aiohttp.ClientSession, email: str, password: str) -> None:
        self._session = session
        self._email = email
        self._password = password
        self._token: str | None = None
        self.user_id: int | None = None

    async def login(self) -> None:
        async with self._session.post(
            f"{API_URL}/auth/login",
            json={"email": self._email, "password": self._password, "application": "MOBILE_APP"},
        ) as resp:
            if resp.status in (400, 401, 403):
                raise OstromAuthError(f"login rejected ({resp.status})")
            if resp.status >= 400:
                raise OstromApiError(f"login failed ({resp.status})")
            body = await resp.json()
            self.user_id = body.get("id")
            cookie = resp.cookies.get("access_token")
            self._token = (cookie.value if cookie else None) or body.get("accessToken")
        if not self._token:
            raise OstromAuthError("no access token in login response")

    async def _request(self, method: str, path: str, json=None, _retry: bool = True, base: str = API_URL):
        if self._token is None:
            await self.login()
        async with self._session.request(
            method, f"{base}{path}", json=json,
            headers={"Authorization": f"Bearer {self._token}"},
        ) as resp:
            if resp.status == 401 and _retry:
                self._token = None
                return await self._request(method, path, json, _retry=False, base=base)
            if resp.status == 401:
                raise OstromAuthError("session rejected")
            if resp.status >= 400:
                raise OstromApiError(f"{method} {path} -> {resp.status}")
            text = await resp.text()
            # control-charging / permanent-hold answer with an empty body
            return json_module.loads(text) if text.strip() else None

    async def get(self, path: str):
        return await self._request("GET", path)

    async def put(self, path: str, json: dict):
        return await self._request("PUT", path, json=json)

    async def update_vehicle(self, vehicle: dict, **changes) -> dict:
        """PUT /vehicles/{id} like the app: full NeoGrid snapshot with the changed field replaced.

        Fields (from the app): isVppEnabled, batteryLevelNeeded (int %), requiredForUseAt ("HH:mm"), contractId.
        """
        body = {
            "isVppEnabled": bool(vehicle.get("isVppEnabled")),
            "batteryLevelNeeded": vehicle.get("batteryLevelNeeded"),
            "contractId": vehicle.get("contractId"),
            "requiredForUseAt": vehicle.get("requiredForUseAt"),
        }
        body.update(changes)
        return await self.put(f"/vehicles/{vehicle['id']}", body)

    async def update_charger(self, charger: dict, **changes) -> None:
        """PUT /chargers/{id} {optimizedCharging, requiredForUseAt}. Verified live: Ostrom rejects a null time."""
        body = {
            "optimizedCharging": bool(charger.get("optimizedCharging")),
            "requiredForUseAt": charger.get("requiredForUseAt") or "07:00",  # app default; null gives HTTP 400
        }
        body.update(changes)
        await self.put(f"/chargers/{charger['id']}", body)

    async def update_hvac(self, hvac: dict, **changes) -> None:
        """POST /hvacs/{id}/permanent-hold?gateway=... {mode, heatSetpoint, coolSetpoint} like the app."""
        body = {
            "mode": hvac.get("mode"),
            "heatSetpoint": hvac.get("heatSetpoint"),
            "coolSetpoint": hvac.get("coolSetpoint"),
        }
        body.update(changes)
        await self._request("POST", f"/hvacs/{hvac['id']}/permanent-hold?gateway={hvac['gateway']}", json=body)

    async def control_charging(self, vehicle_id: int, action: str) -> None:
        """PUT /vehicles/{id}/control-charging {action: "START"|"STOP"} (EVChargingStatus enum in the app)."""
        await self.put(f"/vehicles/{vehicle_id}/control-charging", {"action": action})

    async def _try_get(self, path: str):
        """Optional endpoint: None if Ostrom rejects it, auth errors still propagate."""
        try:
            return await self.get(path)
        except OstromApiError:
            return None

    async def fetch_account(self) -> dict:
        """Contract level data (meter readings, consumption, payments, credits, solar). Slow-changing."""
        if self.user_id is None:
            await self.login()
        uid = self.user_id
        home = await self.get(f"/users/{uid}/home-page-info")
        contracts = [c for group in (home.get("contracts") or {}).values() for c in group]
        if not contracts:
            return {}
        cid = contracts[0]["id"]
        inverters = await self._try_get("/inverters") or []
        solar = None
        if inverters:
            today = date.today()
            solar = await self._try_get(
                f"/production-statistics/{inverters[0]['id']}?day={today.day}&month={today.month}&year={today.year}")
        today = date.today()
        vehicle_stats = {}
        for v in await self._try_get("/vehicles") or []:
            # per-vehicle charging statistics incl. sessions (type "neogrid"/"external") and NeoGrid credits in cents
            st = await self._try_get(f"/vehicles/{v['id']}/interval-charging-session-statistics?month={today:%Y-%m}")
            if st:
                vehicle_stats[v["id"]] = st
        return {
            "contract_id": cid,
            "vehicle_stats": vehicle_stats,
            "readings": await self._try_get(f"/contracts/{cid}/meter-readings"),
            "consumption": await self._try_get(f"/smart-meters/{cid}/consumption-info"),
            "payment": await self._try_get(f"/contracts/{cid}/monthly-payment"),
            "graph": await self._try_get(f"/contracts/{cid}/graph-info"),
            "credits": await self._try_get(f"/users/{uid}/account-transactions"),
            "emissions": await self._try_get(f"/users/{uid}/emissions-info"),
            "inverters": inverters,
            "solar": solar,
        }

    async def vpp_session(self, vehicle_id: int):
        """Latest NeoGrid session of a vehicle from the VPP host: {"session": null | {...}}.

        404 "Vehicle not found" means the vehicle is not registered for NeoGrid.
        """
        try:
            return await self._request("GET", f"/smart-devices/vehicles/{vehicle_id}/session-information", base=VPP_URL)
        except OstromApiError:
            return None

    async def fetch_all(self) -> dict:
        """Read-only snapshot of everything the integration exposes."""
        vehicles = await self.get("/vehicles")
        sessions = {v["id"]: await self.vpp_session(v["id"]) for v in vehicles if v.get("isVppRegistered")}
        return {
            "vehicles": vehicles,
            "vpp_sessions": sessions,
            "chargers": await self.get("/chargers"),
            "hvacs": await self.get("/hvacs"),
            "energy_flow": await self.get("/smart-devices/energy-flow"),
            "energy_graph": await self._try_get("/smart-devices/energy-flow/graph"),
        }
