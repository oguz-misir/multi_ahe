#!/usr/bin/env bash
# =============================================================================
# AHE-MRTA — Robust Gazebo Experiment Batch Runner  (çok ölçekli, video destekli)
#
# Kullanım:
#   bash run_experiments_robust.sh                          # varsayılan (3r/15g, tüm combos)
#   bash run_experiments_robust.sh --robots 5 --tasks 15   # 5r/15g ölçeği
#   bash run_experiments_robust.sh --robots 10 --tasks 25  # 10r/25g ölçeği
#   bash run_experiments_robust.sh --robots 15 --tasks 35  # 15r/35g ölçeği
#   bash run_experiments_robust.sh --record-video           # seed=01 için Gazebo+RViz mp4
#   bash run_experiments_robust.sh --combos "ahe_mrta_v3 robot_failure,big_mrta mixed_stress"
#   bash run_experiments_robust.sh --chunk 1 --size 5      # ilk 5 deney
#   bash run_experiments_robust.sh --seeds "1 2 3"
#   bash run_experiments_robust.sh --dry-run
# =============================================================================

set -eo pipefail
REPO="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO"
# Ortak yük koruması + temizlik + DONE ledger yardımcıları
source "$REPO/scripts/exp_lib.sh"
EXPECTED_TOTAL="${EXPECTED_TOTAL:-60}"

# ── Varsayılanlar ─────────────────────────────────────────────────────────────
DRY_RUN=0
SKIP_DONE=1
CHUNK=0
CHUNK_SIZE=0
SEEDS="1 2 3 4 5"
RESULTS_DIR="$REPO/results/raw/gazebo"
ROBOT_COUNT=3
TASK_COUNT=15
STARTUP_DELAY=75.0
TIMEOUT_SEC=900
COMBOS_OVERRIDE=""   # "strategy1 scenario1,strategy2 scenario2,..."
RECORD_VIDEO=0       # 1 = seed=01 için Gazebo + RViz mp4 kaydet
VIDEO_SEED=1         # video kaydı yapılacak seed (varsayılan 01)
VIDEO_DISPLAY_GZ=":1"   # Gazebo Xvfb display
VIDEO_DISPLAY_RV=":2"   # RViz Xvfb display

# ── Argüman ayrıştırma ────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)    DRY_RUN=1;               shift ;;
        --skip-done)  SKIP_DONE="$2";          shift 2 ;;
        --chunk)      CHUNK="$2";              shift 2 ;;
        --size)       CHUNK_SIZE="$2";         shift 2 ;;
        --seeds)      SEEDS="$2";              shift 2 ;;
        --timeout)    TIMEOUT_SEC="$2";        shift 2 ;;
        --robots)     ROBOT_COUNT="$2";        shift 2 ;;
        --tasks)      TASK_COUNT="$2";         shift 2 ;;
        --startup)    STARTUP_DELAY="$2";      shift 2 ;;
        --combos)     COMBOS_OVERRIDE="$2";    shift 2 ;;
        --results-dir) RESULTS_DIR="$2";       shift 2 ;;
        --record-video) RECORD_VIDEO=1;        shift ;;
        --video-seed) VIDEO_SEED="$2";         shift 2 ;;
        -h|--help)    grep "^#" "$0" | head -20; exit 0 ;;
        *) echo "[HATA] Bilinmeyen argüman: $1"; exit 1 ;;
    esac
done

# Robot sayısına göre startup delay ve timeout otomatik ayarla
if [[ -z "$STARTUP_DELAY" ]] || [[ "$STARTUP_DELAY" == "75.0" ]]; then
    case "$ROBOT_COUNT" in
        3)  STARTUP_DELAY=120.0; TIMEOUT_SEC=1200 ;;
        5)  STARTUP_DELAY=120.0; TIMEOUT_SEC=1200 ;;
        10) STARTUP_DELAY=360.0; TIMEOUT_SEC=1800 ;;
        20) STARTUP_DELAY=180.0; TIMEOUT_SEC=1380 ;;
        *)  STARTUP_DELAY=90.0;  TIMEOUT_SEC=960  ;;
    esac
