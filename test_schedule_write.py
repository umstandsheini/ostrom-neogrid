"""Real write test on the UNPLUGGED vehicle: set target SoC + 'ready until', check, restore originals.

Uses the app's full-snapshot payload. Prints ids/values of these fields only. Always restores (finally).
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
unplugged = [v for v in c.get("/vehicles") if not v["chargeState"]["isPluggedIn"]]
if not unplugged:
    sys.exit("no unplugged vehicle, aborting")
v = unplugged[0]
vid = v["id"]
FIELDS = ("isVppEnabled", "batteryLevelNeeded", "requiredForUseAt", "optimizedCharging")


def snap(x):
    return {k: x.get(k) for k in FIELDS}


def put(cur, **changes):
    body = {"isVppEnabled": bool(cur["isVppEnabled"]), "batteryLevelNeeded": cur.get("batteryLevelNeeded"),
            "contractId": cur.get("contractId"), "requiredForUseAt": cur.get("requiredForUseAt")}
    body.update(changes)
    return c.request("PUT", f"/vehicles/{vid}", body, auth="bearer")


def fresh():
    return next(x for x in c.get("/vehicles") if x["id"] == vid)


orig = fresh()
print("original:", snap(orig))
try:
    r = put(orig, batteryLevelNeeded=80, requiredForUseAt="07:00")
    print("PUT response:", snap(r))
    time.sleep(3)
    print("after set:   ", snap(fresh()))
finally:
    r = put(fresh(), batteryLevelNeeded=orig.get("batteryLevelNeeded"), requiredForUseAt=orig.get("requiredForUseAt"))
    time.sleep(3)
    print("restored:    ", snap(fresh()))
