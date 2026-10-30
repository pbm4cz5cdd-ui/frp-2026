#!/usr/bin/env python3
"""Build data/missing-retry.csv: universities whose crawl ended with 0 facts.
Reads the shard logs and keeps the original homepage from data/missing.csv.

Usage: python3 scripts/build_retry.py [data/missing.csv] [data/missing-retry.csv]
"""

import csv
import glob
import re
import sys

INP = sys.argv[1] if len(sys.argv) > 1 else "data/missing.csv"
OUT = sys.argv[2] if len(sys.argv) > 2 else "data/missing-retry.csv"
ZERO = re.compile(r"\]\s+(.+?):\s+0 facts\s*$")


def zero_names():
    names = set()
    for path in glob.glob("data/fill-missing-*.log"):
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = ZERO.search(line)
                if m:
                    names.add(m.group(1).strip())
    return names


def main():
    rows = list(csv.DictReader(open(INP, encoding="utf-8")))
    names = zero_names()
    keep = [r for r in rows if r["name"] in names]
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(keep)
    print(f"0-fact names: {len(names)}, rows written: {len(keep)} -> {OUT}")


if __name__ == "__main__":
    main()
