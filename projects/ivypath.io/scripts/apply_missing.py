#!/usr/bin/env python3
"""Merge data/proposals-missing.csv into data/universities.csv.
Only rows whose quote supports the number/status are applied; the rest go to
data/review-missing.csv. Existing values are never overwritten.

Usage: python3 scripts/apply_missing.py [--dry-run] [--prop FILE] [--review FILE]
"""

import csv
import re
import sys

PROP = "data/proposals-missing.csv"
CSV = "data/universities.csv"
REVIEW = "data/review-missing.csv"
RECOMMENDED = re.compile(r"рекоменд", re.I)
RANK = {"accepted": 0.5, "not_required": 1, "varies": 2, "value": 3}


def num(v):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def has_value(q, v):
    s = str(v).strip()
    variants = {s, s[:-2]} if s.endswith(".0") else {s, s + ".0"}
    if re.fullmatch(r"\d{4,}", s):
        # pages write 1190 as 1,190 or 1 190
        variants.add(f"{int(s):,}")
        variants.add(f"{int(s):,}".replace(",", " "))
    return any(re.search(r"(?<![\d.,])" + re.escape(x) + r"(?!\d)", q)
               for x in variants)


def supported_not_required(q):
    if re.search(r"(?<!not )required to submit|(?<!not )are required|(?<!not )is required", q, re.I):
        return False
    if re.search(r"for applicants from|English-speaking", q, re.I):
        return False
    return bool(re.search(r"not required|do(?:es)? not require|test-optional|test-?free"
                          r"|do(?:es)? not review|optional|waiv|exempt"
                          r"|not accepted|not considered|not used|not utiliz"
                          r"|will not be", q, re.I))


def supported_varies(q):
    return bool(re.search(r"vary|varies|depend|range|program", q, re.I))


TESTS = {"ielts": r"IELTS", "toefl": r"TOEFL", "hsk": r"HSK"}


def supported_accepted(q, fact):
    if re.search(r"not accepted|not considered|not required|do(?:es)? not (?:accept|require)"
                 r"|cannot be used|will not be", q, re.I):
        return False
    test = TESTS.get(fact, r"")
    if not test or not re.search(test, q, re.I):
        return False
    # Pages list an accepted test many ways: "we require TOEFL, IELTS",
    # "submit one of the following test scores", "provide proof ... TOEFL".
    # So look for an admission verb within about one line of the test name.
    words = (r"accept|requir|submit|submission|provide|take|demonstrat|welcome"
             r"|proof|results?|one of the following|exams?:"
             # "TOEFL minimum 600", "recognised English tests", "evidence of
             # English proficiency": pages often list the test without a verb.
             r"|scores?|minimum|at least|evidence|recognis|recogniz")
    for m in re.finditer(test, q, re.I):
        window = q[max(0, m.start() - 120):m.end() + 120]
        if re.search(words, window, re.I):
            return True
    return False


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


def note_for(status, q, original, fact="sat"):
    if status in ("not_required", "varies") and re.search(r"ориентир|цель", original, re.I):
        return original
    if status == "accepted":
        label = {"hsk": "HSK", "ielts": "IELTS", "toefl": "TOEFL"}.get(fact, "тест")
        return f"{label} принимается; минимальный балл не опубликован"
    if status == "not_required":
        if re.search(r"test-optional", q, re.I):
            return "тест-опционально"
        label = {"ap": "AP", "hsk": "HSK", "ib": "IB", "ielts": "IELTS", "toefl": "TOEFL"}.get(fact)
        if label is None:
            label = "SAT/ACT" if "SAT" in q else ""
        return f"{label} не требуется".strip()
    if status == "varies":
        return "зависит от программы"
    return original


