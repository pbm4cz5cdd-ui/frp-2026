#!/bin/bash
# UK SAT, second pass for the 30 rows still empty. Waits for the China
# language finisher first: two apply_missing runs at once would write the same
# rows twice. Then crawl, verify, apply and report coverage.
cd "$(dirname "$0")/.." || exit 1

OTHER=1542238
LOG=data/finish-uk-sat2.log

while kill -0 "$OTHER" 2>/dev/null; do sleep 30; done
echo "--- crawl $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/find_uk_entry_pages.py data/missing-uk-sat2.csv data/proposals-uk-sat2.csv >>"$LOG" 2>&1
echo "--- verify $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/verify_uk_sat.py data/proposals-uk-sat2.csv data/verified-uk-sat2.csv >>"$LOG" 2>&1
echo "--- apply $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/apply_uk_sat.py data/verified-uk-sat2.csv >>"$LOG" 2>&1
echo "--- coverage $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/coverage.py >>"$LOG" 2>&1
echo "--- done $(date +%H:%M:%S)" >>"$LOG"
