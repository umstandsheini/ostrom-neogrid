"""Read-only: where does Ostrom expose kWh charged via NeoGrid?

Tries  GET /vehicles/{id}/interval-charging-session-statistics?month=...  (param formats guessed)
and    GET /smart-devices/vehicles/{id}/session-information
for each vehicle. Prints the response with location-like fields removed, truncated.
"""
import datetime as dt
import json
import os
import sys

from ostrom_client import API, OstromClient, OstromError

email, pw = os.environ.get("OSTROM_EMAIL"), os.environ.get("OSTROM_PASSWORD")
if not email or not pw:
    sys.exit("set OSTROM_EMAIL and OSTROM_PASSWORD first")
c = OstromClient(os.environ.get("OSTROM_BASE", API))
c.login(email, pw)
SKIP = ("lat", "lon", "address", "street", "zip", "city", "location")


def clean(v):
    if isinstance(v, dict):
        return {k: clean(x) for k, x in v.items() if not any(s in k.lower() for s in SKIP)}
    if isinstance(v, list):
        return [clean(x) for x in v[:6]]
    return v


def show(label, path):
    try:
        r = c.get(path)
        print(f"{label} OK:", json.dumps(clean(r), default=str)[:1500])
        return True
    except OstromError as e:
        print(f"{label} {e.status}: {str(e)[:120]}")
        return False


today = dt.date.today()
for v in c.get("/vehicles"):
    vid = v["id"]
    print(f"--- vehicle {vid} (...{str(v['information'].get('vin', ''))[-4:]})")
    for fmt in (f"{today:%Y-%m}", f"{today.month}", f"{today:%Y-%m-01}"):
        if show(f"stats month={fmt}", f"/vehicles/{vid}/interval-charging-session-statistics?month={fmt}"):
            break
    show("session-information", f"/smart-devices/vehicles/{vid}/session-information")
