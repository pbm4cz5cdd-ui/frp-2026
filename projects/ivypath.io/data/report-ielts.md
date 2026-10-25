# IELTS check, 2026-10-25

- Universities: 115
- Pages that opened: 64
- Links not OK: 51 (404, connection error, 403/405/202; see data/report.md)
- Exact IELTS minimum: 2
- Not a single number (marked in `ielts_note`): 4
- No IELTS statement on the checked page: 58

| University | IELTS | Note | Source |
|---|---|---|---|
| University of Toronto | 6.5 | no band below 6.0 | https://future.utoronto.ca/english-language-requirements |
| University of Waterloo | 6.5 | 7.0 is also accepted; some programmes ask for more | https://uwaterloo.ca/future-students/admissions/english-language-requirements |
| Harvard University | — | not required for first-year/transfer; may submit | https://college.harvard.edu/admissions/apply/international-applicants |
| University of Edinburgh | — | varies by degree; see degree finder | https://study.ed.ac.uk/undergraduate/entry-requirements/english-language |
| University of Manchester | — | varies by course; typical 5.5-7.5+ | https://www.manchester.ac.uk/study/international/admissions/language-requirements/ |

## Why not filled automatically

Two naive extractions were wrong and were removed:

- Waterloo: the page says **6.5 overall**, and separately that **7.0 is "also acceptable"**. A parser that takes the last "minimum overall IELTS" number filled 7.0.
- Manchester: the page shows a **table 5.5 / 6 / 6.5 / 7 / 7.5+** by course. A parser filled the lowest number, 5.5.

Edinburgh puts the numbers in a per-degree finder; Harvard does not require the exam.
So a number is filled only where one sentence states one overall minimum. Pages with
several bands or a table are marked `ielts_note = varies`, not given a fake number.

Every value and note has an exact quote in `data/evidence.csv` and a date (`*_checked`).
Next: TOEFL with the same rule, then SAT, deadline and cost; 51 links still need replacing.
