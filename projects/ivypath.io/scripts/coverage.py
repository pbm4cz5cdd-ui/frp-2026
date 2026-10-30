#!/usr/bin/env python3
import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REQ = ("ielts", "toefl", "sat", "hsk", "ap", "aid")


def is_filled(row, key):
    checked = (row.get(key + "_checked") or "").strip()
    if key == "aid":
        return bool(checked and ((row.get("aid_type") or "").strip() or (row.get("aid_note") or "").strip()))
    value = (row.get(key) or "").strip()
    note = (row.get(key + "_note") or "").strip()
    return bool(checked and (value or note))


def load_page(path):
    html = path.read_text(encoding="utf-8")
    # Cards live in the first UNIS array and in the UNIS.push(...) blocks after it.
    static = {
        m.group(1): m.group(2)
        for m in re.finditer(r'\{n:"([^"]+)",c:"([^"]+)"', html)
    }
    imported = []
    match = re.search(r"const IMPORTED=(\[.*?\]);\s*UNIS\.push", html, re.S)
    if match:
        imported = json.loads(match.group(1))
    unis = dict(static)
    for item in imported:
        name = (item.get("n") or "").strip()
        if name:
            unis.setdefault(name, item.get("c") or "?")
    return unis


def main():
    root = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description="Show requirement coverage by country.")
    ap.add_argument("--csv", default=str(root / "data" / "universities.csv"))
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.csv, newline="", encoding="utf-8")))
    unis = load_page(root / "index.html")
    by_name = {}
    unmatched = []
    for row in rows:
        name = (row.get("name") or "").strip()
        if name in unis:
            by_name[name] = row
        else:
            unmatched.append(name)

    by_country = defaultdict(list)
    for name, country in unis.items():
        by_country[(country or "?").strip() or "?"].append(by_name.get(name))

    header = ["country", "rows"] + [x.upper() for x in REQ]
    print("\t".join(header))
    for country, group in sorted(by_country.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        counts = [str(sum(is_filled(r, key) for r in group if r)) + "/" + str(len(group)) for key in REQ]
        print("\t".join([country, str(len(group))] + counts))
    totals = [str(sum(is_filled(r, key) for r in by_name.values())) + "/" + str(len(unis)) for key in REQ]
    print("\t".join(["TOTAL", str(len(unis))] + totals))

    if unmatched:
        print(f"note: {len(unmatched)} CSV rows do not match a page name: {', '.join(unmatched)}", file=sys.stderr)


if __name__ == "__main__":
    main()
