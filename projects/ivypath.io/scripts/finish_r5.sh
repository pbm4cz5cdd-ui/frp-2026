#!/bin/bash
# Wait for the three deeper UK/Canada/USA crawlers, then merge, apply and report.
# Run with setsid so it keeps going after the session ends.
cd "$(dirname "$0")/.." || exit 1

PIDS=$(cat data/r5.pids)
LOG=data/finish-r5.log

echo "start $(date +%H:%M:%S), waiting for: $PIDS" >>"$LOG"
for i in $(seq 1 480); do
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
python3 -I scripts/merge_proposals.py data/proposals-r5.csv data/proposals-r5-0.csv data/proposals-r5-1.csv data/proposals-r5-2.csv >>"$LOG" 2>&1
echo "--- apply $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/apply_missing.py --prop data/proposals-r5.csv --review data/review-r5.csv >>"$LOG" 2>&1
echo "--- coverage $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/coverage.py >>"$LOG" 2>&1
echo "--- done $(date +%H:%M:%S)" >>"$LOG"
