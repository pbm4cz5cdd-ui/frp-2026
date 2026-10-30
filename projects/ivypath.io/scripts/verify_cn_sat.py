#!/usr/bin/env python3
"""Re-check the China SAT proposals on their official pages.

A Chinese university takes you on the school certificate plus HSK or an exam
of its own, so SAT is not part of admission. apply_missing.py will not accept
that: it wants a quote that says "not required" in so many words, and Chinese
pages do not write it that way. This script uses the UK evidence standard
instead (see verify_uk_sat.py): the quote must be a real sentence that names
the entry route, and the page must never mention SAT or ACT. Every row is
fetched again, so a proposal is confirmed only if the page still says it.

Usage: python3 scripts/verify_cn_sat.py IN.csv OUT.csv [REVIEW.csv]
"""

import csv
import datetime
import gzip
import html
import re
import sys
import time
import urllib.request

UA = "ivypath-check/1.0 (student project; 1 request/second)"
SAT = re.compile(r"\bSAT\b|\bACT\b")
# The entry route: a school certificate, a diploma, or the HSK level a
# Chinese-taught programme asks for.
REQ = re.compile(r"high school (?:diploma|certificate|graduat)|senior high school"
                 r"|secondary school (?:diploma|certificate)|high school graduates?"
                 r"|HSK\s*(?:level\s*)?[4-9]\b", re.I)
VERB = re.compile(r"\b(?:must|should|shall|requires?|required|submit|provide|hold"
                  r"|obtain|have|pass)\b", re.I)
JUNK = re.compile(r"\?|scholarship", re.I)
NOTE = "SAT не требуется: приём по аттестату и HSK/вступительным экзаменам вуза"
HEAD = ["name", "country", "fact", "status", "value", "note", "quote",
        "source", "checked", "tier"]
REVIEW_HEAD = ["name", "fact", "status", "value", "quote", "source", "reason"]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=10) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
    enc = r.headers.get_content_charset() or "utf-8"
    try:
        return raw.decode(enc, "replace")
    except LookupError:
        return raw.decode("utf-8", "replace")


def text(s):
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    return flat(s)


def flat(s):
    s = html.unescape(s).replace("\u00a0", " ")
    return re.sub(r"\s+", " ", s).strip()


def on_page(quote, page):
    """True if a good part of the quote is still on the page.

    The crawler already cut the quote from the page text, but the page may
    have changed a little (a menu item moved), so any 60-character window is
    enough. Shorter quotes must match whole.
    """
    q = flat(quote)
    if not q:
        return False
    if len(q) <= 60:
        return q in page
    step = 20
    for i in range(0, len(q) - 60 + 1, step):
        if q[i:i + 60] in page:
            return True
    return False


def main():
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    src, out = sys.argv[1], sys.argv[2]
    review = sys.argv[3] if len(sys.argv) > 3 else None
    today = datetime.date.today().isoformat()
    rows = list(csv.DictReader(open(src, encoding="utf-8")))
    ok, bad = [], []
    for p in rows:
        name, q, url = p["name"], flat(p["quote"]), p["source"].strip()
        if p["fact"] != "sat":
            bad.append((p, "не SAT"))
            continue
        if not REQ.search(q) or not VERB.search(q) or JUNK.search(q):
            bad.append((p, "цитата не называет условия приёма"))
            continue
        try:
            page = text(get(url))
        except Exception as e:
            bad.append((p, f"страница не открылась: {e}"))
            time.sleep(1.2)
            continue
        if SAT.search(page):
            bad.append((p, "на странице упоминается SAT/ACT"))
        elif not on_page(q, page):
            bad.append((p, "цитаты больше нет на странице"))
        else:
            ok.append(p)
        time.sleep(1.2)
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEAD)
        w.writeheader()
        for p in ok:
            w.writerow({"name": p["name"], "country": p["country"], "fact": "sat",
                        "status": "not_required", "value": "", "note": NOTE,
                        "quote": p["quote"], "source": p["source"],
                        "checked": today, "tier": "page"})
    if review:
        with open(review, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=REVIEW_HEAD)
            w.writeheader()
            for p, why in bad:
                w.writerow({"name": p["name"], "fact": p["fact"],
                            "status": p["status"], "value": p["value"],
                            "quote": p["quote"], "source": p["source"],
                            "reason": why})
    print(f"verified {len(ok)} of {len(rows)}")
    for p, why in bad:
        print("REJECT", p["name"], "|", why)
    return 0


if __name__ == "__main__":
    sys.exit(main())
