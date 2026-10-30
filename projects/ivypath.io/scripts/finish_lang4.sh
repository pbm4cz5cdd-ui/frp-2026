#!/bin/bash
# Wait for the three language crawlers (remaining English-language countries),
# then merge, apply and report. Only one apply run may write universities.csv,
# so nothing else must be running when this starts.
# Run with setsid so it keeps going after the session ends.
cd "$(dirname "$0")/.." || exit 1

PIDS=$(cat data/lang4.pids)
LOG=data/finish-lang4.log

echo "start $(date +%H:%M:%S), waiting for: $PIDS" >>"$LOG"
for i in $(seq 1 240); do
  alive=""
  for p in $PIDS; do
    if kill -0 "$p" 2>/dev/null; then alive="$alive $p"; fi
  done
  if [ -z "$alive" ]; then
    echo "all finished $(date +%H:%M:%S)" >>"$LOG"
    break
  fi
  sleep 30
done

echo "--- merge $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/merge_proposals.py data/proposals-lang4.csv data/proposals-lang4-0.csv data/proposals-lang4-1.csv data/proposals-lang4-2.csv >>"$LOG" 2>&1
echo "--- apply $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/apply_missing.py --prop data/proposals-lang4.csv --review data/review-lang4.csv >>"$LOG" 2>&1
echo "--- coverage $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/coverage.py >>"$LOG" 2>&1
echo "--- done $(date +%H:%M:%S)" >>"$LOG"
