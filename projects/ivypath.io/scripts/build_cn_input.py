#!/usr/bin/env python3
"""Build the fill_missing.py input for Chinese/HK universities from the English
seeds in data/missing-en.csv. Keeps only rows that still have no IELTS, TOEFL
or SAT on data/universities.csv.

Usage: python3 scripts/build_cn_input.py
Output: data/missing-cn.csv (name,country,homepage); prints the count.
"""

import csv

EMPTY = ("ielts", "toefl", "sat")


def empty(row, key):
    return not row[key].strip() and not row[key + "_note"].strip()


def main():
    have = {r["name"]: r for r in csv.DictReader(open("data/universities.csv", encoding="utf-8"))}
    rows = []
    for r in csv.DictReader(open("data/missing-en.csv", encoding="utf-8")):
        if r["country"] not in ("china", "hongkong"):
            continue
        u = have.get(r["name"])
        if u is None:
            print("missing from universities.csv:", r["name"])
            continue
        if all(empty(u, k) for k in EMPTY):
            rows.append(r)
    with open("data/missing-cn.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["name", "country", "homepage"])
        w.writeheader()
        w.writerows(rows)
    print(f"data/missing-cn.csv: {len(rows)} rows")


if __name__ == "__main__":
    main()
