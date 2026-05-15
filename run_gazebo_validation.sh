#!/usr/bin/env bash
# =============================================================================
# AHE-MRTA — Gazebo Doğrulama Deneyleri (Paper Validation Set)
#
# 5 strateji × 3 senaryo × 3 seed = 45 deney
# (Her deney: 45s Nav2 başlatma + maks. 300s çalışma + 10s temizlik ≈ ~6 dakika)
# Tahmini toplam: ~4.5 saat (tam set) veya ~1 saat (--quick ile 2 seed)
#
# Kullanım:
#   bash run_gazebo_validation.sh               # 45 deney (3 seed)
#   bash run_gazebo_validation.sh --seeds "1 2" # 30 deney (2 seed, ~3 saat)
#   bash run_gazebo_validation.sh --quick       # 15 deney (1 seed, ~90 dk)
#   bash run_gazebo_validation.sh --dry-run     # komutları göster
#   bash run_gazebo_validation.sh --set core    # sadece AHE vs SW vs BiG (18 deney)
#
# Strateji seti:
#   full_ahe_mrta, static_weighted, big_mrta,
#   ahe_no_event_replanning, greedy_nearest
#
# Senaryo seti:
#   dynamic_task_arrival, robot_failure, deadline_pressure
#
# Çıktı: results/raw/gazebo/
# =============================================================================

set -euo pipefail
REPO="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO"

# ── Varsayılanlar ─────────────────────────────────────────────────────────────
DRY_RUN=0
SEEDS="1 2 3"
STARTUP_DELAY=45
EXPERIMENT_TIMEOUT=300      # Nav2 navigasyon süresi max (saniye)
TOTAL_TIMEOUT=$((STARTUP_DELAY + EXPERIMENT_TIMEOUT + 10))
SET="full"
RESULTS_DIR="$REPO/results/raw/gazebo"

# ── Argüman ayrıştırma ────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)   DRY_RUN=1;              shift ;;
        --seeds)     SEEDS="$2";             shift 2 ;;
        --quick)     SEEDS="1";              shift ;;
        --set)       SET="$2";               shift 2 ;;
        --startup)   STARTUP_DELAY="$2";     shift 2 ;;
        --timeout)   EXPERIMENT_TIMEOUT="$2"; TOTAL_TIMEOUT=$((STARTUP_DELAY + EXPERIMENT_TIMEOUT + 10)); shift 2 ;;
        -h|--help)   grep "^#" "$0" | head -30; exit 0 ;;
        *) echo "[HATA] Bilinmeyen argüman: $1"; exit 1 ;;
    esac
done

# ── Strateji setleri ──────────────────────────────────────────────────────────
ALL_STRATEGIES=("full_ahe_mrta" "static_weighted" "big_mrta" "ahe_no_event_replanning" "greedy_nearest")
CORE_STRATEGIES=("full_ahe_mrta" "static_weighted" "big_mrta")
AHE_STRATEGIES=("full_ahe_mrta" "ahe_no_event_replanning" "ahe_no_dominance")

SCENARIOS=("dynamic_task_arrival" "robot_failure" "deadline_pressure")

case "$SET" in
    full)  STRATEGIES=("${ALL_STRATEGIES[@]}") ;;
    core)  STRATEGIES=("${CORE_STRATEGIES[@]}") ;;
    ahe)   STRATEGIES=("${AHE_STRATEGIES[@]}") ;;
    *)     echo "[HATA] Bilinmeyen set: $SET (full|core|ahe)"; exit 1 ;;
esac

# ── Workspace kontrolü ────────────────────────────────────────────────────────
if ! command -v ros2 &>/dev/null; then
    if [ -f "$REPO/install/setup.bash" ]; then
        source "$REPO/install/setup.bash"
    else
        echo "[HATA] ROS2 bulunamadı. Önce workspace'i build edin:"
        echo "  cd $REPO && colcon build --symlink-install"
        echo "  source install/setup.bash"
        exit 1
    fi
fi

# WSL2 için grafik ayarları
export DISPLAY="${DISPLAY:-:0}"
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe

mkdir -p "$RESULTS_DIR"

