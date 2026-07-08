#!/usr/bin/env bash
# HISTORICAL/RETIRED: non-destructive Nav2+Gazebo validation for rejected F53.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

PROFILE="${1:-pilot}"
RESULTS_ROOT="${F53_RESULTS_ROOT:-$REPO/results/raw/gazebo_f53_validation}"
REFERENCE_DIR="${F53_REFERENCE_DIR:-$REPO/results/raw/gazebo}"
COMBOS="ahe_mrta_v3 robot_failure,ahe_mrta_v3 mixed_stress,ahe_mrta_v3 deadline_pressure"

case "$PROFILE" in
    smoke)
        SCALES="3:15"
        SEEDS="1"
        ;;
    pilot)
        SCALES="3:15"
        SEEDS="1 2 3"
        ;;
    paper)
        SCALES="5:25"
        SEEDS="1 2 3 4 5"
        ;;
    full)
        SCALES="3:15 5:25 10:50"
        SEEDS="1 2 3 4 5"
        ;;
    *)
        echo "Usage: $0 {smoke|pilot|paper|full}" >&2
        exit 2
        ;;
esac

mkdir -p "$RESULTS_ROOT"
printf 'profile=%s\nseeds=%s\nscales=%s\nreference=%s\n' \
    "$PROFILE" "$SEEDS" "$SCALES" "$REFERENCE_DIR" > "$RESULTS_ROOT/campaign.conf"
git rev-parse HEAD > "$RESULTS_ROOT/git_commit.txt" 2>/dev/null || true
git status --short > "$RESULTS_ROOT/working_tree_status.txt" 2>/dev/null || true
git diff -- src scripts tests > "$RESULTS_ROOT/working_tree.patch" 2>/dev/null || true
find src scripts tests -type f \( -name '*.py' -o -name '*.yaml' -o -name '*.sh' \) \
    -print0 | sort -z | xargs -0 sha256sum > "$RESULTS_ROOT/source_sha256.txt"

for scale in $SCALES; do
    robots="${scale%%:*}"
    tasks="${scale##*:}"
    tag="r${robots}t${tasks}"
    raw_dir="$RESULTS_ROOT/$tag"
    processed_dir="$REPO/results/processed/gazebo_f53_validation/$tag"
    stats_dir="$REPO/results/stats/gazebo_f53_validation/$tag"

    bash "$REPO/run_experiments_robust.sh" \
        --robots "$robots" --tasks "$tasks" --seeds "$SEEDS" \
        --combos "$COMBOS" --results-dir "$raw_dir" --skip-done 1

    python3 "$REPO/scripts/consolidate_results.py" \
        --raw-dir "$raw_dir" --processed-dir "$processed_dir"
    python3 "$REPO/scripts/compare_f53_gazebo.py" \
        --reference-dir "$REFERENCE_DIR" --candidate-dir "$raw_dir" \
        --output-dir "$stats_dir"
done

echo "F53 $PROFILE validation complete: $RESULTS_ROOT"
