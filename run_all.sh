#!/usr/bin/env bash
# =============================================================================
# AHE-MRTA — Tek komutla tam offline deney + analiz pipeline'ı
#
# Kullanım:
#   bash run_all.sh                        # debug ölçek (3R/15T, 3 seed)
#   bash run_all.sh --scale paper          # makale ölçeği (5R/25T, 20 seed)
#   bash run_all.sh --scale both           # her iki ölçek
#   bash run_all.sh --scale paper --seeds "1 2 3 4 5"
#   bash run_all.sh --strategies "full_ahe_mrta greedy_nearest big_mrta"
#   bash run_all.sh --skip-experiments     # sadece analiz (mevcut veriden)
#
# Çıktılar:
#   results/raw/            — ham deney CSV'leri
#   results/processed/      — birleştirilmiş CSV'ler
#   results/paper_figures/  — 14 PNG figür (300 DPI)
#   results/reports/        — istatistik tabloları + özet rapor
# =============================================================================

set -e
REPO="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO"

# ── Varsayılan argümanlar ─────────────────────────────────────────────────────
SCALE="debug"
SEEDS="1 2 3"
STRATEGIES="all"
SKIP_EXP=0
RAW_DIR="results/raw"
DPI=300

# ── Argüman ayrıştırma ────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --scale)       SCALE="$2";       shift 2 ;;
        --seeds)       SEEDS="$2";       shift 2 ;;
        --strategies)  STRATEGIES="$2";  shift 2 ;;
        --raw-dir)     RAW_DIR="$2";     shift 2 ;;
        --dpi)         DPI="$2";         shift 2 ;;
        --skip-experiments) SKIP_EXP=1;  shift   ;;
        -h|--help)
            grep "^#" "$0" | head -20; exit 0 ;;
        *) echo "[HATA] Bilinmeyen argüman: $1"; exit 1 ;;
    esac
done

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          AHE-MRTA  Offline Experiment Pipeline               ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo "  Ölçek      : $SCALE"
echo "  Seed'ler   : $SEEDS"
echo "  Stratejiler: $STRATEGIES"
echo "  Ham klasör : $RAW_DIR"
echo ""

# ── Python kontrolü ───────────────────────────────────────────────────────────
PY=$(which python3)
if ! $PY -c "import pandas, matplotlib, numpy" 2>/dev/null; then
    echo "[KURULUM] Eksik paketler kuruluyor..."
    if [ -f "$HOME/.local/bin/pip" ]; then
        "$HOME/.local/bin/pip" install --break-system-packages pandas matplotlib numpy scipy 2>&1 | tail -3
    else
        echo "[HATA] pip bulunamadı. Şunu çalıştırın:"
        echo "  curl -sS https://bootstrap.pypa.io/get-pip.py | python3 - --user --break-system-packages"
        exit 1
    fi
fi

# ── Adım 1: Deneyler ──────────────────────────────────────────────────────────
if [ "$SKIP_EXP" -eq 0 ]; then
    echo "▶ Adım 1/4: Standalone simülasyon deneyleri çalıştırılıyor..."

    SEED_ARGS=""
    for s in $SEEDS; do SEED_ARGS="$SEED_ARGS $s"; done

    STRAT_ARGS=""
    if [ "$STRATEGIES" != "all" ]; then
        STRAT_ARGS="--strategies $STRATEGIES"
    fi

    $PY scripts/run_experiments.py \
        --scale "$SCALE" \
        --seeds $SEED_ARGS \
        $STRAT_ARGS \
        --results-dir "$RAW_DIR"

    echo "  ✓ Deneyler tamamlandı → $RAW_DIR/"
else
    echo "▶ Adım 1/4: Deneyler atlandı (--skip-experiments)"
fi

