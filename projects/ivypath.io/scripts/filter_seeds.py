#!/usr/bin/env python3
"""Drop seeds that point at graduate/professional-school pages.

find_seeds.py searches the whole host, so `site:uga.edu IELTS TOEFL` happily
returns grad.uga.edu. This removes those rows before they reach fill_missing.py.

Usage: python3 scripts/filter_seeds.py IN.csv OUT.csv
"""

import csv
import sys
from urllib.parse import urlparse

BAD_HOST = ("grad.", "gradschool", "mba.", "law.", "med.", "medicine.", "dent.",
            "publichealth", "socialwork", "tssw", "sps.", "pharmacy.", "nursing.",
            "business.", "executive", "online.")
BAD_PATH = ("graduate", "grad-degree", "grad-admission", "/grad/", "masters", "master-", "doctoral",
            "phd", "mba", "law-school", "/law", "medicine", "medical-school",
            "dental", "public-health", "publichealth", "social-work", "tssw",
            "executive-education", "professional-studies", "continuing")


def main():
    src, dst = sys.argv[1], sys.argv[2]
    rows = list(csv.DictReader(open(src, encoding="utf-8")))
    keep, drop = [], []
    for r in rows:
        u = r["homepage"]
        host = (urlparse(u).hostname or "").lower()
        path = (urlparse(u).path or "").lower()
        if any(host.startswith(b) or f".{b}" in host for b in BAD_HOST) or \
                any(b in path for b in BAD_PATH):
            drop.append(r)
        else:
            keep.append(r)
    with open(dst, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["name", "country", "homepage"])
        w.writeheader()
        w.writerows(keep)
    print(f"{src}: {len(rows)} seeds -> {len(keep)} kept, {len(drop)} dropped")
    for r in drop:
        print("  drop", r["name"], r["homepage"])


if __name__ == "__main__":
    main()