# ── Deney sayısı özeti ────────────────────────────────────────────────────────
NSEED=$(echo $SEEDS | wc -w)
TOTAL=$(( ${#STRATEGIES[@]} * ${#SCENARIOS[@]} * NSEED ))
EST_MIN=$(( TOTAL * TOTAL_TIMEOUT / 60 ))

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     AHE-MRTA  Gazebo Doğrulama Deneyleri (Paper Val.)        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo "  Stratejiler   : ${STRATEGIES[*]}"
echo "  Senaryolar    : ${SCENARIOS[*]}"
echo "  Seed'ler      : $SEEDS"
echo "  Başlatma gecikmesi: ${STARTUP_DELAY}s"
echo "  Deney timeout : ${EXPERIMENT_TIMEOUT}s"
echo "  Toplam timeout: ${TOTAL_TIMEOUT}s / deney"
echo "  Toplam deney  : $TOTAL"
echo "  Tahmini süre  : ~${EST_MIN} dakika"
echo "  Sonuç klasörü : $RESULTS_DIR"
echo "  Dry-run       : $([ $DRY_RUN -eq 1 ] && echo 'evet' || echo 'hayır')"
echo ""

if [ $DRY_RUN -eq 1 ]; then
    echo "=== DRY RUN — çalıştırılacak komutlar ==="
fi

# ── ROS2 / Gazebo süreçlerini temizle ─────────────────────────────────────────
cleanup_ros() {
    # Tüm Gazebo ve ROS2 süreçlerini güvenli şekilde sonlandır
    pkill -f "gz sim"      2>/dev/null || true
    pkill -f "gzserver"    2>/dev/null || true
    pkill -f "gzclient"    2>/dev/null || true
    pkill -f "ros2 launch" 2>/dev/null || true
    pkill -f "robot_interface_node" 2>/dev/null || true
    pkill -f "experiment_runner_node" 2>/dev/null || true
    pkill -f "ecosystem_manager_node" 2>/dev/null || true
    pkill -f "nav2_bringup" 2>/dev/null || true
    pkill -f "amcl"        2>/dev/null || true
    # ROS2 daemon'u yeniden başlat
    ros2 daemon stop 2>/dev/null || true
    sleep 2
    ros2 daemon start 2>/dev/null || true
    sleep 3
}

# ── Tek deney çalıştırıcı ─────────────────────────────────────────────────────
run_experiment() {
    local strategy="$1"
    local scenario="$2"
    local seed="$3"
    local exp_num="$4"

    local exp_id="${strategy}__${scenario}__seed${seed}"
    local exp_dir="$RESULTS_DIR/$exp_id"
    local log_file="$RESULTS_DIR/${exp_id}.log"
    local done_file="$exp_dir/DONE"

    # Daha önce tamamlandıysa atla
    if [ -f "$done_file" ]; then
        echo "  ↷ [$exp_num/$TOTAL] $strategy | $scenario | seed=$seed  (zaten tamamlandı)"
        return 0
    fi

    echo "  ▶ [$exp_num/$TOTAL] $strategy | $scenario | seed=$seed"

    local cmd="ros2 launch m_ahe_mrta_bringup phase9_experiments.launch.py \
        strategy:=${strategy} \
        scenario:=${scenario} \
        seed:=${seed} \
        startup_delay:=${STARTUP_DELAY} \
        results_dir:=${RESULTS_DIR}"

    echo "    → $cmd"

    if [ $DRY_RUN -eq 1 ]; then
        return 0
    fi

    # Önceki deneyin temizliğini yap
    cleanup_ros

    # Deneyi çalıştır (timeout ile — deney bitince node SIGTERM gönderir)
    local launch_pid
    eval "$cmd > '$log_file' 2>&1 &"
    launch_pid=$!

    # DONE dosyasını veya TOTAL_TIMEOUT'u bekle
    local waited=0
    local done=0
    while [ $waited -lt $TOTAL_TIMEOUT ]; do
        sleep 2
        waited=$((waited + 2))
        if [ -f "$done_file" ]; then
            done=1
            break
        fi
        # Launch process hala çalışıyor mu?
        if ! kill -0 "$launch_pid" 2>/dev/null; then
            # Process öldüyse ve DONE dosyası yoksa hata
            if [ ! -f "$done_file" ]; then
                echo "    ✗ Launch process beklenmedik şekilde sona erdi"
                return 1
            fi
            done=1
            break
        fi
    done

    # Temizlik
    if kill -0 "$launch_pid" 2>/dev/null; then
        kill "$launch_pid" 2>/dev/null || true
        sleep 3
        kill -9 "$launch_pid" 2>/dev/null || true
    fi
    cleanup_ros

    if [ $done -eq 1 ]; then
        local makespan
        makespan=$(cat "$done_file" 2>/dev/null || echo "?")
        echo "    ✓ Tamamlandı (makespan=${makespan}s)"
    else
        echo "    ⚠ Timeout (${TOTAL_TIMEOUT}s) — sonuçlar kısmen kaydedilmiş olabilir"
    fi

    sleep 5  # Gazebo'nun tam kapanması için
}

# ── Ana döngü ─────────────────────────────────────────────────────────────────
EXP_NUM=0
for strategy in "${STRATEGIES[@]}"; do
    for scenario in "${SCENARIOS[@]}"; do
        for seed in $SEEDS; do
            EXP_NUM=$(( EXP_NUM + 1 ))
            echo ""
            echo "── Deney $EXP_NUM/$TOTAL ──────────────────────────────────────────"
            run_experiment "$strategy" "$scenario" "$seed" "$EXP_NUM"
        done
    done
done

# ── Özet ─────────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           Gazebo Doğrulama Deneyleri Tamamlandı              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

if [ $DRY_RUN -eq 0 ]; then
    NDONE=$(find "$RESULTS_DIR" -name "DONE" 2>/dev/null | wc -l)
    echo "  Tamamlanan : $NDONE / $TOTAL"
    echo "  Sonuçlar   : $RESULTS_DIR"
    echo ""
    echo "  Analiz için:"
    echo "    python3 scripts/consolidate_results.py \\"
    echo "        --raw-dir results/raw/gazebo \\"
    echo "        --processed-dir results/processed_gazebo/"
    echo ""
    echo "    python3 scripts/plot_results.py \\"
    echo "        --processed-dir results/processed_gazebo/ \\"
    echo "        --output-dir results/paper_figures/gazebo/"
fi
