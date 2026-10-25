#!/usr/bin/env python3
"""Open each official admissions page once, record the link status, and fill
only facts that the page states unambiguously. Polite: one request per second."""

import csv, re, sys, time
from datetime import date
from html.parser import HTMLParser

import requests

CSV = "data/universities.csv"
LOG = "data/page-check.csv"
REPORT = "data/report.md"
TODAY = date.today().isoformat()
UA = "ivypath-check/1.0 (student project; 1 request/second)"
FACT_SOURCE = ["ielts", "toefl", "sat", "deadline", "cost"]
COST_ENABLED = False

COLS = ["name", "country", "admissions_url",
        "ielts", "ielts_source", "ielts_checked",
        "toefl", "toefl_source", "toefl_checked",
        "sat", "sat_source", "sat_checked",
        "deadline", "deadline_source", "deadline_checked",
        "cost_amount", "cost_currency", "cost_year", "cost_source", "cost_checked",
        "intl_admission_rate", "intl_source", "intl_checked",
        "qs_rank", "qs_year", "qs_source", "qs_checked"]

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], 1)}
MONTHS.update({k[:3]: v for k, v in list(MONTHS.items())})
CURRENCIES = {"$": "USD", "£": "GBP", "€": "EUR", "US$": "USD", "C$": "CAD",
              "A$": "AUD", "S$": "SGD", "CHF": "CHF", "¥": "JPY", "₸": "KZT"}


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


def page_text(html):
    p = Text()
    p.feed(html)
    return re.sub(r"\s+", " ", " ".join(p.out))


def sentences(text):
    return re.split(r"(?<=[.!?])\s+", text)


def unique(values):
    return list(dict.fromkeys(values))


def first_number(sentence, word, lo, hi, decimals=False):
    if decimals:
        pat = rf"{word}[^.\d]{{0,200}}(\d\.\d)"
        ok = lambda v: lo <= float(v) <= hi
    else:
        pat = rf"{word}[^.\d]{{0,200}}(\d{{2,4}})"
        ok = lambda v: lo <= int(v) <= hi
    for m in re.finditer(pat, sentence, re.I):
        if ok(m.group(1)):
            return m.group(1)
    return None


def extract(text):
    found, quotes = {}, {}
    sents = sentences(text)

    def put(fact, value, sent):
        found.setdefault(fact, []).append(value)
        quotes.setdefault(fact, []).append(sent[:300])

    for s in sents:
        if re.search(r"\bIELTS\b", s):
            v = first_number(s, r"IELTS", 4.0, 9.0, decimals=True)
            if v:
                put("ielts", v, s)
        if re.search(r"\bTOEFL\b", s):
            v = first_number(s, r"TOEFL", 40, 120)
            if v:
                put("toefl", v, s)
        if re.search(r"\bSAT\b", s):
            v = first_number(s, r"SAT", 400, 1600)
            if v:
                put("sat", v, s)

        if re.search(r"deadline|apply by|applications? (?:close|due)|due by", s, re.I):
            for m in re.finditer(
                    r"\b(" + "|".join(MONTHS) + r")\s+(\d{1,2})(?:,?\s+(20\d{2}))?", s, re.I):
                mon, day, year = m.group(1).lower(), int(m.group(2)), m.group(3)
                if year and 1 <= day <= 31 and mon in MONTHS:
                    put("deadline", f"{int(year):04d}-{MONTHS[mon]:02d}-{day:02d}", s)

        if COST_ENABLED and re.search(r"tuition|fees?|cost of attendance", s, re.I):
            m = re.search(r"[$£€]\s?([\d,]{4,8})", s) or re.search(
                r"([\d,]{4,8})\s?(USD|GBP|EUR|CAD|AUD|SGD|CHF)", s)
            if m:
                amount = m.group(1).replace(",", "")
                cur = m.group(2) if m.lastindex and m.lastindex >= 2 else \
                    next((c for sym, c in CURRENCIES.items() if sym in m.group(0)), None)
                if cur and 1000 <= int(amount) <= 200000:
                    put("cost", f"{amount} {cur}", s)
                    y = re.search(r"20\d{2}\s*[-–/]\s*\d{2,4}", s)
                    if y:
                        put("cost_year", y.group(0), s)

    picked = {}
    for fact, vals in found.items():
        vals = unique(vals)
        if len(vals) == 1:
            picked[fact] = vals[0]
            quotes[fact] = quotes[fact][0]
        else:
            quotes[fact] = " | ".join(unique(quotes[fact]))[:600]
    return picked, quotes, found


