"""Read-only probe: login, then GET a few endpoints. Prints only structure, never values.

Run in your own terminal (credentials stay out of chat and files):
    $env:OSTROM_EMAIL = "..."; $env:OSTROM_PASSWORD = "..."; python probe_readonly.py
Optional: $env:OSTROM_BASE = "https://vpp.ostrom.de/v1" to test the other host.
"""
import os
import sys

from ostrom_client import API, OstromClient, OstromError

ENDPOINTS = ["/contracts", "/users/me", "/me", "/smart-devices/contract-locations", "/vehicles", "/chargers", "/batteries", "/hvacs",
             "/smart-devices/energy-flow", "/smart-devices/schedules"]


def shape(v, depth=0):
    """Describe JSON structure without leaking values (strings/numbers shown as their type)."""
    if isinstance(v, dict):
        return {k: shape(x, depth + 1) for k, x in v.items()} if depth < 4 else "{...}"
    if isinstance(v, list):
        return [shape(v[0], depth + 1)] if v else []
    return type(v).__name__


def main():
    email, pw = os.environ.get("OSTROM_EMAIL"), os.environ.get("OSTROM_PASSWORD")
    if not email or not pw:
        sys.exit("set OSTROM_EMAIL and OSTROM_PASSWORD first")
    c = OstromClient(os.environ.get("OSTROM_BASE", API))
    try:
        resp = c.login(email, pw)
    except OstromError as e:
        sys.exit(f"login failed: {e}")
    print("login ok. body shape:", shape(resp))
    print("Set-Cookie names:", c.cookie_attrs())
    print("cookie flags:", c.cookie_flags)
    for p in ENDPOINTS:
        try:
            print(f"GET {p} ->", shape(c.get(p)))
        except OstromError as e:
            print(f"GET {p} -> {e.status}")


main()
