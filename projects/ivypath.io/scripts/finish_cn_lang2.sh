#!/bin/bash
# Wait for the four China IELTS/TOEFL crawlers (second pass), then merge,
# apply and report. Run with setsid so it keeps going after the session ends.
cd "$(dirname "$0")/.." || exit 1

PIDS="1664129 1664165 1664186 1664206"
LOG=data/finish-cn-lang2.log

echo "start $(date +%H:%M:%S), waiting for: $PIDS" >>"$LOG"
for i in $(seq 1 240); do
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
python3 -I scripts/fix_cn_headers.py data/proposals-cn-lang2-0.csv data/proposals-cn-lang2-1.csv data/proposals-cn-lang2-2.csv data/proposals-cn-lang2-3.csv >>"$LOG" 2>&1
echo "--- merge $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/merge_proposals.py data/proposals-cn-lang2.csv data/proposals-cn-lang2-0.csv data/proposals-cn-lang2-1.csv data/proposals-cn-lang2-2.csv data/proposals-cn-lang2-3.csv >>"$LOG" 2>&1
echo "--- apply $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/apply_missing.py --prop data/proposals-cn-lang2.csv --review data/review-cn-lang2.csv >>"$LOG" 2>&1
echo "--- coverage $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/coverage.py >>"$LOG" 2>&1
echo "--- done $(date +%H:%M:%S)" >>"$LOG"
