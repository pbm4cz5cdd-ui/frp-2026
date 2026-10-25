#!/usr/bin/env python3
"""Read the 64 official pages that opened, ask the class model for undergraduate
requirements, and keep a value only if its quote is on the page and the number
is in the quote. Nothing is guessed; unknown stays empty."""

import csv, json, re, sys, time
from datetime import date
from html.parser import HTMLParser

import requests

CSV = "data/universities.csv"
REPORT = "data/report-requirements.md"
EVIDENCE = "data/evidence-requirements.csv"
TODAY = date.today().isoformat()
UA = "ivypath-check/1.0 (student project; 1 request/second)"
API = "http://127.0.0.1:19040/v1/chat/completions"
MODEL = "DeepSeek-V4.1-Flash"
FACTS = ["ielts", "toefl", "sat", "deadline", "cost"]


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
    return re.sub(r"\s+", " ", " ".join(p.out)).strip()


def windows(text, limit=8000):
    marks = list(re.finditer(
        r"IELTS|TOEFL|SAT\b|deadline|apply by|tuition|fees?|cost of attendance",
        text, re.I))
    out = []
    for m in marks:
        w = text[max(0, m.start() - 500):m.start() + 900]
        if w not in out:
            out.append(w)
    return "\n---\n".join(out)[:limit]


PROMPT = """This text is from a university admissions page. Extract requirements for
undergraduate international applicants only.

Return ONLY JSON:
{"ielts":{"value":"6.5","quote":"..."},"toefl":{"value":"100","quote":"..."},
 "sat":{"value":"1450","quote":"..."},"deadline":{"value":"2027-01-15","quote":"..."},
 "cost":{"value":"45000 USD","quote":"..."}}

Rules:
- value is the minimum overall/total score or one yearly cost; keep the number.
- quote is an exact sentence from the text that contains the value.
- Use null when the text does not state it, or when several different
  undergraduate values apply (do not pick one).
- cost: yearly tuition or cost of attendance for one international undergraduate
  student, with currency. Null if it is a range.
- deadline: only if the year is written or can be read from the text; ISO date.
No explanations outside the JSON.

TEXT:
"""


def ask(text):
    r = requests.post(API, json={
        "model": MODEL, "max_tokens": 600, "temperature": 0,
        "messages": [{"role": "user", "content": PROMPT + text[:8000]}]},
        timeout=90)
    r.raise_for_status()
    raw = r.json()["choices"][0]["message"]["content"].strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw).strip()
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise ValueError("no JSON in answer")
    return json.loads(m.group(0))


def norm(s):
    return re.sub(r"\s+", " ", s or "").strip()


def num_in(value, quote, lo, hi):
    m = re.search(r"\d+(?:\.\d+)?", value)
    if not m:
        return None
    raw = m.group(0)
    v = float(raw)
    if not (lo <= v <= hi):
        return None
    if not re.search(r"(?<![\d.])" + re.escape(raw) + r"(?![\d.])", quote):
        return None
    return raw


def quote_date(quote):
    months = {m: i for i, m in enumerate(
        ["january", "february", "march", "april", "may", "june", "july",
         "august", "september", "october", "november", "december"], 1)}
    m = re.search(r"\b(" + "|".join(months) + r")\s+(\d{1,2}),?\s+(20\d{2})",
                  quote, re.I)
    if m:
        return (m.group(3), months[m.group(1).lower()], int(m.group(2)))
    m = re.search(r"\b(\d{1,2})\s+(" + "|".join(months) + r"),?\s+(20\d{2})",
                  quote, re.I)
    if m:
        return (m.group(3), months[m.group(2).lower()], int(m.group(1)))
    m = re.search(r"\b(20\d{2})-(\d{2})-(\d{2})\b", quote)
    if m:
        return (m.group(1), int(m.group(2)), int(m.group(3)))
    return None


def parse_deadline(value, quote):
    iso = re.search(r"\b(20\d{2})-(\d{2})-(\d{2})\b", value + " " + quote)
    if iso:
        return iso.group(0)
    months = {m: i for i, m in enumerate(
        ["january", "february", "march", "april", "may", "june", "july",
         "august", "september", "october", "november", "december"], 1)}
    m = re.search(r"\b(" + "|".join(months) + r")\s+(\d{1,2}),?\s+(20\d{2})",
                  quote, re.I)
    if m:
        return f"{m.group(3)}-{months[m.group(1).lower()]:02d}-{int(m.group(2)):02d}"
    m = re.search(r"\b(\d{1,2})\s+(" + "|".join(months) + r"),?\s+(20\d{2})",
                  quote, re.I)
    if m:
        return f"{m.group(3)}-{months[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
    return None


def parse_cost(value, quote):
    m = re.search(r"([\d,]{4,8})\s*(USD|GBP|EUR|CAD|AUD|SGD|CHF|JPY|KZT)", value, re.I)
    if not m:
        m = re.search(r"([$£€])\s?([\d,]{4,8})", value)
        if not m:
            return None
        cur = {"$": "USD", "£": "GBP", "€": "EUR"}[m.group(1)]
        amount = m.group(2).replace(",", "")
    else:
        amount, cur = m.group(1).replace(",", ""), m.group(2).upper()
    if not (500 <= int(amount) <= 200000):
        return None
    if not re.search(r"tuition|fees?|cost of attendance", quote, re.I):
        return None
    if re.search(r"\bto\b|–|range|up to|from .* to|average|income", quote, re.I) \
            and len(re.findall(r"[\d,]{4,8}", quote)) > 1:
        return None
    if amount not in quote.replace(",", ""):
        return None
    return amount, cur


