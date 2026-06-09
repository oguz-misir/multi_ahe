#!/usr/bin/env bash
# =============================================================================
# run_until_complete.sh — AHE-MRTA çökme-güvenli batch sürücüsü
#
# Amaç: bilgisayar donsa / çökse / yeniden başlasa bile batch KALDIĞI YERDEN
# devam etsin. `run_experiments_robust.sh` zaten DONE olan deneyleri atlar;
# bu sarmalayıcı onu, beklenen sayıya ulaşılana kadar tekrar tekrar çağırır.
#
#   - .batch_active bayrağı: batch sürerken var; bitince silinir. @reboot cron
#     yalnızca bu bayrak varken yeniden başlatır (gereksiz boot'ta tetiklenmez).
#   - Her tur arası load_guard + temizlik.
#   - Her DONE PROGRESS.md + MEMORY ledger'a işlenir (runner içinden).
#
# Kullanım:
#   nohup bash run_until_complete.sh > results/until_complete.log 2>&1 &
#   EXPECTED_TOTAL=60 bash run_until_complete.sh --robots 5 --tasks 25
# =============================================================================

set -uo pipefail
REPO="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO"
source "$REPO/scripts/exp_lib.sh"

RESULTS_DIR="$REPO/results/raw/gazebo"
EXPECTED_TOTAL="${EXPECTED_TOTAL:-60}"
MAX_ROUNDS="${MAX_ROUNDS:-40}"     # sonsuz döngü koruması
PASS_ARGS=()

# --results-dir / --expected'ı yakala, gerisini runner'a aktar
while [[ $# -gt 0 ]]; do
    case "$1" in
        --results-dir) RESULTS_DIR="$2"; PASS_ARGS+=("$1" "$2"); shift 2 ;;
        --expected)    EXPECTED_TOTAL="$2"; shift 2 ;;
        *) PASS_ARGS+=("$1"); shift ;;
    esac
done
export EXPECTED_TOTAL

ACTIVE_FLAG="$REPO/results/.batch_active"
LOCK="$REPO/results/.until_complete.lock"
mkdir -p "$REPO/results"

# Tek örnek kilidi (aynı anda iki sürücü çalışmasın)
exec 201>"$LOCK"
if ! flock -n 201; then
    echo "[run_until_complete] Zaten çalışan bir örnek var → çıkılıyor."
    exit 0
fi

echo "$(date '+%F %T') > batch_active set; hedef=$EXPECTED_TOTAL; dizin=$RESULTS_DIR"
date '+%Y-%m-%dT%H:%M:%S' > "$ACTIVE_FLAG"
# Cron sarmalayıcılarının (reboot-resume, 45dk rapor) okuduğu bayraklar
echo "$EXPECTED_TOTAL" > "$REPO/results/.batch_expected"
echo "$RESULTS_DIR"   > "$REPO/results/.batch_results_dir"

done_count() { find "$RESULTS_DIR" -name DONE 2>/dev/null | wc -l; }

round=0
while :; do
    nd=$(done_count)
    bash "$REPO/scripts/exp_status.sh" --results-dir "$RESULTS_DIR" --expected "$EXPECTED_TOTAL" || true
    if [ "$nd" -ge "$EXPECTED_TOTAL" ]; then
        echo "$(date '+%F %T') > TÜM DENEYLER TAMAM ($nd/$EXPECTED_TOTAL) — çıkılıyor."
        break
    fi
    round=$(( round + 1 ))
    if [ "$round" -gt "$MAX_ROUNDS" ]; then
        echo "$(date '+%F %T') > MAX_ROUNDS=$MAX_ROUNDS aşıldı ($nd/$EXPECTED_TOTAL) — duruyor (manuel inceleme)."
        break
    fi

    echo "──────── Tur $round | $nd/$EXPECTED_TOTAL DONE | $(date '+%F %T') ────────"
    load_guard

    # Runner çökse bile (set -e ile exit etse de) döngü yakalar: || true
    bash "$REPO/run_experiments_robust.sh" "${PASS_ARGS[@]}" || \
        echo "$(date '+%F %T') > runner tur $round hata/çöküş ile döndü — temizleyip tekrar denenecek."

    cleanup_ros_gz
    sleep 10
done

# Beklenen sayıya ulaşıldıysa bayrağı kaldır (reboot'ta tekrar başlamasın)
final=$(done_count)
if [ "$final" -ge "$EXPECTED_TOTAL" ]; then
    rm -f "$ACTIVE_FLAG"
    bash "$REPO/scripts/exp_status.sh" --results-dir "$RESULTS_DIR" --expected "$EXPECTED_TOTAL" || true
    echo "$(date '+%F %T') > batch_active temizlendi. Bitti: $final/$EXPECTED_TOTAL"
else
    echo "$(date '+%F %T') > Eksik kaldı ($final/$EXPECTED_TOTAL); .batch_active duruyor → reboot/yeniden çağrı devam eder."
fi
