#!/usr/bin/env bash
# =============================================================================
# cron_status_report.sh — her 30 dk'da bir ilerleme/ETA raporu üretir.
# Yalnızca aktif bir batch varken (.batch_active) çalışır; raporu hem stdout'a
# hem results/status_report.log'a yazar, MEMORY ledger'ı yeniler.
# =============================================================================
REPO="/home/oguz/multi_ahe"
FLAG="$REPO/results/.batch_active"
LOG="$REPO/results/status_report.log"

[ -f "$FLAG" ] || exit 0   # aktif batch yok → sessizce çık

EXP="$(cat "$REPO/results/.batch_expected" 2>/dev/null || echo 60)"
RD="$(cat "$REPO/results/.batch_results_dir" 2>/dev/null || echo "$REPO/results/raw/gazebo")"

line=$(EXPECTED_TOTAL="$EXP" bash "$REPO/scripts/exp_status.sh" --results-dir "$RD" --expected "$EXP")
echo "$line" | tee -a "$LOG"
