"""Probe #4: does the smart-charging-override route exist on the VPP host? EMPTY body, no vehicle id -> nothing can start."""
import os
import sys

from ostrom_client import API, OstromClient, OstromError

VPP = "https://vpp.ostrom.de/v1"
email, pw = os.environ.get("OSTROM_EMAIL"), os.environ.get("OSTROM_PASSWORD")
if not email or not pw:
    sys.exit("set OSTROM_EMAIL and OSTROM_PASSWORD first")
c = OstromClient(API)
c.login(email, pw)
try:
    r = c.request("POST", "/smart-devices/smart-charging-override", {}, base=VPP)
    print("POST {} on VPP unexpectedly accepted:", r)
except OstromError as e:
    print("POST {} on VPP ->", e.status, str(e)[:500])
