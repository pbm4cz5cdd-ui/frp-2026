#!/usr/bin/env python3
"""Resolve the 12 review rows from batch 1 with checked notes/values.
Writes data/universities.csv and empties data/review-batch1.csv."""

import csv

CSV = "data/universities.csv"
BATCH = "data/us-batch1.csv"
REVIEW = "data/review-batch1.csv"
TODAY = "2026-10-26"

C = [
    ("Indiana University Bloomington", "sat", "", "SAT EBRW 560; альтернатива языковому тесту",
     "https://bloomington.iu.edu/admissions/apply/international/english-proficiency.html"),
    ("Case Western Reserve University", "sat", "", "SAT EBRW 630; альтернатива языковому тесту",
     "https://case.edu/admission/apply/international-applicants"),
    ("Syracuse University", "ielts", "6.5", "минимум; для части колледжей 7.0",
     "https://www.syracuse.edu/admissions-aid/application-process/international/undergraduate/requirements/"),
    ("Syracuse University", "toefl", "85", "минимум; для части колледжей 90–102",
     "https://www.syracuse.edu/admissions-aid/application-process/international/undergraduate/requirements/"),
    ("Illinois Institute of Technology", "sat", "", "SAT EBRW 550; альтернатива языковому тесту",
     "https://www.iit.edu/admissions-aid/undergraduate-admission/international-undergraduate-students/english-language-proficiency-requirements"),
    ("Saint Joseph's University", "sat", "", "SAT/ACT: тест-опционально; условия на сайте",
     "https://www.sju.edu/admission/undergraduate/first-year"),
    ("Hofstra University", "ielts", "6.5", "минимум",
     "https://www.hofstra.edu/admission/english-proficiency.html"),
    ("Hofstra University", "toefl", "80", "минимум",
     "https://www.hofstra.edu/admission/english-proficiency.html"),
    ("Hofstra University", "sat", "", "SAT EBRW 500; SAT/ACT не требуются",
     "https://www.hofstra.edu/admission/english-proficiency.html"),
    ("Adelphi University", "sat", "", "SAT EBRW 550; альтернатива языковому тесту",
     "https://www.adelphi.edu/admissions/international/english-proficiency-requirements/"),
    ("Creighton University", "sat", "", "SAT 560/ACT 22 — только альтернатива английскому; SAT/ACT необязательны",
     "https://www.creighton.edu/admissions/admissions-requirements/international"),
    ("St. John's University", "sat", "", "SAT/ACT: условие — при наличии языкового теста; см. сайт",
     "https://www.stjohns.edu/admission/international-admission/undergraduate-application-requirements"),
    ("Emerson College", "sat", "", "SAT/ACT засчитывается вместо языкового экзамена",
     "https://emerson.edu/admission-aid/undergraduate-admission/undergraduate-application-process/international-applicants/"),
    ("Sacred Heart University", "toefl", "", "обязателен для иностранцев с родным языком не английским",
     "https://www.sacredheart.edu/admissions--aid/undergraduate-admissions/freshman-admission/test-optional-policy/"),
]


def main():
    rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
    head = list(rows[0].keys())
    by_name = {r["name"]: r for r in rows}
    country = {r["name"]: r["country"] for r in csv.DictReader(open(BATCH, encoding="utf-8"))}

    for name, fact, value, note, source in C:
        u = by_name.get(name)
        if u is None:
            u = {h: "" for h in head}
            u["name"] = name
            u["country"] = country.get(name, "")
            rows.append(u)
            by_name[name] = u
        u[fact] = value
        u[f"{fact}_note"] = note
        u[f"{fact}_source"] = source
        u[f"{fact}_checked"] = TODAY

    with open(CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=head)
        w.writeheader()
        w.writerows(rows)
    with open(REVIEW, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["name", "fact", "status", "value", "quote", "source", "reason"])
        w.writeheader()
    print(f"resolved {len(C)} review rows; csv {len(rows)} rows; review is empty")


if __name__ == "__main__":
    main()
