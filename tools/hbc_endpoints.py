"""Summarise REST calls (method, path pieces, body keys) from hbc-decompiler output."""
import re
import sys

KEYS = ("smart-devices", "/chargers", "/vehicles", "/hvacs", "/hems", "/schedules", "/batteries",
        "/power-cloud", "/charging-pair", "/active-contract", "/production-statistics", "/meters")
lines = open(sys.argv[1], encoding="utf-8", errors="replace").read().split("\n")
out = []
for i, l in enumerate(lines):
    m = re.search(r"// Original name: (\w+), environment", l)
    if not m:
        continue
    blk = []
    for j in range(i + 1, min(i + 70, len(lines))):
        if "Original name:" in lines[j]:
            break
        blk.append(lines[j])
    txt = "\n".join(blk)
    if not any(k in txt for k in KEYS):
        continue
    meth = re.findall(r"= r\d+\.(post|get|put|delete|patch)\b;", txt)
    strs = re.findall(r"= '([^']*)';", txt)
    pieces = [s for s in strs if s.startswith("/") or "?" in s or s.startswith("&")]
    body = re.findall(r"\['(\w+)'\] =", txt)
    out.append(f"{m.group(1):38s} {','.join(meth) or '?':6s} {' + '.join(pieces)}   body={body}")
print("\n".join(sorted(set(out))))
