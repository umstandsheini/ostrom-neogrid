"""Read-only: latest account transactions (NeoGrid credits) to find where a new credit shows up.

Prints your own credit bookings (type, amount, dates, status). No IBAN/name/address.
"""
import os
import sys

from ostrom_client import API, OstromClient

email, pw = os.environ.get("OSTROM_EMAIL"), os.environ.get("OSTROM_PASSWORD")
if not email or not pw:
    sys.exit("set OSTROM_EMAIL and OSTROM_PASSWORD first")
c = OstromClient(os.environ.get("OSTROM_BASE", API))
uid = c.login(email, pw)["id"]
d = c.get(f"/users/{uid}/account-transactions")
print("current invoice credits:", d["currentInvoiceCreditsAmount"], "| marketplace:", d["currentMarketPlaceCreditsAmount"])
tx = sorted(d["transactions"], key=lambda t: t["createdAt"], reverse=True)
print("latest 8 of", len(tx), "(createdAt, type, subType, amount, invoiceCredits, marketCredits, status, availableAt):")
for t in tx[:8]:
    print(" ", t["createdAt"][:19], t["type"], t["subType"], t["amount"], t["invoiceCreditsAmount"],
          t["marketPlaceCreditsAmount"], t["status"], (t["availableAt"] or "")[:10])
