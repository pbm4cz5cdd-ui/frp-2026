#!/usr/bin/env python3
"""SAT targets for US universities from official IPEDS admissions data.

Target = 75th percentile of admitted students' SAT (ERW75 + Math75).
Writes sat_note / sat_source / sat_checked; leaves `sat` empty so the card
shows "SAT ~N (optional)" (index.html reads the number from the note).

Usage:
  python3 scripts/ipeds_sat.py            # dry run, writes /tmp/ipeds_plan.csv
  python3 scripts/ipeds_sat.py --apply    # write into data/universities.csv
"""
import csv, io, os, re, sys, unicodedata, zipfile, difflib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IPEDS = "/tmp/ipeds"
DATE = "2026-10-29"

ALIAS = {
    "Columbia University": "190150", "UC Berkeley": "110635", "UCLA": "110662",
    "Georgia Institute of Technology": "139755", "University of Michigan": "170976",
    "Caltech": "110404", "UC San Diego": "110680", "Purdue University": "243780",
    "Embry-Riddle Aeronautical University": "133553", "Virginia Tech": "233921",
    "St. John's University": "195809", "St. John's College": "163976",
    "Penn State University Park": "214777", "Trinity College (CT)": "130590",
    "The Ohio State University": "204796", "Union College": "196866",
    "University of New Hampshire": "183044", "SUNY Geneseo": "196167",
    "SUNY New Paltz": "196176", "Ohio University": "204857",
    "University of South Carolina": "218663", "University of Cincinnati": "201885",
    "Louisiana State University": "159391", "University of New Mexico": "187985",
    "Miami University": "204024", "Kent State University": "203517",
    "Colorado State University": "126818", "University of Missouri": "178396",
    "University of Oklahoma": "207500", "Pratt Institute": "194578",
    "Arizona State University": "104151", "North Dakota State University": "200332",
    "Tulane University": "160755", "University of Virginia": "234076",
    "Baruch College": "190512", "Hunter College": "190594",
    "City College of New York": "190567", "Brooklyn College": "190549",
    "Queens College": "190664", "University of Pittsburgh": "215293",
    "North Carolina State University": "199193", "Bowling Green State University": "201441",
    "Oklahoma State University": "207388", "Texas A&M University": "228723",
    "Parsons School of Design (The New School)": "193654",
    "Fashion Institute of Technology (SUNY)": "191126",
    "New England Conservatory": "167057", "Johnson & Wales University": "217235",
    "University of Colorado Denver": "126562", "Wheaton College": "149781",
}