fi
# gazebo_startup_delay_sec param'ı DOUBLE olmalı (ana_method §7.4) — tamsayı
# verilirse ".0" ekleyerek float'a zorla (InvalidParameterTypeException önler).
[[ "$STARTUP_DELAY" == *.* ]] || STARTUP_DELAY="${STARTUP_DELAY}.0"

SCALE_TAG="r${ROBOT_COUNT}t${TASK_COUNT}"
mkdir -p "$RESULTS_DIR"

# ── Workspace source ──────────────────────────────────────────────────────────
if [ -f "$REPO/install/setup.bash" ]; then
    source "$REPO/install/setup.bash"
fi
if ! command -v ros2 &>/dev/null; then
    echo "[HATA] ROS2 bulunamadı."
    exit 1
fi

# Video kayıt seçildiyse Xvfb + ffmpeg + rviz2 zorunlu
if [ "$RECORD_VIDEO" -eq 1 ]; then
    for tool in Xvfb ffmpeg rviz2; do
        if ! command -v "$tool" &>/dev/null; then
            echo "[HATA] --record-video için '$tool' gerekli ama bulunamadı."
            echo "       Xvfb için: sudo apt install xvfb"
            exit 1
        fi
    done
fi

export DISPLAY="${DISPLAY:-:1}"
unset GTK_PATH GTK_EXE_PREFIX GTK_MODULES GTK_IM_MODULE_FILE 2>/dev/null || true
export FASTRTPS_DEFAULT_PROFILES_FILE="$REPO/fastdds_udp_only.xml"

# ── Deney kombinasyonları ─────────────────────────────────────────────────────
declare -a ALL_COMBOS

if [[ -n "$COMBOS_OVERRIDE" ]]; then
    IFS=',' read -ra ALL_COMBOS <<< "$COMBOS_OVERRIDE"
else
    # Varsayılan: G1 karşılaştırma kombinasyonları (3r/15g)
    ALL_COMBOS=(
        "ahe_mrta_v3                robot_failure"
        "ahe_mrta_v3                mixed_stress"
        "ahe_mrta_v3                deadline_pressure"
        "big_mrta                   robot_failure"
        "big_mrta                   mixed_stress"
        "big_mrta                   deadline_pressure"
        "rostam_ea                  robot_failure"
        "rostam_ea                  mixed_stress"
        "rostam_ea                  deadline_pressure"
        "consensus_dbta             robot_failure"
        "consensus_dbta             mixed_stress"
        "consensus_dbta             deadline_pressure"
    )
fi

declare -a EXPERIMENT_LIST=()
for entry in "${ALL_COMBOS[@]}"; do
    read -r strategy scenario <<< "$entry"
    for seed in $SEEDS; do
        EXPERIMENT_LIST+=("${strategy} ${scenario} ${seed}")
    done
done

