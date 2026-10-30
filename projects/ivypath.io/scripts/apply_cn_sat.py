#!/usr/bin/env python3
"""Write verified "SAT не требуется" notes for Chinese rows.

Input comes from verify_cn_sat.py: every row was re-checked on its official
page (the entry-route sentence is still there, no SAT/ACT anywhere). Fields
that already have a value or a note are left alone.

Usage: python3 scripts/apply_cn_sat.py FILE.csv [--dry-run]
"""

import csv
import os
import sys

CSV = "data/universities.csv"
REVIEW = "data/review-cn-sat-apply.csv"


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
            skipped.append((p, "нет в CSV"))
            continue
        if not (p["note"] or "").startswith("SAT не требуется"):
            skipped.append((p, "неожиданное примечание"))
            continue
        if (u.get("sat") or "").strip() or (u.get("sat_note") or "").strip():
            skipped.append((p, "уже заполнено"))
            continue
        if not dry:
            u["sat_note"] = p["note"]
            u["sat_source"] = p["source"]
            u["sat_checked"] = p["checked"]
        applied.append(p)
    print(f"applied {len(applied)}, skipped {len(skipped)}")
    for p in applied:
        print("APPLY", p["name"])
    if skipped:
        with open(REVIEW, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["name", "reason"])
            for p, why in skipped:
                w.writerow([p["name"], why])
                print("SKIP", p["name"], "|", why)
    if dry:
        return 0
    tmp = CSV + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=head)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, CSV)
    return 0


if __name__ == "__main__":
    sys.exit(main())