def load_year(y):
    z = zipfile.ZipFile(f"{IPEDS}/ADM{y}.zip")
    names = [n for n in z.namelist() if n.endswith("_rv.csv")] or \
            [n for n in z.namelist() if n.endswith(".csv")]
    return {r["UNITID"]: r for r in
            csv.DictReader(io.TextIOWrapper(z.open(names[0]), encoding="latin-1"))}


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = s.lower().replace("&", " and ")
    s = re.sub(r"\bsaint\b", "st", s)
    s = re.sub(r"\bthe\b", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def num(row, key):
    v = (row.get(key) or "").strip()
    return int(v) if v.isdigit() else None


def main():
    apply = "--apply" in sys.argv
    hd = {r["UNITID"]: r for r in
          csv.DictReader(open(f"{IPEDS}/HD2023.csv", encoding="utf-8-sig"))}
    years = {y: load_year(y) for y in ("2023", "2022", "2021", "2019")}
    label = {"2023": "2023/24", "2022": "2022/23", "2021": "2021/22", "2019": "2019/20"}

    rows = list(csv.DictReader(open(f"{ROOT}/data/universities.csv", encoding="utf-8")))
    fields = list(rows[0].keys())
    names = [(uid, norm(v["INSTNM"])) for uid, v in hd.items()]

    plan = []
    stats = {"target2023": 0, "target_old": 0, "blind": 0, "nodata": 0}
    for r in rows:
        if r["country"] != "usa" or r["sat"].strip():
            continue
        uid = ALIAS.get(r["name"])
        if not uid:
            n = norm(r["name"])
            sc = sorted(((difflib.SequenceMatcher(None, n, x[1]).ratio(), x[0])
                         for x in names), reverse=True)
            if sc[0][0] >= 0.95 and sc[1][0] < sc[0][0] - 0.01:
                uid = sc[0][1]
        if not uid:
            print("UNMATCHED", r["name"])
            continue
        a23 = years["2023"].get(uid, {})
        con = (a23.get("ADMCON7") or "").strip()
        if con == "3":                       # test blind
            note = ("SAT не учитывается при приёме (test blind, IPEDS 2023/24): "
                    "вуз не рассматривает SAT, даже если его сдать.")
            plan.append((r["name"], uid, "", note, f"https://nces.ed.gov/collegenavigator/?id={uid}", ""))
            stats["blind"] += 1
            continue
        use = None
        for y in ("2023", "2022", "2021", "2019"):
            a = years[y].get(uid, {})
            vr75, mt75, vr25, mt25 = (num(a, "SATVR75"), num(a, "SATMT75"),
                                      num(a, "SATVR25"), num(a, "SATMT25"))
            if vr75 and mt75 and vr75 > 200 and mt75 > 200:
                use = (y, vr25, vr75, mt25, mt75)
                break
        if not use:
            print("NODATA", r["name"], "->", hd[uid]["INSTNM"], "ADMCON7=", con)
            stats["nodata"] += 1
            continue
        y, vr25, vr75, mt25, mt75 = use
        n75 = vr75 + mt75
        rng = f"≈ {vr25 + mt25}–{n75}" if (vr25 and mt25) else f"≈ {n75} (75-й)"
        if con == "1":                        # required
            note = (f"SAT обязателен (IPEDS {label[y]}): 75-й перцентиль принятых "
                    f"{n75}; ERW {vr25}–{vr75}, Math {mt25}–{mt75}; сумма 25–75 {rng}.")
            stats["target2023" if y == "2023" else "target_old"] += 1
        else:                                 # test optional
            note = (f"SAT не обязателен (test-optional, IPEDS {label[y]}). "
                    f"ориентир ~{n75} (optional) — 75-й перцентиль принятых; "
                    f"ERW {vr25}–{vr75}, Math {mt25}–{mt75}; сумма 25–75 {rng}.")
            if y != "2023":
                note = note.replace(f"(test-optional, IPEDS {label[y]})",
                                    f"(test-optional; статистика приёма {label[y]}, "
                                    f"позже вуз её не публикует)")
            stats["target2023" if y == "2023" else "target_old"] += 1
        plan.append((r["name"], uid, "", note,
                     f"https://nces.ed.gov/collegenavigator/?id={uid}", label[y]))

    print(len(plan), "rows planned:", stats)
    with open("/tmp/ipeds_plan.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "unitid", "sat", "sat_note", "sat_source", "year"])
        w.writerows(plan)

    if not apply:
        return
    by = {p[0]: p for p in plan}
    tgt = re.compile(r"(?:ориентир|цель)\s*~?\s*\d{3,4}")
    free = re.compile(r"не рассматрива|test-free|не учитыв|test blind|тест-блайнд")
    need = re.compile(r"нужен|нужна|обязателен|ожидается")
    soft = re.compile(r"не обязателен|не требуется|optional|не рассматрива|не учитыв")
    touched = 0
    for r in rows:
        p = by.get(r["name"])
        if not p:
            continue
        name, uid, _sat, note_new, src_ipeds, year = p
        old = r["sat_note"].strip()
        if note_new.startswith("SAT не учитывается"):
            if old:
                continue                      # official / earlier checked note wins
            r["sat_note"] = note_new
            r["sat_source"] = r["sat_source"].strip() or src_ipeds
            r["sat_checked"] = DATE
            touched += 1
            continue
        if tgt.search(old.lower()):
            continue                          # already has an official target
        if free.search(old.lower()):
            continue                          # note says scores are not used
        target = re.search(r"ориентир ~(\d+)", note_new)
        er = re.search(r"ERW (\d+)\u2013(\d+), Math (\d+)\u2013(\d+)", note_new)
        n75 = int(target.group(1)) if target else int(er.group(2)) + int(er.group(4))
        if not old:
            r["sat_note"] = note_new
            r["sat_source"] = r["sat_source"].strip() or src_ipeds
            r["sat_checked"] = DATE
            touched += 1
            continue
        if need.search(old.lower()) and not soft.search(old.lower()):
            add = (f" ; 75-й перцентиль принятых (IPEDS {year}): "
                   f"ERW {er.group(1)}\u2013{er.group(2)}, Math {er.group(3)}\u2013{er.group(4)}, "
                   f"сумма \u2248 {n75}.")
        else:
            add = (f" ; ориентир ~{n75} (optional) — 75-й перцентиль принятых "
                   f"(IPEDS {year}), ERW {er.group(1)}\u2013{er.group(2)}, Math {er.group(3)}\u2013{er.group(4)}.")
        r["sat_note"] = old.rstrip(" .;") + add
        r["sat_checked"] = DATE
        touched += 1
    with open(f"{ROOT}/data/universities.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print("touched:", touched)


if __name__ == "__main__":
    main()
