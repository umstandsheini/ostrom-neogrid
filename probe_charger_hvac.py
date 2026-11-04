"""Read-only: current charger + HVAC values (modes, hold type, setpoints) so writes can be designed safely."""
import os
import sys

from ostrom_client import API, OstromClient

email, pw = os.environ.get("OSTROM_EMAIL"), os.environ.get("OSTROM_PASSWORD")
if not email or not pw:
    sys.exit("set OSTROM_EMAIL and OSTROM_PASSWORD first")
c = OstromClient(os.environ.get("OSTROM_BASE", API))
c.login(email, pw)
for ch in c.get("/chargers"):
    print("CHARGER", ch["id"], {k: ch.get(k) for k in ("vendor", "optimizedCharging", "requiredForUseAt", "isReachable")},
          "| chargeState:", {k: ch["chargeState"].get(k) for k in ("isCharging", "isPluggedIn", "maxCurrent", "powerDeliveryState")})
for h in c.get("/hvacs"):
    print("HVAC", h["id"], {k: h.get(k) for k in ("vendor", "gateway", "mode", "holdType", "heatSetpoint", "coolSetpoint",
                                                 "currentTemperature", "isActive")},
          "| capableModes:", h["capabilities"]["capableModes"],
          "| thermostatState:", h["thermostatState"])
try:
    print("SCHEDULES(vehicle):", c.get("/smart-devices/schedules?ostromDeviceType=vehicle"))
except Exception as e:  # noqa: BLE001
    print("schedules query failed:", e)
