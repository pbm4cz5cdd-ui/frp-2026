#!/usr/bin/env python3
"""Find a UK university page that proves admission is by A-level/IB/UCAS.

For every row of the input (name,country,homepage) the script opens the
homepage, follows up to a few links that look like entry-requirement or
undergraduate-admission pages, and keeps the first page that mentions
A-level / IB / UCAS and never mentions SAT or ACT. The quote written into
the proposal is a real snippet of that page.

Rows for which no page passes are listed on stderr.

Usage: python3 scripts/find_uk_entry_pages.py data/missing-uk-sat.csv OUT.csv
"""

import csv
import datetime
import gzip
import re
import sys
import time
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
LEVELS = re.compile(r"A[- ]?level|International Baccalaureate|\bIB\b|UCAS", re.I)
SAT = re.compile(r"\bSAT\b|\bACT\b", re.I)
# A navigation menu also says "UCAS code" next to a course list, which proves
# nothing. The quote must sit in real admission wording.
STRICT = re.compile(r"entry requirement|typical offer|we require|usually require"
                    r"|grades? (?:of|ranging|between)|points from|admission requirement"
                    r"|require(?:s|d)? (?:a |an )?(?:grade|A[- ]level|UCAS)"
                    r"|accepted (?:qualification|for entry)|considered for entry", re.I)
GOOD = re.compile(r"entry|requirement|undergraduate|admission|how-to-apply|apply", re.I)
HREF = re.compile(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.I | re.S)
NOTE = "SAT не требуется: поступление по национальной системе (A-level/IB/аттестат)"
HEAD = ["name", "country", "fact", "status", "value", "note", "quote",
        "source", "checked", "tier"]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
    return raw.decode("utf-8", "replace")


def text(html):
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def pick(t):
    """Return a quote where the entry-route wording is real, or None."""
    if SAT.search(t):
        return None
    for m in LEVELS.finditer(t):
        window = t[max(0, m.start() - 160):m.end() + 160]
        if not STRICT.search(window):
            continue
        start = max(0, m.start() - 90)
        return t[start:m.end() + 150].strip()
    return None


def links(html, base):
    out, seen = [], set()
    for href, label in HREF.findall(html):
        href = href.strip()
        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        url = urllib.parse.urljoin(base, href).split("#")[0]
        if not url.startswith("http"):
            continue
        host = urllib.parse.urlparse(url).netloc.lstrip("www.")
        if host and host not in urllib.parse.urlparse(base).netloc:
            continue
        if url in seen:
            continue
        if GOOD.search(href) or GOOD.search(re.sub(r"<[^>]+>", " ", label)):
            seen.add(url)
            out.append(url)
    # pages that say "entry requirements" in the path first
    out.sort(key=lambda u: 0 if re.search(r"entry|requirement", u, re.I) else 1)
    return out[:8]


def main():
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    src, out = sys.argv[1], sys.argv[2]
    today = datetime.date.today().isoformat()
    rows = list(csv.DictReader(open(src, encoding="utf-8")))
    done = set()
    try:
        for r in csv.DictReader(open(out, encoding="utf-8")):
            done.add(r["name"])
    except FileNotFoundError:
        pass
    with open(out, "a" if done else "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEAD)
        if not done:
            w.writeheader()
        for row in rows:
            name, home = row["name"], row["homepage"].strip()
            if name in done:
                continue
            found = None
            try:
                page = get(home)
                cands = [home] + links(page, home)
            except Exception as e:
                print("FAIL", name, "home:", e, file=sys.stderr)
                cands = [home]
            for url in cands:
                try:
                    t = text(get(url))
                except Exception as e:
                    print("  skip", url, e, file=sys.stderr)
                    time.sleep(1.2)
                    continue
                hit = pick(t)
                if hit:
                    found = (url, hit)
                    break
                time.sleep(1.2)
            if found:
                w.writerow({"name": name, "country": row["country"], "fact": "sat",
                            "status": "not_required", "value": "", "note": NOTE,
                            "quote": found[1], "source": found[0],
                            "checked": today, "tier": "page"})
                f.flush()
                print("OK", name, found[0], file=sys.stderr)
            else:
                print("NOPAGE", name, file=sys.stderr)
            time.sleep(1.2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
