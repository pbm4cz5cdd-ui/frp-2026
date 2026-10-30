#!/bin/bash
# Wait for the two UK SAT crawlers AND for the earlier language finishers,
# then merge, verify, apply and report. Waiting for the other finishers
# matters: two apply runs at once would write the same rows twice.
# Run with setsid so it keeps going after the session ends.
cd "$(dirname "$0")/.." || exit 1

PIDS="1684926 1684927"
OTHER="1684716"
LOG=data/finish-uk-sat3.log

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
python3 -I scripts/merge_proposals.py data/proposals-uksat3.csv data/proposals-uksat3-0.csv data/proposals-uksat3-1.csv >>"$LOG" 2>&1
echo "--- verify $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/verify_uk_sat.py data/proposals-uksat3.csv data/verified-uksat3.csv >>"$LOG" 2>&1
echo "--- apply $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/apply_uk_sat.py data/verified-uksat3.csv >>"$LOG" 2>&1
echo "--- coverage $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/coverage.py >>"$LOG" 2>&1
echo "--- done $(date +%H:%M:%S)" >>"$LOG"
