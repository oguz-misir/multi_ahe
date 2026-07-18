#!/usr/bin/env bash
# Fresh, paired F45/F58 Nav2+Gazebo campaign. Existing paper data is untouched.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

PROFILE="${1:-pilot}"
RESULTS_ROOT="${F58_RESULTS_ROOT:-$REPO/results/raw/gazebo_f58_validation}"
PROCESSED_ROOT="${F58_PROCESSED_ROOT:-$REPO/results/processed/gazebo_f58_validation}"
STATS_ROOT="${F58_STATS_ROOT:-$REPO/results/stats/gazebo_f58_validation}"
STARTUP="${F58_STARTUP:-120.0}"
TIMEOUT="${F58_TIMEOUT:-1200}"
CANDIDATE_ONLY=0
REFERENCE_OVERRIDE=""
F58_RESERVATION_GAP="${AHE_F58_FAIR_RESERVATION_GAP:-2}"
F58_EXTRA_QUEUE="${AHE_F58_FAIR_EXTRA_QUEUE:-1}"
F58_FAIR_REPAIR="${AHE_F58_FAIR_REPAIR:-1}"
F58_TERMINAL_FACTOR="${AHE_F58_FAIR_TERMINAL_TASKS_PER_ROBOT:-3}"

case "$PROFILE" in
    smoke)
        SCALES="3:15"; SEEDS="1"; COMBOS="ahe_mrta_v3 robot_failure" ;;
    smoke_p1b)
        # Isolated post-F32 repair/cache candidate; never mixes with the
        # completed P0/P1 paper campaign.
        RESULTS_ROOT="${F58_RESULTS_ROOT:-$REPO/results/raw/gazebo_f58_p1b_validation}"
        PROCESSED_ROOT="${F58_PROCESSED_ROOT:-$REPO/results/processed/gazebo_f58_p1b_validation}"
        STATS_ROOT="${F58_STATS_ROOT:-$REPO/results/stats/gazebo_f58_p1b_validation}"
        SCALES="3:15"; SEEDS="1"; COMBOS="ahe_mrta_v3 robot_failure" ;;
    pilot_p1b)
        RESULTS_ROOT="${F58_RESULTS_ROOT:-$REPO/results/raw/gazebo_f58_p1b_validation}"
        PROCESSED_ROOT="${F58_PROCESSED_ROOT:-$REPO/results/processed/gazebo_f58_p1b_validation}"
        STATS_ROOT="${F58_STATS_ROOT:-$REPO/results/stats/gazebo_f58_p1b_validation}"
        SCALES="3:15"; SEEDS="1 2 3"
        COMBOS="ahe_mrta_v3 robot_failure" ;;
    smoke5_p1b)
        RESULTS_ROOT="${F58_RESULTS_ROOT:-$REPO/results/raw/gazebo_f58_p1b_validation}"
        PROCESSED_ROOT="${F58_PROCESSED_ROOT:-$REPO/results/processed/gazebo_f58_p1b_validation}"
        STATS_ROOT="${F58_STATS_ROOT:-$REPO/results/stats/gazebo_f58_p1b_validation}"
        SCALES="5:25"; SEEDS="1"
        COMBOS="ahe_mrta_v3 robot_failure" ;;
    smoke5_p1e)
        RESULTS_ROOT="${F58_RESULTS_ROOT:-$REPO/results/raw/gazebo_f58_p1e_validation}"
        PROCESSED_ROOT="${F58_PROCESSED_ROOT:-$REPO/results/processed/gazebo_f58_p1e_validation}"
        STATS_ROOT="${F58_STATS_ROOT:-$REPO/results/stats/gazebo_f58_p1e_validation}"
        SCALES="5:25"; SEEDS="1"
        COMBOS="ahe_mrta_v3 robot_failure" ;;
    smoke5_p1g)
        RESULTS_ROOT="${F58_RESULTS_ROOT:-$REPO/results/raw/gazebo_f58_p1g_validation}"
        PROCESSED_ROOT="${F58_PROCESSED_ROOT:-$REPO/results/processed/gazebo_f58_p1g_validation}"
        STATS_ROOT="${F58_STATS_ROOT:-$REPO/results/stats/gazebo_f58_p1g_validation}"
        SCALES="5:25"; SEEDS="1"
        COMBOS="ahe_mrta_v3 robot_failure" ;;
    pilot5_p1h)
        RESULTS_ROOT="${F58_RESULTS_ROOT:-$REPO/results/raw/gazebo_f58_p1h_validation}"
        PROCESSED_ROOT="${F58_PROCESSED_ROOT:-$REPO/results/processed/gazebo_f58_p1h_validation}"
        STATS_ROOT="${F58_STATS_ROOT:-$REPO/results/stats/gazebo_f58_p1h_validation}"
        SCALES="5:25"; SEEDS="1 2 3"
        COMBOS="ahe_mrta_v3 robot_failure" ;;
    pilot5_p1i)
        RESULTS_ROOT="${F58_RESULTS_ROOT:-$REPO/results/raw/gazebo_f58_p1i_validation}"
        PROCESSED_ROOT="${F58_PROCESSED_ROOT:-$REPO/results/processed/gazebo_f58_p1i_validation}"
        STATS_ROOT="${F58_STATS_ROOT:-$REPO/results/stats/gazebo_f58_p1i_validation}"
        CANDIDATE_ONLY=1
        REFERENCE_OVERRIDE="$REPO/results/raw/gazebo_f58_p1h_validation/f45"
        F58_RESERVATION_GAP=1
        SCALES="5:25"; SEEDS="1 2 3"
        COMBOS="ahe_mrta_v3 robot_failure" ;;
    smoke5_p1j)
        RESULTS_ROOT="${F58_RESULTS_ROOT:-$REPO/results/raw/gazebo_f58_p1j_validation}"
        PROCESSED_ROOT="${F58_PROCESSED_ROOT:-$REPO/results/processed/gazebo_f58_p1j_validation}"
        STATS_ROOT="${F58_STATS_ROOT:-$REPO/results/stats/gazebo_f58_p1j_validation}"
        CANDIDATE_ONLY=1
        REFERENCE_OVERRIDE="$REPO/results/raw/gazebo_f58_p1h_validation/f45"
        F58_RESERVATION_GAP=1
        F58_EXTRA_QUEUE=2
        SCALES="5:25"; SEEDS="1"
        COMBOS="ahe_mrta_v3 robot_failure" ;;
    smoke5_p1k)
        RESULTS_ROOT="${F58_RESULTS_ROOT:-$REPO/results/raw/gazebo_f58_p1k_validation}"
        PROCESSED_ROOT="${F58_PROCESSED_ROOT:-$REPO/results/processed/gazebo_f58_p1k_validation}"
        STATS_ROOT="${F58_STATS_ROOT:-$REPO/results/stats/gazebo_f58_p1k_validation}"
        CANDIDATE_ONLY=1
        REFERENCE_OVERRIDE="$REPO/results/raw/gazebo_f58_p1h_validation/f45"
        F58_RESERVATION_GAP=2
        F58_EXTRA_QUEUE=1
        SCALES="5:25"; SEEDS="1"
        COMBOS="ahe_mrta_v3 robot_failure" ;;
    pilot5_p1k)
        RESULTS_ROOT="${F58_RESULTS_ROOT:-$REPO/results/raw/gazebo_f58_p1k_validation}"
        PROCESSED_ROOT="${F58_PROCESSED_ROOT:-$REPO/results/processed/gazebo_f58_p1k_validation}"
        STATS_ROOT="${F58_STATS_ROOT:-$REPO/results/stats/gazebo_f58_p1k_validation}"
        CANDIDATE_ONLY=1
        REFERENCE_OVERRIDE="$REPO/results/raw/gazebo_f58_p1h_validation/f45"
        F58_RESERVATION_GAP=2
        F58_EXTRA_QUEUE=1
        SCALES="5:25"; SEEDS="1 2 3"
        COMBOS="ahe_mrta_v3 robot_failure" ;;
    smoke5_p1l)
        RESULTS_ROOT="${F58_RESULTS_ROOT:-$REPO/results/raw/gazebo_f58_p1l_validation}"
        PROCESSED_ROOT="${F58_PROCESSED_ROOT:-$REPO/results/processed/gazebo_f58_p1l_validation}"
        STATS_ROOT="${F58_STATS_ROOT:-$REPO/results/stats/gazebo_f58_p1l_validation}"
        CANDIDATE_ONLY=1
        REFERENCE_OVERRIDE="$REPO/results/raw/gazebo_f58_p1h_validation/f45"
        F58_RESERVATION_GAP=2
        F58_EXTRA_QUEUE=1
        SCALES="5:25"; SEEDS="1"
        COMBOS="ahe_mrta_v3 robot_failure" ;;
    smoke5_p1m)
        # P1M validates the stale-current-task state-machine repair.  Run a
        # fresh F45 reference too: pre-lock semantics changed, so reusing an
        # older binary/source snapshot would not be a matched comparison.
        RESULTS_ROOT="${F58_RESULTS_ROOT:-$REPO/results/raw/gazebo_f58_p1m_validation}"
        PROCESSED_ROOT="${F58_PROCESSED_ROOT:-$REPO/results/processed/gazebo_f58_p1m_validation}"
        STATS_ROOT="${F58_STATS_ROOT:-$REPO/results/stats/gazebo_f58_p1m_validation}"
        F58_RESERVATION_GAP=2
        F58_EXTRA_QUEUE=1
        SCALES="5:25"; SEEDS="1"
        COMBOS="ahe_mrta_v3 robot_failure" ;;
    smoke5_p1n)
        # P1N adds authoritative completion/status race sanitisation.  P1M was
        # intentionally aborted after its invariant checker caught a ghost
        # reassignment, so use a new provenance root and fresh paired runs.
        RESULTS_ROOT="${F58_RESULTS_ROOT:-$REPO/results/raw/gazebo_f58_p1n_validation}"
        PROCESSED_ROOT="${F58_PROCESSED_ROOT:-$REPO/results/processed/gazebo_f58_p1n_validation}"
        STATS_ROOT="${F58_STATS_ROOT:-$REPO/results/stats/gazebo_f58_p1n_validation}"
        F58_RESERVATION_GAP=2
        F58_EXTRA_QUEUE=1
        SCALES="5:25"; SEEDS="1"
        COMBOS="ahe_mrta_v3 robot_failure" ;;
    smoke5_p1o)
        # P1O adds active-snapshot pruning plus a publication-boundary guard;
        # P1N was aborted when persistent queue memory resurrected a task.
        RESULTS_ROOT="${F58_RESULTS_ROOT:-$REPO/results/raw/gazebo_f58_p1o_validation}"
        PROCESSED_ROOT="${F58_PROCESSED_ROOT:-$REPO/results/processed/gazebo_f58_p1o_validation}"
        STATS_ROOT="${F58_STATS_ROOT:-$REPO/results/stats/gazebo_f58_p1o_validation}"
        F58_RESERVATION_GAP=2
        F58_EXTRA_QUEUE=1
        SCALES="5:25"; SEEDS="1"
        COMBOS="ahe_mrta_v3 robot_failure" ;;
    smoke5_p1o_retry)
        RESULTS_ROOT="${F58_RESULTS_ROOT:-$REPO/results/raw/gazebo_f58_p1o_validation}"
        PROCESSED_ROOT="${F58_PROCESSED_ROOT:-$REPO/results/processed/gazebo_f58_p1o_validation}"
        STATS_ROOT="${F58_STATS_ROOT:-$REPO/results/stats/gazebo_f58_p1o_validation}"
        CANDIDATE_ONLY=1
        REFERENCE_OVERRIDE="$REPO/results/raw/gazebo_f58_p1o_validation/f45"
        F58_RESERVATION_GAP=2
        F58_EXTRA_QUEUE=1
        SCALES="5:25"; SEEDS="1"
        COMBOS="ahe_mrta_v3 robot_failure" ;;
    pilot5_p1o)
        RESULTS_ROOT="${F58_RESULTS_ROOT:-$REPO/results/raw/gazebo_f58_p1o_validation}"
        PROCESSED_ROOT="${F58_PROCESSED_ROOT:-$REPO/results/processed/gazebo_f58_p1o_validation}"
        STATS_ROOT="${F58_STATS_ROOT:-$REPO/results/stats/gazebo_f58_p1o_validation}"
        F58_RESERVATION_GAP=2
        F58_EXTRA_QUEUE=1
        SCALES="5:25"; SEEDS="1 2 3"
        COMBOS="ahe_mrta_v3 robot_failure" ;;
    smoke5_p1p)
        # P1P ablation: retain the obstacle-aware oracle but disable the
        # queue-reservation repair that hurt physical delay/makespan in P1O.
        RESULTS_ROOT="${F58_RESULTS_ROOT:-$REPO/results/raw/gazebo_f58_p1p_validation}"
        PROCESSED_ROOT="${F58_PROCESSED_ROOT:-$REPO/results/processed/gazebo_f58_p1p_validation}"
        STATS_ROOT="${F58_STATS_ROOT:-$REPO/results/stats/gazebo_f58_p1p_validation}"
        CANDIDATE_ONLY=1
        REFERENCE_OVERRIDE="$REPO/results/raw/gazebo_f58_p1o_validation/f45"
        F58_FAIR_REPAIR=0
        SCALES="5:25"; SEEDS="1"
        COMBOS="ahe_mrta_v3 robot_failure" ;;
    smoke5_p1q)
        RESULTS_ROOT="${F58_RESULTS_ROOT:-$REPO/results/raw/gazebo_f58_p1q_validation}"
        PROCESSED_ROOT="${F58_PROCESSED_ROOT:-$REPO/results/processed/gazebo_f58_p1q_validation}"
        STATS_ROOT="${F58_STATS_ROOT:-$REPO/results/stats/gazebo_f58_p1q_validation}"
        CANDIDATE_ONLY=1
        REFERENCE_OVERRIDE="$REPO/results/raw/gazebo_f58_p1o_validation/f45"
        F58_FAIR_REPAIR=1
        F58_TERMINAL_FACTOR=2
        SCALES="5:25"; SEEDS="1"
        COMBOS="ahe_mrta_v3 robot_failure" ;;
    pilot5_p1q)
        RESULTS_ROOT="${F58_RESULTS_ROOT:-$REPO/results/raw/gazebo_f58_p1q_validation}"
        PROCESSED_ROOT="${F58_PROCESSED_ROOT:-$REPO/results/processed/gazebo_f58_p1q_validation}"
        STATS_ROOT="${F58_STATS_ROOT:-$REPO/results/stats/gazebo_f58_p1q_validation}"
        CANDIDATE_ONLY=1
        REFERENCE_OVERRIDE="$REPO/results/raw/gazebo_f58_p1o_validation/f45"
        F58_FAIR_REPAIR=1
        F58_TERMINAL_FACTOR=2
        SCALES="5:25"; SEEDS="1 2 3"
        COMBOS="ahe_mrta_v3 robot_failure" ;;
    smoke5_p1r)
        RESULTS_ROOT="${F58_RESULTS_ROOT:-$REPO/results/raw/gazebo_f58_p1r_validation}"
        PROCESSED_ROOT="${F58_PROCESSED_ROOT:-$REPO/results/processed/gazebo_f58_p1r_validation}"
        STATS_ROOT="${F58_STATS_ROOT:-$REPO/results/stats/gazebo_f58_p1r_validation}"
        CANDIDATE_ONLY=1
        REFERENCE_OVERRIDE="$REPO/results/raw/gazebo_f58_p1o_validation/f45"
        F58_FAIR_REPAIR=1
        F58_TERMINAL_FACTOR=3
        SCALES="5:25"; SEEDS="1"
        COMBOS="ahe_mrta_v3 robot_failure" ;;
    pilot5_p1r)
        RESULTS_ROOT="${F58_RESULTS_ROOT:-$REPO/results/raw/gazebo_f58_p1r_validation}"
        PROCESSED_ROOT="${F58_PROCESSED_ROOT:-$REPO/results/processed/gazebo_f58_p1r_validation}"
        STATS_ROOT="${F58_STATS_ROOT:-$REPO/results/stats/gazebo_f58_p1r_validation}"
        CANDIDATE_ONLY=1
        REFERENCE_OVERRIDE="$REPO/results/raw/gazebo_f58_p1o_validation/f45"
        F58_FAIR_REPAIR=1
        F58_TERMINAL_FACTOR=3
        SCALES="5:25"; SEEDS="1 2 3"
        COMBOS="ahe_mrta_v3 robot_failure" ;;
    smoke5_p1r_other)
        # Fresh, same-source references for the two still-unvalidated physical
        # scenarios.  Keep the accepted robot-failure campaign untouched.
        RESULTS_ROOT="${F58_RESULTS_ROOT:-$REPO/results/raw/gazebo_f58_p1r_other_validation}"
        PROCESSED_ROOT="${F58_PROCESSED_ROOT:-$REPO/results/processed/gazebo_f58_p1r_other_validation}"
        STATS_ROOT="${F58_STATS_ROOT:-$REPO/results/stats/gazebo_f58_p1r_other_validation}"
        F58_FAIR_REPAIR=1
        F58_TERMINAL_FACTOR=3
        SCALES="5:25"; SEEDS="1"
        COMBOS="ahe_mrta_v3 mixed_stress,ahe_mrta_v3 deadline_pressure" ;;
    pilot5_p1r_other)
        RESULTS_ROOT="${F58_RESULTS_ROOT:-$REPO/results/raw/gazebo_f58_p1r_other_validation}"
        PROCESSED_ROOT="${F58_PROCESSED_ROOT:-$REPO/results/processed/gazebo_f58_p1r_other_validation}"
        STATS_ROOT="${F58_STATS_ROOT:-$REPO/results/stats/gazebo_f58_p1r_other_validation}"
        F58_FAIR_REPAIR=1
        F58_TERMINAL_FACTOR=3
        SCALES="5:25"; SEEDS="1 2 3"
        COMBOS="ahe_mrta_v3 mixed_stress,ahe_mrta_v3 deadline_pressure" ;;
    pilot)
        SCALES="3:15"; SEEDS="1 2 3"
        COMBOS="ahe_mrta_v3 robot_failure" ;;
    pilot_all)
        SCALES="3:15"; SEEDS="1 2 3"
        COMBOS="ahe_mrta_v3 robot_failure,ahe_mrta_v3 mixed_stress,ahe_mrta_v3 deadline_pressure" ;;
    paper)
        SCALES="5:25"; SEEDS="1 2 3 4 5"
        COMBOS="ahe_mrta_v3 robot_failure,ahe_mrta_v3 mixed_stress,ahe_mrta_v3 deadline_pressure" ;;
    full)
        SCALES="3:15 5:25"; SEEDS="1 2 3 4 5"
        COMBOS="ahe_mrta_v3 robot_failure,ahe_mrta_v3 mixed_stress,ahe_mrta_v3 deadline_pressure" ;;
    paper_scale3)
        # 3r/15t matched scale cell for the n=10 pooled paper protocol.
        RESULTS_ROOT="${F58_RESULTS_ROOT:-$REPO/results/raw/gazebo_f58_scale3_validation}"
        PROCESSED_ROOT="${F58_PROCESSED_ROOT:-$REPO/results/processed/gazebo_f58_scale3_validation}"
        STATS_ROOT="${F58_STATS_ROOT:-$REPO/results/stats/gazebo_f58_scale3_validation}"
        SCALES="3:15"; SEEDS="1 2 3 4 5 6 7 8 9 10"
        COMBOS="ahe_mrta_v3 robot_failure,ahe_mrta_v3 mixed_stress,ahe_mrta_v3 deadline_pressure" ;;
    paper_scale10)
        # 10r/50t matched scale cell; 10-robot bringup needs the longer
        # startup/timeout the robust runner would otherwise auto-select.
        # 360s startup lost seeds under sustained load (9/10 Nav2 ready);
        # healthy missions measured 821-1464s wall, hence the 2400s cap.
        RESULTS_ROOT="${F58_RESULTS_ROOT:-$REPO/results/raw/gazebo_f58_scale10_validation}"
        PROCESSED_ROOT="${F58_PROCESSED_ROOT:-$REPO/results/processed/gazebo_f58_scale10_validation}"
        STATS_ROOT="${F58_STATS_ROOT:-$REPO/results/stats/gazebo_f58_scale10_validation}"
        STARTUP="${F58_STARTUP:-480.0}"
        TIMEOUT="${F58_TIMEOUT:-2400}"
        SCALES="10:50"; SEEDS="1 2 3 4 5 6 7 8 9 10"
        COMBOS="ahe_mrta_v3 robot_failure,ahe_mrta_v3 mixed_stress,ahe_mrta_v3 deadline_pressure" ;;
    *) echo "Usage: $0 {smoke|smoke_p1b|smoke5_p1b|smoke5_p1e|smoke5_p1g|pilot5_p1h|pilot5_p1i|smoke5_p1j|smoke5_p1k|pilot5_p1k|smoke5_p1l|smoke5_p1m|smoke5_p1n|smoke5_p1o|smoke5_p1o_retry|pilot5_p1o|smoke5_p1p|smoke5_p1q|pilot5_p1q|smoke5_p1r|pilot5_p1r|smoke5_p1r_other|pilot5_p1r_other|pilot|pilot_p1b|pilot_all|paper|full|paper_scale3|paper_scale10}" >&2; exit 2 ;;
