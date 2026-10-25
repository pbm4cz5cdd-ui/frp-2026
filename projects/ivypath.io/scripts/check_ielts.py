#!/usr/bin/env python3
"""IELTS only: check official admissions pages and one English-requirements
subpage per university. A number is kept only if the page states exactly one
distinct overall band; several different bands are saved as "varies"."""

import csv, re, sys, time
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import requests

CSV = "data/universities.csv"
EVID = "data/evidence-ielts.csv"
REPORT = "data/report-ielts.md"
TODAY = date.today().isoformat()
UA = "ivypath-check/1.0 (student project; 1 request/second)"


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "svg"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def text_of(html):
    p = Text()
    p.feed(html)
    return re.sub(r"\s+", " ", " ".join(p.out)).strip()


class Anchors(HTMLParser):
    def __init__(self):
        super().__init__()
        self.href, self.buf, self.links = None, [], []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href, self.buf = dict(attrs).get("href"), []

    def handle_data(self, data):
        if self.href is not None:
            self.buf.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            label = re.sub(r"\s+", " ", " ".join(self.buf)).strip()
            if label:
                self.links.append((self.href, label))
            self.href = None


def best_link(base, html):
    a = Anchors()
    a.feed(html)
    best, score = None, 0
    for href, label in a.links:
        full = urljoin(base, href)
        if urlparse(full).netloc != urlparse(base).netloc:
            continue
        if re.search(r"\.(pdf|jpg|png|zip)$", full, re.I) or "#" in href:
            continue
        s = (label + " " + href).lower()
        pts = 0
        if re.search(r"english language (entry )?requirements?", s):
            pts = 5
        elif re.search(r"english (language )?(requirements?|proficiency)", s):
            pts = 4
        elif re.search(r"language requirements?", s):
            pts = 3
        elif re.search(r"international (applicants?|admissions?|students?)", s):
            pts = 2
        elif re.search(r"entry requirements?|admission requirements?", s):
            pts = 1
        if pts > score:
            best, score = full, pts
    return best


def get(url):
    r = requests.get(url, headers={"User-Agent": UA}, timeout=12)
    ctype = r.headers.get("content-type", "").lower()
    if r.status_code != 200 or ("html" not in ctype and "<html" not in r.text[:600].lower()):
        return None
    return r.url, r.text


def ielts_values(text):
    vals = {}
    pats = [
        r"overall (?:band|score)?(?: of)?\s*([4-9](?:\.\d)?)(?![.\d])",
        r"([4-9](?:\.\d)?)(?![.\d])\s*overall\b",
        r"(?:minimum|required|at least)[^.]{0,80}?IELTS[^.]{0,50}?([4-9](?:\.\d)?)(?![.\d])",
        r"IELTS[^.]{0,70}?(?:minimum|at least|required)[^.]{0,30}?([4-9](?:\.\d)?)(?![.\d])",
    ]
    for m in re.finditer(r"IELTS", text, re.I):
        chunk = text[max(0, m.start() - 220):m.start() + 300]
        for pat in pats:
            for mm in re.finditer(pat, chunk, re.I):
                v = mm.group(1)
                if 4.0 <= float(v) <= 9.0:
                    vals.setdefault(v, chunk)
    return vals


def main():
    rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
    if "ielts_note" not in rows[0]:
        for r in rows:
            r["ielts_note"] = ""
    for r in rows:
        r["ielts"] = r["ielts_source"] = r["ielts_checked"] = r["ielts_note"] = ""

    counts = {"filled": 0, "varies": 0, "none": 0, "link": 0}
    values, evidence, problems = [], [], []
    started = time.time()

    for n, row in enumerate(rows, 1):
        url = row["admissions_url"]
        try:
            page = get(url)
        except Exception as e:
            page = None
            problems.append((row["name"], "fetch", str(e)[:100]))
        if not page:
            counts["link"] += 1
            time.sleep(1.1)
            continue
        final, html = page
        text = text_of(html)
        source = final
        sub = best_link(final, html)
        if sub and sub.rstrip("/") != final.rstrip("/"):
            time.sleep(1.1)
            try:
                page2 = get(sub)
            except Exception as e:
                page2 = None
                problems.append((row["name"], "subpage", str(e)[:100]))
            if page2:
                source, html2 = page2
                text += " " + text_of(html2)
        vals = ielts_values(text)
        if len(vals) == 1:
            v, quote = next(iter(vals.items()))
            row["ielts"] = v
            row["ielts_source"], row["ielts_checked"] = source, TODAY
            counts["filled"] += 1
            values.append((row["name"], v, source))
            evidence.append([row["name"], v, quote[:400], source, TODAY])
        elif len(vals) > 1:
            row["ielts_note"] = "varies: " + ", ".join(sorted(vals))
            counts["varies"] += 1
            evidence.append([row["name"], "varies", " | ".join(
                vals[k][:220] for k in sorted(vals)), source, TODAY])
        else:
            counts["none"] += 1
        print(f"{n:3d}/115 {row['name']}: " + (
            row["ielts"] or row["ielts_note"] or "no value"), flush=True)
        if n % 10 == 0:
            save(rows, evidence)
        time.sleep(1.1)

    save(rows, evidence)
    write_report(counts, values, problems, time.time() - started)


def save(rows, evidence):
    cols = list(rows[0].keys())
    with open(CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    with open(EVID, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "ielts", "quote", "source", "checked"])
        w.writerows(evidence)


def write_report(counts, values, problems, secs):
    lines = [f"# IELTS check, {TODAY}", "",
             f"- Universities: {len(values) + counts['varies'] + counts['none'] + counts['link']}",
             f"- Pages that opened: {counts['filled'] + counts['varies'] + counts['none']}",
             f"- Link not OK: {counts['link']}",
             f"- Time: {secs/60:.1f} min, 1 request per second", "",
             "| Result | Count |", "|---|---|",
             f"| One overall band (filled) | {counts['filled']} |",
             f"| Several different bands (not filled) | {counts['varies']} |",
             f"| Not stated on the checked page | {counts['none']} |",
             f"| Page did not open | {counts['link']} |", "",
             "One value means the page had exactly one distinct IELTS band in a sentence "
             "with overall/minimum/required. Several different bands are marked "
             "`ielts_note = varies`; nothing is filled from them.", "",
             "## Filled", "", "| University | IELTS | Source |", "|---|---|---|"]
    for name, v, src in values:
        lines.append(f"| {name} | {v} | {src} |")
    if problems:
        lines += ["", f"## Problems ({len(problems)})", ""]
        for p in problems[:30]:
            lines.append("- " + " / ".join(p))
    open(REPORT, "w", encoding="utf-8").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