TOTAL=${#EXPERIMENT_LIST[@]}

# ── Chunk filtresi ────────────────────────────────────────────────────────────
START_IDX=0
END_IDX=$TOTAL
if [ "$CHUNK" -gt 0 ] && [ "$CHUNK_SIZE" -gt 0 ]; then
    START_IDX=$(( (CHUNK - 1) * CHUNK_SIZE ))
    END_IDX=$(( START_IDX + CHUNK_SIZE ))
    [ "$END_IDX" -gt "$TOTAL" ] && END_IDX=$TOTAL
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║         AHE-MRTA  Robust Gazebo Batch Experiments               ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
printf "  Ölçek        : %s robots / %s tasks  (%s)\n" "$ROBOT_COUNT" "$TASK_COUNT" "$SCALE_TAG"
echo "  Seeds        : $SEEDS"
echo "  Startup      : ${STARTUP_DELAY}s   Timeout: ${TIMEOUT_SEC}s"
echo "  Skip-done    : $SKIP_DONE   Dry-run: $DRY_RUN"
[ "$CHUNK" -gt 0 ] && echo "  Chunk        : $CHUNK (exp $((START_IDX+1))-${END_IDX} / $TOTAL)"
echo "  Sonuç        : $RESULTS_DIR"
echo ""

# ── Video kayıt yardımcıları ──────────────────────────────────────────────────
# Yalnızca --record-video bayrağı verildiğinde ve current seed == VIDEO_SEED
# olduğunda çağrılır. Her ikisi de iki ayrı Xvfb framebuffer kullanır:
#   :1 → Gazebo GUI ekranı (1280×720)
#   :2 → RViz penceresi    (1280×720)
# ffmpeg arka planda kaydeder. teardown SIGTERM ile yapılır.

start_video_recording() {
    local exp_dir="$1"
    mkdir -p "$exp_dir"

    # Xvfb framebuffer'larını başlat (yoksa)
    if ! pgrep -f "Xvfb $VIDEO_DISPLAY_GZ" > /dev/null; then
        Xvfb "$VIDEO_DISPLAY_GZ" -screen 0 1280x720x24 > /dev/null 2>&1 &
        echo $! > /tmp/ahe_xvfb_gz.pid
    fi
    if ! pgrep -f "Xvfb $VIDEO_DISPLAY_RV" > /dev/null; then
        Xvfb "$VIDEO_DISPLAY_RV" -screen 0 1280x720x24 > /dev/null 2>&1 &
        echo $! > /tmp/ahe_xvfb_rv.pid
    fi
    sleep 1

    # RViz'i ayrı Xvfb üzerinde aç (deney monitor config'i)
    local rviz_cfg
    rviz_cfg="$REPO/src/m_ahe_mrta_bringup/config/experiment_monitor.rviz"
    if [ -f "$rviz_cfg" ]; then
        DISPLAY="$VIDEO_DISPLAY_RV" ros2 run rviz2 rviz2 -d "$rviz_cfg" \
            > "$exp_dir/rviz.log" 2>&1 &
        echo $! > /tmp/ahe_rviz.pid
        sleep 2
    fi

    # ffmpeg paralel kayıt (Gazebo GUI ekranı + RViz ekranı)
    ffmpeg -y -hide_banner -loglevel error \
        -f x11grab -r 30 -s 1280x720 -i "$VIDEO_DISPLAY_GZ" \
        -c:v libx264 -preset ultrafast -crf 23 -pix_fmt yuv420p \
        "$exp_dir/video_gazebo.mp4" > "$exp_dir/ffmpeg_gz.log" 2>&1 &
    echo $! > /tmp/ahe_ffmpeg_gz.pid

    ffmpeg -y -hide_banner -loglevel error \
        -f x11grab -r 30 -s 1280x720 -i "$VIDEO_DISPLAY_RV" \
        -c:v libx264 -preset ultrafast -crf 23 -pix_fmt yuv420p \
        "$exp_dir/video_rviz.mp4" > "$exp_dir/ffmpeg_rv.log" 2>&1 &
    echo $! > /tmp/ahe_ffmpeg_rv.pid

    echo "   📹 Video kaydı başladı (gazebo + rviz)"
}

stop_video_recording() {
    # ffmpeg child'ları SIGTERM ile düzgün kapatma — moov atom yazılması için kritik
    for pidfile in /tmp/ahe_ffmpeg_gz.pid /tmp/ahe_ffmpeg_rv.pid; do
        if [ -f "$pidfile" ]; then
            local pid; pid=$(cat "$pidfile")
            kill -SIGTERM "$pid" 2>/dev/null || true
            wait "$pid" 2>/dev/null || true
            rm -f "$pidfile"
        fi
    done
    # RViz'i kapat
    if [ -f /tmp/ahe_rviz.pid ]; then
        kill -SIGTERM "$(cat /tmp/ahe_rviz.pid)" 2>/dev/null || true
        rm -f /tmp/ahe_rviz.pid
    fi
    echo "   📹 Video kaydı durduruldu"
}

stop_xvfb() {
    for pidfile in /tmp/ahe_xvfb_gz.pid /tmp/ahe_xvfb_rv.pid; do
        if [ -f "$pidfile" ]; then
            kill -SIGTERM "$(cat "$pidfile")" 2>/dev/null || true
            rm -f "$pidfile"
        fi
    done
}

# ── Süreç temizleyici ─────────────────────────────────────────────────────────
kill_all_ros_gz() {
    echo "  [cleanup] Tüm ROS/Gazebo süreçleri durduruluyor..."
    pkill -TERM -f "gz sim"                  2>/dev/null || true
    pkill -TERM -f "gz_server\|gz_client\|gzserver\|gzclient" 2>/dev/null || true
    pkill -TERM -f "ros2 launch"             2>/dev/null || true
    pkill -TERM -f "robot_state_pub"         2>/dev/null || true
    pkill -TERM -f "experiment_runner_node"  2>/dev/null || true
    pkill -TERM -f "ecosystem_manager"       2>/dev/null || true
    pkill -TERM -f "robot_interface_node"    2>/dev/null || true
    pkill -TERM -f "parameter_bridge\|ros_gz_bridge" 2>/dev/null || true
    pkill -TERM -f "amcl\|bt_nav\|controller_server\|planner_server\|map_server" 2>/dev/null || true
    sleep 8
    pkill -KILL -f "gz sim\|gz_server\|gzserver\|parameter_bridge" 2>/dev/null || true
    pkill -KILL -f "experiment_runner_node\|ecosystem_manager" 2>/dev/null || true
    pkill -KILL -f "robot_interface_node"    2>/dev/null || true
    pkill -KILL -f "amcl\|bt_navigator\|controller_server\|planner_server\|map_server" 2>/dev/null || true
    pkill -KILL -f "ros2" 2>/dev/null || true
    rm -f /dev/shm/fastrtps_* /tmp/fastrtps_* 2>/dev/null || true
    rm -f /dev/shm/gz_* /tmp/gz_* 2>/dev/null || true
    sleep 5
    echo "  [cleanup] Temiz."
}

# ── Experiment ID ─────────────────────────────────────────────────────────────
exp_id() {
    printf "exp_%s_%s_%s_seed%02d" "$2" "$1" "$SCALE_TAG" "$3"
}

# ── Tek deney çalıştırıcı ────────────────────────────────────────────────────
run_one() {
    local strategy="$1" scenario="$2" seed="$3" num="$4" of="$5"
    local eid; eid=$(exp_id "$strategy" "$scenario" "$seed")
    local done_file="$RESULTS_DIR/${eid}/DONE"

    echo ""
    echo "── Deney $num/$of ─────────────────────────────────────────────────"
    echo "   ID       : $eid"
    echo "   Strategy : $strategy  |  Scenario: $scenario  |  Seed: $seed"

    if [ "$SKIP_DONE" -eq 1 ] && [ -f "$done_file" ]; then
        echo "   ⏭  SKIP — DONE ($(cat "$done_file" | tr -d '\n') s)"
        return 0
    fi

    if [ "$DRY_RUN" -eq 1 ]; then
        echo "   [dry-run] ros2 launch ... strategy:=$strategy scenario:=$scenario seed:=$seed robot_count:=$ROBOT_COUNT task_count:=$TASK_COUNT"
        return 0
    fi

    # Yük koruması: load eşiğin altına inip artık süreçler temizlenene kadar bekle
    load_guard
    kill_all_ros_gz

    # Video kaydı: yalnızca --record-video bayrağı + bu seed eşleşiyorsa
    local record_this=0
    if [ "$RECORD_VIDEO" -eq 1 ] && [ "$seed" = "$VIDEO_SEED" ]; then
        record_this=1
    fi

    local log_file="$RESULTS_DIR/${eid}.log"
    local exp_dir="$RESULTS_DIR/${eid}"
    # Retry markers describe the previous attempt, not the experiment ID
    # forever.  Clear them immediately before a fresh launch so a successful
    # retry cannot remain falsely labelled as a startup/time-jump failure.
    mkdir -p "$exp_dir"
    rm -f "$exp_dir/STARTUP_FAILED" "$exp_dir/INVALID_TIMEJUMP"
    local gz_gui_arg="false"
    if [ "$record_this" -eq 1 ]; then
        gz_gui_arg="true"
        export DISPLAY="$VIDEO_DISPLAY_GZ"
        start_video_recording "$exp_dir"
    else
        export DISPLAY="${DISPLAY:-:1}"
    fi

    local cmd="ros2 launch m_ahe_mrta_bringup phase9_experiments.launch.py \
        strategy:=${strategy} scenario:=${scenario} seed:=${seed} \
        robot_count:=${ROBOT_COUNT} task_count:=${TASK_COUNT} \
        results_dir:=${RESULTS_DIR} startup_delay:=${STARTUP_DELAY} \
        gz_gui:=${gz_gui_arg}"

    echo "   ▶ Başlatılıyor..."
    local t_start=$SECONDS
    # -k: ros2 launch teardown can wedge under heavy load (D-state children
    # ignore TERM); escalate to KILL so a run can never block the batch.
    if timeout -k 60 "$TIMEOUT_SEC" bash -c "$cmd" > "$log_file" 2>&1; then
        echo "   ✓ Tamamlandı ($(( SECONDS - t_start ))s)"
    else
        local ec=$?
        [ $ec -eq 124 ] && echo "   ⚠ Timeout (${TIMEOUT_SEC}s geçti)" \
                        || echo "   ✗ Hata (exit=$ec) — log: $log_file"
    fi

    # A hard-killed previous Gazebo process can keep publishing an old /clock,
    # producing hundreds of thousands of TF "jump back in time" warnings and
    # a formally complete but physically invalid run.  Quarantine such output;
    # skip-done will rerun it on the next campaign invocation.
    local time_jumps=0
    if [ -f "$log_file" ]; then
        time_jumps=$(grep -c "Detected jump back in time" "$log_file" 2>/dev/null || true)
    fi
    if [ "$time_jumps" -gt "${MAX_TIME_JUMPS:-5}" ]; then
        echo "   ✗ INVALID — TF time jumps: $time_jumps"
        printf 'tf_time_jumps=%s\n' "$time_jumps" > "$exp_dir/INVALID_TIMEJUMP"
        if [ -f "$done_file" ]; then
            mv "$done_file" "$exp_dir/DONE.invalid_timejump"
        fi
    fi

    if [ "$record_this" -eq 1 ]; then
        stop_video_recording
    fi

    if [ -f "$done_file" ]; then
        echo "   ✓ DONE ✓"
        # Tamamlanan deneyi kalıcı ledger + MEMORY özetine işle
        record_done "$eid" "$RESULTS_DIR" "$EXPECTED_TOTAL" || true
    else
        echo "   ⚠ DONE yok — log inceleyin: $log_file"
    fi
}

# ── Ana döngü ─────────────────────────────────────────────────────────────────
RUN_NUM=0; SKIP_NUM=0
for i in "${!EXPERIMENT_LIST[@]}"; do
    [ "$i" -lt "$START_IDX" ] || [ "$i" -ge "$END_IDX" ] && continue
    read -r strategy scenario seed <<< "${EXPERIMENT_LIST[$i]}"
    eid=$(exp_id "$strategy" "$scenario" "$seed")
    if [ "$SKIP_DONE" -eq 1 ] && [ -f "$RESULTS_DIR/${eid}/DONE" ]; then
        SKIP_NUM=$(( SKIP_NUM + 1 ))
    else
        RUN_NUM=$(( RUN_NUM + 1 ))
    fi
    run_one "$strategy" "$scenario" "$seed" $(( i - START_IDX + 1 )) $(( END_IDX - START_IDX ))
done

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                      Batch Tamamlandı                           ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
NDONE=$(find "$RESULTS_DIR" -name "DONE" 2>/dev/null | wc -l)
echo "  Çalıştırılan : $RUN_NUM  |  Atlanan: $SKIP_NUM  |  Toplam DONE: $NDONE"
echo ""
