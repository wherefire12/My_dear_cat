#!/bin/bash
cd "$(dirname "$0")"
for w in "$@"; do for k in 1 2 3; do out=$(nice -n 19 python3 repair_frames.py scan "$w" 2>&1 | tail -1); echo "pass $k: $out" | cut -c1-120; case "$out" in *": 0/"*) break;; esac; nice -n 19 python3 repair_frames.py repair "$w" > /dev/null 2>&1; done; done
echo REPAIR DONE
