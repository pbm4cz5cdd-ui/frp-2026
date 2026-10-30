#!/bin/bash
# Wait for the four China crawlers AND for the English-language finisher,
# then merge, apply and report. Waiting for the other finisher matters: two
# apply runs at once would write the same rows twice.
# Run with setsid so it keeps going after the session ends.
cd "$(dirname "$0")/.." || exit 1

PIDS=$(cat data/cn-lang3.pids)
OTHER=$(cat data/lang4.pids)
FINISHER="$1"
LOG=data/finish-cn-lang3.log

echo "start $(date +%H:%M:%S), waiting for: $PIDS, $OTHER and finisher $FINISHER" >>"$LOG"
for i in $(seq 1 240); do
  alive=""
  for p in $PIDS $OTHER; do
    if kill -0 "$p" 2>/dev/null; then alive="$alive $p"; fi
  done
  if [ -n "$FINISHER" ] && kill -0 "$FINISHER" 2>/dev/null; then
    alive="$alive $FINISHER"
  fi
  if [ -z "$alive" ]; then
    echo "all finished $(date +%H:%M:%S)" >>"$LOG"
    break
  fi
  sleep 30
done

echo "--- headers $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/fix_cn_headers.py data/proposals-cn-lang3-0.csv data/proposals-cn-lang3-1.csv data/proposals-cn-lang3-2.csv data/proposals-cn-lang3-3.csv >>"$LOG" 2>&1
echo "--- merge $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/merge_proposals.py data/proposals-cn-lang3.csv data/proposals-cn-lang3-0.csv data/proposals-cn-lang3-1.csv data/proposals-cn-lang3-2.csv data/proposals-cn-lang3-3.csv >>"$LOG" 2>&1
echo "--- apply $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/apply_missing.py --prop data/proposals-cn-lang3.csv --review data/review-cn-lang3.csv >>"$LOG" 2>&1
echo "--- coverage $(date +%H:%M:%S)" >>"$LOG"
python3 -I scripts/coverage.py >>"$LOG" 2>&1
echo "--- done $(date +%H:%M:%S)" >>"$LOG"
