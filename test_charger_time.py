"""Wallbox write test (go-e, must be unplugged): optimizedCharging True with requiredForUseAt "07:00",
then restore False; finally try to clear the time again (null). Prints booleans/times only."""
import os
import sys
import time

from ostrom_client import API, OstromClient, OstromError

email, pw = os.environ.get("OSTROM_EMAIL"), os.environ.get("OSTROM_PASSWORD")
if not email or not pw:
    sys.exit("set OSTROM_EMAIL and OSTROM_PASSWORD first")
c = OstromClient(os.environ.get("OSTROM_BASE", API))
c.login(email, pw)
ch = next(iter(c.get("/chargers")), None)
if ch is None or ch["chargeState"]["isPluggedIn"]:
    sys.exit("no unplugged charger, aborting")
cid = ch["id"]
print("charger", cid, "before:", ch["optimizedCharging"], ch["requiredForUseAt"])


def put(opt, at):
    try:
        r = c.request("PUT", f"/chargers/{cid}", {"optimizedCharging": opt, "requiredForUseAt": at}, auth="bearer")
        print(f"  PUT ({opt}, {at}) ->", {k: r.get(k) for k in ("optimizedCharging", "requiredForUseAt")} if isinstance(r, dict) else r)
        return True
    except OstromError as e:
        print(f"  PUT ({opt}, {at}) failed:", e)
        return False


ok = put(True, "07:00")
time.sleep(3)
if ok:
    put(False, "07:00")  # restore the flag, keep a valid time
    time.sleep(2)
    put(False, None)     # try to clear the time as well
a = next(x for x in c.get("/chargers") if x["id"] == cid)
print("charger after:", a["optimizedCharging"], a["requiredForUseAt"])
