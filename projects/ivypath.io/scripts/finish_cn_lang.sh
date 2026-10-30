#!/bin/bash
# Wait for the four China IELTS/TOEFL crawlers, then merge, apply and report.
# Run with setsid so it keeps going after the session ends.
cd "$(dirname "$0")/.." || exit 1

PIDS="1542140 1542141 1542142 1542143"
LOG=data/finish-cn-lang.log

echo "start $(date +%H:%M:%S), waiting for: $PIDS" >>"$LOG"
for i in $(seq 1 480); do
  alive=""
  for p in $PIDS; do
    if kill -0 "$p" 2>/dev/null; then alive="$alive $p"; fi
  done
  if [ -z "$alive" ]; then
    echo "all crawlers finished $(date +%H:%M:%S)" >>"$LOG"
    break
  fi
  sleep 30
done

echo "--- headers $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/fix_cn_headers.py data/proposals-cn-lang-0.csv data/proposals-cn-lang-1.csv data/proposals-cn-lang-2.csv data/proposals-cn-lang-3.csv >>"$LOG" 2>&1
echo "--- merge $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/merge_proposals.py data/proposals-cn-lang.csv data/proposals-cn-lang-0.csv data/proposals-cn-lang-1.csv data/proposals-cn-lang-2.csv data/proposals-cn-lang-3.csv >>"$LOG" 2>&1
echo "--- apply $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/apply_missing.py --prop data/proposals-cn-lang.csv --review data/review-cn-lang.csv >>"$LOG" 2>&1
echo "--- coverage $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/coverage.py >>"$LOG" 2>&1
echo "--- done $(date +%H:%M:%S)" >>"$LOG"
