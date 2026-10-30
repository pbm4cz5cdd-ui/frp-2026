#!/usr/bin/env python3
"""Fill empty admissions_url from the page catalog and write the input list
for fill_missing.py: universities whose IELTS, TOEFL or SAT is still empty.

Usage: python3 scripts/prepare_core.py
Output: data/missing-core.csv (name,country,homepage)
"""

import csv
import json
import re

CSV = "data/universities.csv"


def page_catalog():
    html = open("index.html", encoding="utf-8").read()
    found = {}
    pat = re.compile(r'\{n:"((?:[^"\\]|\\.)*)",c:"([^"]+)"([^\n{}]*)\}')
    for m in pat.finditer(html):
        name = m.group(1).replace("\\'", "'").replace('\\"', '"')
        u = re.search(r'u:"([^"]*)"', m.group(3))
        found.setdefault(name, (m.group(2), u.group(1) if u else ""))
    m = re.search(r"const IMPORTED=(\[.*?\]);\s*UNIS\.push", html, re.S)
    for it in json.loads(m.group(1)):
        found.setdefault(it["n"], (it["c"], it.get("u", "")))
    return found


def filled(row, fact):
    return bool(row.get(f"{fact}_checked")) and bool(
        row.get(fact, "").strip() or row.get(f"{fact}_note", "").strip())


def main():
    catalog = page_catalog()
    rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
    head = list(rows[0].keys())
    changed = 0
    have = {r["name"] for r in rows}
    for r in rows:
        if not r["admissions_url"].strip() and r["name"] in catalog:
            r["admissions_url"] = catalog[r["name"]][1]
            changed += 1
    # page universities with no row at all: add a stub so they get checked
    for name, (country, url) in catalog.items():
        if name in have:
            continue
        new = {h: "" for h in head}
        new["name"], new["country"], new["admissions_url"] = name, country, url
        rows.append(new)
        have.add(name)
    with open(CSV + ".tmp", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=head)
        w.writeheader()
        w.writerows(rows)
    import os
    os.replace(CSV + ".tmp", CSV)

    missing = []
    for r in rows:
        if any(not filled(r, fact) for fact in ("ielts", "toefl", "sat")):
            url = r["admissions_url"].strip() or catalog.get(r["name"], ("", ""))[1]
            missing.append({"name": r["name"], "country": r["country"],
                            "homepage": url})
    with open("data/missing-core.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["name", "country", "homepage"])
        w.writeheader()
        w.writerows(missing)
    print(f"urls filled {changed}, rows now {len(rows)}, core gaps {len(missing)}")


if __name__ == "__main__":
    main()
