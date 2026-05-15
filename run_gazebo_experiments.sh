#!/usr/bin/env bash
# =============================================================================
# AHE-MRTA — Gazebo Hedefli Deney Batch Script
#
# Makale için gerçek Gazebo + Nav2 + RViz deneyleri (24 adet, ~2.5 saat).
# Her deney phase9_demo.launch.py ile çalıştırılır, tamamlanınca durur.
#
# Kullanım:
#   bash run_gazebo_experiments.sh                 # tüm 24 deney
#   bash run_gazebo_experiments.sh --dry-run        # komutları yazdır, çalıştırma
#   bash run_gazebo_experiments.sh --no-rviz        # RViz olmadan (headless)
#   bash run_gazebo_experiments.sh --set ablation   # sadece ablation deneyleri
#   bash run_gazebo_experiments.sh --set baseline   # sadece baseline karşılaştırma
#   bash run_gazebo_experiments.sh --timeout 360    # deney başına max saniye (def:360)
#
# Deney Setleri:
#   baseline  — AHE-MRTA vs BiG-MRTA vs RoSTAM-EA vs SW (robot_failure + mixed_stress)
#   ablation  — NoER vs NoD vs FC vs NoCS vs full_ahe (robot_failure + mixed_stress)
#   deadline  — AHE-MRTA vs BiG-MRTA vs SW (deadline_pressure)
#   all       — tüm setler (varsayılan)
#
# Çıktı: results/raw/gazebo/<experiment_id>/
# =============================================================================

set -e
REPO="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO"

# ── Varsayılanlar ─────────────────────────────────────────────────────────────
DRY_RUN=0
NO_RVIZ=0
SET="all"
TIMEOUT_SEC=360
SEEDS="1 2 3"
RESULTS_DIR="$REPO/results/raw/gazebo"

# ── Argüman ayrıştırma ────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)   DRY_RUN=1;          shift ;;
        --no-rviz)   NO_RVIZ=1;          shift ;;
        --set)       SET="$2";           shift 2 ;;
        --timeout)   TIMEOUT_SEC="$2";   shift 2 ;;
        --seeds)     SEEDS="$2";         shift 2 ;;
        -h|--help)   grep "^#" "$0" | head -30; exit 0 ;;
        *) echo "[HATA] Bilinmeyen argüman: $1"; exit 1 ;;
    esac
done

mkdir -p "$RESULTS_DIR"

# ── Workspace source kontrolü ─────────────────────────────────────────────────
if ! command -v ros2 &>/dev/null; then
    if [ -f "$REPO/install/setup.bash" ]; then
        # shellcheck disable=SC1090
        source "$REPO/install/setup.bash"
    else
        echo "[HATA] ROS2 bulunamadı. Önce workspace'i build edin:"
        echo "  cd $REPO && colcon build --symlink-install"
        echo "  source install/setup.bash"
        exit 1
    fi
fi

# Display kontrolü (WSLg / X11)
if [ -z "$DISPLAY" ]; then
    export DISPLAY=:0
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║        AHE-MRTA  Gazebo Batch Experiments                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo "  Set        : $SET"
echo "  Seeds      : $SEEDS"
echo "  Timeout    : ${TIMEOUT_SEC}s / deney"
echo "  RViz       : $([ $NO_RVIZ -eq 1 ] && echo 'hayır (headless)' || echo 'evet')"
echo "  Sonuç klas.: $RESULTS_DIR"
echo "  Dry-run    : $([ $DRY_RUN -eq 1 ] && echo 'evet' || echo 'hayır')"
echo ""

# ── Deney tanımları ───────────────────────────────────────────────────────────
# Format: "strategy scenario" — seed döngüsü dışarıda eklenir

declare -a BASELINE_EXPERIMENTS=(
    "full_ahe_mrta  robot_failure"
    "full_ahe_mrta  mixed_stress"
    "big_mrta       robot_failure"
    "big_mrta       mixed_stress"
    "rostam_ea      robot_failure"
    "rostam_ea      mixed_stress"
    "static_weighted robot_failure"
    "static_weighted mixed_stress"
)

declare -a DEADLINE_EXPERIMENTS=(
    "full_ahe_mrta   deadline_pressure"
    "big_mrta        deadline_pressure"
    "static_weighted deadline_pressure"
)

declare -a ABLATION_EXPERIMENTS=(
    "full_ahe_mrta              robot_failure"
    "full_ahe_mrta              mixed_stress"
    "ahe_no_event_replanning    robot_failure"
    "ahe_no_event_replanning    mixed_stress"
    "ahe_no_dominance           robot_failure"
    "ahe_no_dominance           mixed_stress"
    "ahe_fixed_context          robot_failure"
    "ahe_fixed_context          mixed_stress"
)

