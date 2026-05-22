#!/usr/bin/env bash
# =============================================================================
# AHE-MRTA — v3 Batch Runner  (sabit ölçek: 3r/15g)
#
# Deney kurgusu (paper v3 — tüm gruplar 3r/15g):
#   G1 — Karşılaştırma  : 4 yöntem × 3 senaryo × 5 seed = 60 deney
#   G2 — Ablasyon       : 4 varyant × 3 senaryo × 5 seed = 60 deney
#   TOPLAM              : 120 deney (~36 saat)
#
# Karşılaştırma yöntemleri (G1):
#   ahe_mrta_v3   (önerilen)
#   big_mrta      (BiG-MRTA)
#   rostam_ea     (RoSTAM-EA)
#   consensus_dbta
#
# Ablasyon varyantları (G2 — ahe_mrta_v3 baz):
#   ahe_mrta_v3_no_bipartite   (M1 devre dışı)
#   ahe_mrta_v3_no_dense_init  (M17 devre dışı)
#   ahe_mrta_v3_no_recovery    (M8+M11 devre dışı)
#   ahe_mrta_v3_fixed_weights  (ekosistem harmanlama devre dışı)
#
# Senaryolar: robot_failure, mixed_stress, deadline_pressure
# Seed: 01-05
#
# Kullanım:
#   nohup bash run_paper_experiments_v3.sh \
#       >> results/raw/gazebo_v3/paper_run_v3.log 2>&1 &
#
#   # Video kaydı dahil (seed=01):
#   nohup bash run_paper_experiments_v3.sh --record-video \
#       >> results/raw/gazebo_v3/paper_run_v3.log 2>&1 &
# =============================================================================

set -eo pipefail
REPO="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO"
LOG_DIR="$REPO/results/raw/gazebo_v3"
mkdir -p "$LOG_DIR"

RECORD_FLAG=""
for arg in "$@"; do
    case "$arg" in
        --record-video) RECORD_FLAG="--record-video" ;;
        --resume) ;;
        *) echo "[uyarı] bilinmeyen argüman: $arg" ;;
    esac
done

LOCKFILE="$REPO/.batch_v3_running.lock"
exec 200>"$LOCKFILE"
if ! flock -n 200; then
    echo "[ERROR] Another v3 batch instance is already running. Exiting."
    exit 1
fi
echo $$ >&200

source "$REPO/install/setup.bash"
export FASTRTPS_DEFAULT_PROFILES_FILE="$REPO/fastdds_udp_only.xml"
unset GTK_PATH GTK_EXE_PREFIX GTK_MODULES GTK_IM_MODULE_FILE 2>/dev/null || true

TOTAL_EXPERIMENTS=120

run_group() {
    local label="$1" log="$2"
    shift 2
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "  $label"
    echo "════════════════════════════════════════════════════════════════"
    bash "$REPO/run_experiments_robust.sh" $RECORD_FLAG "$@" --results-dir "$LOG_DIR" >> "$log" 2>&1
    local ndone
    ndone=$(find "$LOG_DIR" -name "DONE" 2>/dev/null | wc -l)
    echo "  ✓ $label bitti  |  Toplam DONE: $ndone / $TOTAL_EXPERIMENTS"
}

echo "════════════════════════════════════════════════════════════════"
echo "  AHE-MRTA v3  RA-L Makale Deneyleri  — 120 deney / ~36 saat"
echo "  Başlangıç: $(date)"
echo "  Sonuç dizini: $LOG_DIR"
echo "  Video kaydı: ${RECORD_FLAG:-kapalı}"
echo "════════════════════════════════════════════════════════════════"

# ── G1: Karşılaştırma (4 yöntem × 3 senaryo × 5 seed = 60 deney) ─────────────
COMP_COMBOS="\
ahe_mrta_v3 robot_failure,ahe_mrta_v3 mixed_stress,ahe_mrta_v3 deadline_pressure,\
big_mrta robot_failure,big_mrta mixed_stress,big_mrta deadline_pressure,\
rostam_ea robot_failure,rostam_ea mixed_stress,rostam_ea deadline_pressure,\
consensus_dbta robot_failure,consensus_dbta mixed_stress,consensus_dbta deadline_pressure"

run_group "G1  Karşılaştırma / 3r·15g  (60 deney)" "$LOG_DIR/g1_comparison.log" \
    --robots 3 --tasks 15 \
    --combos "$COMP_COMBOS"

# ── G2: Ablasyon (4 varyant × 3 senaryo × 5 seed = 60 deney) ─────────────────
ABLATION_COMBOS="\
ahe_mrta_v3_no_bipartite robot_failure,ahe_mrta_v3_no_bipartite mixed_stress,ahe_mrta_v3_no_bipartite deadline_pressure,\
ahe_mrta_v3_no_dense_init robot_failure,ahe_mrta_v3_no_dense_init mixed_stress,ahe_mrta_v3_no_dense_init deadline_pressure,\
ahe_mrta_v3_no_recovery robot_failure,ahe_mrta_v3_no_recovery mixed_stress,ahe_mrta_v3_no_recovery deadline_pressure,\
ahe_mrta_v3_fixed_weights robot_failure,ahe_mrta_v3_fixed_weights mixed_stress,ahe_mrta_v3_fixed_weights deadline_pressure"

run_group "G2  Ablasyon / 3r·15g  (60 deney)" "$LOG_DIR/g2_ablation.log" \
    --robots 3 --tasks 15 \
    --combos "$ABLATION_COMBOS"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  TÜM v3 DENEYLERİ TAMAMLANDI"
NDONE=$(find "$LOG_DIR" -name "DONE" 2>/dev/null | wc -l)
NVID=$(find "$LOG_DIR" -name "video_gazebo.mp4" 2>/dev/null | wc -l)
echo "  Toplam DONE: $NDONE / $TOTAL_EXPERIMENTS"
echo "  Video kayıt: $NVID adet (Gazebo — seed=01, 12 video)"
echo "  Bitiş: $(date)"
echo "════════════════════════════════════════════════════════════════"
