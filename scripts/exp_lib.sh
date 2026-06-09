#!/usr/bin/env bash
# =============================================================================
# exp_lib.sh — AHE-MRTA ortak deney yardımcıları
#
#   cleanup_ros_gz   : tüm ROS2/Gazebo/Nav2 süreçlerini ve IPC çöplüğünü temizle
#   load_guard       : yeni deney başlatmadan önce yükü ve zombie'leri güvene al
#   record_done      : tamamlanan deneyi PROGRESS.md + MEMORY ledger'a işle
#
# Kullanım: `source scripts/exp_lib.sh` (REPO değişkeni set edilmiş olmalı).
# =============================================================================

# REPO yoksa bu dosyanın iki üstünü kök kabul et
: "${REPO:=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

# Yük koruması eşikleri (16 çekirdek → 10 makul; ortam değişkeniyle ezilebilir)
: "${MAX_LOAD:=10}"             # load1 bu değerin altına inmeden deney başlatma
: "${MAX_LOAD_WAIT:=900}"       # en fazla bu kadar bekle, sonra zorla temizleyip devam
: "${SETTLE_SLEEP:=5}"          # temizlik sonrası bekleme

AHE_PROC_RE="gz sim|gzserver|gz_server|gzclient|parameter_bridge|ros_gz_bridge|robot_state_pub|experiment_runner_node|ecosystem_manager|robot_interface_node|controller_server|planner_server|bt_navigator|amcl|map_server|lifecycle_manager|ros2 launch"

# ── Süreç + IPC temizliği ─────────────────────────────────────────────────────
cleanup_ros_gz() {
    pkill -TERM -f "gz sim"                                   2>/dev/null || true
    pkill -TERM -f "gz_server|gz_client|gzserver|gzclient"    2>/dev/null || true
    pkill -TERM -f "ros2 launch|ros2 run"                     2>/dev/null || true
    pkill -TERM -f "experiment_runner_node|ecosystem_manager" 2>/dev/null || true
    pkill -TERM -f "robot_interface_node|robot_state_pub"     2>/dev/null || true
    pkill -TERM -f "parameter_bridge|ros_gz_bridge"           2>/dev/null || true
    pkill -TERM -f "amcl|bt_navigator|controller_server|planner_server|map_server|lifecycle_manager" 2>/dev/null || true
    sleep 8
    pkill -KILL -f "gz sim|gz_server|gzserver|gzclient|parameter_bridge|ros_gz_bridge" 2>/dev/null || true
    pkill -KILL -f "experiment_runner_node|ecosystem_manager|robot_interface_node"     2>/dev/null || true
    pkill -KILL -f "amcl|bt_navigator|controller_server|planner_server|map_server|lifecycle_manager" 2>/dev/null || true
    pkill -KILL -f "robot_state_pub|ros2"                     2>/dev/null || true
    rm -f /dev/shm/fastrtps_* /tmp/fastrtps_* 2>/dev/null || true
    rm -f /dev/shm/gz_* /tmp/gz_* /dev/shm/sem.* 2>/dev/null || true
    sleep "$SETTLE_SLEEP"
}

# ── Yük koruması: yeni Gazebo deneyi başlatmadan önce ─────────────────────────
# 1) Artık (zombie) ROS/Gazebo süreçleri varsa temizle.
# 2) load1 eşiğin altına düşene kadar bekle (en fazla MAX_LOAD_WAIT).
load_guard() {
    local leftover
    # pgrep -fc eşleşme yoksa "0" basıp exit 1 döner; `|| echo 0` eklemek "0\n0"
    # üretip integer testini bozuyordu. `|| true` ile yalnız exit kodunu yut.
    leftover=$(pgrep -fc "$AHE_PROC_RE" 2>/dev/null || true)
    leftover=${leftover:-0}
    if [ "$leftover" -gt 0 ]; then
        echo "  [load_guard] $leftover artık süreç bulundu → temizleniyor"
        cleanup_ros_gz
    fi

    local waited=0
    while :; do
        local l; l=$(awk '{print $1}' /proc/loadavg)
        if awk -v a="$l" -v b="$MAX_LOAD" 'BEGIN{exit !(a<b)}'; then
            break
        fi
        if [ "$waited" -ge "$MAX_LOAD_WAIT" ]; then
            echo "  [load_guard] load=$l hâlâ yüksek ama ${MAX_LOAD_WAIT}s doldu → zorla temizleyip devam"
            cleanup_ros_gz
            break
        fi
        echo "  [load_guard] load=$l ≥ $MAX_LOAD → 15s bekle (toplam ${waited}s)"
        sleep 15
        waited=$(( waited + 15 ))
    done
}

# ── Tamamlanan deneyi kalıcı ledger'a yaz ─────────────────────────────────────
# record_done <experiment_id> <results_dir> [expected_total]
# DONE dosyaları gerçek kaynak; bu sadece insan-okunur + MEMORY özetini yeniler.
record_done() {
    local eid="$1" rdir="$2" expected="${3:-}"
    local ts; ts=$(date '+%Y-%m-%d %H:%M:%S')
    local prog="$REPO/results/PROGRESS.md"
    mkdir -p "$REPO/results"
    # idempotent: aynı eid satırını iki kez yazma
    if ! grep -q "| $eid |" "$prog" 2>/dev/null; then
        [ -f "$prog" ] || printf '# AHE-MRTA Deney İlerleme Ledger\n\n| Zaman | Deney ID | Süre(s) |\n|---|---|---|\n' > "$prog"
        local secs="?"; [ -f "$rdir/$eid/DONE" ] && secs=$(tr -d '\n ' < "$rdir/$eid/DONE")
        printf '| %s | %s | %s |\n' "$ts" "$eid" "$secs" >> "$prog"
    fi
    # MEMORY özetini yenile (varsa status script'i ile)
    if [ -f "$REPO/scripts/exp_status.sh" ]; then
        EXPECTED_TOTAL="${expected:-${EXPECTED_TOTAL:-60}}" \
            bash "$REPO/scripts/exp_status.sh" --results-dir "$rdir" --quiet 2>/dev/null || true
    fi
}
