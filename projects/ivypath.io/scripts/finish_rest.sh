#!/bin/bash
# Wait for the background crawlers, then merge, apply and report coverage.
# Started with setsid so it keeps running after the session ends.
cd "$(dirname "$0")/.." || exit 1

PIDS="1420525 1420526 1420527 1420528 1420529 1420530 1420531 1420532 1420533 1420534 1420535 1420536"
LOG=data/finish-rest.log

echo "start $(date +%H:%M:%S), waiting for: $PIDS"
for i in $(seq 1 240); do
  alive=""
  for p in $PIDS; do
    if kill -0 "$p" 2>/dev/null; then alive="$alive $p"; fi
  done
  if [ -z "$alive" ]; then
    echo "all crawlers finished $(date +%H:%M:%S)"
    break
  fi
  sleep 30
done

echo "--- proposals before merge $(date +%H:%M:%S)"
wc -l data/proposals-west-*.csv data/proposals-china-*.csv 2>/dev/null

python3 scripts/merge_proposals.py data/proposals-rest-autorun.csv \
  data/proposals-west-*.csv data/proposals-china-*.csv >>"$LOG" 2>&1

echo "--- apply $(date +%H:%M:%S)"
python3 scripts/apply_missing.py --prop data/proposals-rest-autorun.csv >>"$LOG" 2>&1

echo "--- coverage $(date +%H:%M:%S)"
python3 scripts/coverage.py >>"$LOG" 2>&1

echo "--- done $(date +%H:%M:%S)"
