#!/usr/bin/env bash
# Complete the 3-robot cells of the warm-up campaign: seeds 3-5 across all
# three task densities, so the efficiency table's latency column reaches the
# same n=15 as its other columns.  Same env, same output tree as the first
# 48 runs; SKIP_DONE leaves seeds 1-2 untouched.
set -eo pipefail
cd /home/oguz/multi_ahe
source scripts/exp_lib.sh

export AHE_F58_GEODESIC=1 AHE_F58_FAIR_REPAIR=1 \
       AHE_F58_FAIR_RESERVATION_GAP=2 AHE_F58_FAIR_EXTRA_QUEUE=1 \
       AHE_F58_FAIR_TERMINAL_TASKS_PER_ROBOT=3 \
       AHE_WARMUP=1

OUT=/home/oguz/multi_ahe/results/raw/gazebo_warmup_campaign
COMBOS="ahe_mrta_v3 robot_failure,ahe_mrta_v3 mixed_stress,ahe_mrta_v3 deadline_pressure"

for tc in 9 15 24; do
    echo "########## FILL 3r/${tc}t seeds 3-5 ##########"
    bash run_experiments_robust.sh \
        --robots 3 --tasks "$tc" --seeds "3 4 5" \
        --combos "$COMBOS" --results-dir "$OUT/r3t${tc}"
done
echo "3R FILL COMPLETE"
