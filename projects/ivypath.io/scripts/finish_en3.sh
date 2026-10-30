#!/bin/bash
# Wait for the three UK/USA/Canada/HK language crawlers AND for both China
# finishers, then merge, apply and report. Waiting for the China finishers
# matters: two apply runs at once would write the same rows twice.
# Run with setsid so it keeps going after the session ends.
cd "$(dirname "$0")/.." || exit 1

PIDS="1684577 1684578 1684579"
OTHER="1664558 1664967"
LOG=data/finish-en3.log

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
python3 -I scripts/merge_proposals.py data/proposals-en3.csv data/proposals-en3-0.csv data/proposals-en3-1.csv data/proposals-en3-2.csv >>"$LOG" 2>&1
echo "--- apply $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/apply_missing.py --prop data/proposals-en3.csv --review data/review-en3.csv >>"$LOG" 2>&1
echo "--- coverage $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/coverage.py >>"$LOG" 2>&1
echo "--- done $(date +%H:%M:%S)" >>"$LOG"
