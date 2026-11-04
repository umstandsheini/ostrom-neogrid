"""Read-only probe #3.

1) GET <vpp host>/smart-devices/vehicles/{id}/session-information  (NeoGrid session state / why a session is not eligible)
2) POST /smart-devices/smart-charging-override with an EMPTY body: expected to be rejected with a validation
   message that names the required fields. It sends no vehicle id, so nothing can start.
Prints responses with location-like fields removed.
"""
import json
import os
import sys

from ostrom_client import API, OstromClient, OstromError

VPP = "https://vpp.ostrom.de/v1"
email, pw = os.environ.get("OSTROM_EMAIL"), os.environ.get("OSTROM_PASSWORD")
if not email or not pw:
    sys.exit("set OSTROM_EMAIL and OSTROM_PASSWORD first")
c = OstromClient(API)
c.login(email, pw)
SKIP = ("lat", "lon", "address", "street", "zip", "city", "location")


def clean(v):
    if isinstance(v, dict):
        return {k: clean(x) for k, x in v.items() if not any(s in k.lower() for s in SKIP)}
    if isinstance(v, list):
        return [clean(x) for x in v[:5]]
    return v


for v in c.get("/vehicles"):
    vid = v["id"]
    tail = str(v["information"].get("vin", ""))[-4:]
    for base in (VPP, API):
        try:
            r = c.get(f"/smart-devices/vehicles/{vid}/session-information", base=base)
            print(f"vehicle ...{tail} session-information via {base}: OK", json.dumps(clean(r), default=str)[:900])
            break
        except OstromError as e:
            print(f"vehicle ...{tail} session-information via {base}: {e.status} {str(e)[:140]}")

try:
    r = c.request("POST", "/smart-devices/smart-charging-override", {})
    print("override POST {} -> unexpectedly accepted:", r)
except OstromError as e:
    print("override POST {} ->", e.status, str(e)[:400])
