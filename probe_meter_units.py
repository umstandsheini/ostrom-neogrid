"""Read-only: show the latest meter readings + register format so we can fix the unit (kWh vs Wh).

Prints reading values (your own meter readings) - compare with the number on the meter itself.
"""
import os
import sys

from ostrom_client import API, OstromClient

email, pw = os.environ.get("OSTROM_EMAIL"), os.environ.get("OSTROM_PASSWORD")
if not email or not pw:
    sys.exit("set OSTROM_EMAIL and OSTROM_PASSWORD first")
c = OstromClient(os.environ.get("OSTROM_BASE", API))
uid = c.login(email, pw)["id"]
home = c.get(f"/users/{uid}/home-page-info")
cid = home["contracts"]["electricity"][0]["id"]
readings = sorted(c.get(f"/contracts/{cid}/meter-readings"), key=lambda r: r["readAt"], reverse=True)
print("latest readings (readAt, obis, value, difference, status, origin, qualifier):")
for r in readings[:4]:
    print(" ", r["readAt"], r["obis"], r["value"], r["difference"], r["status"], r["origin"], r["qualifier"])
for reg in c.get(f"/contracts/{cid}/registers"):
    print("register: obis", reg["obis"], "digits", reg["digits"], "precision", reg["precision"],
          "lastReading", reg["lastReading"]["readAt"], reg["lastReading"]["value"])
cons = c.get(f"/smart-meters/{cid}/consumption-info")
print("consumption month list:", cons["month"]["consumption"][:3], "| year total:", cons["year"]["totalConsumption"])
