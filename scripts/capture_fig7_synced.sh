#!/usr/bin/env bash
# Capture Gazebo and RViz from one frozen simulation timestamp for Fig. 7.
#
# Both GUI clients run concurrently on separate virtual displays.  Once the
# 10-robot mission has started and plans are visible, Gazebo physics is paused
# through WorldControl; the two X11 frames are then grabbed in parallel.  The
# resulting panels therefore show the same run, seed, and simulation instant.

set -eo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

source /opt/ros/jazzy/setup.bash
source install/setup.bash
set -u

# A full 10-robot Nav2 stack plus two llvmpipe GUIs can make the workstation
# unresponsive. Require an explicit opt-in and pass the repository load gate
# before creating any X server or ROS node.
if [[ "${ALLOW_HIGH_LOAD_CAPTURE:-0}" != "1" ]]; then
    echo '[refused] 10-robot dual-GUI capture is disabled by default.' >&2
    echo 'Use the recorded-state low-load workflow documented in YUK_KONTROL.md.' >&2
    exit 75
fi
LOAD_GUARD_MAX_LOAD="${FIG7_MAX_LOAD_1M:-8.0}" \
LOAD_GUARD_MIN_MEM_MB="${FIG7_MIN_MEM_MB:-6144}" \
LOAD_GUARD_MAX_HEAVY=0 \
    bash scripts/load_guard.sh 'fig7-preflight'
python3 scripts/validate_fig7_environment.py

GZ_DISPLAY="${GZ_DISPLAY:-:21}"
RVIZ_DISPLAY="${RVIZ_DISPLAY:-:23}"
SCREEN_SIZE="${SCREEN_SIZE:-1920x1080}"
ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-77}"
STARTUP_TIMEOUT="${STARTUP_TIMEOUT:-600}"
POST_START_SETTLE="${POST_START_SETTLE:-90}"
OUTDIR="${OUTDIR:-results/figures/fig7_synced}"
RESULTS_DIR="${RESULTS_DIR:-results/raw/_fig7_sync_capture}"
LAUNCH_LOG="$OUTDIR/fig7_sync_launch.log"

mkdir -p "$OUTDIR" "$RESULTS_DIR"

owned_pids=()
launch_pid=""

cleanup() {
    if [[ -n "$launch_pid" ]] && kill -0 "$launch_pid" 2>/dev/null; then
        kill -TERM -- "-$launch_pid" 2>/dev/null || true
        for _ in 1 2 3 4 5; do
            kill -0 "$launch_pid" 2>/dev/null || break
            sleep 2
        done
        kill -KILL -- "-$launch_pid" 2>/dev/null || true
    fi
    for pid in "${owned_pids[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
}
trap cleanup EXIT INT TERM

start_display() {
    local display="$1"
    if ! DISPLAY="$display" xdpyinfo >/dev/null 2>&1; then
        Xvfb "$display" -screen 0 "${SCREEN_SIZE}x24" -ac \
            +extension GLX +render -noreset >"/tmp/fig7_xvfb_${display#:}.log" 2>&1 &
        owned_pids+=("$!")
        sleep 2
    fi
    DISPLAY="$display" fluxbox >"/tmp/fig7_fluxbox_${display#:}.log" 2>&1 &
    owned_pids+=("$!")
    sleep 2
    DISPLAY="$display" xsetroot -solid '#202020'
}

start_display "$GZ_DISPLAY"
start_display "$RVIZ_DISPLAY"

# The Gazebo server runs HEADLESS during the mission: attaching the GUI from
# launch start (a) nearly halts the sim (RTF~0 under llvmpipe) and (b) has
# produced plugin-less blank GUI shells. The GUI client is attached later,
# to the frozen (paused) scene, which is the proven matched-pair workflow.
echo "[launch] 10 robots / 50 tasks / dynamic_task_arrival / seed 1 (gz headless)"
setsid env ROS_DOMAIN_ID="$ROS_DOMAIN_ID" ros2 launch \
    m_ahe_mrta_bringup phase9_demo.launch.py \
    strategy:=ahe_mrta_v3 scenario:=dynamic_task_arrival seed:=1 \
    robot_count:=10 task_count:=50 results_dir:="$RESULTS_DIR" \
    startup_delay:="${STARTUP_TIMEOUT}.0" gz_gui:=false use_rviz:=true \
    rviz_delay:=110.0 use_gz_markers:=false \
    gz_display:="$GZ_DISPLAY" rviz_display:="$RVIZ_DISPLAY" \
    >"$LAUNCH_LOG" 2>&1 &
launch_pid="$!"

echo "[wait] Nav2 readiness and mission start (max ${STARTUP_TIMEOUT}s)"
started=0
for _ in $(seq 1 $((STARTUP_TIMEOUT / 5 + 12))); do
    LOAD_GUARD_MAX_LOAD="${FIG7_MAX_LOAD_1M:-8.0}" \
    LOAD_GUARD_MIN_MEM_MB="${FIG7_RUNTIME_MIN_MEM_MB:-4096}" \
    LOAD_GUARD_MAX_HEAVY="${FIG7_MAX_HEAVY_PROCS:-120}" \
        bash scripts/load_guard.sh 'fig7-startup'
    if grep -q 'ExperimentRunner started:' "$LAUNCH_LOG"; then
        started=1
        break
    fi
    if ! kill -0 "$launch_pid" 2>/dev/null; then
        echo "[error] launch exited before mission start; see $LAUNCH_LOG" >&2
        exit 1
    fi
    sleep 5
done
if [[ "$started" -ne 1 ]]; then
    echo "[error] mission did not start; see $LAUNCH_LOG" >&2
    exit 1
fi

