#!/usr/bin/env python3
"""Write the SAT targets found by fill_sat.py into data/universities.csv.

Replaces "ориентир не опубликован" in sat_note with the found target
("ориентир ~1540 (75-й перцентиль принятых)"), sets sat_source and
sat_checked. Never touches a row that already has "~N".

Usage: python3 scripts/apply_sat.py [--dry-run] [proposals ...]
"""

import csv
import glob
import os
import re
import sys
from datetime import date

CSV = "data/universities.csv"
TARGET = re.compile(r"ориентир[^.;]*?не опубликован", re.I)
HAS = re.compile(r"(?:ориентир|цель)\s*~?\s*\d{3,4}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    dry = "--dry-run" in sys.argv
    files = args or sorted(glob.glob("data/proposals-sat*.csv"))
    files = [f for f in files if os.path.exists(f)]
    props = {}
    for path in files:
        for r in csv.DictReader(open(path, encoding="utf-8")):
            name = (r.get("name") or "").strip()
            try:
                hi = int(r.get("sat_target") or 0)
            except ValueError:
                continue
            if not name or not (1000 <= hi <= 1600):
                continue
            src = (r.get("source") or "").strip()
            app = (r.get("note_appendix") or "").strip()
            if not src.startswith("http") or "ориентир ~" not in app:
                continue
            props[name] = (hi, app, src)

    rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
    fields = list(rows[0].keys())
    done, skip = [], []
    for r in rows:
        p = props.get(r["name"].strip())
        if not p:
            continue
        hi, app, src = p
        note = r.get("sat_note", "")
        if HAS.search(note):
            skip.append((r["name"], "уже есть ~N"))
            continue
        new = TARGET.sub(app.rstrip("."), note, count=1)
        if new == note:
            new = (note.rstrip(". ") + "; " + app).strip("; ")
        r["sat_note"] = new
        r["sat_source"] = src
        r["sat_checked"] = date.today().isoformat()
        # keep sat empty: a number there would render as "SAT 1540" (looks required)
        done.append(r["name"])

    if dry:
        print(f"would update {len(done)}, skip {len(skip)}, proposals {len(props)}")
        for n in done[:10]:
            print("  ", n, props[n][1])
        return
    if done:
        with open(CSV, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
    print(f"updated {len(done)}, skip {len(skip)}, rows {len(rows)}")
    for n, why in skip[:5]:
        print("  skip", n, why)


if __name__ == "__main__":
    main()
