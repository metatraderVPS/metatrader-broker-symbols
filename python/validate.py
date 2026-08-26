#!/usr/bin/env python3
"""Structural checks on the dataset. Run before opening a PR; CI runs it too.

Catches the failure modes that actually happen with hand-edited data: a CSV
that no longer agrees with the JSON, a symbol string silently whitespace-padded,
an instrument that lost its variants entry, a GMT offset outside the range any
real broker uses.
"""
import csv
import json
import sys
from pathlib import Path

D = Path(__file__).resolve().parent.parent / "data"
errors: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


brokers = json.loads((D / "brokers.json").read_text(encoding="utf-8"))
variants = json.loads((D / "variants.json").read_text(encoding="utf-8"))
instruments = set(json.loads((D / "instruments.json").read_text(encoding="utf-8")))
rows = list(csv.DictReader((D / "symbols.csv").open(encoding="utf-8")))

if not brokers:
    err("brokers.json is empty")

for slug, b in brokers.items():
    if not b.get("name"):
        err(f"{slug}: no name")
    if b.get("platform") not in ("MT4", "MT5", ""):
        err(f"{slug}: odd platform {b.get('platform')!r}")
    off = b.get("gmtOffset")
    if off is not None and not (-12 <= float(off) <= 14):
        err(f"{slug}: implausible gmtOffset {off}")
    for canon, e in (b.get("symbols") or {}).items():
        s = e.get("symbol")
        if not s:
            err(f"{slug}/{canon}: empty symbol")
            continue
        if s != s.strip():
            err(f"{slug}/{canon}: symbol {s!r} has surrounding whitespace")
        if canon not in instruments:
            err(f"{slug}/{canon}: instrument missing from instruments.json")
        if s not in variants.get(canon, []):
            err(f"{slug}/{canon}: {s!r} missing from variants.json")

csv_pairs = {(r["broker_slug"], r["canonical"], r["symbol"]) for r in rows}
json_pairs = {
    (slug, c, e["symbol"])
    for slug, b in brokers.items()
    for c, e in (b.get("symbols") or {}).items()
}
if csv_pairs != json_pairs:
    only_csv, only_json = csv_pairs - json_pairs, json_pairs - csv_pairs
    err(f"symbols.csv and brokers.json disagree: {len(only_csv)} only in CSV, "
        f"{len(only_json)} only in JSON")

print(f"{len(brokers)} brokers · {len(rows)} rows · {len(instruments)} instruments")
if errors:
    print(f"\n{len(errors)} problem(s):")
    for e in errors[:25]:
        print("  -", e)
    sys.exit(1)
print("dataset OK")
