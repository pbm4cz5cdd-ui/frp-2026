#!/usr/bin/env python3
"""Re-check "test is accepted" proposals against the page they cite.

The crawler often quotes only a page title ("International English Language
Testing System, or IELTS"), which proves nothing. This script opens the cited
page again and keeps the proposal only when the test name really sits next to
admission wording ("we accept ... for entry", "official IELTS scores must be
submitted"). The quote it writes is that real snippet.

Usage: python3 scripts/verify_accepted.py IN.csv OUT.csv
"""

import csv
import gzip
import re
import sys
import time
import urllib.request

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
TESTS = {"ielts": r"IELTS", "toefl": r"TOEFL", "hsk": r"HSK"}
REJECT = re.compile(r"not accepted|not considered|not required|do(?:es)? not (?:accept|require)"
                    r"|cannot be used|will not be", re.I)
WORDS = re.compile(r"accept|requir|submit|submission|provide|take|demonstrat|welcome"
                   r"|proof|results?|one of the following|exams?:", re.I)


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


def find_quote(t, test):
    for m in re.finditer(test, t, re.I):
        window = t[max(0, m.start() - 120):m.end() + 120]
        words = WORDS.search(window)
        if not words:
            continue
        if REJECT.search(window):
            continue
        start = max(0, m.start() - 90)
        return t[start:m.end() + 150].strip()
    return None


def main():
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    src, out = sys.argv[1], sys.argv[2]
    rows = [r for r in csv.DictReader(open(src, encoding="utf-8"))
            if r["status"] == "accepted" and r["fact"] in TESTS]
    kept, dropped = [], []
    for r in rows:
        url = (r.get("source") or "").strip()
        if not url:
            dropped.append((r["name"], "нет источника"))
            continue
        try:
            t = text(get(url))
        except Exception as e:
            # one failed page must not stop the rest
            dropped.append((r["name"], f"не открылась: {e}"))
            time.sleep(1.2)
            continue
        q = find_quote(t, TESTS[r["fact"]])
        if q:
            row = dict(r)
            row["quote"] = q
            kept.append(row)
        else:
            dropped.append((r["name"], "на странице нет подтверждения"))
        time.sleep(1.2)
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else
                           ["name", "country", "fact", "status", "value", "note",
                            "quote", "source", "checked", "tier"])
        w.writeheader()
        w.writerows(kept)
    print(f"kept {len(kept)}, dropped {len(dropped)} -> {out}")
    for name, why in dropped:
        print("DROP", name, "|", why)
    return 0


if __name__ == "__main__":
    sys.exit(main())
