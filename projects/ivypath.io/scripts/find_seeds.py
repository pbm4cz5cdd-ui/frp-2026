#!/usr/bin/env python3
"""Find the official requirements page for universities whose homepage crawls
badly (JavaScript shells, requirements not linked from the homepage).

For each name in the list it asks DuckDuckGo (through the Jina reader, as the
web-search skill says) for `site:<host> IELTS TOEFL English proficiency`, keeps
same-site results and writes them as extra fill_missing.py seeds. One row per
URL, the same name may appear more than once.

Usage: python3 scripts/find_seeds.py NAMES.txt OUT.csv [queries_per_name]
Input: NAMES.txt (one university name per line), data/missing-core.csv (homepage)
Output: OUT.csv with name,country,homepage
"""

import csv
import re
import sys
import time
from urllib.parse import unquote, urlparse

import requests

UA = "ivypath-check/1.0 (student project; 1 request/second)"
DELAY = 1.1
JINA = "https://r.jina.ai/"
QUERIES = (
    "site:{host} IELTS TOEFL English language proficiency undergraduate",
    "site:{host} first-year international applicants english requirements",
)
GOOD = ("english", "language", "proficiency", "requirement", "ielts", "toefl",
        "international", "admission", "apply", "standardized", "testing",
        "first-year", "freshman")
BAD = ("graduate", "graduat", "masters", "mba", "doctoral", "law", "medicine",
       "medical", "dental", "business", "alumni", "donate", "news", "events",
       "login", "executive", "professional-studies", "continuing")


def base_domain(host):
    parts = re.sub(r"^www\.", "", host).split(".")
    if len(parts) >= 3 and parts[-2] in ("ac", "co", "com", "edu", "gov", "net", "org", "sch"):
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def search(query):
    url = JINA + "https://html.duckduckgo.com/html/?q=" + requests.utils.quote(query) + "&kl=us-en"
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=45)
    except Exception as e:
        print(f"  search failed: {type(e).__name__}", flush=True)
        return []
    if r.status_code != 200:
        print(f"  search HTTP {r.status_code}", flush=True)
        return []
    out = []
    for m in re.finditer(r"uddg=([^&)\s]+)", r.text):
        u = unquote(m.group(1)).split("#")[0]
        if u.startswith("http"):
            out.append(u)
    return out


def score(url, host):
    path = (urlparse(url).path + " " + urlparse(url).query).lower()
    if any(b in path for b in BAD):
        return -1
    return sum(2 for w in GOOD if w in path)


def main():
    names_file, out_file = sys.argv[1], sys.argv[2]
    nq = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    names = [x.strip() for x in open(names_file, encoding="utf-8") if x.strip()]
    rows = {r["name"]: r for r in csv.DictReader(open("data/missing-core.csv", encoding="utf-8"))}
    out, missing = [], []
    for i, name in enumerate(names, 1):
        r = rows.get(name)
        if not r:
            missing.append(name)
            print(f"[{i}/{len(names)}] no row: {name}", flush=True)
            continue
        host = (urlparse(r["homepage"]).hostname or "").removeprefix("www.")
        found = []
        for q in QUERIES[:nq]:
            for u in search(q.format(host=host)):
                h = (urlparse(u).hostname or "").removeprefix("www.")
                if h and (h == host or base_domain(h) == base_domain(host)):
                    s = score(u, host)
                    if s >= 4 and u not in [x[1] for x in found]:
                        found.append((s, u))
            time.sleep(DELAY)
            if found:
                break
        found.sort(reverse=True)
        picked = [u for _, u in found[:2]]
        for u in picked:
            out.append({"name": name, "country": r["country"], "homepage": u})
        print(f"[{i}/{len(names)}] {name}: {len(picked)} seeds {picked[:1]}", flush=True)
    with open(out_file, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["name", "country", "homepage"])
        w.writeheader()
        w.writerows(out)
    print(f"{out_file}: {len(out)} seeds for {len(names) - len(missing)} universities", flush=True)
    if missing:
        print("not in missing-core.csv: " + ", ".join(missing), flush=True)


if __name__ == "__main__":
    main()
