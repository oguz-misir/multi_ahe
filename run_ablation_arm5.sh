#!/usr/bin/env bash
# Fifth ablation arm: fixed spatial-greedy (AHE_FORCE_PARADIGM=0).
#
# NOT part of the pre-registered design (paper/PREREGISTRATION.md), and must be
# reported as exploratory rather than folded into the primary family.  Added
# because re-running the proxy ablation on the corrected scenario definitions
# put fixed-spatial AHEAD of the full selector (0.348 vs 0.329 mean fitness),
# and the registered arms covered only the two paradigms the overrides target
# (H_TEMP, H_RECOV) -- not the one the dominance fallback returns in 99.9% of
# the states it decides, which is exactly spatial-greedy.  Leaving the best
# candidate untested in the closed loop is the obvious reviewer question.
#
# 3 scenarios x 20 seeds = 60 runs.  AHE runs complete early (CR=1.000), so
# expect ~5.5 min/run, about 6 hours.
set -eo pipefail
cd /home/oguz/multi_ahe

# Must precede the source: exp_lib.sh sets the default itself.
export MAX_LOAD="${MAX_LOAD:-5}"
source scripts/exp_lib.sh

export AHE_F58_GEODESIC=1 AHE_F58_FAIR_REPAIR=1 \
       AHE_F58_FAIR_RESERVATION_GAP=2 AHE_F58_FAIR_EXTRA_QUEUE=1 \
       AHE_F58_FAIR_TERMINAL_TASKS_PER_ROBOT=3 \
       AHE_WARMUP=1 \
       AHE_FORCE_PARADIGM=0

OUT=/home/oguz/multi_ahe/results/raw/gazebo_ablation/fixed-spatial
SEEDS="1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20"
COMBOS="ahe_mrta_v3 robot_failure,ahe_mrta_v3 mixed_stress,ahe_mrta_v3 deadline_pressure"

echo "########## KOL fixed-spatial  (AHE_FORCE_PARADIGM=0) ##########"
bash run_experiments_robust.sh \
    --robots 5 --tasks 25 --seeds "$SEEDS" \
    --combos "$COMBOS" --results-dir "$OUT"

echo "ARM5 COMPLETE"
