#!/usr/bin/env bash
# record_gazebo_view.sh — HAFİF Gazebo 3D kaydı (Nav2 YOK, OOM yok), N robot.
#
# Neden ayrı: GPU sürücüsü olmayan bu makinede Gazebo GUI yazılım render'ı
# + Nav2 birlikte RAM'i aşıp Gazebo'yu OOM ile öldürüyor (yük 250). Bu script
# Gazebo GUI + arena + N robotu Nav2 OLMADAN açar, robotları gz cmd_vel ile
# arenada gezdirir ve :2'yi TAM EKRAN kaydeder. RViz videoları (gerçek
# navigasyon + yol planı) ayrı script ile alınır — BİRLEŞTİRME YOK.
#
# Kullanım: ./record_gazebo_view.sh <N_robots> <tag> [dur_s]
#   örn: ./record_gazebo_view.sh 5 5r_t25 90
# Çıktı: results/videos/ahe_gazebo_<tag>.mkv (kesintiye dayanıklı) + .mp4 (remux)

set -o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
source /opt/ros/jazzy/setup.bash

N="${1:-3}"
TAG="${2:-${N}r}"
DUR="${3:-80}"
TRAJ="${4:-}"   # opsiyonel: ros2 bag dizini (Nav2 cmd_vel) → REPLAY modu

VIDEO_DIR="${SCRIPT_DIR}/results/demo_videos_mixed"
mkdir -p "$VIDEO_DIR"
MKV="${VIDEO_DIR}/ahe_gazebo_${TAG}.mkv"
MP4="${VIDEO_DIR}/ahe_gazebo_${TAG}.mp4"

if [[ -f "$MP4" ]]; then echo "[SKIP] $MP4 zaten var."; exit 0; fi

export DISPLAY=:2 LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe MESA_GL_VERSION_OVERRIDE=4.5
export GZ_SIM_RESOURCE_PATH=/opt/ros/jazzy/share/turtlebot3_gazebo/models
TEMPLATE="${SCRIPT_DIR}/src/m_ahe_mrta_gazebo/worlds/ahe_inspection_arena.sdf"
BASE_CFG="${SCRIPT_DIR}/src/m_ahe_mrta_bringup/config/gz_gui_ogre1.config"

