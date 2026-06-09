#!/usr/bin/env bash
# record_gazebo_view.sh — HAFİF Gazebo 3D kaydı (Nav2 YOK, OOM yok).
#
# Neden ayrı: GPU sürücüsü olmayan bu makinede Gazebo GUI yazılım render'ı
# + 3×Nav2 birlikte 15 GB RAM'i aşıp Gazebo'yu OOM ile öldürüyor (yük 250).
# Bu script Gazebo GUI + arena + 3 robotu Nav2 OLMADAN açar (smoke test'te
# sorunsuz), robotları gz topic cmd_vel ile arenada gezdirir ve :2'yi kaydeder.
# Çıktı: results/videos/ahe_gazebo_3r.mp4
#
# RViz videoları (gerçek navigasyon) ayrı script ile alınır — BİRLEŞTİRME YOK.

set -o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
source /opt/ros/jazzy/setup.bash

VIDEO_DIR="${SCRIPT_DIR}/results/videos"
mkdir -p "$VIDEO_DIR"
OUT="${VIDEO_DIR}/ahe_gazebo_3r.mp4"
DUR=${1:-80}          # kayıt süresi (s)

export DISPLAY=:2 LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe MESA_GL_VERSION_OVERRIDE=4.5
export GZ_SIM_RESOURCE_PATH=/opt/ros/jazzy/share/turtlebot3_gazebo/models
WORLD="${SCRIPT_DIR}/src/m_ahe_mrta_gazebo/worlds/ahe_inspection_arena.sdf"
CFG="${SCRIPT_DIR}/src/m_ahe_mrta_bringup/config/gz_gui_ogre1.config"

# Sanal ekran
if ! DISPLAY=:2 xdpyinfo &>/dev/null; then
    Xvfb :2 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &>/dev/null &
    sleep 2
fi
pgrep -f fluxbox &>/dev/null || { DISPLAY=:2 fluxbox &>/dev/null & sleep 1; }

cleanup() { pkill -9 -f "gz sim|ruby" 2>/dev/null; pkill -9 -f ffmpeg 2>/dev/null; rm -f /dev/shm/gz_* /tmp/gz_* 2>/dev/null; }
cleanup; sleep 2

echo "[gz] Gazebo başlatılıyor (OGRE1, Nav2 yok)..."
gz sim -r --render-engine-gui ogre --gui-config "$CFG" "$WORLD" > "${OUT%.mp4}_gz.log" 2>&1 &
sleep 18   # GUI render hazır olsun

echo "[rec] ffmpeg kaydı (${DUR}s)..."
ffmpeg -y -loglevel warning -f x11grab -video_size 1920x1080 -framerate 25 \
    -i :2.0+0,0 -c:v libx264 -preset ultrafast -crf 23 -t "$DUR" "$OUT" \
    > "${OUT%.mp4}_ff.log" 2>&1 &
FF=$!
sleep 2

# Robotları arenada gezdir: forward-ağırlıklı, ara sıra dönüş → koridorda ilerleme
echo "[drive] robotlar sürülüyor..."
N=$(( (DUR-4) / 2 ))
for t in $(seq 1 $N); do
    phase=$(( t % 6 ))
    if [[ $phase -lt 4 ]]; then
        # düz ilerle
        gz topic -t /model/robot_1/cmd_vel -m gz.msgs.Twist -p "linear:{x:0.30},angular:{z:0.05}" 2>/dev/null
        gz topic -t /model/robot_2/cmd_vel -m gz.msgs.Twist -p "linear:{x:0.28},angular:{z:-0.05}" 2>/dev/null
        gz topic -t /model/robot_3/cmd_vel -m gz.msgs.Twist -p "linear:{x:0.26},angular:{z:0.08}" 2>/dev/null
    else
        # dön (yön değiştir)
        gz topic -t /model/robot_1/cmd_vel -m gz.msgs.Twist -p "linear:{x:0.05},angular:{z:0.6}" 2>/dev/null
        gz topic -t /model/robot_2/cmd_vel -m gz.msgs.Twist -p "linear:{x:0.05},angular:{z:-0.6}" 2>/dev/null
        gz topic -t /model/robot_3/cmd_vel -m gz.msgs.Twist -p "linear:{x:0.05},angular:{z:0.6}" 2>/dev/null
    fi
    sleep 2
done

wait $FF 2>/dev/null
cleanup
echo ""
if [[ -f "$OUT" ]]; then
    echo "[ok] $(du -h "$OUT"|cut -f1)  süre=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT" 2>/dev/null)s  → $OUT"
else
    echo "[hata] kayıt oluşmadı"
fi