# ── Adım 2: Konsolidasyon ─────────────────────────────────────────────────────
echo ""
echo "▶ Adım 2/4: Ham CSV'ler birleştiriliyor..."
$PY scripts/consolidate_results.py \
    --raw-dir "$RAW_DIR" \
    --processed-dir results/processed

echo "  ✓ Konsolidasyon tamamlandı → results/processed/"

# ── Adım 3: Figürler ─────────────────────────────────────────────────────────
echo ""
echo "▶ Adım 3/4: Makale figürleri üretiliyor (${DPI} DPI)..."
mkdir -p results/paper_figures
$PY scripts/plot_results.py \
    --processed-dir results/processed \
    --output-dir results/paper_figures \
    --dpi "$DPI" 2>&1 | grep -E "^\[OK\]|\[DONE\]"

echo "  ✓ 14 PNG figür → results/paper_figures/"

# ── Adım 4: İstatistik + Rapor ────────────────────────────────────────────────
echo ""
echo "▶ Adım 4/4: İstatistiksel analiz ve rapor üretiliyor..."
mkdir -p results/reports
$PY scripts/statistical_analysis.py \
    --processed-dir results/processed \
    --output results/reports/statistical_tables.md 2>&1 | grep -v "UserWarning\|warnings.warn"

$PY scripts/report_generator.py \
    --processed-dir results/processed \
    --figures-dir results/paper_figures \
    --stats results/reports/statistical_tables.md \
    --output results/reports/summary_report.md

echo "  ✓ İstatistik tabloları → results/reports/statistical_tables.md"
echo "  ✓ Özet rapor          → results/reports/summary_report.md"

# ── Özet ─────────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    TAMAMLANDI                                ║"
echo "╚══════════════════════════════════════════════════════════════╝"

$PY - <<'PYEOF'
import pandas as pd, sys
try:
    df = pd.read_csv('results/processed/all_summary.csv')
    order = ['greedy_nearest','deadline_aware','auction_based','static_weighted',
             'big_mrta','rostam_ea','consensus_dbta',
             'ahe_no_dominance','ahe_no_cooperation_suppression',
             'ahe_no_event_replanning','ahe_fixed_context','full_ahe_mrta']
    labels = {'greedy_nearest':'Greedy','deadline_aware':'EDF','auction_based':'Auction',
              'static_weighted':'SW','big_mrta':'BiG-MRTA','rostam_ea':'RoSTAM-EA',
              'consensus_dbta':'Cons-DBTA','ahe_no_dominance':'AHE-NoD',
              'ahe_no_cooperation_suppression':'AHE-NoCS','ahe_no_event_replanning':'AHE-NoER',
              'ahe_fixed_context':'AHE-FC','full_ahe_mrta':'AHE-MRTA*'}
    methods = [m for m in order if m in df['strategy'].unique()]
    print(f"\n  {'Yöntem':<12}  {'Tamamlama':>10}  {'Makespan':>10}  {'WL Dengesi':>10}  {'DL İhlali':>10}")
    print("  " + "-"*56)
    for m in methods:
        s = df[df['strategy']==m]
        mark = " ◄" if m == 'full_ahe_mrta' else ""
        print(f"  {labels[m]:<12}  {s.task_completion_rate.mean():>10.3f}  "
              f"{s.makespan_s.mean():>10.1f}s  {s.workload_balance.mean():>10.3f}  "
              f"{s.deadline_violation_rate.mean():>10.3f}{mark}")
    print()
    print(f"  Toplam deney: {len(df)}")
    print(f"  Figürler:     results/paper_figures/ (14 PNG)")
    print(f"  Raporlar:     results/reports/")
except Exception as e:
    print(f"  [UYARI] Özet tablosu üretilemedi: {e}")
PYEOF

echo ""
echo "  Gazebo demo için:"
echo "  source install/setup.bash"
echo "  ros2 launch m_ahe_mrta_bringup phase9_demo.launch.py strategy:=full_ahe_mrta scenario:=robot_failure seed:=1"
echo ""