def main():
    rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
    for row in rows:
        for f in FACTS:
            if f == "cost":
                row["cost_amount"] = row["cost_currency"] = row["cost_year"] = ""
                row["cost_source"] = row["cost_checked"] = ""
                continue
            row[f] = ""
            row[f + "_source"] = row[f + "_checked"] = ""
    counts = {f: {"filled": 0, "rejected": 0, "none": 0, "link": 0} for f in FACTS}
    evidence, problems = [], []
    started = time.time()
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        rows = rows[:int(sys.argv[1])]
    dry = "--dry" in sys.argv

    for n, row in enumerate(rows, 1):
        url = row["admissions_url"]
        if not url:
            for f in FACTS:
                counts[f]["link"] += 1
            continue
        try:
            resp = requests.get(url, headers={"User-Agent": UA},
                                timeout=10, allow_redirects=True)
        except Exception as e:
            for f in FACTS:
                counts[f]["link"] += 1
            problems.append((row["name"], "fetch", str(e)[:120]))
            continue
        ctype = resp.headers.get("content-type", "").lower()
        if resp.status_code != 200 or ("html" not in ctype and "<html" not in resp.text[:600].lower()):
            for f in FACTS:
                counts[f]["link"] += 1
            problems.append((row["name"], "status", str(resp.status_code)))
            time.sleep(1.05)
            continue

        text = page_text(resp.text)
        final = resp.url
        try:
            ans = ask(windows(text))
        except Exception as e:
            for f in FACTS:
                counts[f]["none"] += 1
            problems.append((row["name"], "model", str(e)[:120]))
            time.sleep(1.05)
            continue

        for f in FACTS:
            item = ans.get(f) if isinstance(ans, dict) else None
            if not item or not item.get("value") or not item.get("quote"):
                counts[f]["none"] += 1
                continue
            q, val = norm(item["quote"]), norm(str(item["value"]))
            if q not in text or not q:
                counts[f]["rejected"] += 1
                problems.append((row["name"], f, "quote not found"))
                continue
            if f == "ielts":
                v = num_in(val, q, 4.0, 9.0)
            elif f == "toefl":
                v = num_in(val, q, 40, 120) or num_in(val, q, 3.0, 6.0)
            elif f == "sat":
                v = num_in(val, q, 400, 1600)
            elif f == "deadline":
                v = parse_deadline(val, q)
                d = quote_date(q)
                if not v or not d or (v[0:4], int(v[5:7]), int(v[8:10])) != d:
                    v = None
            else:
                v = parse_cost(val, q)
            if not v:
                counts[f]["rejected"] += 1
                problems.append((row["name"], f, "number check failed"))
                continue
            if f == "cost":
                amount, cur = v
                row["cost_amount"], row["cost_currency"] = amount, cur
                row["cost_source"], row["cost_checked"] = final, TODAY
                shown = f"{amount} {cur}"
            else:
                row[f] = v
                row[f + "_source"], row[f + "_checked"] = final, TODAY
                shown = v
            counts[f]["filled"] += 1
            evidence.append([row["name"], f, shown, q[:400], final, TODAY])
        print(f"{n:3d}/115 {row['name']} -> " + ", ".join(
            f for f in FACTS if ans.get(f) and ans[f].get("value")), flush=True)
        if n % 5 == 0 and not dry:
            save(rows, evidence)
        time.sleep(1.05)

    if dry:
        print("counts", counts)
        for e in evidence:
            print(e[0], e[1], e[2], "|", e[3][:110])
        return
    save(rows, evidence)
    write_report(counts, problems, time.time() - started)


def save(rows, evidence):
    cols = list(rows[0].keys())
    with open(CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    with open(EVIDENCE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "fact", "value", "quote", "source", "checked"])
        w.writerows(evidence)


def write_report(counts, problems, secs):
    lines = [f"# Requirements from official pages, {TODAY}", "",
             f"- Checked pages: {115 - counts['ielts']['link']} of 115 opened",
             f"- Time: {secs/60:.1f} min, 1 request per second",
             "", "| Fact | Filled | Rejected by quote/number check | Not on page | Page did not open |",
             "|---|---|---|---|---|"]
    for f in FACTS:
        c = counts[f]
        lines.append(f"| {f} | {c['filled']} | {c['rejected']} | {c['none']} | {c['link']} |")
    lines += ["", "Filled = the model quoted a sentence, the sentence is on the page, "
              "and the number in it passed the range check. Everything else is empty.",
              "`*_source` and `*_checked` are in data/universities.csv; quotes are in "
              "data/evidence-requirements.csv.", ""]
    if problems:
        lines += ["## Problems", "", "| University | Fact | Problem |", "|---|---|---|"]
        for p in problems[:80]:
            lines.append("| " + " | ".join(p) + " |")
        lines += ["", f"(first 80 of {len(problems)})"]
    open(REPORT, "w", encoding="utf-8").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
