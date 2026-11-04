"""Read-only probe #2: what data (meter readings, consumption, prices, credits ...) does the account expose?

Prints structure only (keys + types, list lengths), never values. Same env vars as probe_readonly.py.
"""
import datetime as dt
import os
import sys

from ostrom_client import API, OstromClient, OstromError


def shape(v, depth=0):
    if isinstance(v, dict):
        return {k: shape(x, depth + 1) for k, x in v.items()} if depth < 4 else "{...}"
    if isinstance(v, list):
        return f"list[{len(v)}] of " + str(shape(v[0], depth + 1)) if v else "list[0]"
    return type(v).__name__


def find_ids(v, found, key=""):
    """Collect values of keys that look like contract ids."""
    if isinstance(v, dict):
        for k, x in v.items():
            if "contract" in k.lower() and k.lower().endswith("id") and isinstance(x, (int, str)):
                found.add(str(x))
            find_ids(x, found, k)
    elif isinstance(v, list):
        for x in v:
            find_ids(x, found, key)


email, pw = os.environ.get("OSTROM_EMAIL"), os.environ.get("OSTROM_PASSWORD")
if not email or not pw:
    sys.exit("set OSTROM_EMAIL and OSTROM_PASSWORD first")
c = OstromClient(os.environ.get("OSTROM_BASE", API))
uid = c.login(email, pw)["id"]
today = dt.date.today()


def try_get(path):
    try:
        r = c.get(path)
        print(f"GET {path} ->", shape(r))
        return r
    except OstromError as e:
        print(f"GET {path} -> {e.status}")


home = try_get(f"/users/{uid}/home-page-info")
ids = set()
inverter_ids = []
contracts = [x for group in (home or {}).get("contracts", {}).values() for x in group]
for ct in contracts:
    ids.add(str(ct["id"]))
    print("contract.smartMeter:", shape(ct.get("smartMeter"), 2))
    print("contract.settings:", shape(ct.get("settings"), 2))
for x in c.get("/inverters") or []:
    inverter_ids.append(x["id"])
print("contract ids found:", len(ids))
for cid in sorted(ids)[:3]:
    print(f"--- contract {cid}")
    for sub in ("", "/graph-info", "/meter-readings", "/registers", "/monthly-payment", "/payments",
                "/tariffs", "/tariffs-history", "/invoices", "/interim-invoice-status"):
        try_get(f"/contracts/{cid}{sub}")
    try_get(f"/smart-meters/{cid}/consumption-info")
    try_get(f"/dynamic-pricing/{cid}/graph-info")
    try_get(f"/dynamic-pricing/{cid}/month-estimation-info")
print("--- user level")
for sub in ("emissions-info", "account-transactions", "referrals-info"):
    try_get(f"/users/{uid}/{sub}")
for iid in inverter_ids[:2]:
    for base in (f"/production-statistics/{iid}", f"/inverters/{iid}/production-statistics"):
        try_get(f"{base}?day={today.day}&month={today.month}&year={today.year}")
