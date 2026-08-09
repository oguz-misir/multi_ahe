#!/usr/bin/env bash
# Paired A/B: identical F58 configuration, warm-up on vs off.
set -eo pipefail
cd /home/oguz/multi_ahe
export AHE_F58_GEODESIC=1 AHE_F58_FAIR_REPAIR=1 \
       AHE_F58_FAIR_RESERVATION_GAP=2 AHE_F58_FAIR_EXTRA_QUEUE=1 \
       AHE_F58_FAIR_TERMINAL_TASKS_PER_ROBOT=3

for arm in off on; do
    export AHE_WARMUP=$([ "$arm" = on ] && echo 1 || echo 0)
    echo "############ ARM: warmup=$arm ############"
    bash run_experiments_robust.sh \
        --robots 5 --tasks 25 --seeds "1 2" \
        --combos "ahe_mrta_v3 mixed_stress" \
        --results-dir "/home/oguz/multi_ahe/results/raw/gazebo_warmup_ab/$arm"
done
echo "ALL ARMS DONE"
