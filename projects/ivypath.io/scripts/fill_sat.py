#!/usr/bin/env python3
"""Find the official SAT target (75th percentile of admitted students) for
universities whose SAT is optional and whose note has no ~N yet.
Reads data/universities.csv, writes data/proposals-sat.csv.

Usage: python3 scripts/fill_sat.py [limit]
Env: INP, SHARD, NSHARDS, OUT, DONE, MAXPAGES (8), MAXASKS (4), DELAY (1.1)
"""

import csv
import json
import os
import re
import sys
import time
from datetime import date
from io import BytesIO
from urllib.parse import quote_plus, unquote, urljoin, urlparse

import pypdf
import requests

from fill_missing import (BAD, DELAY, UA, API, MODEL, SPACES, Links, base_domain,
                          clean, get, norm, relevant, same_site)

INP = os.environ.get("INP", "data/universities.csv")
SHARD = int(os.environ.get("SHARD", "0"))
NSHARDS = int(os.environ.get("NSHARDS", "1"))
SUFFIX = f"-{SHARD}" if NSHARDS > 1 else ""
OUT = os.environ.get("OUT") or f"data/proposals-sat{SUFFIX}.csv"
DONE = os.environ.get("DONE") or f"data/fill-sat-done{SUFFIX}.txt"
MAXPAGES = int(os.environ.get("MAXPAGES", "10"))
MAXASKS = int(os.environ.get("MAXASKS", "4"))
TODAY = date.today().isoformat()
# NO_NOTE=1 also searches rows whose SAT is simply empty with no note yet
# (used for US universities where the site never mentioned SAT at all).
NO_NOTE = os.environ.get("NO_NOTE") == "1"
FIELDS = ["name", "country", "sat_target", "kind", "low", "quote", "source",
          "note_appendix", "checked"]


def sleep_official():
    """Polite pause between requests to the same servers."""
    time.sleep(DELAY)

PROFILE = re.compile(
    r"class[- ]?profile|admitted|class[- ]of|statistic|facts|common[- ]data|"
    r"cds\b|data[- ]set|student[- ]profile|entering[- ]class|"
    r"first[- ]year[- ]profile|admission[- ]stat|profile", re.I)
GUESS = ("/class-profile", "/class-profile/", "/admissions/class-profile",
         "/admissions/class-profile/", "/about/class-profile",
         "/about/class-profile/", "/admissions/undergraduate/class-profile",
         "/first-year-class-profile", "/admissions/apply/class-profile",
         "/about/facts", "/about/facts-figures", "/admissions/facts",
         "/admissions/undergraduate-admissions/class-profile",
         "/admissions/first-year/class-profile", "/first-year/class-profile",
         "/admissions/class-profile/facts", "/admissions/why-bu/class-profile/")
CDS = re.compile(r"common[- _]?data|data[- _]?set|\bcds\b", re.I)
STRONG = re.compile(r"class[- ]?profile|entering[- ]class|first[- ]year[- ]profile|"
                    r"student[- ]profile|admission[- ]stat|classof|facts",
                    re.I)
JUNK = ("/news", "/event", "/blog", "/story", "/athletic", "/article", "/20",
        "checklist", "admitted-student", "next-step", "majors-minors",
        "scholarship", "tuition", "financial-aid", "/visit", "contact",
        "apply/", "/apply", "international", "transfer", "graduate", "mba",
        "continuing", "online", "alumni", "donate")


def admissions_home(url):
    """The admissions section root, where the class profile is usually linked."""
    p = urlparse(url)
    host = p.hostname or ""
    out = []
    if host.startswith("admissions."):
        out.append(f"{p.scheme}://{host}/")
    for marker in ("/admissions/", "/admission/"):
        if marker in p.path:
            out.append(f"{p.scheme}://{host}{p.path.split(marker)[0]}{marker}")
    out.append(f"{p.scheme}://{host}/admissions/")
    return out


