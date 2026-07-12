#!/usr/bin/env bash
# F58 benchmark eki: 3r yoğunluk süpürmesi (9 ve 24 görev hücreleri).
# Efficiency/effectsize tablolarının orijinal tasarımı (yoğunluk 9/15/24
# havuzu, senaryo başına n=15) için 15-görev hücresine ek iki yoğunluk.
# 4 yöntem × 3 senaryo × 5 tohum × 2 yoğunluk = 120 koşu.
# Çökme sonrası aynı komutla devam: DONE'ları atlar.
set -o pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
source "$REPO/scripts/exp_lib.sh"
source "$REPO/install/setup.bash"
set -u

LOG="${F58_BENCH_LOG:-$REPO/results/f58_benchmark_campaign.log}"
RAW_ROOT="$REPO/results/raw/gazebo_benchmark_f58"
WATCHDOG_SILENCE_SEC=4500

export AHE_SIM_GEODESIC_EXECUTION=1
export AHE_F58_GEODESIC=1
export AHE_F58_FAIR_REPAIR=1
export AHE_F58_FAIR_RESERVATION_GAP=2
export AHE_F58_FAIR_EXTRA_QUEUE=1
export AHE_F58_FAIR_TERMINAL_TASKS_PER_ROBOT=3

count_done() { find "$1" -name DONE 2>/dev/null | wc -l; }
kill_attempt() {
    local pid="$1"
    echo "[$(date '+%F %T')] watchdog: deneme ağacı öldürülüyor (pid $pid)"
    pkill -9 -f "run_experiments_robust.sh" 2>/dev/null || true
    kill -9 "$pid" 2>/dev/null || true
    cleanup_ros_gz || true
}
run_attempt() {
    local robots="$1" tasks="$2" startup="$3" timeout="$4" outdir="$5"
    bash "$REPO/run_experiments_robust.sh" \
        --robots "$robots" --tasks "$tasks" \
        --startup "$startup" --timeout "$timeout" \
        --results-dir "$outdir" &
    local pid=$!
    while kill -0 "$pid" 2>/dev/null; do
        sleep 120
        local age=$(( $(date +%s) - $(stat -c %Y "$LOG" 2>/dev/null || date +%s) ))
        if [ "$age" -ge "$WATCHDOG_SILENCE_SEC" ]; then
            echo "[$(date '+%F %T')] watchdog: log ${age}s sessiz -> asılı deneme"
            kill_attempt "$pid"
            return 1
        fi
    done
    wait "$pid"
}

declare -A CFG=( [r3t9]="3 9 120 1200" [r3t24]="3 24 120 1500" )
TARGET=60
for scale in r3t9 r3t24; do
    read -r R T SU TO <<< "${CFG[$scale]}"
    outdir="$RAW_ROOT/$scale"
    mkdir -p "$outdir"
    stall=0
    while true; do
        before=$(count_done "$outdir")
        if [ "$before" -ge "$TARGET" ]; then
            echo "[$(date '+%F %T')] $scale: COMPLETE ($before/$TARGET DONE)"; break
        fi
        echo "[$(date '+%F %T')] $scale: deneme başlıyor (DONE=$before/$TARGET)"
        run_attempt "$R" "$T" "$SU" "$TO" "$outdir"; rc=$?
        after=$(count_done "$outdir")
        if [ "$after" -ge "$TARGET" ] && [ "$rc" -eq 0 ]; then
            echo "[$(date '+%F %T')] $scale: COMPLETE ($after/$TARGET DONE)"; break
        fi
        if [ "$after" -gt "$before" ]; then stall=0; else
            stall=$((stall + 1))
            echo "[$(date '+%F %T')] $scale: ilerleme yok (stall=$stall/3)"
            [ "$stall" -ge 3 ] && { echo "[$(date '+%F %T')] $scale: STALL ABORT"; exit 3; }
        fi
        cleanup_ros_gz || true
        sleep 10
    done
done
echo "[$(date '+%F %T')] YOGUNLUK SUPURMESI TAMAM: $(count_done "$RAW_ROOT/r3t9")+$(count_done "$RAW_ROOT/r3t24")/120 DONE"
