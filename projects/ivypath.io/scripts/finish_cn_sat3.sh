#!/bin/bash
# Wait for the three China SAT crawlers AND for the China language finisher,
# then merge, verify, apply and report. Waiting for the other finisher matters:
# two writers on universities.csv at once would write the same rows twice.
# Run with setsid so it keeps going after the session ends.
cd "$(dirname "$0")/.." || exit 1

PIDS="1664866 1664867 1664868"
OTHER=1664558
LOG=data/finish-cn-sat3.log

echo "start $(date +%H:%M:%S), waiting for: $PIDS and $OTHER" >>"$LOG"
for i in $(seq 1 480); do
  alive=""
  for p in $PIDS $OTHER; do
    if kill -0 "$p" 2>/dev/null; then alive="$alive $p"; fi
  done
  if [ -z "$alive" ]; then
    echo "all finished $(date +%H:%M:%S)" >>"$LOG"
    break
  fi
  sleep 30
done

echo "--- merge $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/merge_proposals.py data/proposals-cnsat3.csv data/proposals-cnsat3-0.csv data/proposals-cnsat3-1.csv data/proposals-cnsat3-2.csv >>"$LOG" 2>&1
echo "--- verify $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/verify_cn_sat.py data/proposals-cnsat3.csv data/verified-cnsat3.csv data/review-cnsat3.csv >>"$LOG" 2>&1
echo "--- apply $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/apply_cn_sat.py data/verified-cnsat3.csv >>"$LOG" 2>&1
echo "--- coverage $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/coverage.py >>"$LOG" 2>&1
echo "--- done $(date +%H:%M:%S)" >>"$LOG"
