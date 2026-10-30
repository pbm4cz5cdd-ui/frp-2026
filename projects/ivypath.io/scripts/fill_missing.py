#!/usr/bin/env python3
"""Read official pages for the universities in data/missing.csv and propose
IELTS/TOEFL/SAT facts. Keeps only answers whose quote is found on the page.
Resumes: names in data/fill-missing-done.txt are skipped.

Usage: python3 scripts/fill_missing.py [limit]
Output: data/proposals-missing.csv
"""

import csv
import glob
import json
import os
import re
import sys
import time
from datetime import date
from html.parser import HTMLParser
from types import SimpleNamespace
from urllib.parse import urljoin, urlparse

import requests

INP = os.environ.get("INP", "data/missing.csv")
SHARD = int(os.environ.get("SHARD", "0"))
NSHARDS = int(os.environ.get("NSHARDS", "1"))
SUFFIX = f"-{SHARD}" if NSHARDS > 1 else ""
MAXPAGES = int(os.environ.get("MAXPAGES", "9"))
MAXASKS = int(os.environ.get("MAXASKS", "5"))
MAXROUNDS = int(os.environ.get("MAXROUNDS", "2"))
OUT = os.environ.get("OUT") or f"data/proposals-missing{SUFFIX}.csv"
DONE = os.environ.get("DONE") or f"data/fill-missing-done{SUFFIX}.txt"
TODAY = date.today().isoformat()
UA = "ivypath-check/1.0 (student project; 1 request/second)"
API = "http://127.0.0.1:19040/v1/chat/completions"
MODEL = "dsv41"
DELAY = 1.1
FACTS = tuple((os.environ.get("FACTS") or "ielts,toefl,sat").split(","))
PROMPT_KEYS = ("ielts", "toefl", "sat", "hsk", "ap", "ib")
SKIP_EXT = (".pdf", ".jpg", ".png", ".zip", ".doc", ".docx", ".xls", ".xlsx",
            ".ico", ".gif", ".svg", ".webp", ".css", ".js", ".mp4", ".mov")


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.out = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "svg"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.href = None
        self.txt = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.txt = []

    def handle_data(self, data):
        if self.href is not None:
            self.txt.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.href:
            self.links.append((self.href, " ".join(self.txt)))
            self.href = None


SPACES = re.compile("[\u00a0\u2000-\u200a\u202f\u205f\u200b\u200c\u200d]")


def clean(html):
    p = Text()
    p.feed(html)
    return re.sub(r"\s+", " ", SPACES.sub(" ", " ".join(p.out))).strip()


def norm(s):
    return re.sub(r"\s+", " ", SPACES.sub(" ", s)).strip().lower()


GRAD = re.compile(r"\b(graduate|postgraduate|masters|master's|doctoral|PhD|MBA)\b", re.I)
UNDER = re.compile(r"\b(undergraduate|undergrad|first-year|freshman|bachelor)\b", re.I)


def undergrad_quote(q):
    """A page about graduate admission gives graduate scores: keep those out."""
    return not GRAD.search(q) or bool(UNDER.search(q))


def sentences(text):
    return re.split(r"(?<=[.!?])\s+", text)


def relevant(text):
    parts = sentences(text)
    keep = []
    for i, s in enumerate(parts):
        if re.search(r"IELTS|TOEFL|SAT\b|English language|language proficiency|English proficiency"
                     r"|HSK|Advanced Placement|\bAP\b|International Baccalaureate|\bIB\b"
                     # French-language Canadian pages name the requirement this way
                     r"|anglais|niveau d.anglais|test d.anglais|compétence linguistique", s, re.I):
            keep.extend(parts[max(0, i - 1):i + 2])
    out = " ".join(dict.fromkeys(keep))
    return out[:16000]


