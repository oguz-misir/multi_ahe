#!/usr/bin/env bash
# =============================================================================
# exp_status.sh — AHE-MRTA deney ilerleme + ETA raporu
#
# DONE dosyalarını (gerçek kaynak) sayar; geçen süre / ortalama / kalan / ETA
# hesaplar; üç yere yazar:
#   1) stdout (insan-okunur özet)   — cron her 45 dk bunu loglar
#   2) results/PROGRESS_STATUS.md   — repo içi anlık durum
#   3) MEMORY ledger dosyası        — /clear sonrası hatırlama için
#
# Kullanım:
#   bash scripts/exp_status.sh [--results-dir DIR] [--expected N] [--quiet]
#   EXPECTED_TOTAL=60 bash scripts/exp_status.sh --quiet
# =============================================================================

REPO="$(cd "$(dirname "$0")/.." && pwd)"
RESULTS_DIR="$REPO/results/raw/gazebo"
EXPECTED="${EXPECTED_TOTAL:-60}"
QUIET=0
MEM_DIR="/home/oguz/.claude/projects/-home-oguz-multi-ahe/memory"
MEM_FILE="$MEM_DIR/experiment_progress.md"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --results-dir) RESULTS_DIR="$2"; shift 2 ;;
        --expected)    EXPECTED="$2";    shift 2 ;;
        --quiet)       QUIET=1;          shift ;;
        --mem-file)    MEM_FILE="$2";    shift 2 ;;
        *) shift ;;
    esac
done

now_epoch=$(date +%s)
now_h=$(date '+%Y-%m-%d %H:%M:%S')

# ── DONE say + en eski/yeni zaman damgaları ───────────────────────────────────
mapfile -t DONES < <(find "$RESULTS_DIR" -name DONE -printf '%T@\n' 2>/dev/null | sort -n)
done_count=${#DONES[@]}
remaining=$(( EXPECTED - done_count ))
[ "$remaining" -lt 0 ] && remaining=0

eta_h="—"; avg_h="—"; elapsed_h="—"; rate_h="—"
if [ "$done_count" -gt 0 ]; then
    first_epoch=${DONES[0]%.*}
    last_epoch=${DONES[$((done_count-1))]%.*}
    elapsed=$(( now_epoch - first_epoch ))
    [ "$elapsed" -lt 1 ] && elapsed=1
    avg=$(( elapsed / done_count ))
    eta=$(( avg * remaining ))
    fmt() { local s=$1; printf '%dsa %ddk' $(( s/3600 )) $(( (s%3600)/60 )); }
    elapsed_h=$(fmt "$elapsed")
    avg_h="$(( avg/60 ))dk $(( avg%60 ))s"
    eta_h=$(fmt "$eta")
    rate_h="$(awk -v d="$done_count" -v e="$elapsed" 'BEGIN{printf "%.1f", d/(e/3600)}')/saat"
fi

pct=0; [ "$EXPECTED" -gt 0 ] && pct=$(( done_count * 100 / EXPECTED ))

# ── stdout özet ───────────────────────────────────────────────────────────────
SUMMARY="[$now_h] İlerleme: $done_count/$EXPECTED (%$pct) | kalan: $remaining | geçen: $elapsed_h | ort/deney: $avg_h | hız: $rate_h | tahmini kalan (ETA): $eta_h"
[ "$QUIET" -eq 0 ] && echo "$SUMMARY"

# ── results/PROGRESS_STATUS.md ────────────────────────────────────────────────
mkdir -p "$REPO/results"
{
    echo "# AHE-MRTA Deney Durumu"
    echo
    echo "- **Güncelleme:** $now_h"
    echo "- **Tamamlanan:** $done_count / $EXPECTED  (%$pct)"
    echo "- **Kalan:** $remaining deney"
    echo "- **Geçen süre:** $elapsed_h   |   **Ort/deney:** $avg_h   |   **Hız:** $rate_h"
    echo "- **Tahmini kalan süre (ETA):** $eta_h"
    echo "- **Sonuç dizini:** \`$RESULTS_DIR\`"
} > "$REPO/results/PROGRESS_STATUS.md"

# ── MEMORY ledger (frontmatter + özet; /clear sonrası hatırlanır) ─────────────
if [ -d "$MEM_DIR" ]; then
    {
        echo "---"
        echo "name: experiment-progress"
        echo "description: \"Canlı Gazebo batch ilerlemesi: $done_count/$EXPECTED DONE (%$pct), ETA $eta_h — güncelleme $now_h\""
        echo "metadata:"
        echo "  type: project"
        echo "---"
        echo
        echo "Canlı deney ilerleme ledger'ı (otomatik; \`scripts/exp_status.sh\` yazar). Kaynak = disk DONE dosyaları."
        echo
        echo "## Anlık durum ($now_h)"
        echo
        echo "- **$done_count / $EXPECTED DONE** (%$pct), kalan **$remaining**"
        echo "- Geçen: $elapsed_h · ort/deney: $avg_h · hız: $rate_h · **ETA: $eta_h**"
        echo "- Dizin: \`$RESULTS_DIR\`"
        echo
        echo "Devam: \`bash run_until_complete.sh\` (DONE olanlar atlanır). Detay ledger: \`results/PROGRESS.md\`."
        echo "İlgili: [[project-batch-status]] · [[evaluation-framework]]"
    } > "$MEM_FILE"
fi
