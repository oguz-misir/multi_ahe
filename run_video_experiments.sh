#!/usr/bin/env bash
# run_video_experiments.sh — RViz kanıt videoları (gerçek navigasyon).
#
# Headless Gazebo (gz_gui:=false) + tam Nav2 + RViz (:3) → RViz kaydı.
# Bu, robotların gerçek navigasyonunu (global/yerel planlar, harita, lazer,
# görev işaretçileri) gösteren GÜVENİLİR kayıttır.
#
# Gazebo 3D görüntüsü AYRI alınır (record_gazebo_view.sh) çünkü bu donanımda
# Gazebo-GUI + Nav2 aynı anda OOM'a yol açıyor. BİRLEŞTİRME YOK — ayrı videolar.
#
# Çıktı: results/videos/ahe_<N>r_t<M>_rviz.mp4
# Yeniden başlatılabilir: çıktı varsa o ölçek atlanır.

set -o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
source /opt/ros/jazzy/setup.bash
source "${SCRIPT_DIR}/install/setup.bash"

VIDEO_DIR="${SCRIPT_DIR}/results/videos"
RAW_DIR="${SCRIPT_DIR}/results/raw/gazebo_video"
mkdir -p "$VIDEO_DIR" "$RAW_DIR"

STRATEGY="ahe_mrta_v3"; SCENARIO="mixed_stress"; SEED="1"; SEED_PAD="01"

# (robot_count task_count startup_delay wall_timeout)
EXPERIMENTS=(
    "3  9   90.0   900"
    "3  15  90.0   960"
    "3  24  90.0   1080"
)

_ensure_xvfb() {
    local disp=$1
    DISPLAY=$disp xdpyinfo &>/dev/null || { Xvfb $disp -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &>/dev/null & sleep 2; }
    pgrep -f fluxbox &>/dev/null || { DISPLAY=$disp fluxbox &>/dev/null & sleep 1; }
    DISPLAY=$disp xsetroot -solid black 2>/dev/null || true
}
_ensure_xvfb :3

cleanup_ros() {
    pkill -9 -f "gz sim|gz_server|gzserver|parameter_bridge|ros_gz_bridge|ruby" 2>/dev/null
    pkill -9 -f "robot_interface_node|experiment_runner_node|ecosystem_manager|gz_path|tf_relay" 2>/dev/null
    pkill -9 -f "nav2|amcl|bt_navigator|planner_server|controller_server|lifecycle_manager|map_server|behavior_server|smoother|velocity_smoother|waypoint" 2>/dev/null
    pkill -9 -f "ros2 launch|ros2 run|rviz2|robot_state_publisher" 2>/dev/null
    rm -f /dev/shm/fastrtps_* /tmp/fastrtps_* /dev/shm/gz_* /tmp/gz_* 2>/dev/null
    sleep 5
}

load_guard() {
    while true; do
        local L; L=$(cut -d' ' -f1 /proc/loadavg | cut -d. -f1)
        [[ "$L" -lt 8 ]] && break
        echo "[yük] load=$L > 8, 30s bekleniyor..."; sleep 30
    done
}

for exp in "${EXPERIMENTS[@]}"; do
    read -r N M STARTUP WALL <<< "$exp"
    TAG="ahe_${N}r_t${M}"
    OUT="${VIDEO_DIR}/${TAG}_rviz.mp4"
    RES="${RAW_DIR}/${TAG}_rviz"
    DONE_FILE="${RES}/exp_${SCENARIO}_${STRATEGY}_r${N}t${M}_seed${SEED_PAD}/DONE"

    if [[ -f "$OUT" ]]; then echo "[SKIP] $TAG zaten var."; continue; fi

    echo ""
    echo "══════════════════════════════════════════════════════"
    echo "  $TAG  (robots=$N tasks=$M)  — RViz kaydı"
    echo "══════════════════════════════════════════════════════"
    mkdir -p "$RES"; rm -f "$DONE_FILE" 2>/dev/null
    load_guard; cleanup_ros
    DISPLAY=:3 xsetroot -solid black 2>/dev/null || true; sleep 1

    # RViz, Nav2 bringup'ı boğmamak için 110s gecikmeli başlar (phase9 rviz_delay).
    # ffmpeg'i de RViz belirmeden hemen önce başlat → siyah giriş olmasın.
    RVIZ_DELAY=110

    ros2 launch m_ahe_mrta_bringup phase9_demo.launch.py \
        strategy:="${STRATEGY}" scenario:="${SCENARIO}" seed:="${SEED}" \
        robot_count:="${N}" task_count:="${M}" results_dir:="${RES}" \
        startup_delay:="${STARTUP}" gz_gui:=false use_rviz:=true \
        rviz_delay:="${RVIZ_DELAY}.0" \
        > "${OUT%.mp4}_launch.log" 2>&1 &
    RP=$!

    # Nav2 bringup penceresini RViz/ffmpeg yükü olmadan geçir
    echo "  [bekle] Nav2 bringup için ${RVIZ_DELAY}s (RViz/ffmpeg yok)..."
    sleep $((RVIZ_DELAY - 5))

    # Şimdi ffmpeg başlat (RViz ~5s sonra belirecek)
    ffmpeg -y -loglevel warning -f x11grab -video_size 1920x1080 -framerate 25 \
        -i :3.0+0,0 -c:v libx264 -preset ultrafast -crf 23 "$OUT" \
        > "${OUT%.mp4}_ff.log" 2>&1 &
    FF=$!

    EL=$((RVIZ_DELAY - 5))
    while [[ ! -f "$DONE_FILE" ]] && kill -0 $RP 2>/dev/null; do
        sleep 10; EL=$((EL+10))
        [[ $EL -ge $WALL ]] && { echo "  [uyarı] ${WALL}s doldu"; break; }
        (( EL % 120 == 0 )) && echo "  [ilerleme] ${EL}s / ${WALL}s  load=$(cut -d' ' -f1 /proc/loadavg)"
    done
    [[ -f "$DONE_FILE" ]] && { echo "  [ok] DONE"; sleep 8; }

    kill -INT $FF 2>/dev/null; wait $FF 2>/dev/null
    kill -INT $RP 2>/dev/null; cleanup_ros

    [[ -f "$OUT" ]] && echo "[ok] $(du -h "$OUT"|cut -f1) → $OUT"
done

echo ""
echo "════════════════════════════════════════════════════════"
echo "  RViz kayıtları tamamlandı!"
ls -lh "${VIDEO_DIR}"/*_rviz.mp4 2>/dev/null
echo "════════════════════════════════════════════════════════"