def ddg(query):
    """Search through Jina (direct DuckDuckGo is blocked from the class server)."""
    url = ("https://r.jina.ai/https://html.duckduckgo.com/html/?q="
           + quote_plus(query))
    r = requests.get(url, headers={"User-Agent": UA}, timeout=60)
    time.sleep(DELAY * 1.5)
    if r.status_code != 200:
        print(f"  search {r.status_code}", flush=True)
        return []
    out = []
    for x in re.findall(r"duckduckgo\.com/l/\?uddg=([^\)&\s\"']+)", r.text):
        try:
            out.append(unquote(x))
        except Exception:
            continue
    return list(dict.fromkeys(out))


def search_candidates(name, starts, limit=4):
    """Official Common Data Set / class profile pages found by a web search."""
    dom = ""
    for s in starts:
        dom = urlparse(s).hostname or ""
        if dom:
            break
    site = "." + base_domain(dom) if dom else ""
    queries = [f'{name} "common data set" SAT{(" site:" + site) if site else ""}',
               f'{name} SAT middle 50 admitted students{(" site:" + site) if site else ""}']
    hits = []
    for q in queries:
        for u in ddg(q):
            if not u.startswith("http"):
                continue
            if site and not same_site(u, "https://" + site.strip(".")):
                continue
            if any(b in u.lower() for b in ("/news", "/event", "/blog", "/story")):
                continue
            hits.append(u)
        if len(hits) >= limit:
            break
    pdf = [u for u in hits if u.lower().split("?")[0].endswith(".pdf")]
    pdf = [u for u in pdf if not stale(u)]
    other = [u for u in hits if u not in pdf]
    pdf.sort(key=lambda u: (0 if CDS.search(u) else 1, -year_of(u)))
    other.sort(key=lambda u: 0 if CDS.search(u) else (1 if STRONG.search(u) else 2))
    return list(dict.fromkeys(pdf + other))[:limit]


def year_of(url, html=""):
    years = [int(x) for x in re.findall(r"(20[12]\d)", url + " " + html)]
    return max(years) if years else 0


def stale(url, html=""):
    """A class profile older than a few years is not a fair target."""
    y = year_of(url, html)
    return bool(y and y < date.today().year - 4)


def pdf_links(html, base, limit=6):
    """PDF links on a CDS listing page (the page itself usually has no numbers)."""
    l = Links()
    l.feed(html)
    out = []
    for href, txt in l.links:
        u = urljoin(base, href).split("#")[0]
        if not same_site(u, base) or stale(u, txt):
            continue
        s = (u + " " + txt).lower()
        if not re.search(r"\.pdf|\.ashx|viewcontent\.cgi|download|/files/|assets", s):
            continue
        if not (CDS.search(s) or re.search(r"\b20[12]\d\b", s)):
            continue
        out.append(u)
    out.sort(key=lambda u: (0 if CDS.search(u) else 1, -year_of(u)))
    return list(dict.fromkeys(out))[:limit]