def main():
    rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
    for r in rows:
        for c in COLS:
            r.setdefault(c, "")
    logs, evidence = [], []
    counts = {f: {"filled": 0, "ambiguous": 0, "none": 0} for f in FACT_SOURCE}
    statuses = {}

    for n, row in enumerate(rows, 1):
        url = row["admissions_url"]
        status, final, note = "", "", ""
        try:
            resp = requests.get(url, headers={"User-Agent": UA},
                                timeout=10, allow_redirects=True)
            status, final = str(resp.status_code), resp.url
            ctype = resp.headers.get("content-type", "")
            if resp.status_code == 200 and "html" in ctype:
                txt = page_text(resp.text)
                picked, quotes, found = extract(txt)
                for fact, val in picked.items():
                    if fact == "cost":
                        amount, cur = val.split()
                        row["cost_amount"], row["cost_currency"] = amount, cur
                        row["cost_source"], row["cost_checked"] = final, TODAY
                    elif fact == "cost_year":
                        row["cost_year"] = val
                    else:
                        row[fact] = val
                        row[fact + "_source"], row[fact + "_checked"] = final, TODAY
                    evidence.append([row["name"], fact, val, quotes.get(fact, ""), final, TODAY])
                for fact in FACT_SOURCE:
                    if fact in picked:
                        counts[fact]["filled"] += 1
                    elif len(unique(found.get(fact, []))) > 1:
                        counts[fact]["ambiguous"] += 1
                    else:
                        counts[fact]["none"] += 1
            else:
                note = "not html" if resp.status_code == 200 else ""
        except Exception as e:
            status, note = "ERR", str(e)[:120]
        statuses[status] = statuses.get(status, 0) + 1
        logs.append([row["name"], url, status, final, note])
        print(f"{n:3d}/115 {status:>4} {row['name']}", flush=True)
        if n % 10 == 0:
            write_csv(rows)
        time.sleep(1.1)

    write_csv(rows)
    with open(LOG, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "url", "status", "final_url", "note"])
        w.writerows(logs)
    with open("data/evidence.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "fact", "value", "quote", "source", "checked"])
        w.writerows(evidence)
    report(rows, counts, statuses, logs)


def write_csv(rows):
    with open(CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)


def report(rows, counts, statuses, logs):
    broken = [l for l in logs if l[2] != "200"]
    lines = [f"# Official page check, {TODAY}", "",
             f"- Universities: {len(rows)}",
             f"- Links OK (HTTP 200): {statuses.get('200', 0)}",
             f"- Links broken/blocked/error: {len(broken)}", "",
             "## Facts", "", "| Fact | Filled | Ambiguous | Not found |", "|---|---|---|---|"]
    for f in FACT_SOURCE:
        c = counts[f]
        lines.append(f"| {f} | {c['filled']} | {c['ambiguous']} | {c['none']} |")
    lines += ["", "## Links not OK", "", "| University | Status | URL |", "|---|---|---|"]
    for name, url, status, _, note in broken:
        lines.append(f"| {name} | {status}{(' ' + note) if note else ''} | {url} |")
    lines += ["", "Filled = exactly one value found on the page. Ambiguous = several "
              "values (different programmes); nothing filled. Not found = no match.",
              "Every filled value has *_source and *_checked in data/universities.csv; "
              "quotes are in data/evidence.csv. QS and international admission rate are "
              "not checked in this step."]
    open(REPORT, "w", encoding="utf-8").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
