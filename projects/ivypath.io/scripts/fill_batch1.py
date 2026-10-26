#!/usr/bin/env python3
"""Extract IELTS/TOEFL/SAT evidence for a batch CSV with the class model,
keeping only answers whose quote is found on the official page.
Defaults to data/us-batch1.csv -> data/proposals-batch1.csv; use --csv and
--out for another batch. Does not change the site or universities.csv."""

import csv
import os
import re
import sys
import time
from datetime import date
from urllib.parse import urlparse

from fill_requirements import DELAY, ask, clean, get, norm, relevant
from find_batch_urls import links_from

SRC = "data/us-batch1.csv"
OUT = "data/proposals-batch1.csv"
TODAY = date.today().isoformat()
FACTS = ("ielts", "toefl", "sat")
FIELDS = ["name", "fact", "status", "value", "note", "quote", "source", "checked"]


def main():
    global SRC, OUT
    args = sys.argv[1:]
    limit = int(args[0]) if args and not args[0].startswith("--") else 999
    for flag, name in (("--csv", "SRC"), ("--out", "OUT")):
        if flag in args:
            try:
                value = args[args.index(flag) + 1]
            except IndexError:
                print(f"{flag} needs a file path", file=sys.stderr)
                return 2
            if name == "SRC":
                SRC = value
            else:
                OUT = value
    rows = list(csv.DictReader(open(SRC, encoding="utf-8")))
    todo = [r for r in rows if (r.get("final_url") or r.get("admissions_url"))][:limit]

    done = set()
    try:
        for r in csv.DictReader(open(OUT, encoding="utf-8")):
            done.add((r["name"], r["fact"]))
    except FileNotFoundError:
        pass

    exists = os.path.exists(OUT)
    f = open(OUT, "a", encoding="utf-8", newline="")
    w = csv.DictWriter(f, fieldnames=FIELDS)
    if not exists:
        w.writeheader()
        f.flush()

    for i, u in enumerate(todo, 1):
        name = u["name"]
        if all((name, fact) in done for fact in FACTS):
            print(f"[{i}/{len(todo)}] skip {name}", flush=True)
            continue
        start = u.get("final_url") or u.get("admissions_url")
        first = None
        seen = set()
        queue = [(start, 0)]
        found = False
        pages = 0
        while queue and pages < 6 and not all((name, fact) in done for fact in FACTS):
            url, depth = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            try:
                if url == start and first is not None:
                    page = first
                else:
                    page = get(url)
                    time.sleep(DELAY)
                pages += 1
                if page.status_code != 200:
                    continue
                if url == start:
                    first = page
                txt = clean(page.text)
                rel = relevant(txt)
                if rel and re.search(r"IELTS|TOEFL", rel, re.I):
                    ans = ask(rel, url)
                    time.sleep(0.3)
                    for fact in FACTS:
                        if (name, fact) in done:
                            continue
                        a = ans.get(fact) or {}
                        q = (a.get("quote") or "").strip()
                        if not q or norm(q)[:110] not in norm(txt):
                            continue
                        status = a.get("status")
                        if status not in ("value", "not_required", "varies", "not_stated"):
                            continue
                        val = a.get("value")
                        if status == "value" and val in (None, ""):
                            continue
                        if fact == "sat" and status == "not_required" and re.search(r"SAT\s+(Essay|Subject)", q, re.I):
                            continue
                        w.writerow({"name": name, "fact": fact, "status": status,
                                    "value": val, "note": a.get("note", ""),
                                    "quote": q, "source": url, "checked": TODAY})
                        done.add((name, fact))
                        f.flush()
                        found = True
                if found:
                    print(f"[{i}/{len(todo)}] {name}: {url} OK", flush=True)
                if depth < 2:
                    for nxt in links_from(page.text, page.url)[:3]:
                        if nxt not in seen:
                            queue.append((nxt, depth + 1))
            except Exception as e:
                print(f"[{i}/{len(todo)}] {name}: {url} {type(e).__name__}", flush=True)
        if not found:
            print(f"[{i}/{len(todo)}] {name}: nothing", flush=True)
    f.close()


if __name__ == "__main__":
    main()
