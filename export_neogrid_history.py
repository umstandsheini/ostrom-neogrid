"""Read-only: export your own NeoGrid history (per day: NeoGrid kWh, credit in ct) to neogrid_history.csv.

Walks back month by month (24 months, no early stop).
Only dates, kWh and credits are written - no locations, no ids.
"""
import csv
import datetime as dt
import os
import sys

from ostrom_client import API, OstromClient, OstromError

email, pw = os.environ.get("OSTROM_EMAIL"), os.environ.get("OSTROM_PASSWORD")
if not email or not pw:
    sys.exit("set OSTROM_EMAIL and OSTROM_PASSWORD first")
c = OstromClient(os.environ.get("OSTROM_BASE", API))
c.login(email, pw)
rows, windows, empty = [], [], 0
today = dt.date.today().replace(day=1)
for vehicle in c.get("/vehicles"):
    vid, y, m, empty = vehicle["id"], today.year, today.month, 0
    for _ in range(24):
        try:
            st = c.get(f"/vehicles/{vid}/interval-charging-session-statistics?month={y}-{m:02d}")
        except OstromError:
            st = None
        got = 0
        for day in (st or {}).get("days") or []:
            kwh = sum(s.get("kwhSum") or 0 for s in day.get("sessions") or [] if s.get("type") == "neogrid")
            if kwh > 0:
                got += 1
                rows.append((day["date"], vehicle["id"], round(kwh, 3), day.get("neogridCredits") or 0))
                for ses in day.get("sessions") or []:
                    if ses.get("type") == "neogrid":
                        windows.append((day["date"], vehicle["id"], ses["from"], ses["to"], ses.get("kwhSum")))
        # no early stop: the first run quit after 3 empty months and missed the Jan/Feb credits
        m -= 1
        if m == 0:
            y, m = y - 1, 12
rows.sort()
with open("neogrid_history.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["date", "vehicle_id", "neogrid_kwh", "credits_ct"])
    w.writerows(rows)
with open("neogrid_sessions.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["day", "vehicle_id", "from", "to", "kwh"])
    w.writerows(sorted(windows))
print(f"{len(windows)} NeoGrid sessions written to neogrid_sessions.csv")
print(f"{len(rows)} NeoGrid days written to neogrid_history.csv")
if rows:
    print("first:", rows[0][0], "last:", rows[-1][0], "| total kWh:", round(sum(r[2] for r in rows), 1),
          "| total credits EUR:", round(sum(r[3] for r in rows) / 100, 2))
