#!/usr/bin/env bash
# capture_method_shots.sh — her yöntem için tek-kare RViz ekran görüntüsü
# (yol planları + lidar + costmap + robot modeli). Makale figürü için.
# Headless Gazebo (gz_gui:=false) + Nav2 (AMCL) + RViz (:3) → ffmpeg tek-kare.
# Gazebo 3D görünümü ayrı (record_gazebo_view.sh). 3r, deadline_pressure
# (tüm robotlar aktif → net yollar). Kullanım: bash scripts/capture_method_shots.sh
set -o pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"; cd "$REPO"
source /opt/ros/jazzy/setup.bash 2>/dev/null
source install/setup.bash 2>/dev/null

DISP=:3
N=3 ; M=9 ; SCEN="deadline_pressure" ; SEED=1
# startup düşük → dispatch erken; capture geç → yollar+lidar kesin çizili.
STARTUP="${STARTUP:-60}" ; RVIZ_DELAY="${RVIZ_DELAY:-100}" ; NAV_SETTLE="${NAV_SETTLE:-170}"
OUTDIR="results/figures/method_shots"; mkdir -p "$OUTDIR"
read -ra METHODS <<< "${METHODS:-ahe_mrta_v3 big_mrta rostam_ea consensus_dbta}"

_xvfb() {
    DISPLAY=$DISP xdpyinfo &>/dev/null || { Xvfb $DISP -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &>/dev/null & sleep 2; }
    pgrep -f fluxbox &>/dev/null || { DISPLAY=$DISP fluxbox &>/dev/null & sleep 1; }
    DISPLAY=$DISP xsetroot -solid white 2>/dev/null || true
}
_clean() {
    pkill -9 -f "gz sim|gz_server|gzserver|parameter_bridge|ros_gz_bridge|ruby" 2>/dev/null
    pkill -9 -f "robot_interface_node|experiment_runner_node|ecosystem_manager|gz_path|tf_relay" 2>/dev/null
    pkill -9 -f "nav2|amcl|bt_navigator|planner_server|controller_server|lifecycle_manager|map_server|behavior_server|smoother|waypoint" 2>/dev/null
    pkill -9 -f "ros2 launch|ros2 run|rviz2|robot_state_publisher" 2>/dev/null
    rm -f /dev/shm/fastrtps_* /tmp/fastrtps_* /dev/shm/gz_* /tmp/gz_* 2>/dev/null
    sleep 5
}

_xvfb
for m in "${METHODS[@]}"; do
    echo "════════ $m ════════"
    _clean
    RES="results/raw/_shot_${m}"; rm -rf "$RES"; mkdir -p "$RES"
    DOM=$((20 + RANDOM % 70))
    echo "  [launch] $m (domain=$DOM)"
    ROS_DOMAIN_ID=$DOM ros2 launch m_ahe_mrta_bringup phase9_demo.launch.py \
        strategy:="$m" scenario:="$SCEN" seed:="$SEED" \
        robot_count:="$N" task_count:="$M" results_dir:="$RES" \
        startup_delay:="${STARTUP}.0" gz_gui:=false use_rviz:=true \
        rviz_delay:="${RVIZ_DELAY}.0" > "$OUTDIR/${m}_launch.log" 2>&1 &
    LP=$!
    echo "  [bekle] Nav2+RViz init ${RVIZ_DELAY}s + nav settle ${NAV_SETTLE}s..."
    sleep $((RVIZ_DELAY + NAV_SETTLE))
    # RViz penceresini tam ekran
    WID=$(DISPLAY=$DISP wmctrl -l 2>/dev/null | grep -i "RViz" | awk '{print $1}' | head -1)
    [[ -n "$WID" ]] && { DISPLAY=$DISP wmctrl -i -r "$WID" -b add,fullscreen 2>/dev/null; sleep 3; }
    echo "  [shot] RViz WID=$WID → ${m}_rviz.png"
    ffmpeg -y -loglevel error -f x11grab -draw_mouse 0 -video_size 1920x1080 \
        -i $DISP -frames:v 1 "$OUTDIR/${m}_rviz.png" 2>/dev/null
    ls -l "$OUTDIR/${m}_rviz.png" 2>/dev/null || echo "  ✗ shot başarısız"
    kill -9 "$LP" 2>/dev/null
    _clean
done
echo "BİTTİ — $OUTDIR"
ls -l "$OUTDIR"/*.png 2>/dev/null