# ── N-robot world SDF üret (placement.robot_spawns ile aynı yerleşim) ─────────
WORLD="/tmp/ahe_arena_${N}r.sdf"
python3 - "$TEMPLATE" "$N" "$WORLD" <<'PY'
import sys, importlib.util
tmpl, n, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
spec = importlib.util.spec_from_file_location(
    "mrh", "src/m_ahe_mrta_bringup/launch/multi_robot_helpers.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
m.generate_world_sdf(tmpl, n, out)
print(f"[world] {n} robot -> {out}")
PY
[[ -f "$WORLD" ]] || { echo "[hata] world üretilemedi"; exit 1; }

# ── Tam-ekran (straight-down) kamera: arena (~20x20m) frame'i doldursun ───────
# NOT: cleanup() '/tmp/gz_*' siliyor → config'i o glob'un DIŞINDA tut.
CFG="/tmp/ahe_gui_${TAG}.config"
sed 's#<camera_pose>.*</camera_pose>#<camera_pose>0 0 18.5 0 1.5707 1.5708</camera_pose>#' \
    "$BASE_CFG" > "$CFG"

# ── Sanal ekran + pencere yöneticisi ─────────────────────────────────────────
if ! DISPLAY=:2 xdpyinfo &>/dev/null; then
    Xvfb :2 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &>/dev/null &
    sleep 2
fi
pgrep -f "fluxbox" &>/dev/null || { DISPLAY=:2 fluxbox &>/dev/null & sleep 1; }
DISPLAY=:2 xsetroot -solid black 2>/dev/null || true

cleanup() {
    pkill -9 -f "gz sim|ruby" 2>/dev/null
    pkill -9 -f "ffmpeg.*x11grab" 2>/dev/null
    pkill -9 -f "ros_gz_bridge|parameter_bridge" 2>/dev/null
    pkill -9 -f "ros2 bag play|rosbag2" 2>/dev/null
    rm -f /dev/shm/gz_* /tmp/gz_* 2>/dev/null
}
cleanup; sleep 2

echo "[gz] Gazebo başlatılıyor (OGRE1, $N robot, Nav2 yok)..."
gz sim -r --render-engine-gui ogre --gui-config "$CFG" "$WORLD" > "${MKV%.mkv}_gz.log" 2>&1 &
sleep 20   # GUI render hazır olsun

# Pencereyi tam ekran yap (fluxbox başlık/dekorasyon kalksın)
WID=$(DISPLAY=:2 wmctrl -l 2>/dev/null | grep -i "Gazebo" | awk '{print $1}' | head -1)
[[ -n "$WID" ]] && DISPLAY=:2 wmctrl -i -r "$WID" -b add,fullscreen 2>/dev/null
sleep 2

# REPLAY modu: traje bag varsa Nav2 cmd_vel'lerini köprüle+oynat (gerçek Nav2 hareketi).
# Yoksa: scripted sürüş (eski davranış, Nav2'siz).
REPLAY=0
if [[ -n "$TRAJ" && -d "$TRAJ" ]]; then
    REPLAY=1
    BAGDUR=$(ros2 bag info "$TRAJ" 2>/dev/null | awk -F'[: ]+' '/Duration/{print int($2)+5}')
    [[ -z "$BAGDUR" || "$BAGDUR" -lt 10 ]] && BAGDUR="$DUR"
    REC_T="$BAGDUR"
    echo "[replay] traje: $TRAJ  (kayıt ${REC_T}s — Nav2 cmd_vel oynatılacak)"
else
    REC_T="$DUR"
    echo "[scripted] traje yok → scripted sürüş (${REC_T}s)"
fi

# Üstteki başlık+turuncu toolbar'ı (~88px) atla → sadece sahne; 1080'e ölçekle.
TOPCROP=88
echo "[rec] ffmpeg MKV kaydı (${REC_T}s, üst ${TOPCROP}px kırpıldı)..."
ffmpeg -y -loglevel warning -f x11grab -draw_mouse 0 -video_size 1920x$((1080-TOPCROP)) -framerate 25 \
    -i ":2.0+0,${TOPCROP}" -vf "scale=1920:1080" \
    -c:v libx264 -preset ultrafast -crf 23 -t "$REC_T" "$MKV" \
    > "${MKV%.mkv}_ff.log" 2>&1 &
FF=$!
sleep 2

if [[ "$REPLAY" == "1" ]]; then
    # cmd_vel köprüsü (ROS /robot_i/cmd_vel → gz /model/robot_i/cmd_vel)
    source "${SCRIPT_DIR}/install/setup.bash" 2>/dev/null
    BYAML="/tmp/ahe_cmdvel_bridge_${TAG}.yaml"
    : > "$BYAML"
    for i in $(seq 1 "$N"); do
        cat >> "$BYAML" <<EOF2
- ros_topic_name: /robot_${i}/cmd_vel
  gz_topic_name: /model/robot_${i}/cmd_vel
  ros_type_name: geometry_msgs/msg/Twist
  gz_type_name: gz.msgs.Twist
  direction: ROS_TO_GZ
EOF2
    done
    ros2 run ros_gz_bridge parameter_bridge --ros-args -p config_file:="$BYAML" \
        > "${MKV%.mkv}_bridge.log" 2>&1 &
    sleep 3
    echo "[replay] Nav2 cmd_vel bag oynatılıyor..."
    ros2 bag play "$TRAJ" > "${MKV%.mkv}_bagplay.log" 2>&1
    echo "[replay] bag bitti."
else
    # Scripted sürüş (Nav2 yok): forward-ağırlıklı, ara sıra dönüş
    echo "[drive] $N robot sürülüyor..."
    STEPS=$(( (REC_T-4) / 2 ))
    for t in $(seq 1 "$STEPS"); do
        phase=$(( t % 6 ))
        for r in $(seq 1 "$N"); do
            if (( r % 2 == 0 )); then sz="-0.06"; tz="-0.6"; else sz="0.06"; tz="0.6"; fi
            if [[ $phase -lt 4 ]]; then
                gz topic -t "/model/robot_${r}/cmd_vel" -m gz.msgs.Twist \
                    -p "linear:{x:0.28},angular:{z:${sz}}" 2>/dev/null
            else
                gz topic -t "/model/robot_${r}/cmd_vel" -m gz.msgs.Twist \
                    -p "linear:{x:0.05},angular:{z:${tz}}" 2>/dev/null
            fi
        done
        sleep 2
    done
fi

wait $FF 2>/dev/null
cleanup
echo ""
if [[ -f "$MKV" ]]; then
    # temiz bitiş → mp4'e remux (re-encode yok)
    ffmpeg -y -loglevel error -i "$MKV" -c copy "$MP4" 2>/dev/null && rm -f "$MKV"
    echo "[ok] $(du -h "$MP4"|cut -f1)  süre=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$MP4" 2>/dev/null)s  → $MP4"
else
    echo "[hata] kayıt oluşmadı (bkz ${MKV%.mkv}_ff.log)"
fi
