"""Write test that changes nothing: PUT /vehicles/{id} {isVppEnabled: <current value>}.

Picks the vehicle that is NOT plugged in (or the first one). Prints status only, no personal data.
Same env vars as probe_readonly.py (OSTROM_EMAIL / OSTROM_PASSWORD).
"""
import os
import sys

from ostrom_client import API, OstromClient, OstromError

email, pw = os.environ.get("OSTROM_EMAIL"), os.environ.get("OSTROM_PASSWORD")
if not email or not pw:
    sys.exit("set OSTROM_EMAIL and OSTROM_PASSWORD first")
c = OstromClient(os.environ.get("OSTROM_BASE", API))
c.login(email, pw)
vehicles = c.get("/vehicles")
unplugged = [v for v in vehicles if not v["chargeState"]["isPluggedIn"]]
v = (unplugged or vehicles)[0]
print(f"vehicle id={v['id']} isVppAvailable={v['isVppAvailable']} isVppEnabled={v['isVppEnabled']} (unchanged write)")
try:
    resp = c.request("PUT", f"/vehicles/{v['id']}", {"isVppEnabled": v["isVppEnabled"]}, auth="bearer")
    print("PUT ok; response keys:", sorted(resp) if isinstance(resp, dict) else resp)
except OstromError as e:
    print("PUT failed:", e)
after = next(x for x in c.get("/vehicles") if x["id"] == v["id"])
print("isVppEnabled after:", after["isVppEnabled"])