def decide(p):
    """Return (column, value, note) or (None, None, reason)."""
    fact, status = p["fact"], p["status"]
    q = p["quote"].strip()
    v = p["value"].strip()
    original = p["note"].strip()
    if fact in ("ielts", "toefl", "sat", "hsk"):
        if status == "value":
            x = num(v)
            if x is None or not has_value(q, v):
                return None, None, "значение не найдено в цитате"
            if RECOMMENDED.search(original):
                return "", None, recommended_note(fact, v, original, q)
            if fact == "ielts" and not 4 <= x <= 9:
                return None, None, "IELTS вне шкалы"
            if fact == "toefl" and x < 20:
                return "", "", f"новая шкала {v}; {original}".strip("; ")
            if fact == "toefl" and x > 120:
                return None, None, "TOEFL вне шкалы"
            if fact == "sat" and re.search(r"Evidence-Based|EBRW|ERW|Reading and Writing", q, re.I):
                return "", None, f"SAT EBRW {v}; {original}".strip("; ")
            if fact == "sat" and x < 800:
                return None, None, "SAT меньше 800: похоже на секцию"
            return fact, v, re.sub(r"[,;]?\s*до X\b", "", original).strip(" ,;")
        if status in ("not_required", "varies", "accepted"):
            if status == "accepted":
                if fact not in ("ielts", "toefl", "hsk"):
                    return None, None, "accepted не подходит для этого факта"
                if not supported_accepted(q, fact):
                    return None, None, "цитата не подтверждает: тест принимается"
                return "", None, note_for(status, q, original, fact)
            target = re.search(r"ориентир\s*~?\s*(\d{3,4})", original)
            if target and not has_value(q, target.group(1)):
                return None, None, "ориентир не найден в цитате"
            if target and int(target.group(1)) < 800:
                return None, None, "ориентир меньше 800: похоже на секцию"
            if status == "not_required" and not supported_not_required(q):
                # A test-optional school's class profile proves the target range,
                # not the "optional" part (that comes from the admissions page).
                if not (target and re.search(r"\d{3,4}\s*[–—\-]\s*\d{3,4}", q)):
                    return None, None, "цитата не подтверждает not required"
            if status == "varies" and not supported_varies(q):
                return None, None, "цитата не подтверждает varies"
            return "", None, note_for(status, q, original, fact)
        return None, None, "status not_stated"
    if fact in ("ap", "ib"):
        if status == "value" and v:
            if fact == "ib":
                x = num(v)
                if x is None or not 24 <= x <= 45:
                    return None, None, "IB вне шкалы 24–45"
                if not has_value(q, v):
                    return None, None, "значение не найдено в цитате"
            return fact, v, original
        if status in ("not_required", "varies"):
            return fact, "", note_for(status, q, original, fact)
        return None, None, "status not_stated"
    return None, None, "неизвестный факт"


def main():
    global PROP, REVIEW
    args = sys.argv[1:]
    for flag, name in (("--prop", "PROP"), ("--review", "REVIEW")):
        if flag in args:
            try:
                value = args[args.index(flag) + 1]
            except IndexError:
                print(f"{flag} needs a file path", file=sys.stderr)
                return 2
            if name == "PROP":
                PROP = value
            else:
                REVIEW = value
    dry = "--dry-run" in args

    rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
    head = list(rows[0].keys())
    by_name = {r["name"]: r for r in rows}

    # Keep one best proposal per (name, fact).
    props = {}
    for p in csv.DictReader(open(PROP, encoding="utf-8")):
        key = (p["name"], p["fact"])
        old = props.get(key)
        if old is None or RANK.get(p["status"], 0) >= RANK.get(old["status"], 0):
            props[key] = p

    applied, review = [], []
    for p in props.values():
        name, fact = p["name"], p["fact"]
        col, val, n = decide(p)
        if col is None:
            review.append({"name": name, "fact": fact, "status": p["status"],
                           "value": p["value"], "quote": p["quote"],
                           "source": p["source"], "reason": n})
            continue
        u = by_name.get(name)
        if u is None:
            u = {h: "" for h in head}
            u["name"] = name
            u["country"] = p.get("country", "")
            rows.append(u)
            by_name[name] = u
        if u.get(fact):
            review.append({"name": name, "fact": fact, "status": p["status"],
                           "value": p["value"], "quote": p["quote"],
                           "source": p["source"], "reason": "поле уже заполнено"})
            continue
        old_note = u.get(f"{fact}_note", "")
        if old_note and "ориентир ~" in old_note and "ориентир ~" not in n:
            review.append({"name": name, "fact": fact, "status": p["status"],
                           "value": p["value"], "quote": p["quote"],
                           "source": p["source"], "reason": "уже есть ориентир"})
            continue
        if old_note and "ориентир ~" not in n:
            review.append({"name": name, "fact": fact, "status": p["status"],
                           "value": p["value"], "quote": p["quote"],
                           "source": p["source"], "reason": "уже есть примечание"})
            continue
        if col:
            u[col] = val if val is not None else ""
        u[f"{fact}_note"] = n
        u[f"{fact}_source"] = p["source"]
        u[f"{fact}_checked"] = p["checked"]
        if fact == "ap" and not u.get("ap"):
            u["ap"] = val or ""
        applied.append({"name": name, "fact": fact, "status": p["status"],
                        "value": val or p["value"], "note": n, "source": p["source"]})

    print(f"applied {len(applied)} rows, review {len(review)} rows, csv {len(rows)} rows")
    if dry:
        for r in applied:
            print("APPLY", r["name"], "|", r["fact"], "|", r["value"], "|", r["note"])
        for r in review:
            print("REVIEW", r["name"], "|", r["fact"], "|", r["reason"])
        return
    tmp = CSV + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=head)
        w.writeheader()
        w.writerows(rows)
    import os
    os.replace(tmp, CSV)
    with open(REVIEW, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["name", "fact", "status", "value",
                                          "quote", "source", "reason"])
        w.writeheader()
        w.writerows(review)


if __name__ == "__main__":
    main()
