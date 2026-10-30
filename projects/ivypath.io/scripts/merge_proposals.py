#!/usr/bin/env python3
"""Merge shard proposal files into one CSV, keeping the best row per (name, fact).

Usage: python3 scripts/merge_proposals.py OUT INP [INP ...]
Never globs: the caller lists the files, so OUT can never include itself.
"""

import csv
import sys

RANK = {"not_required": 1, "varies": 2, "value": 3}


def main():
    out, inputs = sys.argv[1], sys.argv[2:]
    best, head = {}, None
    for path in inputs:
        if path == out:
            continue
        with open(path, encoding="utf-8") as fh:
            rd = csv.DictReader(fh)
            head = head or rd.fieldnames
            for row in rd:
                key = (row["name"], row["fact"])
                old = best.get(key)
                score = (RANK.get(row["status"], 0), "ориентир ~" in (row["note"] or ""))
                if old is None or score > old[0]:
                    best[key] = (score, row)
    rows = [r for _, r in best.values()]
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=head)
        w.writeheader()
        w.writerows(rows)
    print(f"merged {len(rows)} proposals from {len(inputs)} files -> {out}")


if __name__ == "__main__":
    main()
