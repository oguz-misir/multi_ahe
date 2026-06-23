#!/usr/bin/env bash
# =============================================================================
# run_campaign.sh — Genel parametreli crash-güvenli Gazebo toplama.
# Ölçek-bağımsız: RC robot, TC görev, SEEDS tohumlar, 4 yöntem × 3 senaryo (vars).
# Readiness-gated startup (bozuk→STARTUP_FAILED→retry), setsid+pgid kill (orphan yok),
# koşu-başı ROS_DOMAIN_ID, load_guard<5 + temiz cleanup. AHE = tek config (gate yok).
# Round-based: DONE-atlamalı, hücre-başı CAP deneme.
#
#   RC=15 TC=75 SEEDS="1" DIR=results/raw/gazebo_15r METHODS="ahe_mrta_v3" \
#     nohup bash run_campaign.sh > results/camp_15r_smoke.log 2>&1 &   # smoke
#   RC=5  TC=15 SEEDS="1 2 3 4 5" DIR=results/raw/gazebo_5r_low \
#     nohup bash run_campaign.sh > results/camp_5r_low.log 2>&1 &      # full
# =============================================================================
set -o pipefail
REPO="$(cd "$(dirname "$0")" && pwd)"; cd "$REPO"
source "$REPO/scripts/exp_lib.sh"
source /opt/ros/jazzy/setup.bash 2>/dev/null
source "$REPO/install/setup.bash" 2>/dev/null
export MAX_LOAD=5 SETTLE_SLEEP=15

RC="${RC:?RC (robot sayısı) gerekli}"
TC="${TC:?TC (görev sayısı) gerekli}"
SEEDS="${SEEDS:-1 2 3 4 5}"
DIR="${DIR:?DIR gerekli}"
METHODS="${METHODS:-ahe_mrta_v3 big_mrta rostam_ea consensus_dbta}"
SCENARIOS="${SCENARIOS:-mixed_stress deadline_pressure robot_failure}"
CAP="${CAP:-6}"
# ölçeğe göre startup/timeout (readiness erken başlatır; bunlar ÜST sınır)
case "$RC" in
  5)  SD="${SD:-180}";  TO="${TO:-1800}" ;;
  10) SD="${SD:-360}";  TO="${TO:-3000}" ;;
  15) SD="${SD:-600}";  TO="${TO:-4200}" ;;
  *)  SD="${SD:-300}";  TO="${TO:-2400}" ;;
esac
LOG(){ echo "$(date '+%F %T') [camp r${RC}t${TC}] $*"; }
IDX=0; declare -A ATT
tag="r${RC}t${TC}"

run_one(){  # method scenario seed
    local m="$1" scen="$2" sd="$3"
    local eid="exp_${scen}_${m}_${tag}_seed$(printf '%02d' "$sd")"
    local donef="$DIR/$eid/DONE"
    load_guard; cleanup_ros_gz
    rm -rf "$DIR/$eid"; mkdir -p "$DIR"
    IDX=$((IDX+1)); local dom=$((11 + IDX % 89))
    LOG "RUN $eid (deneme $((${ATT[$eid]:-0}))/$CAP, DOMAIN=$dom, SD=${SD}s)"
    (
        export ROS_DOMAIN_ID="$dom"
        exec setsid timeout "$TO" ros2 launch m_ahe_mrta_bringup phase9_experiments.launch.py \
            strategy:="$m" scenario:="$scen" seed:="$sd" robot_count:="$RC" task_count:="$TC" \
            results_dir:="$DIR" startup_delay:="${SD}.0" gz_gui:=false > "$DIR/${eid}_launch.log" 2>&1
    ) &
    local lp=$! i
    for i in $(seq 1 $((TO/10))); do
        [ -f "$donef" ] && break
        [ -f "$DIR/$eid/STARTUP_FAILED" ] && { LOG "  startup-failed"; break; }
        kill -0 "$lp" 2>/dev/null || break
        sleep 10
    done
    kill -9 -"$lp" 2>/dev/null
    cleanup_ros_gz
    if [ -f "$donef" ] && ! run_health_ok "$DIR/${eid}_launch.log"; then
        # DONE üretti ama AMCL sapması → bozuk veri. DONE'u iptal et → retry.
        LOG "  ✗ UNHEALTHY $eid → DONE iptal, yeniden denenecek"
        rm -f "$donef"
    fi
    if [ -f "$donef" ]; then
        local moved
        moved=$(awk -F, 'NR>1{if($2 in lx){d[$2]+=sqrt(($3-lx[$2])^2+($4-ly[$2])^2)}lx[$2]=$3;ly[$2]=$4}END{m=0;for(r in d)if(d[r]>0.5)m++;print m"/"length(d)}' "$DIR/$eid/robot_state_timeseries.csv" 2>/dev/null)
        LOG "  ✓ DONE $(awk -F, 'NR==2{print "comp="$8"/"$7" mk="$12"s CR="$11}' "$DIR/$eid/summary.csv") hareketli=$moved"
    else
        LOG "  ✗ FAIL $eid"
    fi
}

want=$(( $(echo $SCENARIOS|wc -w) * $(echo $METHODS|wc -w) * $(echo $SEEDS|wc -w) ))
LOG "BAŞLADI — hedef $want koşu ($DIR)"
while true; do
    pending=()
    for scen in $SCENARIOS; do for m in $METHODS; do for sd in $SEEDS; do
        eid="exp_${scen}_${m}_${tag}_seed$(printf '%02d' "$sd")"
        [ -f "$DIR/$eid/DONE" ] && continue
        [ "${ATT[$eid]:-0}" -ge "$CAP" ] && continue
        pending+=("$m $scen $sd")
    done; done; done
    dn=$(find "$DIR" -name DONE 2>/dev/null | wc -l)
    [ "${#pending[@]}" -eq 0 ] && { LOG "Tamam — denenecek kalmadı (DONE=$dn/$want)"; break; }
    LOG "=== TARAMA: ${#pending[@]} hücre (DONE=$dn/$want) ==="
    for cell in "${pending[@]}"; do
        read -r m scen sd <<< "$cell"
        eid="exp_${scen}_${m}_${tag}_seed$(printf '%02d' "$sd")"
        [ -f "$DIR/$eid/DONE" ] && continue
        ATT[$eid]=$(( ${ATT[$eid]:-0} + 1 ))
        run_one "$m" "$scen" "$sd"
    done
done
LOG "BİTTİ — DONE=$(find "$DIR" -name DONE 2>/dev/null|wc -l)/$want"
touch "$REPO/results/.camp_${tag}_done"
