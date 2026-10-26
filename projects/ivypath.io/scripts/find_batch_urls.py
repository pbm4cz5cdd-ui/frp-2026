#!/usr/bin/env python3
"""Find the best official admissions page for each row of a batch CSV
(default: data/us-batch1.csv; use --csv for another batch).
Writes admissions_url, http_status, final_url, checked and note. Resumes rows
that already have a final_url. One request per second."""

import csv
import os
import sys
import time
from datetime import date
from urllib.parse import urljoin, urlparse

from fill_requirements import Links, clean, get, same_site, SKIP_EXT

CSV = "data/us-batch1.csv"
TODAY = date.today().isoformat()
DELAY = 1.1
COLS = ["name", "country", "homepage", "admissions_url", "http_status",
        "final_url", "checked", "note"]


def page_score(href, text):
    s = (href + " " + text).lower()
    n = 0
    for word, points in [
            ("admission", 4), ("international", 3), ("apply", 2),
            ("undergraduate", 2), ("first-year", 2), ("freshman", 2),
            ("english", 4), ("language", 3), ("proficiency", 4),
            ("ielts", 4), ("toefl", 4), ("requirement", 2), ("testing", 1)]:
        if word in s:
            n += points
    s2 = s.replace("undergraduate", "").replace("undergrad", "")
    for word, points in [
            ("graduate", 6), ("transfer", 2), ("visit", 3), ("athletic", 4),
            ("alumni", 3), ("donate", 4), ("login", 5), ("portal", 4),
            ("news", 3), ("events", 3), ("summer", 2), ("online", 2),
            ("dentistry", 12), ("dental", 12), ("law-school", 10),
            ("medicine", 10), ("medical", 10), ("business", 8),
            ("performing", 10), ("continuing", 10), ("contact", 8),
            ("tuition", 8), ("financial-aid", 8), ("scholarship", 8),
            ("paying", 8), ("graduation", 8), ("faculty", 6),
            ("research", 5), ("student-life", 5), ("request-information", 12),
            ("travel", 12), ("request-info", 12), ("directions", 10)]:
        if word in s2:
            n -= points
    return n


def links_from(html, base):
    p = Links()
    p.feed(html)
    seen, out = set(), []
    bad_paths = ("/graduate", "/masters", "/doctoral", "/physical-therapy",
                 "/physician", "/law", "/medicine", "/dental", "/continuing",
                 "/eli", "/part-time", "/online", "/tuition", "/financial-aid",
                 "/scholarship", "/paying", "/request-information", "/travel")
    for href, txt in p.links:
        if not href or href.startswith(("mailto:", "javascript:", "tel:", "#")):
            continue
        if any(href.lower().endswith(e) for e in SKIP_EXT):
            continue
        if any(b in urlparse(href).path.lower() for b in bad_paths):
            continue
        u = urljoin(base, href).split("#")[0]
        if u in seen or not same_site(u, base):
            continue
        seen.add(u)
        score = page_score(href, txt)
        if score >= 2:
            out.append((score, u))
    out.sort(reverse=True)
    return [u for _, u in out[:4]]


def text_score(html):
    txt = clean(html).lower()
    n = 0
    if "ielts" in txt:
        n += 5
    if "toefl" in txt:
        n += 5
    if "english language" in txt or "english proficiency" in txt:
        n += 3
    if "admission" in txt:
        n += 2
    if "undergraduate" in txt:
        n += 1
    return n


def save(rows):
    tmp = CSV + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, CSV)


def main():
    global CSV
    if "--csv" in sys.argv:
        try:
            CSV = sys.argv[sys.argv.index("--csv") + 1]
        except IndexError:
            print("--csv needs a file path", file=sys.stderr)
            return 2
    force = "--force" in sys.argv
    with open(CSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for c in COLS:
            r.setdefault(c, "")
    total = len(rows)
    if "--summary" in sys.argv:
        ok = [r for r in rows if r["admissions_url"]]
        print(f"{len(ok)}/{total} have admissions_url")
        for r in rows:
            if not r["admissions_url"]:
                print("missing:", r["name"], "|", r["note"])
        return 0 if len(ok) == total else 1
    for i, r in enumerate(rows, 1):
        if r["final_url"] and r["checked"] and not force:
            print(f"[{i}/{total}] skip {r['name']}", flush=True)
            continue
        if force:
            r["admissions_url"] = ""
            r["http_status"] = ""
            r["final_url"] = ""
            r["checked"] = ""
            r["note"] = ""
        homepage = r["homepage"].strip()
        best = None
        try:
            try:
                resp = get(homepage)
            except Exception:
                host = urlparse(homepage).hostname or ""
                if host and not host.startswith("www."):
                    alt = homepage.replace(host, "www." + host, 1)
                    print(f"  retry {alt}", flush=True)
                    resp = get(alt)
                    homepage = alt
                else:
                    raise
            time.sleep(DELAY)
            r["http_status"] = str(resp.status_code)
            r["final_url"] = resp.url
            r["checked"] = TODAY
            if resp.status_code != 200:
                r["note"] = f"homepage {resp.status_code}"
                save(rows)
                print(f"[{i}/{total}] {r['name']}: homepage {resp.status_code}", flush=True)
                continue
            cands = links_from(resp.text, resp.url)
            if not cands:
                cands = [urljoin(resp.url, p) for p in ("/admission/", "/admissions/", "/admission")]
            best = None
            for url in cands[:3]:
                try:
                    cr = get(url)
                    time.sleep(DELAY)
                    if cr.status_code == 200 and "html" in cr.headers.get("content-type", ""):
                        sc = text_score(cr.text)
                        if best is None or sc > best[0]:
                            best = (sc, cr.url)
                        if sc >= 5:
                            break
                except Exception as e:
                    print(f"  candidate {url}: {type(e).__name__}", flush=True)
            if best:
                r["admissions_url"] = best[1]
                r["final_url"] = best[1]
                r["http_status"] = "200"
                r["note"] = "ok" if best[0] >= 5 else "candidate 200; check requirements"
                print(f"[{i}/{total}] {r['name']}: {best[1]}", flush=True)
            else:
                r["note"] = "no candidate opened"
                r["admissions_url"] = ""
                print(f"[{i}/{total}] {r['name']}: no candidate opened", flush=True)
        except Exception as e:
            r["note"] = f"{type(e).__name__}: {e}"[:160]
            r["checked"] = TODAY
            print(f"[{i}/{total}] {r['name']}: {type(e).__name__}", flush=True)
        save(rows)
    ok = sum(1 for r in rows if r["admissions_url"])
    print(f"done: {ok}/{total} have admissions_url", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
