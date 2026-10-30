#!/usr/bin/env python3
"""Find Chinese universities' English/international pages and quote their test rules.

A Chinese homepage is in Chinese and never names IELTS, so the crawler finds
nothing there. This script goes to the English site (en.HOST), the international
students office (iso.HOST) and follows links about international admission, then
keeps a page only when a test name sits next to admission wording.

Usage: python3 scripts/find_cn_pages.py IN.csv OUT.csv [MAXROWS]
"""

import csv
import datetime
import gzip
import os
import re
import sys
import time
import urllib.parse
import urllib.request

UA = "ivypath-check/1.0 (student project; 1 request/second)"
TESTS = [("ielts", r"IELTS"), ("toefl", r"TOEFL"), ("hsk", r"HSK")]
# MODE=sat looks for the opposite: a page that lists what admission needs and
# never mentions SAT/ACT. A Chinese university takes you on the school
# certificate plus HSK or an English test, so SAT is simply not part of it.
SAT = re.compile(r"\bSAT\b|\bACT\b")
ADM = re.compile(r"HSK\s*(?:level\s*)?[4-9]\b"
                 r"|high school (?:diploma|graduate|certificate)"
                 r"|senior high school|secondary school (?:diploma|certificate)", re.I)
VERB = re.compile(r"\b(?:must|should|shall|requires?|required|submit|provide|hold"
                  r"|obtain|have|pass)\b", re.I)
# A FAQ heading or a scholarship offer also names the entry route, but it
# does not state a requirement: skip those sentences.
JUNK = re.compile(r"\?|scholarship|FAQ", re.I)
SENT = re.compile(r"[^.!?]{30,320}[.!?]")
if os.environ.get("MODE") == "sat":
    TESTS = [("sat", r"\bSAT\b|\bACT\b")]
WORDS = re.compile(r"accept|requir|submit|submission|provide|take|demonstrat|welcome"
                   r"|proof|results?|one of the following|exams?:|score", re.I)
REJECT = re.compile(r"not accepted|not considered|do(?:es)? not (?:accept|require)"
                    r"|cannot be used|will not be", re.I)
GOOD = re.compile(r"international|admission|apply|enroll|entry|requirement|study"
                  r"|undergraduate|program", re.I)
# The Chinese homepage has no admissions section, but it does link to the
# English version of the site, and that English site links to the international
# students office. Those two hops are the only way in.
LANG = re.compile(r"english|intl|\biso\b|en\.|英文|\bEn\b", re.I)
HREF = re.compile(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.I | re.S)
# A score written right after the test name is the published minimum:
# "IELTS 6.0", "TOEFL iBT 80". A page that lists a master's and a bachelor's
# programme names two numbers, so a number seen next to "postgraduate" and
# nowhere near "undergraduate" is not the bachelor minimum.
SCORE = {"ielts": re.compile(r"IELTS[^0-9]{0,40}([4-9](?:\.\d)?)", re.I),
         "toefl": re.compile(r"TOEFL(?:\s*iBT)?[^0-9]{0,40}((?:4[5-9]|[5-9]\d|1[01]\d|120))\b", re.I)}
POST = re.compile(r"postgraduate|master'?s?|doctoral|ph\.?d", re.I)
UNDER = re.compile(r"undergraduate|bachelor", re.I)
NOTE_VALUE = {"ielts": "минимум по официальной странице приёма",
              "toefl": "минимум по официальной странице приёма"}
NOTE = {"ielts": "IELTS принимается; минимальный балл не опубликован",
        "toefl": "TOEFL принимается; минимальный балл не опубликован",
        "hsk": "HSK принимается; минимальный балл не опубликован",
        "sat": "SAT не требуется: приём по аттестату и HSK/вступительным экзаменам вуза"}
HEAD = ["name", "country", "fact", "status", "value", "note", "quote",
        "source", "checked", "tier"]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=8) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
    enc = r.headers.get_content_charset() or "utf-8"
    try:
        return raw.decode(enc, "replace")
    except LookupError:
        return raw.decode("utf-8", "replace")


def text(html):
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def domain(url):
    host = urllib.parse.urlparse(url).netloc.lower()
    parts = host.lstrip("www.").split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in ("edu.cn", "com.cn", "org.cn"):
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def seeds(home):
    p = urllib.parse.urlparse(home)
    host = p.netloc
    base = domain(home)
    out = [home]
    # Chinese hosts often answer on https but not http (or the other way
    # round), and an unknown subdomain fails at DNS, which is cheap.
    for sub in ("en", "iso", "english", "international", "admission", "study", "lxs"):
        for sch in ("http", "https"):
            out.append(f"{sch}://{sub}.{base}/")
    for path in ("english/", "en/", "en/index.htm", "english/index.htm"):
        out.append(f"{p.scheme}://{host}/{path}")
    seen, uniq = set(), []
    for u in out:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq


