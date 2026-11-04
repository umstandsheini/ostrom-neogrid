"""Write tests, safe by design:
 1) HVAC: POST permanent-hold with the CURRENT mode + setpoint (already PERMANENT, so nothing changes)
 2) Charger (go-e, unplugged): set optimizedCharging True, then restore False.
Prints booleans / temperatures only.
"""
import os
import sys
import time

from ostrom_client import API, OstromClient, OstromError

email, pw = os.environ.get("OSTROM_EMAIL"), os.environ.get("OSTROM_PASSWORD")
if not email or not pw:
    sys.exit("set OSTROM_EMAIL and OSTROM_PASSWORD first")
c = OstromClient(os.environ.get("OSTROM_BASE", API))
c.login(email, pw)

# 1) HVAC no-op (only if the thermostat is already in a permanent hold)
h = next((x for x in c.get("/hvacs") if x["holdType"] == "PERMANENT"), None)
if h is None:
    print("no thermostat in PERMANENT hold; skipping HVAC test")
else:
    body = {"mode": h["mode"], "heatSetpoint": h["heatSetpoint"], "coolSetpoint": h["coolSetpoint"]}
    print("HVAC", h["id"], "sending unchanged", body)
    try:
        r = c.request("POST", f"/hvacs/{h['id']}/permanent-hold?gateway={h['gateway']}", body, auth="bearer")
        print("  accepted; response:", {k: r.get(k) for k in ("mode", "holdType", "heatSetpoint")} if isinstance(r, dict) else r)
    except OstromError as e:
        print("  failed:", e)
    time.sleep(3)
    a = next(x for x in c.get("/hvacs") if x["id"] == h["id"])
    print("  after:", {k: a.get(k) for k in ("mode", "holdType", "heatSetpoint")})

# 2) charger toggle on the unplugged go-e wallbox
ch = next(iter(c.get("/chargers")), None)
if ch is None or ch["chargeState"]["isPluggedIn"]:
    print("no unplugged charger; skipping charger test")
else:
    cid, orig = ch["id"], ch["optimizedCharging"]
    print("CHARGER", cid, "optimizedCharging originally", orig)
    def put(v):
        return c.request("PUT", f"/chargers/{cid}", {"optimizedCharging": v, "requiredForUseAt": ch["requiredForUseAt"]}, auth="bearer")
    try:
        r = put(True)
        print("  set True -> response says", r.get("optimizedCharging"))
        time.sleep(3)
    finally:
        r = put(False if orig is None else orig)
        print("  restored ->", r.get("optimizedCharging"))
