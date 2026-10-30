#!/usr/bin/env python3
"""Pick a working English-friendly seed for Chinese/HK universities.
Tries the homepage first, then the usual official subdomains (en., iso.,
international., apply.); keeps the first page that answers 200 with HTML.

Usage: python3 scripts/seed_cn.py
Input: data/missing-core.csv (china/hongkong rows)
Output: data/missing-cn2.csv (name,country,homepage)
"""

import csv
import time
from urllib.parse import urlparse

import requests

UA = "ivypath-check/1.0 (student project; 1 request/second)"
DELAY = 1.1
SUBS = ("en", "iso", "international", "apply", "admission")


def ok(url):
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=12,
                         allow_redirects=True)
    except Exception:
        return None
    if r.status_code == 200 and "html" in r.headers.get("content-type", ""):
        return r.url
    return None


def main():
    rows = [r for r in csv.DictReader(open("data/missing-core.csv", encoding="utf-8"))
            if r["country"] in ("china", "hongkong") and r["homepage"].strip()]
    out = []
    seeded = 0
    for r in rows:
        host = urlparse(r["homepage"]).hostname or ""
        host = host[4:] if host.startswith("www.") else host
        cands = [r["homepage"].strip()]
        cands += [f"https://{s}.{host}/" for s in SUBS]
        got = None
        for u in cands:
            got = ok(u)
            time.sleep(DELAY)
            if got:
                break
        seeded += bool(got)
        out.append({"name": r["name"], "country": r["country"],
                    "homepage": got or r["homepage"].strip()})
        print(("OK  " if got else "NO  ") + r["name"] + " " + (got or ""), flush=True)
    with open("data/missing-cn2.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["name", "country", "homepage"])
        w.writeheader()
        w.writerows(out)
    print(f"data/missing-cn2.csv: {len(out)} rows, {seeded} seeded", flush=True)


if __name__ == "__main__":
    main()
