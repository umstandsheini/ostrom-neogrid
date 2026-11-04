"""Real write test: switch NeoGrid ON for the unplugged vehicle, check, then restore the original value.

Prints ids/booleans only. Always restores the original value (finally block).
"""
import os
import sys
import time

from ostrom_client import API, OstromClient

email, pw = os.environ.get("OSTROM_EMAIL"), os.environ.get("OSTROM_PASSWORD")
if not email or not pw:
    sys.exit("set OSTROM_EMAIL and OSTROM_PASSWORD first")
c = OstromClient(os.environ.get("OSTROM_BASE", API))
c.login(email, pw)
vehicles = c.get("/vehicles")
unplugged = [v for v in vehicles if not v["chargeState"]["isPluggedIn"]]
if not unplugged:
    sys.exit("no unplugged vehicle, aborting")
v = unplugged[0]
vid, original = v["id"], v["isVppEnabled"]


def state():
    return next(x for x in c.get("/vehicles") if x["id"] == vid)


def put(value):
    r = c.request("PUT", f"/vehicles/{vid}", {"isVppEnabled": value}, auth="bearer")
    print(f"PUT isVppEnabled={value} -> response says {r.get('isVppEnabled')}")


print(f"vehicle {vid}: isVppEnabled={original}, isVppRegistered={v['isVppRegistered']}")
try:
    put(not original)
    time.sleep(3)
    s = state()
    print("after toggle:", {k: s[k] for k in ("isVppEnabled", "isVppRegistered", "optimizedCharging")})
finally:
    put(original)
    time.sleep(3)
    s = state()
    print("restored:", {k: s[k] for k in ("isVppEnabled", "isVppRegistered", "optimizedCharging")})
