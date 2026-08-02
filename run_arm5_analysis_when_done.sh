#!/usr/bin/env bash
# Run the exploratory fifth-arm analysis as soon as the arm completes.
#
# Deliberately a SECOND watcher rather than an edit to run_alloc_only_rebuild.sh:
# bash reads a script incrementally while executing it, so editing a running
# script can make it execute garbage.  The two watchers are independent and both
# gate on the same DONE count.
#
# Usage:  nohup bash run_arm5_analysis_when_done.sh > results/arm5_analysis.log 2>&1 &

set -u
REPO="/home/oguz/multi_ahe"
cd "$REPO" || exit 1

ARM_DIR="$REPO/results/raw/gazebo_ablation/fixed-spatial"
TARGET=60
MAX_WAIT_S=$((12 * 3600))

log() { printf '[%s] %s\n' "$(date '+%F %T')" "$*"; }

# Gate on the DONE count, never on a process pattern (self-match trap; CLAUDE.md).
log "waiting for fixed-spatial: target ${TARGET} DONE"
waited=0
while :; do
    n=$(find "$ARM_DIR" -name DONE 2>/dev/null | wc -l)
    [ "$n" -ge "$TARGET" ] && { log "arm complete: ${n}/${TARGET}"; break; }
    if [ "$waited" -ge "$MAX_WAIT_S" ]; then
        log "GIVING UP: still ${n}/${TARGET} after $((MAX_WAIT_S/3600))h — check results/arm5.log"
        exit 1
    fi
    sleep 120
    waited=$((waited + 120))
    [ $((waited % 1800)) -eq 0 ] && log "  ... ${n}/${TARGET}"
done

# The analysis is a few seconds of one core; no load gate needed.
log "running exploratory analysis"
python3 scripts/analyze_arm5_exploratory.py || { log "analysis FAILED"; exit 1; }

# The registered four-arm analysis is unaffected by this arm, but re-run it so
# tab:gazebo-ablation reflects any late-arriving seeds in the registered arms.
log "re-running the registered four-arm analysis (unchanged arms, refreshes tab:gazebo-ablation)"
python3 scripts/analyze_ablation.py > results/ablation_analysis.txt 2>&1 \
    && log "  -> results/ablation_analysis.txt" \
    || log "  registered analysis reported a problem — read results/ablation_analysis.txt"

log "done — read results/arm5_exploratory.txt, then write the sec:gazebo-ablation paragraph (EN + TR)"
