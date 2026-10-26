#!/usr/bin/env python3
"""Apply only safe batch-1 proposals to data/universities.csv.
A proposal is applied only if its quote contains the number or clearly supports
the status. Suspicious rows go to data/review-batch1.csv."""

import csv
import re
import sys

PROP = "data/proposals-batch1.csv"
BATCH = "data/us-batch1.csv"
CSV = "data/universities.csv"
REVIEW = "data/review-batch1.csv"
RECOMMENDED = re.compile(r"рекоменд", re.I)


def recommended_note(fact, v, original, q):
    if fact == "sat":
        if re.search(r"Evidence-Based|EBRW|ERW|Reading and Writing", q, re.I):
            return f"рекомендуемый ориентир {v} (Reading & Writing); SAT не требуется"
        return f"рекомендуемый ориентир {v}; SAT не требуется"
    parts = [x.strip() for x in original.split(";")
             if x.strip() and not RECOMMENDED.search(x)]
    n = f"рекомендуемый балл {v}"
    if fact == "toefl" and num(v) is not None and num(v) < 20:
        n += " по новой шкале (1–6)"
    if parts:
        n += "; " + "; ".join(parts)
    return n


def num(v):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def has_value(q, v):
    s = str(v)
    variants = {s, s[:-2]} if s.endswith(".0") else {s, s + ".0"}
    return any(re.search(r"(?<![\d.])" + re.escape(x) + r"(?!\d)", q)
               for x in variants)


def note(status, q, original):
    if status in ("not_required", "varies") and re.search(r"ориентир|цель", original, re.I):
        return original
    if status == "not_required":
        return "тест-опционально" if re.search(r"test-optional", q, re.I) else "SAT/ACT не требуется" if "SAT" in q else "не требуется"
    if status == "varies":
        return "зависит от программы"
    return original


def supported_not_required(q):
    if re.search(r"(?<!not )required to submit|(?<!not )are required|(?<!not )is required", q, re.I):
        return False
    if re.search(r"for applicants from|English-speaking", q, re.I):
        return False
    return bool(re.search(r"not required|does not require|test-optional|optional|waiv|exempt", q, re.I))


def supported_varies(q):
    return bool(re.search(r"vary|varies|depend|range|program", q, re.I))


def main():
    global PROP, BATCH, REVIEW
    args = sys.argv[1:]
    for flag, name in (("--prop", "PROP"), ("--batch", "BATCH"), ("--review", "REVIEW")):
        if flag in args:
            try:
                value = args[args.index(flag) + 1]
            except IndexError:
                print(f"{flag} needs a file path", file=sys.stderr)
                return 2
            if name == "PROP":
                PROP = value
            elif name == "BATCH":
                BATCH = value
            else:
                REVIEW = value
    dry = "--dry-run" in args
    rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
    head = list(rows[0].keys())
    by_name = {r["name"]: r for r in rows}
    country = {r["name"]: r["country"] for r in csv.DictReader(open(BATCH, encoding="utf-8"))}

    applied = []
    review = []
    for p in csv.DictReader(open(PROP, encoding="utf-8")):
        name, fact, status = p["name"], p["fact"], p["status"]
        q, v = p["quote"].strip(), p["value"].strip()
        reason = ""
        col = None
        val = ""
        n = ""
        if fact in ("ielts", "toefl"):
            col = fact
            if status == "value":
                x = num(v)
                if x is None or not has_value(q, v):
                    reason = "значение не найдено в цитате"
                elif RECOMMENDED.search(p["note"]):
                    col = ""
                    n = recommended_note(fact, v, p["note"], q)
                elif fact == "ielts" and not 4 <= x <= 9:
                    reason = "IELTS вне шкалы"
                elif fact == "toefl" and x < 20:
                    col = ""
                    n = f"новая шкала {v}; {p['note']}".strip("; ")
                    val = ""
                elif fact == "toefl" and x > 120:
                    reason = "TOEFL вне шкалы"
                else:
                    val, n = v, re.sub(r"[,;]?\s*до X\b", "", p["note"]).strip(" ,;")
            elif status in ("not_required", "varies"):
                if status == "not_required" and not supported_not_required(q):
                    reason = "цитата не подтверждает not required"
                elif status == "varies" and not supported_varies(q):
                    reason = "цитата не подтверждает varies"
                else:
                    n = note(status, q, p["note"])
            else:
                reason = "status not_stated"
        elif fact == "sat":
            col = "sat"
            if status == "value":
                x = num(v)
                if x is None or not has_value(q, v):
                    reason = "значение не найдено в цитате"
                elif RECOMMENDED.search(p["note"]):
                    col = ""
                    n = recommended_note(fact, v, p["note"], q)
                elif re.search(r"Evidence-Based|EBRW|ERW|Reading and Writing", q, re.I):
                    col = ""
                    n = f"SAT EBRW {v}; {p['note']}".strip("; ")
                elif x < 800:
                    reason = "SAT меньше 800: похоже на секцию"
                else:
                    val, n = v, re.sub(r"[,;]?\s*до X\b", "", p["note"]).strip(" ,;")
            elif status in ("not_required", "varies"):
                if status == "not_required" and not supported_not_required(q):
                    reason = "цитата не подтверждает not required"
                elif status == "varies" and not supported_varies(q):
                    reason = "цитата не подтверждает varies"
                else:
                    n = note(status, q, p["note"])
            else:
                reason = "status not_stated"

        if reason:
            review.append({"name": name, "fact": fact, "status": status,
                           "value": v, "quote": q, "source": p["source"],
                           "reason": reason})
            continue
        u = by_name.get(name)
        if u is None:
            u = {h: "" for h in head}
            u["name"] = name
            u["country"] = country.get(name, "")
            rows.append(u)
            by_name[name] = u
        if u.get(col or fact):
            review.append({"name": name, "fact": fact, "status": status,
                           "value": v, "quote": q, "source": p["source"],
                           "reason": "поле уже заполнено"})
            continue
        if col:
            u[col] = val
        u[f"{fact}_note"] = n
        u[f"{fact}_source"] = p["source"]
        u[f"{fact}_checked"] = p["checked"]
        applied.append({"name": name, "fact": fact, "status": status,
                        "value": val or v, "note": n, "source": p["source"]})

    print(f"applied {len(applied)} rows, review {len(review)} rows, csv {len(rows)} rows")
    if dry:
        for r in applied:
            print("APPLY", r["name"], "|", r["fact"], "|", r["value"], "|", r["note"])
        for r in review:
            print("REVIEW", r["name"], "|", r["fact"], "|", r["reason"])
        return
    with open(CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=head)
        w.writeheader()
        w.writerows(rows)
    with open(REVIEW, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["name", "fact", "status", "value", "quote", "source", "reason"])
        w.writeheader()
        w.writerows(review)


if __name__ == "__main__":
    main()
