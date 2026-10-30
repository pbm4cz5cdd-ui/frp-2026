#!/usr/bin/env python3
"""Build a fill_missing.py input list for given countries.

Keeps rows that still have no IELTS, TOEFL or SAT value/note. The homepage
comes from data/missing-en.csv when the school is there, otherwise from the
admissions_url column of data/universities.csv.

The optional third argument lists the facts to look at (default: ielts,toefl,sat),
so a SAT-only run does not re-crawl universities that only lack SAT.

Usage: python3 scripts/build_missing_input.py uk,canada data/missing-uk.csv [sat]
"""

import csv
import sys

EMPTY = ("ielts", "toefl", "sat")


def empty(row, key):
    return not (row.get(key) or "").strip() and not (row.get(key + "_note") or "").strip()


def main():
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    countries = {c.strip() for c in sys.argv[1].split(",") if c.strip()}
    out = sys.argv[2]
    facts = tuple(x.strip() for x in sys.argv[3].split(",") if x.strip()) if len(sys.argv) > 3 else EMPTY
    have = {r["name"]: r for r in csv.DictReader(open("data/universities.csv", encoding="utf-8"))}
    seeds = {}
    try:
        for r in csv.DictReader(open("data/missing-en.csv", encoding="utf-8")):
            if r.get("homepage", "").strip():
                seeds[r["name"]] = r["homepage"].strip()
    except FileNotFoundError:
        pass
    rows = []
    for name, u in have.items():
        if (u.get("country") or "").strip() not in countries:
            continue
        if not any(empty(u, k) for k in facts):
            continue
        home = seeds.get(name) or (u.get("admissions_url") or "").strip()
        if not home:
            print("no homepage:", name, file=sys.stderr)
            continue
        rows.append({"name": name, "country": u["country"].strip(), "homepage": home})
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["name", "country", "homepage"])
        w.writeheader()
        w.writerows(rows)
    print(f"{out}: {len(rows)} rows")


if __name__ == "__main__":
    main()