def sitemap_candidates(base, limit=10):
    """Cheap sitemap walk: finds class-profile pages whose URL is not linked."""
    p = urlparse(base)
    origin = f"{p.scheme}://{p.netloc}"
    seen, locs = set(), []
    for path in ("/sitemap.xml", "/sitemap_index.xml", "/sitemap-index.xml"):
        try:
            r = get(origin + path)
            time.sleep(DELAY)
            if r.status_code != 200 or "xml" not in r.headers.get("content-type", ""):
                continue
        except Exception:
            continue
        found = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r.text[:600000])
        if not found:
            continue
        children = [u for u in found if u.lower().endswith(".xml")]
        locs = [u for u in found if not u.lower().endswith(".xml")]
        for child in children[:15]:
            if not same_site(child, origin):
                continue
            try:
                cr = get(child)
                time.sleep(DELAY)
                if cr.status_code == 200:
                    locs.extend(re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", cr.text[:600000]))
            except Exception:
                continue
            if len(locs) > 4000:
                break
        break
    scored = []
    for u in locs:
        if u in seen or not same_site(u, origin):
            continue
        seen.add(u)
        s = u.lower()
        if any(b in s for b in JUNK):
            continue
        if CDS.search(s):
            scored.append((10, u))
        elif STRONG.search(s):
            scored.append((8, u))
        elif PROFILE.search(s):
            scored.append((4, u))
    scored.sort(key=lambda x: -x[0])
    return [u for _, u in scored[:limit]]


def optional_row(r):
    if r["sat"]:
        return False
    note = r["sat_note"] or ""
    if "~" in note:
        return False
    if NO_NOTE and not note.strip():
        return True
    return bool(re.search(r"не треб|не обязат|optional|не обязателен", note, re.I))


def start_urls(r):
    out = []
    for k in ("sat_source", "admissions_url", "homepage"):
        v = (r.get(k) or "").strip()
        if v.startswith("http") and v not in out:
            out.append(v)
    return out


def origin(url):
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def profile_links(html, base, limit=8):
    l = Links()
    l.feed(html)
    scored, seen = [], set()
    for href, txt in l.links:
        u = urljoin(base, href).split("#")[0]
        if u in seen or not u.startswith("http"):
            continue
        seen.add(u)
        s = (u + " " + txt).lower()
        if not same_site(u, base):
            continue
        # "undergraduate" contains "graduate": do not throw those pages away
        path_l = u.lower().replace("undergraduate", "").replace("undergrad", "")
        if any(b in path_l for b in JUNK):
            continue
        is_pdf = urlparse(u).path.lower().endswith(".pdf")
        if is_pdf:
            if re.search(r"common[- _]?data|cds|data[- _]?set", s):
                scored.append((5, u))
            continue
        if any(b in s for b in ("news", "event", "blog", "story", "athletic")):
            continue
        if PROFILE.search(s):
            scored.append((3, u))
    scored.sort(key=lambda x: -x[0])
    return [u for _, u in scored[:limit]]


def pdf_text(data, limit=14000):
    try:
        rd = pypdf.PdfReader(BytesIO(data))
    except Exception as e:
        print(f"  pdf read {type(e).__name__}", flush=True)
        return ""
    out = []
    try:
        pages = list(rd.pages[:40])
    except Exception as e:  # encrypted PDFs need a package we do not install
        print(f"  pdf pages {type(e).__name__}", flush=True)
        return ""
    for pg in pages:
        try:
            t = pg.extract_text() or ""
        except Exception:
            continue
        if re.search(r"SAT|Evidence.Based Reading", t, re.I):
            out.append(t)
        if sum(len(x) for x in out) > limit:
            break
    return re.sub(r"\s+", " ", SPACES.sub(" ", " ".join(out)))[:limit]


def sat_text(text):
    # keep paragraphs around SAT mentions (works for HTML text and CDS PDFs)
    parts = re.split(r"(?<=[.!?])\s+|\n", text)
    keep = []
    for i, s in enumerate(parts):
        if re.search(r"SAT|middle 50|75th|percentile", s, re.I):
            keep.extend(parts[max(0, i - 1):i + 3])
    out = " ".join(dict.fromkeys(keep))
    return out[:14000]


def ask(text, url):
    prompt = (
        "You read one university web page (or Common Data Set table) and find the SAT scores "
        "of admitted first-year students. Use ONLY the text below. Never use outside knowledge. "
        "Return JSON only, no markdown.\n"
        'Schema: {"status":"range|average|sections|none","low":null,"high":null,'
        '"erw_low":null,"erw_high":null,"math_low":null,"math_high":null,"quote":""}\n'
        "status=range if the page gives the middle 50% (25th-75th percentile) of the composite/total SAT "
        "(e.g. 1400-1550, or 'middle 50%: 1400-1550'); high=the 75th percentile, low=the 25th. "
        "status=average if it gives only an average/mean total SAT; put it in high. "
        "status=sections if it gives only section percentiles (SAT Evidence-Based Reading and Writing "
        "and/or SAT Math) and no total: fill erw_low/erw_high/math_low/math_high with those numbers. "
        "status=none if the page says nothing usable. "
        "quote must be copied word for word from the text (one sentence or table row) and must contain the numbers.\n"
        f"URL: {url}\nTEXT:\n{text}")
    body = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
            "temperature": 0, "max_tokens": 400}
    r = requests.post(API, json=body, timeout=120)
    r.raise_for_status()
    out = r.json()["choices"][0]["message"]["content"]
    m = re.search(r"\{.*\}", out, re.S)
    if not m:
        raise ValueError("no JSON: " + out[:200])
    return json.loads(m.group(0))


