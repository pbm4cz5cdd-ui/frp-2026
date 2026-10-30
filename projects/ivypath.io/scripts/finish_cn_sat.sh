#!/bin/bash
# Wait for the four China SAT crawlers AND for the IELTS finisher, then merge,
# apply and report. Waiting for the other finisher matters: two apply_missing
# runs at once would write the same rows twice.
# Run with setsid so it keeps going after the session ends.
cd "$(dirname "$0")/.." || exit 1

PIDS="1503677 1503680 1503684 1503686"
OTHER=1499778
LOG=data/finish-cn-sat.log

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

echo "--- headers $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/fix_cn_headers.py data/proposals-cn-sat-0.csv data/proposals-cn-sat-1.csv data/proposals-cn-sat-2.csv data/proposals-cn-sat-3.csv >>"$LOG" 2>&1
echo "--- merge $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/merge_proposals.py data/proposals-cn-sat.csv data/proposals-cn-sat-0.csv data/proposals-cn-sat-1.csv data/proposals-cn-sat-2.csv data/proposals-cn-sat-3.csv >>"$LOG" 2>&1
echo "--- apply $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/apply_missing.py --prop data/proposals-cn-sat.csv --review data/review-cn-sat.csv >>"$LOG" 2>&1
echo "--- coverage $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/coverage.py >>"$LOG" 2>&1
echo "--- done $(date +%H:%M:%S)" >>"$LOG"
