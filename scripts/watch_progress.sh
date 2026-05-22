#!/usr/bin/env bash
# Tamamlanan deney sonuçlarını terminalde izler.
# Önerilen yöntem (full_ahe_mrta) KIRMIZI ile vurgulanır.
# Kullanım: bash scripts/watch_progress.sh [sonuç_dizini]

RESULTS="${1:-/home/oguz/multi_ahe/results/raw/gazebo}"
LIVE_LOG="$RESULTS/../live_progress.tsv"
PROPOSED="full_ahe_mrta"

RED='\033[0;31m'
GRN='\033[0;32m'
NC='\033[0m'
BOLD='\033[1m'

header() {
    printf "${BOLD}%-35s %-15s %4s  %6s  %9s  %7s${NC}\n" \
        "Strateji" "Senaryo" "Seed" "TCR%" "Makespan" "WBalance"
    printf '%s\n' "$(printf '%.0s-' {1..80})"
}

print_row() {
    local strategy="$1" scenario="$2" seed="$3" tcr="$4" ms="$5" wb="$6"
    local fmt="%-35s %-15s %4s  %6s  %9s  %7s\n"
    if [ "$strategy" = "$PROPOSED" ]; then
        printf "${RED}${BOLD}${fmt}${NC}" "$strategy" "$scenario" "$seed" "$tcr" "$ms" "$wb"
    else
        printf "${fmt}" "$strategy" "$scenario" "$seed" "$tcr" "$ms" "$wb"
    fi
}

read_summary() {
    local csv="$1"
    # Başlık satırını bul, değerleri çek
    python3 - "$csv" <<'EOF'
import csv, sys
path = sys.argv[1]
with open(path) as f:
    reader = csv.DictReader(f)
    for row in reader:
        tcr  = row.get('task_completion_rate', row.get('tasks_completed','?'))
        ms   = row.get('makespan_s', row.get('makespan','?'))
        wb   = row.get('workload_balance', '?')
        strat= row.get('strategy','?')
        scen = row.get('scenario','?')
        seed = row.get('seed','?')
        # TCR genellikle 0-1 arası float; yüzdeye çevir
        try:
            tcr_pct = f"{float(tcr)*100:.1f}"
        except:
            tcr_pct = tcr
        try:
            ms_fmt = f"{float(ms):.1f}s"
        except:
            ms_fmt = ms
        try:
            wb_fmt = f"{float(wb):.3f}"
        except:
            wb_fmt = wb
        print(f"{strat}|{scen}|{seed}|{tcr_pct}|{ms_fmt}|{wb_fmt}")
        break
EOF
}

# TSV başlığı
mkdir -p "$(dirname "$LIVE_LOG")"
if [ ! -f "$LIVE_LOG" ]; then
    printf "strategy\tscenario\tseed\ttcr_pct\tmakespan_s\tworkload_balance\n" > "$LIVE_LOG"
fi

clear
echo "AHE-MRTA Deney İzleyici — $(date '+%H:%M:%S')"
echo "Sonuç dizini: $RESULTS"
echo ""
header

SEEN=()

while true; do
    mapfile -t DONE_FILES < <(find "$RESULTS" -name "DONE" | sort)
    for done_file in "${DONE_FILES[@]}"; do
        exp_dir="$(dirname "$done_file")"
        summary="$exp_dir/summary.csv"
        [ -f "$summary" ] || continue
        exp_id="$(basename "$exp_dir")"
        # Zaten gösterildiyse atla
        [[ " ${SEEN[*]} " == *" $exp_id "* ]] && continue
        SEEN+=("$exp_id")

        line="$(read_summary "$summary")"
        [ -z "$line" ] && continue
        IFS='|' read -r strategy scenario seed tcr ms wb <<< "$line"
        print_row "$strategy" "$scenario" "$seed" "$tcr" "$ms" "$wb"
        # TSV'ye ekle
        printf "%s\t%s\t%s\t%s\t%s\t%s\n" \
            "$strategy" "$scenario" "$seed" "$tcr" "$ms" "$wb" >> "$LIVE_LOG"
    done
    printf "\r[%s] Tamamlanan: %d / toplam beklenen: 85" "$(date '+%H:%M:%S')" "${#SEEN[@]}"
    sleep 30
done