def jina_slot():
    """Keep all shards to at most one reader request per 1.2 s together."""
    import fcntl
    try:
        fh = open("/tmp/ivypath-jina.lock", "a+")
    except OSError:
        time.sleep(1.2)
        return
    try:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            last = float(open("/tmp/ivypath-jina.last").read().strip() or 0)
        except (OSError, ValueError):
            last = 0.0
        wait = 1.2 - (time.time() - last)
        if wait > 0:
            time.sleep(wait)
        with open("/tmp/ivypath-jina.last", "w") as out:
            out.write(str(time.time()))
    finally:
        fcntl.flock(fh, fcntl.LOCK_UN)
        fh.close()


def jina(url):
    """Render a JavaScript-only page through the Jina reader: the web-search
    skill's way to read pages that need JavaScript. Markdown links become
    <a href> so the crawl can follow them."""
    jina_slot()
    try:
        r = requests.get("https://r.jina.ai/" + url, headers={"User-Agent": UA}, timeout=60)
    except Exception as e:
        print(f"  jina {type(e).__name__}"[:120], flush=True)
        return None
    if r.status_code != 200 or "Markdown Content:" not in r.text:
        return None
    md = r.text.split("Markdown Content:", 1)[1]
    return re.sub(r"\[([^\]]*)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', md)


def get(url):
    resp = None
    try:
        resp = requests.get(url, headers={"User-Agent": UA}, timeout=25, allow_redirects=True)
    except requests.exceptions.SSLError:
        # Some universities serve a certificate that does not cover the bare
        # domain (https://virginia.edu); the www host usually has a valid one.
        host = urlparse(url).hostname or ""
        if not host or host.startswith("www."):
            pass
        else:
            time.sleep(DELAY)
            try:
                resp = requests.get(url.replace(host, "www." + host, 1),
                                    headers={"User-Agent": UA}, timeout=25, allow_redirects=True)
            except requests.exceptions.RequestException:
                resp = None
    except requests.exceptions.RequestException:
        resp = None
    # Bot protection answers 403 and some sites time out; the reader that the
    # web-search skill uses still returns the page text, so read it there.
    if resp is None or resp.status_code >= 400 or len(clean(resp.text)) < 400:
        rendered = jina(url)
        if rendered and (resp is None or len(clean(rendered)) > len(clean(resp.text))):
            return SimpleNamespace(status_code=200, url=url, text=rendered,
                                   headers={"content-type": "text/html"})
    if resp is not None and resp.status_code == 200 and len(clean(resp.text)) < 400:
        rendered = jina(resp.url)
        if rendered and len(clean(rendered)) > len(clean(resp.text)):
            resp._content = rendered.encode("utf-8")
            resp.headers["content-type"] = "text/html"
    # requests falls back to ISO-8859-1 when a page names no charset, which turns
    # UTF-8 Chinese and French text into "â€" gibberish. Use UTF-8 when it decodes.
    if resp is not None and resp.status_code == 200 \
            and (resp.encoding or "").lower() in ("", "ascii", "iso-8859-1"):
        try:
            resp._content.decode("utf-8")
        except UnicodeDecodeError:
            pass
        else:
            resp.encoding = "utf-8"
    return resp


def base_domain(host):
    parts = re.sub(r"^www\.", "", host).split(".")
    if len(parts) >= 3 and parts[-2] in ("ac", "co", "com", "edu", "gov", "net", "org", "sch"):
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def same_site(a, b):
    ha = urlparse(a).hostname or ""
    hb = urlparse(b).hostname or ""
    return ha == hb or base_domain(ha) == base_domain(hb)


BAD = ("graduate", "masters", "doctoral", "law-school", "law.", "/law", "medicine",
       "medical", "dental", "business", "mba", "continuing", "online", "athletic",
       "alumni", "donate", "visit", "tuition", "financial-aid", "scholarship",
       "paying", "login", "portal", "news", "events", "contact", "request-info",
       "request-information", "travel", "directions", "summer", "intensive",
       "see-campus", "meet-your", "campus-tour")

# Pages that quote a number but not the undergraduate one: ESL placement,
# pathway/foundation years, pre-sessional courses. Word boundaries keep
# "Wesleyan" from matching "esl".
BAD_URL_RE = re.compile(
    r"(?:^|[/_.-])(?:esl|aep|els|placement|pathway|foundation|pre-sessional|"
    r"presessional|english-language-centre|language-centre|language-center|"
    r"study-abroad|studyabroad|summer-session)(?:[/_.-]|$)", re.I)


# Many universities keep admission on its own subdomain: the root site's own
# admission pages often stop at "contact us", while admission.<host> links on
# to the English-proficiency requirements.
ADMISSION_HOSTS = ("admission", "admissions", "apply", "enroll", "enrollment",
                   "enrol", "undergrad", "undergraduate", "futurestudents",
                   "future-students")


def page_bonus(url):
    """Points for the pages that actually carry the test requirements.

    "Apply to Tulane" beats "Degrees & Requirements" and "About Tulane"; the
    about/campus/visit pages are dead ends for us.
    """
    parsed = urlparse(url)
    n = 0
    if (parsed.hostname or "").split(".")[0] in ADMISSION_HOSTS:
        n += 3
    path = (parsed.path or "").lower()
    for w, p in [("english", 3), ("apply", 4), ("proficiency", 3),
                 ("requirement", 2), ("international", 1), ("testing", 1)]:
        if w in path:
            n += p
    for w, p in [("about", 3), ("history", 3), ("campus", 3), ("visit", 3)]:
        if w in path:
            n -= p
    return n


def admission_seeds(start):
    """Guess the admission site from the bare domain.

    Many university roots are JavaScript marketing pages that ship no <a> links
    at all (https://uga.edu returned none), so the admissions subdomain is the
    real doorway to the requirement pages.
    """
    host = urlparse(start).hostname or ""
    if (host.split(".")[0] in ADMISSION_HOSTS
            or any(w in (urlparse(start).path or "").lower()
                   for w in ("admission", "apply", "international"))):
        return []
    bd = base_domain(host)
    if not bd:
        return []
    return [f"https://admission.{bd}/", f"https://admissions.{bd}/",
            f"https://www.{bd}/admission", f"https://www.{bd}/admissions",
            f"https://www.{bd}/admission-aid", f"https://www.{bd}/admissions-aid"]


def score_link(href, txt, base):
    s = (href + " " + txt).lower().replace("undergraduate", "").replace("undergrad", "")
    if any(href.lower().endswith(e) for e in SKIP_EXT):
        return -1
    if href.startswith(("mailto:", "javascript:", "tel:", "#")):
        return -1
    if not same_site(urljoin(base, href), base):
        return -1
    if any(b in s for b in BAD):
        return -1
    n = 0
    for w, p in [("english", 5), ("proficiency", 5), ("language", 4),
                 ("ielts", 4), ("toefl", 4),
                 ("standardized", 4), ("testing", 3), ("international", 2),
                 ("requirement", 2), ("admission", 2), ("undergraduate", 1),
                 ("apply", 1),
                 # French-language Canadian sites
                 ("anglais", 5), ("langue", 4), ("exigence", 2)]:
        if w in s:
            n += p
    return n + page_bonus(urljoin(base, href))


def link_candidates(base_html, base_url, threshold, limit):
    l = Links()
    l.feed(base_html)
    seen, out = set(), []
    for href, txt in l.links:
        u = urljoin(base_url, href).split("#")[0]
        if u in seen:
            continue
        seen.add(u)
        sc = score_link(href, txt, base_url)
        if sc >= threshold:
            out.append((sc, u))
    out.sort(reverse=True)
    picks = [u for _, u in out[:limit]]
    # The admission site's own front page is the doorway to its requirement
    # pages, even when the homepage only links a few of its deep pages.
    for href, _txt in l.links:
        host = (urlparse(urljoin(base_url, href)).hostname or "").lower()
        if host.split(".")[0] in ADMISSION_HOSTS:
            root = f"https://{host}/"
            if root not in picks:
                picks.insert(0, root)
    return picks


def ask(text, url):
    prompt = (
        "You read one university web page and extract English-test requirements for undergraduate international applicants. "
        "Use ONLY the text below. Never use outside knowledge. Return JSON only, no markdown.\n"
        'Schema: {"ielts":{"status":"value|accepted|not_required|varies|not_stated","value":null,"note":"","quote":""},'
        '"toefl":{"status":"value|accepted|not_required|varies|not_stated","value":null,"note":"","quote":""},'
        '"sat":{"status":"value|not_required|varies|not_stated","value":null,"note":"","quote":""}}\n'
        "Rules: status=value if the page gives one minimum overall score, or a table/range by course: "
        "then use the LOWEST published overall score and note='минимум; зависит от программы, до X'. "
        "If it gives a minimum plus higher scores for some programmes, use value and say that in note. "
        "Use status=varies only if the page says requirements vary and gives no number. "
        "status=not_required only if the page says the test is not required. "
        "Use status=accepted (IELTS/TOEFL/HSK only) if the page lists the test as accepted or as required "
        "from applicants whose native language is not English, but publishes no minimum score; "
        "put note='IELTS принимается; минимальный балл не опубликован' (TOEFL or HSK instead of IELTS). "
        "If SAT is optional (test-optional, not test-free), still look for a published middle 50% range or average of admitted students: "
        "put the upper bound (or average) in sat.note as 'SAT не требуется; ориентир ~N (75-й перцентиль)' and quote that range. "
        "If no range is on the page, use 'SAT не требуется; ориентир не опубликован'. If SAT is not used, use 'SAT не используется'. "
        "For HSK/AP/IB: if the page states Chinese HSK requirements for international applicants, put it in an extra key "
        '"hsk":{"status":"value|not_required|varies|not_stated","value":null,"note":"","quote":""}; '
        "if it states AP credit/Advanced Placement, use the same shape under key \"ap\". "
        "If it states International Baccalaureate requirements (points total, or Higher Level subjects), use key "
        '"ib" with that same shape; for IB use the minimum total points when one is given. '
        "status=not_stated if the page does not state it. "
        "note must be Russian, max 100 chars. quote must be copied word for word from the text (one sentence).\n"
        + (os.environ.get("EXTRA", "") + "\n" if os.environ.get("EXTRA") else "")
        + f"URL: {url}\nTEXT:\n{text}")
    body = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
            "temperature": 0, "max_tokens": 900}
    r = requests.post(API, json=body, timeout=120)
    r.raise_for_status()
    out = r.json()["choices"][0]["message"]["content"]
    m = re.search(r"\{.*\}", out, re.S)
    if not m:
        raise ValueError("no JSON: " + out[:200])
    return json.loads(m.group(0))


