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

VIDEO_DIR="${SCRIPT_DIR}/results/demo_videos_mixed"
RAW_DIR="${SCRIPT_DIR}/results/demo_videos_mixed/raw"
mkdir -p "$VIDEO_DIR" "$RAW_DIR"

# mixed_stress: robot arızası (t=45s) + kurtarma — paper'ın vurgusu. Sabit-süre
# kayıt yaptığımız için tamamlanma gerekmiyor; arıza+kurtarma kayıt penceresinde
# doğal görünür (arızalı robot durur, diğerleri devam eder).
STRATEGY="ahe_mrta_v3"; SCENARIO="mixed_stress"; SEED="1"; SEED_PAD="01"

# (robot_count task_count startup_delay record_seconds)
# 6 konfig (ölçek merdiveni × görev): her biri RViz + Gazebo replay = 12 video.
# DONE beklemiyoruz; sabit süre GERÇEK navigasyon kaydedip durduruyoruz.
EXPERIMENTS=(
    "3   9   90.0   200"
    "3   15  90.0   200"
    "3   24  90.0   200"
    "5   15  110.0  240"
    "5   25  110.0  240"
    "10  50  170.0  330"
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
    read -r N M STARTUP REC <<< "$exp"
    TAG="ahe_${N}r_t${M}"
    OUT="${VIDEO_DIR}/${TAG}_rviz.mp4"
    MKV="${VIDEO_DIR}/${TAG}_rviz.mkv"   # kesintiye dayanıklı; sonda mp4'e remux
    RES="${RAW_DIR}/${TAG}_rviz"

    # Ancak HEM RViz HEM Gazebo geçerliyse atla (yoksa eksik gazebo'yu tamamla).
    GZ_OUT="${VIDEO_DIR}/ahe_gazebo_${N}r_t${M}.mp4"
    if [[ -f "$OUT" ]] && ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT" &>/dev/null \
       && [[ -f "$GZ_OUT" ]] && ffprobe -v error -show_entries format=duration -of csv=p=0 "$GZ_OUT" &>/dev/null; then
        echo "[SKIP] $TAG zaten var (RViz+Gazebo geçerli)."; continue
    fi
    rm -f "$OUT" "$MKV" 2>/dev/null

    echo ""
    echo "══════════════════════════════════════════════════════"
    echo "  $TAG  (robots=$N tasks=$M)  — RViz kaydı"
    echo "══════════════════════════════════════════════════════"
    mkdir -p "$RES"
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

    # Nav2 cmd_vel trajesini kaydet → Gazebo replay için (gerçek Nav2 hareketi).
    # Launch'tan hemen sonra başlat: topic'ler belirince ilk komuttan itibaren yakalar.
    TRAJ="${VIDEO_DIR}/traj_${N}r_t${M}"
    rm -rf "$TRAJ" 2>/dev/null
    CMD_TOPICS=""; for i in $(seq 1 "$N"); do CMD_TOPICS="$CMD_TOPICS /robot_${i}/cmd_vel"; done
    ros2 bag record -o "$TRAJ" $CMD_TOPICS > "${TRAJ}_rec.log" 2>&1 &
    BAG=$!

    # Nav2 bringup penceresini RViz/ffmpeg yükü olmadan geçir
    echo "  [bekle] Nav2 bringup için ${RVIZ_DELAY}s (RViz/ffmpeg yok)..."
    sleep $((RVIZ_DELAY - 5))

    # RViz penceresini tam ekran yap (fluxbox dekorasyonu kalksın)
    WID=$(DISPLAY=:3 wmctrl -l 2>/dev/null | grep -i "RViz" | awk '{print $1}' | head -1)
    [[ -n "$WID" ]] && DISPLAY=:3 wmctrl -i -r "$WID" -b add,fullscreen 2>/dev/null

    # Şimdi ffmpeg başlat (RViz ~5s sonra belirecek). MKV → SIGKILL'e dayanıklı.
    # 15 fps: yükü düşürür, dosya küçülür. Üst ~44px (fluxbox başlık + RViz menü
    # çubuğu) kırpılır → temiz tam-ekran 3D görünüm; 1080'e ölçeklenir.
    RTOP=52; RBOT=30
    ffmpeg -y -loglevel warning -f x11grab -draw_mouse 0 -video_size 1920x$((1080-RTOP-RBOT)) -framerate 15 \
        -i ":3.0+0,${RTOP}" -vf "scale=1920:1080" \
        -c:v libx264 -preset ultrafast -crf 23 "$MKV" \
        > "${OUT%.mp4}_ff.log" 2>&1 &
    FF=$!

    # DONE beklemeden sabit süre GERÇEK navigasyon kaydet (robotlar Nav2 ile gezer).
    echo "  [kayıt] ${REC}s navigasyon kaydediliyor..."
    EL=0
    while [[ $EL -lt $REC ]] && kill -0 $RP 2>/dev/null; do
        sleep 10; EL=$((EL+10))
        (( EL % 60 == 0 )) && echo "  [ilerleme] ${EL}/${REC}s  load=$(cut -d' ' -f1 /proc/loadavg)"
    done

    kill -INT $FF 2>/dev/null; wait $FF 2>/dev/null
    # Traje bag'i finalize et: SIGINT bu ortamda ASILIYOR → SIGTERM temiz flush eder
    # (mcap cache'i diske yazar + metadata.yaml). En fazla 15s bekle, sonra SIGKILL.
    kill -TERM $BAG 2>/dev/null
    for _ in $(seq 1 15); do kill -0 $BAG 2>/dev/null || break; sleep 1; done
    kill -9 $BAG 2>/dev/null; wait $BAG 2>/dev/null
    kill -INT $RP 2>/dev/null; cleanup_ros

    # Temiz bitiş → MKV'yi mp4'e remux (re-encode yok). MKV kesintide de oynar.
    if [[ -f "$MKV" ]]; then
        ffmpeg -y -loglevel error -i "$MKV" -c copy "$OUT" 2>/dev/null && rm -f "$MKV"
    fi
    [[ -f "$OUT" ]] && echo "[ok] RViz: $(du -h "$OUT"|cut -f1) → $OUT"

    # ── Gazebo replay: bu sahnenin Nav2 cmd_vel'lerini hafif Gazebo-GUI'de oynat ──
    # (Nav2+GUI birlikte değil → OOM yok; ama robotlar GERÇEK Nav2 komutlarıyla hareket eder.)
    GZ_OUT="${VIDEO_DIR}/ahe_gazebo_${N}r_t${M}.mp4"
    if [[ -d "$TRAJ" ]]; then
        rm -f "$GZ_OUT" 2>/dev/null   # scripted placeholder'ı (varsa) değiştir
        echo "  [gazebo-replay] ${N}r_t${M} — Nav2 trajesi oynatılıyor..."
        load_guard
        bash "${SCRIPT_DIR}/record_gazebo_view.sh" "$N" "${N}r_t${M}" 90 "$TRAJ"
    else
        echo "  [uyarı] traje bag yok ($TRAJ) → Gazebo replay atlandı."
    fi
done

echo ""
echo "════════════════════════════════════════════════════════"
echo "  RViz kayıtları tamamlandı!"
ls -lh "${VIDEO_DIR}"/*_rviz.mp4 2>/dev/null
echo "════════════════════════════════════════════════════════"