def number(v):
    try:
        n = int(re.sub(r"[^\d]", "", str(v)))
    except ValueError:
        return None
    return n


def pick(ans, txt):
    """Return (target, kind, low, note_appendix) or None."""
    status = ans.get("status")
    q = (ans.get("quote") or "").strip()
    if not q or norm(q)[:110] not in norm(txt):
        return None
    # pre-2016 CDS scores include a Writing section (2400 scale): not comparable
    if re.search(r"SAT\s+Writing", q, re.I):
        return None
    if status == "range":
        hi, lo = number(ans.get("high")), number(ans.get("low"))
        if hi and 800 <= hi <= 1600:
            lo = lo if lo and 400 <= lo <= hi else None
            return hi, "range", lo, f"ориентир ~{hi} (75-й перцентиль принятых)"
    elif status == "average":
        hi = number(ans.get("high"))
        if hi and 800 <= hi <= 1600:
            return hi, "average", None, f"ориентир ~{hi} (средний балл принятых)"
    elif status == "sections":
        eh, mh = number(ans.get("erw_high")), number(ans.get("math_high"))
        el, ml = number(ans.get("erw_low")), number(ans.get("math_low"))
        if eh and mh and 200 <= eh <= 800 and 200 <= mh <= 800:
            hi = eh + mh
            lo = el + ml if el and ml and 400 <= el <= eh and 200 <= ml <= mh else None
            return (hi, "sections", lo,
                    f"ориентир ~{hi} (сумма 75-х перцентилей ERW {eh} + Math {mh})")
    return None


