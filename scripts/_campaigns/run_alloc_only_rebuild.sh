#!/usr/bin/env bash
# Rebuild the allocation-only campaign on the CORRECTED scenario parameters.
#
# Why: results/stats/f58_allocation_only{,_3r15t,_10r50t}/ were produced on
# 2026-06-29, before the scenario definitions were aligned with the paper
# (deadline budgets were U[200,400] s where the design specifies U[36,120] s).
# They report fitness 1.000 / DVR 0.000 in every cell, which contradicts the
# rebuilt perfect-navigation plane of tab:fitness (0.840 at 5r/25t deadline
# pressure).  tab:allocation and the first paragraph of sec:results-sim rest on
# the stale numbers.  See results/README.md.
#
# This driver waits for the fixed-spatial Gazebo arm to finish before it starts,
# so it never competes with the campaign for CPU.
#
# Usage:  nohup bash run_alloc_only_rebuild.sh > results/alloc_rebuild.log 2>&1 &

set -u
REPO="/home/oguz/multi_ahe"
cd "$REPO" || exit 1

ARM5_DONE_DIR="$REPO/results/raw/gazebo_ablation/fixed-spatial"
ARM5_TARGET=60
MAX_WAIT_S=$((12 * 3600))
LOAD_CEILING=5

log() { printf '[%s] %s\n' "$(date '+%F %T')" "$*"; }

# ── 1. Wait for the Gazebo arm ───────────────────────────────────────────────
# Gate on the DONE *count*, never on a process pattern: a `pgrep -f <pattern>`
# wait matches its own wrapper's command line and blocks forever (this has bitten
# us three times; see CLAUDE.md).
log "waiting for fixed-spatial arm: target ${ARM5_TARGET} DONE"
waited=0
while :; do
    done_n=$(find "$ARM5_DONE_DIR" -name DONE 2>/dev/null | wc -l)
    [ "$done_n" -ge "$ARM5_TARGET" ] && { log "arm complete: ${done_n}/${ARM5_TARGET}"; break; }
    if [ "$waited" -ge "$MAX_WAIT_S" ]; then
        log "GIVING UP: still ${done_n}/${ARM5_TARGET} after $((MAX_WAIT_S/3600))h."
        log "The arm probably died. Check results/arm5.log, then re-run this script."
        exit 1
    fi
    sleep 120
    waited=$((waited + 120))
    [ $((waited % 1800)) -eq 0 ] && log "  ... ${done_n}/${ARM5_TARGET} (${waited}s waited)"
done

# The last experiment's teardown outlives its DONE file; let the box settle.
log "waiting for load to fall below ${LOAD_CEILING}"
for _ in $(seq 1 60); do
    load1=$(cut -d' ' -f1 /proc/loadavg)
    awk -v l="$load1" -v c="$LOAD_CEILING" 'BEGIN{exit !(l<c)}' && break
    sleep 30
done
log "load now $(cut -d' ' -f1-3 /proc/loadavg)"

# ── 2. Rebuild the three cells ───────────────────────────────────────────────
# --variant f58 sets AHE_F58_GEODESIC / AHE_SIM_GEODESIC_EXECUTION internally,
# so the Euclidean-oracle trap does not apply here.  validate_f45_allocation.py
# calls sim.benchmark() directly and writes only to --output-dir, so the
# canonical processed/sim_fitness.csv is NOT clobbered.
run_cell() {
    local robots=$1 tasks=$2 outdir=$3
    log "cell ${robots}r/${tasks}t -> results/stats/${outdir}"
    python3 scripts/validate_f45_allocation.py \
        --mode allocation-only --variant f58 \
        --robots "$robots" --tasks "$tasks" --seeds 100 --seed-start 1 \
        --output-dir "results/stats/${outdir}" || {
            log "FAILED on ${robots}r/${tasks}t"; return 1; }
}

mkdir -p "$REPO/results/_backup_alloc_stale_20260802"
for d in f58_allocation_only f58_allocation_only_3r15t f58_allocation_only_10r50t; do
    [ -d "results/stats/$d" ] && cp -r "results/stats/$d" \
        "$REPO/results/_backup_alloc_stale_20260802/$d"
done
log "stale campaign backed up to results/_backup_alloc_stale_20260802/"

run_cell 3 15 f58_allocation_only_3r15t  || exit 1
run_cell 5 25 f58_allocation_only        || exit 1
run_cell 10 50 f58_allocation_only_10r50t || exit 1

# ── 3. Regenerate tab:allocation (both languages) ────────────────────────────
log "regenerating paper/table/allocation_only{,_tr}.tex"
python3 scripts/make_allocation_table.py || exit 1

# ── 4. Report what changed, so the prose can be written against it ───────────
log "=== NEW allocation-only numbers (AHE-MRTA) ==="
python3 - <<'PY'
import pandas as pd, pathlib
for label, d in (('3r/15t', 'f58_allocation_only_3r15t'),
                 ('5r/25t', 'f58_allocation_only'),
                 ('10r/50t', 'f58_allocation_only_10r50t')):
    p = pathlib.Path('results/stats')/d/'summary.csv'
    if not p.exists():
        print(f'{label}: MISSING'); continue
    f = pd.read_csv(p)
    a = f[f.strategy == 'ahe_mrta_v3']
    for r in a.itertuples(index=False):
        print(f'{label:8s} {r.scenario:18s} fitness={r.alloc_fitness:.3f} '
              f'CR={r.completion_rate:.3f} DVR={r.deadline_violation_rate:.3f} '
              f'JainAct={r.workload_balance_active:.3f} '
              f'dist={r.total_distance:.1f} lat={r.mean_decision_latency_ms:.3f}ms')
PY

cat <<'EOF'

────────────────────────────────────────────────────────────────────────────
STILL NEEDS A HUMAN (or a session with judgement):

1. sec:results-sim first paragraph, BOTH languages, currently asserts
   "fitness = CR = 1 and DVR = 0 in all nine cells" and "this setting does not
   separate the leading policies".  Rewrite against the numbers printed above.
   EN  paper/main.tex    ~line 965   TR  paper/main_tr.tex  ~line 977
   The two are line-parallel; keep them so.

2. Limitation (v) leans on the same claim ("the navigation-independent setting
   confirms the allocation policy itself scales further") -- check it still holds.

3. The fifth Gazebo arm (fixed-spatial) is now complete but
   scripts/analyze_ablation.py does NOT include it in ARMS.  It has to be
   analysed separately as an exploratory arm and added to sec:gazebo-ablation,
   which sec:ablation already forward-references in both languages.

4. Limitation (xii)'s priority-factor A/B (results/processed/ab_prio_*.csv,
   2026-07-30) is stale for the same reason, but NO script in the repo produces
   it -- it was an ad-hoc run.  It needs to be re-derived by hand.

5. Recompile both PDFs:  pdflatex + bibtex + pdflatex x2, EN and TR separately.
────────────────────────────────────────────────────────────────────────────
EOF
log "done"