# Seçilen setleri birleştir
declare -a SELECTED_EXPERIMENTS=()
case "$SET" in
    all)
        SELECTED_EXPERIMENTS=("${BASELINE_EXPERIMENTS[@]}" "${DEADLINE_EXPERIMENTS[@]}" "${ABLATION_EXPERIMENTS[@]}")
        ;;
    baseline)
        SELECTED_EXPERIMENTS=("${BASELINE_EXPERIMENTS[@]}")
        ;;
    deadline)
        SELECTED_EXPERIMENTS=("${DEADLINE_EXPERIMENTS[@]}")
        ;;
    ablation)
        SELECTED_EXPERIMENTS=("${ABLATION_EXPERIMENTS[@]}")
        ;;
    *)
        echo "[HATA] Bilinmeyen set: $SET (baseline|deadline|ablation|all)"
        exit 1
        ;;
esac

# ── Deney sayısı özeti ────────────────────────────────────────────────────────
NSEED=$(echo $SEEDS | wc -w)
TOTAL=$(( ${#SELECTED_EXPERIMENTS[@]} * NSEED ))
EST_MIN=$(( TOTAL * TIMEOUT_SEC / 60 ))
echo "  Toplam deney : $TOTAL  (${#SELECTED_EXPERIMENTS[@]} deney × $NSEED seed)"
echo "  Tahmini süre : ~${EST_MIN} dk  (worst-case ${TIMEOUT_SEC}s/deney)"
echo ""

if [ $DRY_RUN -eq 1 ]; then
    echo "=== DRY RUN — sadece komutlar ==="
fi

# ── Yardımcı: tek deney çalıştır ─────────────────────────────────────────────
run_experiment() {
    local strategy="$1"
    local scenario="$2"
    local seed="$3"

    local exp_id="${strategy}__${scenario}__seed${seed}__$(date +%Y%m%d_%H%M%S)"
    local log_file="$RESULTS_DIR/${exp_id}.log"

    local launch_args=(
        "strategy:=${strategy}"
        "scenario:=${scenario}"
        "seed:=${seed}"
        "results_dir:=${RESULTS_DIR}"
    )

    # RViz olmadan: phase9_demo yerine phase9_experiments (headless) kullan
    local launch_file
    if [ $NO_RVIZ -eq 1 ]; then
        launch_file="phase9_experiments.launch.py"
    else
        launch_file="phase9_demo.launch.py"
    fi

    local cmd="ros2 launch m_ahe_mrta_bringup ${launch_file} ${launch_args[*]}"

    echo "  ▶ [$strategy | $scenario | seed=$seed]"
    echo "    $cmd"

    if [ $DRY_RUN -eq 1 ]; then
        return 0
    fi

    # Deneyi timeout ile çalıştır, log'a yaz
    if timeout "$TIMEOUT_SEC" bash -c "$cmd" > "$log_file" 2>&1; then
        echo "    ✓ Tamamlandı"
    else
        local ec=$?
        if [ $ec -eq 124 ]; then
            echo "    ⚠ Timeout (${TIMEOUT_SEC}s) — deney sonuçları kaydedilmiş olabilir"
        else
            echo "    ✗ Hata (exit=$ec) — log: $log_file"
        fi
    fi

    # Gazebo'nun tam kapanması için bekleme
    sleep 5
}

# ── Ana döngü ─────────────────────────────────────────────────────────────────
EXP_NUM=0
for entry in "${SELECTED_EXPERIMENTS[@]}"; do
    # boşluk ile ayır (leading whitespace temizle)
    read -r strategy scenario <<< "$entry"
    for seed in $SEEDS; do
        EXP_NUM=$(( EXP_NUM + 1 ))
        echo ""
        echo "── Deney $EXP_NUM/$TOTAL ──────────────────────────────────────────"
        run_experiment "$strategy" "$scenario" "$seed"
    done
done

# ── Bitince analiz ───────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              Gazebo Deneyleri Tamamlandı                     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  Sonuçlar: $RESULTS_DIR"
echo ""
echo "  Gazebo sonuçlarını offline pipeline'a eklemek için:"
echo "    bash run_all.sh --skip-experiments --raw-dir results/raw/gazebo"
echo ""

# Hızlı özet: kaç deney var
if [ $DRY_RUN -eq 0 ]; then
    NDONE=$(find "$RESULTS_DIR" -name "summary.csv" 2>/dev/null | wc -l)
    echo "  Tamamlanan deney (summary.csv bulunan): $NDONE / $TOTAL"
    echo ""
fi
