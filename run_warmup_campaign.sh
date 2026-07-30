#!/usr/bin/env bash
# Warm-up ON campaign: refresh AHE's latency column on every cell the paper
# reports.  Baselines are untouched by the change (they have no warmup hook),
# so the whole budget goes to AHE.  The paired 4-run A/B separately established
# that the warm-up-OFF arm reproduces the published campaign's cold start
# (299.9 ms vs 298.5 ms), which licenses the canonical data as the OFF baseline.
set -eo pipefail
cd /home/oguz/multi_ahe
source scripts/exp_lib.sh

export AHE_F58_GEODESIC=1 AHE_F58_FAIR_REPAIR=1 \
       AHE_F58_FAIR_RESERVATION_GAP=2 AHE_F58_FAIR_EXTRA_QUEUE=1 \
       AHE_F58_FAIR_TERMINAL_TASKS_PER_ROBOT=3 \
       AHE_WARMUP=1

OUT=/home/oguz/multi_ahe/results/raw/gazebo_warmup_campaign
COMBOS="ahe_mrta_v3 robot_failure,ahe_mrta_v3 mixed_stress,ahe_mrta_v3 deadline_pressure"

run_cell() {   # robots tasks seeds label
    echo "########## CELL $4  (${1}r/${2}t, seeds: $3) ##########"
    bash run_experiments_robust.sh \
        --robots "$1" --tasks "$2" --seeds "$3" \
        --combos "$COMBOS" --results-dir "$OUT/$4"
}

# 3-robot efficiency cell pools three densities (paper Table: efficiency)
run_cell 3  9 "1 2" r3t9
run_cell 3 15 "1 2" r3t15
run_cell 3 24 "1 2" r3t24
# 5-robot primary scale
run_cell 5 25 "1 2 3 4 5" r5t25
# 10-robot scalability
run_cell 10 50 "1 2 3 4 5" r10t50

echo "CAMPAIGN COMPLETE"