def load_done():
    if os.environ.get("FORCE"):
        return set()
    names = set()
    for path in __import__("glob").glob("data/fill-sat-done*.txt"):
        with open(path, encoding="utf-8") as fh:
            names.update(x.strip() for x in fh if x.strip())
    return names


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 9999
    rows = [r for r in csv.DictReader(open(INP, encoding="utf-8")) if optional_row(r)]
    rows = rows[SHARD::NSHARDS][:limit]
    done = load_done()
    new_file = not os.path.exists(OUT) or os.path.getsize(OUT) == 0
    f = open(OUT, "a", encoding="utf-8", newline="")
    w = csv.DictWriter(f, fieldnames=FIELDS)
    if new_file:
        w.writeheader()
        f.flush()
    df = open(DONE, "a", encoding="utf-8")
    total = len(rows)
    for i, r in enumerate(rows, 1):
        name = r["name"]
        if name in done:
            print(f"[{i}/{total}] skip {name}", flush=True)
            continue
        starts = start_urls(r)
        if not starts:
            print(f"[{i}/{total}] {name}: no url", flush=True)
            continue
        seen, pages = set(), []

        def fetch(url):
            if url in seen:
                return None
            seen.add(url)
            resp = None
            for attempt in (1, 2):
                try:
                    resp = get(url)
                    break
                except requests.exceptions.SSLError:
                    # some "media." hosts have a broken certificate chain;
                    # the same file is served by the main official host
                    p = urlparse(url)
                    h = p.hostname or ""
                    # "media." may sit inside the host: bpir.media.uconn.edu
                    if ".media." in h and attempt == 1:
                        url = url.replace(h, h.replace(".media.", ".", 1), 1)
                        seen.add(url)
                        sleep_official()
                        continue
                    print(f"  {name}: {url} SSLError"[:200], flush=True)
                    return None
                except requests.exceptions.RequestException as e:
                    if attempt == 2:
                        print(f"  {name}: {url} {type(e).__name__}"[:200], flush=True)
                        return None
                    sleep_official()
            if resp is None:
                return None
            sleep_official()
            if resp.status_code != 200:
                return None
            ct = resp.headers.get("content-type", "")
            if "html" in ct:
                return resp.url, resp.text, None
            if "pdf" in ct or urlparse(url).path.lower().endswith(".pdf"):
                return resp.url, None, resp.content
            return None

        asked, got = 0, 0

        def try_candidates(urls, max_asks):
            nonlocal asked, got
            for u in urls:
                if got or asked >= max_asks:
                    break
                p = fetch(u)
                if not p:
                    continue
                _, html, pdf = p
                txt = sat_text(clean(html)) if html else sat_text(pdf_text(pdf))
                if not txt or not re.search(r"SAT|percentile", txt, re.I):
                    continue
                asked += 1
                try:
                    ans = ask(txt, p[0])
                    time.sleep(0.3)
                except Exception as e:
                    print(f"  {name}: {u} {type(e).__name__} {e}"[:240], flush=True)
                    continue
                pickd = pick(ans, txt)
                if not pickd:
                    continue
                hi, kind, lo, appendix = pickd
                w.writerow({"name": name, "country": r["country"], "sat_target": hi,
                            "kind": kind, "low": lo or "", "quote": ans.get("quote", "").strip(),
                            "source": p[0], "note_appendix": appendix, "checked": TODAY})
                f.flush()
                got += 1
                print(f"[{i}/{total}] {name}: SAT ~{hi} ({kind}) {p[0]}", flush=True)

        # A web search for the official Common Data Set is the surest source:
        # many class-profile pages are 404 or drawn by JavaScript.
        search_urls = []
        if not os.environ.get("NOSEARCH"):
            hits = search_candidates(name, starts)
            is_pdf = lambda u: u.lower().split("?")[0].endswith(".pdf")
            pages_hits = [u for u in hits if not is_pdf(u)]
            pdfs = [u for u in hits if is_pdf(u)]
            # a CDS listing page links the actual PDFs
            for pu in pages_hits[:2]:
                p = fetch(pu)
                if not p:
                    continue
                if p[2]:
                    pdfs.append(p[0])
                elif p[1]:
                    pdfs.extend(pdf_links(p[1], p[0]))
            search_urls = list(dict.fromkeys(pdfs + pages_hits))
            if os.environ.get("DEBUG"):
                print(f"  {name}: search {search_urls}", flush=True)
        try_candidates(search_urls, MAXASKS)

        cand = []
        for s in ([] if got else starts[:2]):
            p = fetch(s)
            if not p:
                continue
            pages.append(p)
            if p[1]:
                cand.extend(profile_links(p[1], p[0]))
                cand.extend(origin(p[0]) + g for g in GUESS)
        if not got and not pages:
            print(f"[{i}/{total}] {name}: start failed", flush=True)
            df.write(name + "\n")
            df.flush()
            continue
        if not got:
            # admissions home links to the class profile in its menu
            for au in admissions_home(pages[0][0])[:2]:
                if au in seen:
                    continue
                p = fetch(au)
                if p and p[1]:
                    pages.append(p)
                    cand.extend(profile_links(p[1], p[0]))
                    break
            # the site root often links to facts / class profile
            root = origin(pages[0][0]) + "/"
            if root not in seen:
                p = fetch(root)
                if p:
                    pages.append(p)
                    if p[1]:
                        cand.extend(profile_links(p[1], p[0]))
            # sitemap often knows the class profile page even when nothing links to it
            cand = sitemap_candidates(pages[0][0]) + cand
            cand = list(dict.fromkeys(u for u in cand if same_site(u, pages[0][0])))
            if os.environ.get("DEBUG"):
                print(f"  {name}: pages {[p[0] for p in pages]}", flush=True)
                print(f"  {name}: cand {cand[:MAXPAGES]}", flush=True)
            try_candidates(cand[:MAXPAGES], MAXASKS)
        if not got:
            print(f"[{i}/{total}] {name}: no target", flush=True)
        df.write(name + "\n")
        df.flush()
    f.close()
    df.close()


if __name__ == "__main__":
    main()