echo "[wait] mission visualisation settle (${POST_START_SETTLE}s)"
for _ in $(seq 1 $((POST_START_SETTLE / 5))); do
    LOAD_GUARD_MAX_LOAD="${FIG7_MAX_LOAD_1M:-8.0}" \
    LOAD_GUARD_MIN_MEM_MB="${FIG7_RUNTIME_MIN_MEM_MB:-4096}" \
    LOAD_GUARD_MAX_HEAVY="${FIG7_MAX_HEAVY_PROCS:-120}" \
        bash scripts/load_guard.sh 'fig7-settle'
    sleep 5
done

rviz_wid="$(DISPLAY="$RVIZ_DISPLAY" wmctrl -l | awk 'BEGIN{IGNORECASE=1} /RViz/{print $1; exit}')"
if [[ -z "$rviz_wid" ]]; then
    echo "[error] RViz window missing" >&2
    DISPLAY="$RVIZ_DISPLAY" wmctrl -l || true
    exit 1
fi
DISPLAY="$RVIZ_DISPLAY" wmctrl -i -r "$rviz_wid" -b add,fullscreen
sleep 5

echo "[freeze] pausing world ahe_inspection_mvp"
pause_reply="$(gz service -s /world/ahe_inspection_mvp/control \
    --reqtype gz.msgs.WorldControl --reptype gz.msgs.Boolean \
    --timeout 10000 --req 'pause: true')"
echo "$pause_reply"
if ! printf '%s' "$pause_reply" | grep -q 'data: true'; then
    echo "[error] Gazebo pause request was not acknowledged" >&2
    exit 1
fi
sleep 3

# Attach the Gazebo GUI client to the FROZEN scene. Env is sanitized against
# snap/VS Code contamination (GTK_* etc. break Qt plugin loading -> blank
# plugin-less window); OGRE1 + software GL is the only stack that renders
# reliably without a GPU driver here.
echo "[gui] attaching gz sim -g to the frozen scene on $GZ_DISPLAY"
GUI_CFG="$REPO/src/m_ahe_mrta_bringup/config/gz_gui_ogre1.config"
env -u GTK_PATH -u GTK_MODULES -u GTK_IM_MODULE_FILE -u GTK_EXE_PREFIX \
    -u GIO_MODULE_DIR -u LOCPATH \
    GSETTINGS_SCHEMA_DIR=/usr/share/glib-2.0/schemas \
    DISPLAY="$GZ_DISPLAY" LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe \
    gz sim -g --render-engine-gui ogre --gui-config "$GUI_CFG" \
    >"$OUTDIR/gz_gui_client.log" 2>&1 &
owned_pids+=("$!")

gz_wid=""
for _ in $(seq 1 36); do
    gz_wid="$(DISPLAY="$GZ_DISPLAY" wmctrl -l | awk 'BEGIN{IGNORECASE=1} /Gazebo|GZ Sim/{print $1; exit}')"
    [[ -n "$gz_wid" ]] && break
    sleep 5
done
if [[ -z "$gz_wid" ]]; then
    echo "[error] gz GUI client window did not appear; see $OUTDIR/gz_gui_client.log" >&2
    exit 1
fi
DISPLAY="$GZ_DISPLAY" wmctrl -i -r "$gz_wid" -b add,fullscreen
echo "[gui] window up; waiting for scene stream + OGRE1 render"
sleep 60

# A blank plugin-less shell compresses to a tiny PNG; a rendered arena does
# not. Retry the grab until the frame carries an actual scene.
for attempt in 1 2 3 4; do
    ffmpeg -y -loglevel error -f x11grab -draw_mouse 0 \
        -video_size "$SCREEN_SIZE" -i "$GZ_DISPLAY" -frames:v 1 \
        "$OUTDIR/gazebo_10r_synced_screen.png"
    sz=$(stat -c%s "$OUTDIR/gazebo_10r_synced_screen.png")
    if ((sz > 40000)); then
        break
    fi
    echo "[gui] frame still looks blank (${sz}B), attempt $attempt; waiting 45s"
    sleep 45
done

echo "[capture] frozen Gazebo and RViz frames"
ffmpeg -y -loglevel error -f x11grab -draw_mouse 0 \
    -video_size "$SCREEN_SIZE" -i "$GZ_DISPLAY" -frames:v 1 \
    "$OUTDIR/gazebo_10r_synced_screen.png" &
cap_gz="$!"
ffmpeg -y -loglevel error -f x11grab -draw_mouse 0 \
    -video_size "$SCREEN_SIZE" -i "$RVIZ_DISPLAY" -frames:v 1 \
    "$OUTDIR/rviz_10r_synced_screen.png" &
cap_rviz="$!"
wait "$cap_gz"
wait "$cap_rviz"

# Publication panels: retain the full arena while removing desktop chrome and
# unused side margins. Both crops derive from the frozen full-screen frames.
ffmpeg -y -loglevel error -i "$OUTDIR/gazebo_10r_synced_screen.png" \
    -vf 'crop=1080:1032:420:48' -frames:v 1 "$OUTDIR/gazebo_10r_synced.png"
ffmpeg -y -loglevel error -i "$OUTDIR/rviz_10r_synced_screen.png" \
    -vf 'crop=1080:990:420:87' -frames:v 1 "$OUTDIR/rviz_10r_synced.png"

echo "[clock] frozen ROS simulation time"
ROS_DOMAIN_ID="$ROS_DOMAIN_ID" timeout 15 ros2 topic echo /clock --once || true

file "$OUTDIR/gazebo_10r_synced.png" "$OUTDIR/rviz_10r_synced.png"
echo "[ok] synchronized panels written to $OUTDIR"
