#!/usr/bin/env bash
# =============================================================================
# run_gazebo_matrix.sh — çökme-güvenli Gazebo yoğunluk-sweep sürücüsü.
#
# 3 robot × {9,15,24} görev (düşük/orta/yüksek yoğunluk) × 4 yöntem × 3 senaryo
# × 5 seed = 180 deney. DONE olanları atlar → donma/çökme/reboot sonrası kaldığı
# yerden devam. Her tur load_guard + cleanup. .batch_active bayrağı sürdükçe
# @reboot cron bunu yeniden çağırır; bitince siler. record_done her DONE'da
# PROGRESS.md + MEMORY ledger'ı günceller (run_experiments_robust içinden).
#
# Kullanım:
#   nohup bash scripts/run_gazebo_matrix.sh > results/gazebo_matrix.log 2>&1 &
# =============================================================================
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"; cd "$REPO"
source "$REPO/scripts/exp_lib.sh"

RESULTS_DIR="$REPO/results/raw/gazebo"
DENSITIES=(9 15 24)
EXPECTED_TOTAL=180
MAX_ROUNDS="${MAX_ROUNDS:-60}"
export EXPECTED_TOTAL
mkdir -p "$RESULTS_DIR" "$REPO/results"

LOCK="$REPO/results/.gazebo_matrix.lock"
exec 202>"$LOCK"
if ! flock -n 202; then echo "[matrix] zaten çalışıyor → çık"; exit 0; fi

date '+%Y-%m-%dT%H:%M:%S' > "$REPO/results/.batch_active"
echo "180" > "$REPO/results/.batch_expected"
echo "$RESULTS_DIR" > "$REPO/results/.batch_results_dir"
echo "matrix"        > "$REPO/results/.batch_mode"

done_count() { find "$RESULTS_DIR" -name DONE 2>/dev/null | wc -l; }

round=0
while :; do
    nd=$(done_count)
    bash "$REPO/scripts/exp_status.sh" --results-dir "$RESULTS_DIR" --expected 180 || true
    if [ "$nd" -ge "$EXPECTED_TOTAL" ]; then
        echo "$(date '+%F %T') > TÜM GAZEBO MATRİS TAMAM ($nd/180) — çıkılıyor."; break
    fi
    round=$(( round + 1 ))
    [ "$round" -gt "$MAX_ROUNDS" ] && { echo "MAX_ROUNDS aşıldı ($nd/180) — duruyor."; break; }
    echo "──── Tur $round | $nd/180 DONE | $(date '+%F %T') ────"
    for d in "${DENSITIES[@]}"; do
        load_guard
        bash "$REPO/run_experiments_robust.sh" --robots 3 --tasks "$d" \
            --results-dir "$RESULTS_DIR" || \
            echo "$(date '+%F %T') > t=$d turu hata/çöküş ile döndü — devam."
        cleanup_ros_gz
    done
    sleep 10
done

final=$(done_count)
if [ "$final" -ge "$EXPECTED_TOTAL" ]; then
    rm -f "$REPO/results/.batch_active" "$REPO/results/.batch_mode"
    echo "$(date '+%F %T') > Gazebo matris bitti: $final/180."
else
    echo "$(date '+%F %T') > Eksik ($final/180); .batch_active duruyor → reboot devam eder."
fi
