#!/usr/bin/env python3
"""For rows whose homepage is a Chinese site, find the English version of the
university site and write it as the seed for fill_missing.py.

Usage: python3 scripts/find_en_seeds.py
Input:  data/missing-core.csv (name,country,homepage)
Output: data/missing-en.csv   (name,country,homepage = working English page)
        data/find-en.log      (one line per university)
"""

import csv
import re
import sys
import time
from urllib.parse import urlparse

import requests

UA = "ivypath-check/1.0 (student project; 1 request/second)"
DELAY = 1.1
INP = "data/missing-core.csv"
OUT = "data/missing-en.csv"
LOG = "data/find-en.log"
CANDIDATES = (
    "https://en.{d}",
    "https://www.{d}/english/",
    "https://www.{d}/en/",
    "https://iso.{d}",
    "https://admissions.{d}",
    "https://international.{d}",
    "http://en.{d}",
    "https://www.{d}/English/",
)


def domain(home):
    h = (urlparse(home).hostname or "").lower()
    return re.sub(r"^(www|en|iso|admissions|international)\.", "", h)


def english_score(html):
    body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", body)
    text = re.sub(r"\s+", " ", text)
    letters = re.findall(r"[A-Za-z]", text)
    cjk = re.findall(r"[一-鿿]", text)
    stop = len(re.findall(r"\b(the|and|of|for|students|university|admission|international)\b",
                          text, re.I))
    return len(letters), len(cjk), stop, text


def get(url):
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=12, allow_redirects=True)
    except Exception as e:
        return None, type(e).__name__
    if r.status_code != 200 or "html" not in r.headers.get("content-type", ""):
        return None, f"HTTP {r.status_code}"
    n_letters, n_cjk, stop, _ = english_score(r.text)
    if len(r.text) < 2000 or n_letters < 600 or stop < 5 or n_cjk > n_letters:
        return None, f"not English (letters {n_letters}, cjk {n_cjk}, en {stop})"
    return r.url, "ok"


def main():
    rows = list(csv.DictReader(open(INP, encoding="utf-8")))
    out = open(OUT, "w", encoding="utf-8", newline="")
    log = open(LOG, "w", encoding="utf-8")
    w = csv.DictWriter(out, fieldnames=["name", "country", "homepage"])
    w.writeheader()
    found = 0
    cn = 0
    for i, r in enumerate(rows, 1):
        home = r["homepage"].strip()
        d = domain(home)
        if not d.endswith((".cn", ".edu.cn")) and r["country"] not in ("china", "hongkong"):
            w.writerow(r)
            continue
        cn += 1
        hit = None
        tried = []
        for tpl in CANDIDATES:
            u = tpl.format(d=d)
            got, why = get(u)
            time.sleep(DELAY)
            tried.append(f"{u} {why}")
            if got:
                hit = got
                break
        if hit:
            found += 1
            w.writerow({"name": r["name"], "country": r["country"], "homepage": hit})
            log.write(f"OK {r['name']}: {hit}\n")
        else:
            w.writerow(r)
            log.write(f"NO {r['name']}: " + " | ".join(tried) + "\n")
        print(f"[{i}/{len(rows)}] {r['name']}: {hit or 'none'}", flush=True)
    out.close()
    log.close()
    print(f"chinese rows {cn}, english seeds found {found}", flush=True)


if __name__ == "__main__":
    main()