def load_done():
    if os.environ.get("FORCE"):
        return set()
    if os.environ.get("ONLY_DONE"):
        if not os.path.exists(DONE):
            return set()
        with open(DONE, encoding="utf-8") as fh:
            return {x.strip() for x in fh if x.strip()}
    names = set()
    for path in glob.glob("data/fill-missing-done*.txt"):
        with open(path, encoding="utf-8") as fh:
            names.update(x.strip() for x in fh if x.strip())
    return names


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 999
    rows = list(csv.DictReader(open(INP, encoding="utf-8")))[:limit]
    rows = rows[SHARD::NSHARDS]
    done = load_done()
    fields = ["name", "country", "fact", "status", "value", "note", "quote", "source", "checked"]
    new_file = not os.path.exists(OUT) or os.path.getsize(OUT) == 0
    f = open(OUT, "a", encoding="utf-8", newline="")
    w = csv.DictWriter(f, fieldnames=fields)
    if new_file:
        w.writeheader()
        f.flush()
    df = open(DONE, "a", encoding="utf-8")
    total = len(rows)
    for i, u in enumerate(rows, 1):
        name = u["name"]
        if name in done:
            print(f"[{i}/{total}] skip {name}", flush=True)
            continue
        start = u["homepage"].strip()
        found = 0
        pages = []          # (url, html) in priority order
        seen = set()

        def fetch(url):
            if url in seen:
                return None
            seen.add(url)
            if BAD_URL_RE.search(url) or re.search(r"(?<!under)graduate", url.lower()):
                return None
            try:
                resp = get(url)
                time.sleep(DELAY)
                if not resp:
                    return None
                if resp.status_code == 200 and "html" in resp.headers.get("content-type", ""):
                    return resp.url, resp.text
                return None
            except Exception as e:
                print(f"  {name}: {url} {type(e).__name__}"[:200], flush=True)
                return None

        home = fetch(start)
        if home:
            pages.append(home)
            ads = link_candidates(home[1], home[0], 2, 4)
            # A JavaScript root page can hide every link: try the admission
            # subdomain before giving up on this university.
            if len(ads) < 2:
                extra = 0
                for su in admission_seeds(start):
                    if extra >= 2 or len(ads) >= 2:
                        break
                    s2 = fetch(su)
                    if not s2:
                        continue
                    more = link_candidates(s2[1], s2[0], 2, 4)
                    if more:
                        pages.append(s2)
                        ads.extend(more)
                        extra += 1
            for au in ads:
                a = fetch(au)
                if a:
                    pages.append(a)
                    deep = link_candidates(a[1], a[0], 4, 2) or link_candidates(a[1], a[0], 2, 2)
                    for eu in deep:
                        e = fetch(eu)
                        if e:
                            pages.append(e)
        else:
            print(f"[{i}/{total}] {name}: homepage failed", flush=True)

        best = {}
        rank = {"accepted": 0.5, "not_required": 1, "varies": 2, "value": 3}
        asked = set()
        tried = 0

        def scan():
            nonlocal tried
            for url, html in pages:
                if (url in asked or tried >= MAXASKS
                        or sum(1 for x in best if x in FACTS) >= len(FACTS)):
                    continue
                txt = clean(html)
                rel = relevant(txt)
                if not rel or not any(re.search(rf"{k}\b", rel, re.I)
                                      for k in ("IELTS", "TOEFL", "SAT", "HSK",
                                                "Advanced Placement", "IB")):
                    continue
                asked.add(url)
                tried += 1
                try:
                    ans = ask(rel, url)
                    time.sleep(0.3)
                    if os.environ.get("DEBUG"):
                        got = {k: (v or {}).get("status") for k, v in ans.items()}
                        print(f"  {name}: {url} rel={len(rel)} -> {got}"[:300], flush=True)
                    for fact in PROMPT_KEYS:
                        a = ans.get(fact) or {}
                        q = (a.get("quote") or "").strip()
                        if not q or not undergrad_quote(q) or norm(q)[:110] not in norm(txt):
                            if os.environ.get("DEBUG") and (a.get("status") in rank):
                                print(f"    {fact} quote rejected: {(q or '')[:90]}"[:200], flush=True)
                            continue
                        status = a.get("status")
                        if status not in rank:
                            continue
                        val = a.get("value")
                        if status == "value" and val in (None, ""):
                            continue
                        note = a.get("note", "")
                        old = best.get(fact)
                        better = old is None or rank[status] > rank[old["status"]]
                        if (status == "not_required" and "ориентир ~" in note
                                and old is not None and "ориентир ~" not in old["note"]):
                            better = True
                        if better:
                            best[fact] = {"name": name, "country": u["country"], "fact": fact,
                                          "status": status, "value": val, "note": note,
                                          "quote": q, "source": url, "checked": TODAY}
                except Exception as e:
                    print(f"[{i}/{total}] {name}: {url} {type(e).__name__} {e}"[:300], flush=True)

        def deep_candidates():
            out = []
            for pu, ph in reversed(pages):
                l = Links()
                l.feed(ph)
                for href, txt in l.links:
                    u2 = urljoin(pu, href).split("#")[0]
                    if u2 in seen or not same_site(u2, pu):
                        continue
                    if BAD_URL_RE.search(u2):
                        continue
                    s = (u2 + " " + txt).lower()
                    # "undergraduate" contains "graduate": do not drop it here
                    s_bad = s.replace("undergraduate", "").replace("undergrad", "")
                    if any(b in s_bad for b in BAD):
                        continue
                    sc = 0
                    for word, points in [("english", 5), ("language requirement", 5),
                                         ("proficiency", 5), ("ielts", 4), ("toefl", 4),
                                         ("standardized", 4),
                                         ("international", 3), ("requirement", 3),
                                         ("first-year", 2), ("freshman", 2), ("entry", 2),
                                         ("applying", 2), ("testing", 2), ("admission", 1),
                                         ("apply", 1)]:
                        if word in s:
                            sc += points
                    sc += page_bonus(u2)
                    # from an international hub, "how to apply" is the way in
                    need = 2 if "international" in pu.lower() else 3
                    if sc >= need:
                        out.append((sc, u2))
            out.sort(reverse=True)
            return list(dict.fromkeys(u for _, u in out))

        # Requirements are often three or four clicks down: international
        # students -> first-year applicants -> English proficiency.
        scan()
        rounds = 0
        while (pages and rounds < MAXROUNDS
               and sum(1 for x in best if x in FACTS) < len(FACTS)
               and len(pages) < MAXPAGES and tried < MAXASKS):
            rounds += 1
            new = 0
            for u2 in deep_candidates():
                if new >= 2 or len(pages) >= MAXPAGES:
                    break
                e = fetch(u2)
                if e:
                    pages.append(e)
                    new += 1
            if not new:
                break
            scan()
        if ("sat" in best and best["sat"]["status"] == "not_required"
                and "~" not in best["sat"]["note"]):
            prof = []
            for pu, ph in pages:
                l = Links()
                l.feed(ph)
                for href, txt in l.links:
                    u2 = urljoin(pu, href).split("#")[0]
                    if (same_site(u2, pu) and re.search(
                            r"profile|admitted|class-of|facts|statistic|common-data|dataset",
                            u2 + " " + txt, re.I)):
                        prof.append(u2)
            for link in prof[:1]:
                p = fetch(link)
                if not p:
                    continue
                ptxt = clean(p[1])
                prel = relevant(ptxt)
                if not prel or not re.search(r"SAT\b", prel, re.I):
                    continue
                try:
                    ans = ask(prel, p[0])
                    time.sleep(0.3)
                    a = ans.get("sat") or {}
                    q = (a.get("quote") or "").strip()
                    if not q or not undergrad_quote(q) or norm(q)[:110] not in norm(ptxt):
                        break
                    # The profile page usually gives a range, not "not required":
                    # take its upper bound as the target, keep SAT as optional.
                    scores = [int(x) for x in re.findall(r"\b(?:1[0-5]\d{2}|1600)\b", q)]
                    if a.get("status") not in ("value", "not_required", "varies") or not scores:
                        break
                    hi = max(scores)
                    tail = ("(75-й перцентиль)"
                            if re.search(r"\d{3,4}\s*[–—\-]\s*\d{3,4}", q) else "")
                    note = f"SAT не требуется; ориентир ~{hi} {tail}".strip()
                    best["sat"] = {"name": name, "country": u["country"], "fact": "sat",
                                   "status": "not_required", "value": hi,
                                   "note": note, "quote": q,
                                   "source": p[0], "checked": TODAY}
                    print(f"  {name}: SAT target from {p[0]}", flush=True)
                except Exception as e:
                    print(f"  {name}: profile {type(e).__name__}", flush=True)
                break

        for row in best.values():
            w.writerow(row)
        f.flush()
        found = len(best)
        if home:
            df.write(name + "\n")
            df.flush()
        print(f"[{i}/{total}] {name}: {found} facts", flush=True)
    f.close()
    df.close()


if __name__ == "__main__":
    main()
