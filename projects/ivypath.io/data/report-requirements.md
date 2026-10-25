# Requirements in the catalog, 2026-10-25

Only facts from an official page with a quote are filled. `≈` means the page
gives a competitive score, not a hard minimum. A range by programme is stored as
the lowest published score plus a note. No number is guessed.

- Universities: 115
- IELTS: 83 values, 32 notes without a value (local language / varies / no minimum), 0 without data
- TOEFL: 81 values, 34 notes without a value, 0 without data
- SAT: 7 values (HKU 1380, HKUST 1190, Koç 1200, Bilkent 1000, Sabancı 1100, SMU 1350, Peking 1400),
  108 notes, 0 without data. All 33 US universities have a value or a checked note.
  Of the non-US notes, 24 were checked one by one against the official page (Japan, Korea, China,
  Hong Kong, Singapore, Canada, Turkey, UAE, Malaysia) and have quotes in evidence.csv; the other 54
  (UK, EU, Australia, NZ) state the country-system rule: SAT is not part of their standard route.
- Universities with IELTS/TOEFL/SAT data or a note: 115
- No requirement data at all: 0

Checked universities: Toronto, Waterloo, Harvard, Edinburgh, Manchester, Yale,
Stanford, Cambridge, MIT, Imperial, UCL, UC Berkeley, UCLA, Carnegie Mellon,
Princeton, TU Munich, KTH, NTU, Queen's, Georgia Tech, Oxford, Columbia, UBC,
McGill, Michigan, NYU, LSE, KCL, Bristol, Dartmouth, Caltech, Rice, UCSD,
Vanderbilt, Brown, Cornell, Notre Dame, JHU, Duke, Northwestern, Penn, Bowdoin, Bristol, UNSW, Monash, Otago, Bilkent, Khalifa, Koç,
Purdue, Embry-Riddle, Sabancı, Kyoto, Amherst, North Dakota, WMU, Alberta, Melbourne, W&L, Illinois,
CUHK, Malaya, Politecnico di Milano, Sciences Po, SMU, SNU, Charles,
Durham, Tokyo PEAK, Fudan, UChicago, RWTH, Heidelberg, LMU, Humboldt,
Stuttgart, Vienna, ETH, EPFL, Sorbonne, Polytechnique, Zurich, Warsaw,
CTU, KAIST, Peking.

TOEFL changed to a 1-6 scale for tests taken from 21 January 2026. The catalog
stores the 0-120 score because the score filter uses it; the new 1-6 score is in
the note.

All 115 cards now carry a value or a note, so no card says "нет данных".
Notes and quotes: `data/evidence.csv`.
