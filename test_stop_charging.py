"""Harmless write test: send STOP to the UNPLUGGED vehicle (nothing is charging there)."""
import os
import sys
import time

from ostrom_client import API, OstromClient, OstromError

email, pw = os.environ.get("OSTROM_EMAIL"), os.environ.get("OSTROM_PASSWORD")
if not email or not pw:
    sys.exit("set OSTROM_EMAIL and OSTROM_PASSWORD first")
c = OstromClient(os.environ.get("OSTROM_BASE", API))
c.login(email, pw)
unplugged = [v for v in c.get("/vehicles") if not v["chargeState"]["isPluggedIn"]]
if not unplugged:
    sys.exit("no unplugged vehicle, aborting")
v = unplugged[0]
cap = v["capabilities"]
print(f"vehicle {v['id']}: stopCharging capable={cap['stopCharging']['isCapable']}, "
      f"startCharging capable={cap['startCharging']['isCapable']}, isCharging={v['chargeState']['isCharging']}")
try:
    r = c.request("PUT", f"/vehicles/{v['id']}/control-charging", {"action": "STOP"}, auth="bearer")
    print("STOP accepted; response type:", type(r).__name__, sorted(r)[:6] if isinstance(r, dict) else r)
except OstromError as e:
    print("STOP failed:", e)
time.sleep(3)
after = next(x for x in c.get("/vehicles") if x["id"] == v["id"])
print("isCharging after:", after["chargeState"]["isCharging"], "powerDeliveryState:", after["chargeState"]["powerDeliveryState"])
