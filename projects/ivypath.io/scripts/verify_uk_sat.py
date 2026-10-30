#!/usr/bin/env python3
"""Check UK "SAT not required" proposals against the page they cite.

UK universities admit on A-levels/IB/UCAS, so their pages list those
qualifications and never demand SAT. The crawler finds that page but quotes
only its title, so apply_missing.py refuses it. This script opens the cited
page again and keeps the proposal only when the page really talks about
A-level/IB/UCAS and never mentions SAT.

Usage: python3 scripts/verify_uk_sat.py data/proposals-g-uksat.csv OUT.csv
"""

import csv
import gzip
import io
import re
import sys
import time
import urllib.request

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
LEVELS = re.compile(r"A[- ]?level|International Baccalaureate|\bIB\b|UCAS", re.I)
SAT = re.compile(r"\bSAT\b|\bACT\b", re.I)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=25) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
    return raw.decode("utf-8", "replace")


def text(html):
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def main():
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    src, out = sys.argv[1], sys.argv[2]
    rows = [r for r in csv.DictReader(open(src, encoding="utf-8"))
            if r["fact"] == "sat" and r["status"] == "not_required"]
    kept, dropped = [], []
    for r in rows:
        url = (r.get("source") or "").strip()
        try:
            t = text(get(url))
        except Exception as e:
            dropped.append((r["name"], f"не открылась: {e}"))
            time.sleep(1.2)
            continue
        m = LEVELS.search(t)
        if not m:
            dropped.append((r["name"], "на странице нет A-level/IB/UCAS"))
        elif SAT.search(t):
            dropped.append((r["name"], "на странице упомянут SAT/ACT"))
        else:
            start = max(0, m.start() - 90)
            quote = t[start:m.end() + 150].strip()
            row = dict(r)
            row["quote"] = quote
            kept.append(row)
        time.sleep(1.2)
    with open(out, "w", encoding="utf-8", newline="") as f:
        head = (list(rows[0].keys()) if rows else
                ["name", "country", "fact", "status", "value", "note",
                 "quote", "source", "checked", "tier"])
        w = csv.DictWriter(f, fieldnames=head)
        w.writeheader()
        w.writerows(kept)
    print(f"kept {len(kept)}, dropped {len(dropped)} -> {out}")
    for name, why in dropped:
        print("DROP", name, "|", why)
    return 0


if __name__ == "__main__":
    sys.exit(main())
