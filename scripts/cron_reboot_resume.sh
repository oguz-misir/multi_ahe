#!/usr/bin/env bash
# =============================================================================
# cron_reboot_resume.sh — @reboot ile çağrılır.
# Yalnızca yarım kalmış bir batch varsa (.batch_active bayrağı) devam ettirir.
# Böylece donma/çökme sonrası yeniden başlatmada batch KALDIĞI YERDEN sürer;
# alakasız boot'larda hiçbir şey başlatmaz.
# =============================================================================
REPO="/home/oguz/multi_ahe"
FLAG="$REPO/results/.batch_active"
LOG="$REPO/results/reboot_resume.log"

[ -f "$FLAG" ] || exit 0   # aktif batch yok → çık

sleep 90   # sistemin oturması için bekle (servisler, ağ, vs.)

echo "$(date '+%F %T') > reboot algılandı, .batch_active var → batch devam ettiriliyor" >> "$LOG"
cd "$REPO" || exit 1
MODE="$(cat "$REPO/results/.batch_mode" 2>/dev/null || echo single)"
if [ "$MODE" = "matrix" ]; then
    # Yoğunluk-sweep sürücüsü (3r × {9,15,24})
    nohup bash "$REPO/scripts/run_gazebo_matrix.sh" >> "$REPO/results/gazebo_matrix.log" 2>&1 &
    echo "$(date '+%F %T') > run_gazebo_matrix pid=$! (mode=matrix)" >> "$LOG"
else
    EXP="$(cat "$REPO/results/.batch_expected" 2>/dev/null || echo 60)"
    EXPECTED_TOTAL="$EXP" nohup bash "$REPO/run_until_complete.sh" >> "$REPO/results/until_complete.log" 2>&1 &
    echo "$(date '+%F %T') > run_until_complete pid=$! (hedef=$EXP)" >> "$LOG"
fi
