#!/usr/bin/env bash
# Re-run the F59 priority-cost A/B (Limitation xii) on the corrected scenarios.
#
# Third in the chain, and deliberately last: it is ~50 minutes of one core
# (measured: 10 seeds = 60 s, so 500 seeds ~= 50 min).  It waits for BOTH the
# Gazebo arm and the allocation-only rebuild, so at no point are two CPU-heavy
# jobs running against each other.
#
#   arm5 (Gazebo, ~18:20)  ->  run_alloc_only_rebuild.sh  ->  this
#
# Usage:  nohup bash run_prio_ab_when_ready.sh > results/prio_ab.log 2>&1 &

set -u
REPO="/home/oguz/multi_ahe"
cd "$REPO" || exit 1

ARM_DIR="$REPO/results/raw/gazebo_ablation/fixed-spatial"
ARM_TARGET=60
REBUILD_LOG="$REPO/results/alloc_rebuild.log"
MAX_WAIT_S=$((14 * 3600))
SEEDS=500

log() { printf '[%s] %s\n' "$(date '+%F %T')" "$*"; }

# ── 1. Wait for the Gazebo arm (DONE count, never a process pattern) ─────────
log "waiting for fixed-spatial: target ${ARM_TARGET} DONE"
waited=0
while :; do
    n=$(find "$ARM_DIR" -name DONE 2>/dev/null | wc -l)
    [ "$n" -ge "$ARM_TARGET" ] && { log "arm complete: ${n}/${ARM_TARGET}"; break; }
    if [ "$waited" -ge "$MAX_WAIT_S" ]; then
        log "GIVING UP on the arm: ${n}/${ARM_TARGET} — check results/arm5.log"; exit 1
    fi
    sleep 120; waited=$((waited + 120))
done

# ── 2. Wait for the allocation-only rebuild to be out of the way ─────────────
# Two independent signals, because neither alone is airtight: the log's terminal
# marker can be missing if the rebuild dies inside a python call, and a process
# check alone is the self-match trap.  The pattern below is only ever in this
# FILE, never in this script's own command line, so pgrep cannot match itself.
log "waiting for the allocation-only rebuild to finish"
waited=0
while :; do
    if [ -f "$REBUILD_LOG" ] && grep -qE '\] done$|GIVING UP|FAILED on' "$REBUILD_LOG"; then
        log "rebuild reached a terminal state"; break
    fi
    if ! pgrep -f "run_alloc_only_rebuil[d]" >/dev/null 2>&1; then
        log "rebuild process is gone"; break
    fi
    if [ "$waited" -ge "$MAX_WAIT_S" ]; then
        log "GIVING UP waiting on the rebuild — check ${REBUILD_LOG}"; exit 1
    fi
    sleep 60; waited=$((waited + 60))
done

# Let the box settle before a 50-minute single-core job.
for _ in $(seq 1 40); do
    load1=$(cut -d' ' -f1 /proc/loadavg)
    awk -v l="$load1" 'BEGIN{exit !(l<5)}' && break
    sleep 30
done
log "load now $(cut -d' ' -f1-3 /proc/loadavg)"

# ── 3. Preserve the stale outputs before overwriting them ───────────────────
BACKUP="$REPO/results/_backup_ab_prio_stale_20260802"
mkdir -p "$BACKUP"
for f in "$REPO"/results/processed/ab_prio_*.csv; do
    [ -f "$f" ] && cp "$f" "$BACKUP/"
done
log "stale A/B backed up to ${BACKUP}/"

# ── 4. Run it ───────────────────────────────────────────────────────────────
log "running the ${SEEDS}-seed paired A/B (~50 min)"
python3 scripts/validate_priority_cost_ab.py --seeds "$SEEDS" \
    | tee "$REPO/results/prio_ab_result.txt"
rc=${PIPESTATUS[0]}
if [ "$rc" -ne 0 ]; then
    log "A/B FAILED (rc=${rc}) — if it says VOID, a baseline moved between arms"
    log "and the harness, not the priority factor, is what differs."
    exit 1
fi

log "done — results/prio_ab_result.txt has the sentence for Limitation (xii)"
log "Update that paragraph in BOTH paper/main.tex and paper/main_tr.tex,"
log "then recompile. If the deltas grew or the p-values shrank, the claim that"
log "the artefact is not measurable in the reported outcomes must be dropped."
