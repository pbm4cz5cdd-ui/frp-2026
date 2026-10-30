#!/usr/bin/env python3
"""Write verified "SAT не требуется" notes for UK rows.

Input comes from verify_uk_sat.py: every row was re-checked on its official
page (A-level/IB/UCAS present, no SAT/ACT). Fields that already have a value
or a note are left alone.

Usage: python3 scripts/apply_uk_sat.py FILE.csv [--dry-run]
"""

import csv
import os
import sys

CSV = "data/universities.csv"
REVIEW = "data/review-uk-sat.csv"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__, file=sys.stderr)
        return 2
    dry = "--dry-run" in sys.argv
    prop = args[0]

    rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
    head = list(rows[0].keys())
    by_name = {r["name"]: r for r in rows}
    applied, skipped = [], []
    for p in csv.DictReader(open(prop, encoding="utf-8")):
        u = by_name.get(p["name"])
        if u is None:
            skipped.append((p["name"], "нет в CSV"))
            continue
        if not (p["note"] or "").startswith("SAT не требуется"):
            skipped.append((p["name"], "неожиданное примечание"))
            continue
        if (u.get("sat") or "").strip() or (u.get("sat_note") or "").strip():
            skipped.append((p["name"], "уже заполнено"))
            continue
        if dry:
            applied.append(p["name"])
            continue
        u["sat_note"] = p["note"]
        u["sat_source"] = p["source"]
        u["sat_checked"] = p["checked"]
        applied.append(p["name"])

    print(f"applied {len(applied)}, skipped {len(skipped)}")
    for name in applied:
        print("APPLY", name)
    for name, why in skipped:
        print("SKIP", name, "|", why)
    if dry:
        return 0
    tmp = CSV + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=head)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, CSV)
    with open(REVIEW, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["name", "reason"])
        w.writeheader()
        w.writerows({"name": n, "reason": why} for n, why in skipped)
    return 0


if __name__ == "__main__":
    sys.exit(main())