def links(html, base):
    base_dom = domain(base)
    out, seen = [], set()
    for href, label in HREF.findall(html):
        href = href.strip()
        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        url = urllib.parse.urljoin(base, href).split("#")[0]
        if not url.startswith("http") or domain(url) != base_dom:
            continue
        if url in seen:
            continue
        label = re.sub(r"<[^>]+>", " ", label)
        if GOOD.search(href) or GOOD.search(label) or LANG.search(href) or LANG.search(label):
            seen.add(url)
            out.append(url)
    out.sort(key=lambda u: 0 if re.search(r"admission|international|apply", u, re.I)
             else 1 if re.search(r"english|intl|\biso\b|en\.", u, re.I) else 2)
    return out[:14]


def prio(url):
    if re.search(r"admission|apply|requirement|program|undergraduate|international-stud|iso",
                 url, re.I):
        return 0
    if re.search(r"intl|english|international|en\.", url, re.I):
        return 1
    return 2


def pick_sat(t):
    """Return one full sentence that names the entry route, or None.

    A menu lists "HSK Exam" and "Application" as bare labels, so the route
    word alone proves nothing. The sentence must also say what the applicant
    has to do (a verb), and the page must never mention SAT/ACT.
    """
    if SAT.search(t):
        return None
    for m in SENT.finditer(t):
        s = m.group(0).strip()
        if not ADM.search(s) or not VERB.search(s) or REJECT.search(s):
            continue
        if JUNK.search(s):
            continue
        return s
    return None


def pick_score(t, fact):
    """Return (value, quote) if the page names a minimum score."""
    m = SCORE[fact].search(t)
    if not m:
        return None
    window = t[max(0, m.start() - 160):m.end() + 160]
    if POST.search(window) and not UNDER.search(window):
        return None
    return m.group(1), t[max(0, m.start() - 90):m.end() + 150].strip()


def find_quote(t, test):
    for m in re.finditer(test, t, re.I):
        window = t[max(0, m.start() - 120):m.end() + 120]
        if not WORDS.search(window):
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
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10 ** 6
    today = datetime.date.today().isoformat()
    rows = list(csv.DictReader(open(src, encoding="utf-8")))[:limit]
    done = set()
    try:
        for r in csv.DictReader(open(out, encoding="utf-8")):
            done.add((r["name"], r["fact"]))
    except FileNotFoundError:
        pass
    # Only an existing OUT means "append": SEED does not make the file exist,
    # and a new file must still get its header.
    new = not done
    # SEED lists (name,fact) pairs the site already answers, so a resumed run
    # does not crawl a university again just to propose what is already there.
    if os.environ.get("SEED"):
        for r in csv.DictReader(open(os.environ["SEED"], encoding="utf-8")):
            done.add((r["name"], r["fact"]))
    with open(out, "a" if not new else "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEAD)
        if new:
            w.writeheader()
        for row in rows:
            name, home = row["name"], row["homepage"].strip()
            if all((name, fact) in done for fact, _ in TESTS):
                continue
            quotes, seen_urls = {}, set()
            # Breadth-first, two hops: Chinese homepage -> English site
            # -> international students office / admission requirements.
            queue = [(home, 0)]
            requests, found_links = 0, 0
            while queue and requests < 36 and len(quotes) < len(TESTS):
                queue.sort(key=lambda x: (x[1], prio(x[0])))
                url, depth = queue.pop(0)
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                try:
                    html = get(url)
                except Exception as e:
                    print("  skip", url, e, file=sys.stderr)
                    time.sleep(1.2)
                    continue
                requests += 1
                t = text(html)
                # An English page still has a "简体中文" language switch in its
                # menu. Only a page that is mostly Chinese is the Chinese site.
                if len(re.findall(r"[一-鿿]", t[:4000])) < 200:
                    for fact, test in TESTS:
                        if fact in quotes or (name, fact) in done:
                            continue
                        val = ""
                        if fact == "sat":
                            q = pick_sat(t)
                        else:
                            got = pick_score(t, fact) if fact in SCORE else None
                            if got:
                                val, q = got
                            else:
                                q = find_quote(t, test)
                        if q:
                            quotes[fact] = (url, q, val)
                if depth < 2:
                    got = links(html, url)
                    found_links += len(got)
                    for u in got:
                        queue.append((u, depth + 1))
                if depth == 0:
                    # Guessed subdomains answer even when the homepage hides
                    # its English link behind a script, so always try them.
                    queue.extend((u, 2) for u in seeds(home)[1:])
                time.sleep(1.2)
            for fact, (url, q, val) in quotes.items():
                status = ("not_required" if fact == "sat"
                          else "value" if val else "accepted")
                note = NOTE_VALUE[fact] if val else NOTE[fact]
                w.writerow({"name": name, "country": row["country"], "fact": fact,
                            "status": status, "value": val, "note": note,
                            "quote": q, "source": url, "checked": today, "tier": "page"})
                f.flush()
            got = ",".join(quotes) or "0 facts"
            print(("OK " if quotes else "NONE ") + name + " " + got, file=sys.stderr)
            time.sleep(1.2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