esac

mkdir -p "$RESULTS_ROOT"
printf 'profile=%s\nseeds=%s\nscales=%s\ncombos=%s\n' \
    "$PROFILE" "$SEEDS" "$SCALES" "$COMBOS" > "$RESULTS_ROOT/campaign.conf"
git rev-parse HEAD > "$RESULTS_ROOT/git_commit.txt" 2>/dev/null || true
# Raw campaigns can contain tens of thousands of untracked CSV files.  They
# are already captured under RESULTS_ROOT; scanning them before every resume
# can stall launch for minutes.  Provenance here needs tracked source changes.
git status --short --untracked-files=no \
    > "$RESULTS_ROOT/working_tree_status.txt" 2>/dev/null || true
git diff -- src scripts tests paper > "$RESULTS_ROOT/working_tree.patch" 2>/dev/null || true
find src scripts tests -type f \( -name '*.py' -o -name '*.yaml' -o -name '*.sh' \) \
    -print0 | sort -z | xargs -0 sha256sum > "$RESULTS_ROOT/source_sha256.txt"

for scale in $SCALES; do
    robots="${scale%%:*}"; tasks="${scale##*:}"; tag="r${robots}t${tasks}"
    if [ "$CANDIDATE_ONLY" -eq 1 ]; then
        f45_dir="$REFERENCE_OVERRIDE/$tag"
    else
        f45_dir="$RESULTS_ROOT/f45/$tag"
    fi
    f58_dir="$RESULTS_ROOT/f58/$tag"
    processed_root="$PROCESSED_ROOT/$tag"
    stats_dir="$STATS_ROOT/$tag"

    if [ "$CANDIDATE_ONLY" -eq 0 ]; then
        AHE_F58_GEODESIC=0 AHE_F58_FAIR_REPAIR=0 \
          bash "$REPO/run_experiments_robust.sh" \
            --robots "$robots" --tasks "$tasks" --seeds "$SEEDS" \
            --combos "$COMBOS" --results-dir "$f45_dir" --skip-done 1 \
            --startup "$STARTUP" --timeout "$TIMEOUT"
    fi

    AHE_F58_GEODESIC=1 AHE_F58_FAIR_REPAIR="$F58_FAIR_REPAIR" \
      AHE_F58_FAIR_RESERVATION_GAP="$F58_RESERVATION_GAP" \
      AHE_F58_FAIR_EXTRA_QUEUE="$F58_EXTRA_QUEUE" \
      AHE_F58_FAIR_TERMINAL_TASKS_PER_ROBOT="$F58_TERMINAL_FACTOR" \
      bash "$REPO/run_experiments_robust.sh" \
        --robots "$robots" --tasks "$tasks" --seeds "$SEEDS" \
        --combos "$COMBOS" --results-dir "$f58_dir" --skip-done 1 \
        --startup "$STARTUP" --timeout "$TIMEOUT"

    python3 "$REPO/scripts/consolidate_results.py" \
        --raw-dir "$f45_dir" --processed-dir "$processed_root/f45"
    python3 "$REPO/scripts/consolidate_results.py" \
        --raw-dir "$f58_dir" --processed-dir "$processed_root/f58"
    python3 "$REPO/scripts/compare_f58_gazebo.py" \
        --reference-dir "$f45_dir" --candidate-dir "$f58_dir" \
        --output-dir "$stats_dir"
done

echo "F58 $PROFILE Gazebo+Nav2 validation complete: $RESULTS_ROOT"
