#!/bin/bash
# Wait for the two Canada SAT crawlers, then merge, verify, apply and report.
# Run with setsid so it keeps going after the session ends.
cd "$(dirname "$0")/.." || exit 1

PIDS="1708063 1708064"
LOG=data/finish-can-sat.log

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
python3 -I scripts/merge_proposals.py data/proposals-cansat.csv data/proposals-cansat-0.csv data/proposals-cansat-1.csv >>"$LOG" 2>&1
echo "--- verify $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/verify_cn_sat.py data/proposals-cansat.csv data/verified-cansat.csv data/review-cansat.csv >>"$LOG" 2>&1
echo "--- apply $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/apply_cn_sat.py data/verified-cansat.csv >>"$LOG" 2>&1
echo "--- coverage $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/coverage.py >>"$LOG" 2>&1
echo "--- done $(date +%H:%M:%S)" >>"$LOG"
