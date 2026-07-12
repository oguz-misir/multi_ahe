#!/usr/bin/env bash
# F58 dört-yöntem benchmark kampanyası (karar 2026-07-10: makale F58 verisine geçer).
# Faz 1: sim düzlemleri (sim_fitness + sim_scalability; AHE=F58, temeller etkilenmez;
#        kilitli v45 CSV'leri *_v45_locked.csv olarak yedeklenir).
# Faz 2: Gazebo Harmonic benchmark — 3 ölçek × 4 yöntem × 3 senaryo × 5 tohum = 180 koşu.
#        Ölçek başına until-complete: DONE hedefi 60; runner hep exit 0 döner, tamamlanma
#        YALNIZ DONE sayısıyla ölçülür. Üç savunma: stall sayacı (3 ilerlemesiz deneme →
#        abort), 75 dk log-sessizliği watchdog'u (asılı ağacı öldür + yeniden dene),
#        load_guard (exp_lib, deney başına).
# Çökme/reboot sonrası: aynı komutla yeniden başlat — DONE'ları atlar.
set -o pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
source "$REPO/scripts/exp_lib.sh"
# ROS/colcon setup dosyaları nounset ile uyumsuz — source'tan SONRA aç
source "$REPO/install/setup.bash"
set -u

LOG="${F58_BENCH_LOG:-$REPO/results/f58_benchmark_campaign.log}"
RAW_ROOT="$REPO/results/raw/gazebo_benchmark_f58"
WATCHDOG_SILENCE_SEC=4500

# Sim yürütme oracle'ı: HERKES için geodezik zemin-gerçeği (F58 Nav2-bağımsız
# doğrulamayla aynı sözleşme; Öklid v45 düzleminden bilinçli ayrılış — tüm
# yöntemler aynı oracle'da ölçülür, adalet korunur).
export AHE_SIM_GEODESIC_EXECUTION=1
# F58 kolu bayrakları (yalnız AHE okur; big_mrta/rostam_ea/consensus_dbta etkilenmez)
export AHE_F58_GEODESIC=1
export AHE_F58_FAIR_REPAIR=1
export AHE_F58_FAIR_RESERVATION_GAP=2
export AHE_F58_FAIR_EXTRA_QUEUE=1
export AHE_F58_FAIR_TERMINAL_TASKS_PER_ROBOT=3

count_done() { find "$1" -name DONE 2>/dev/null | wc -l; }

# ── Faz 1: sim düzlemleri ────────────────────────────────────────────────────
SIM_MARK="$REPO/results/processed/F58_BENCH_SIM_DONE"
if [ ! -f "$SIM_MARK" ]; then
    echo "[$(date '+%F %T')] FAZ1: sim düzlemleri (AHE=F58, 100 tohum)"
    for f in sim_fitness sim_scalability; do
        if [ -f "$REPO/results/processed/$f.csv" ] && \
           [ ! -f "$REPO/results/processed/${f}_v45_locked.csv" ]; then
            cp "$REPO/results/processed/$f.csv" \
               "$REPO/results/processed/${f}_v45_locked.csv"
        fi
    done
    python3 "$REPO/scripts/simulate_and_tune.py" --seeds 100 --scenario all
    python3 "$REPO/scripts/simulate_and_tune.py" --seeds 100 --scenario all \
        --robot-counts 3,5,10
    touch "$SIM_MARK"
    echo "[$(date '+%F %T')] FAZ1 TAMAM (CSV'ler results/processed/ altında; v45 yedekli)"
else
    echo "[$(date '+%F %T')] FAZ1 atlandı (marker var)"
fi

# ── Faz 2: Gazebo benchmark ─────────────────────────────────────────────────
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

# ölçek: robots tasks startup timeout   (10r değerleri doğrulanmış ölçek
# kampanyasından; REKICK runner'da aktif)
declare -A CFG=(
    [r3t15]="3 15 120 1200"
    [r5t25]="5 25 120 1500"
    [r10t50]="10 50 480 2400"
)
TARGET=60   # 4 yöntem × 3 senaryo × 5 tohum

for scale in r3t15 r5t25 r10t50; do
    read -r R T SU TO <<< "${CFG[$scale]}"
    outdir="$RAW_ROOT/$scale"
    mkdir -p "$outdir"
    stall=0
    while true; do
        before=$(count_done "$outdir")
        if [ "$before" -ge "$TARGET" ]; then
            echo "[$(date '+%F %T')] $scale: COMPLETE ($before/$TARGET DONE)"
            break
        fi
        echo "[$(date '+%F %T')] $scale: deneme başlıyor (DONE=$before/$TARGET)"
        run_attempt "$R" "$T" "$SU" "$TO" "$outdir"
        rc=$?
        after=$(count_done "$outdir")
        if [ "$after" -ge "$TARGET" ] && [ "$rc" -eq 0 ]; then
            echo "[$(date '+%F %T')] $scale: COMPLETE ($after/$TARGET DONE)"
            break
        fi
        if [ "$after" -gt "$before" ]; then
            stall=0
        else
            stall=$((stall + 1))
            echo "[$(date '+%F %T')] $scale: ilerleme yok (stall=$stall/3)"
            if [ "$stall" -ge 3 ]; then
                echo "[$(date '+%F %T')] $scale: STALL ABORT — elle inceleme gerekli"
                exit 3
            fi
        fi
        cleanup_ros_gz || true
        sleep 10
    done
done

echo "[$(date '+%F %T')] F58 BENCHMARK KAMPANYASI TAMAM: $(count_done "$RAW_ROOT")/180 DONE"
