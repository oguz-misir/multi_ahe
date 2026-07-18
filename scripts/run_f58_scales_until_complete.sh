#!/usr/bin/env bash
# Crash-safe driver for the F58 3r/10r matched Gazebo scale campaign.
# Reruns each profile until its DONE target is met; --skip-done makes every
# retry resume from the last DONE experiment. Two failure defenses:
#   - stall counter: three consecutive attempts with no new DONE -> abort
#     (persistent failure, not a flake);
#   - hang watchdog: the campaign log falling silent for 75 min means a
#     wedged run (observed: D-state teardown under swap storm) -> kill the
#     attempt's process tree, clean up, retry.
# The runner exits 0 even when runs fail, so completion is judged ONLY by
# the DONE count, never by the profile script's exit status.
set -uo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
source "$REPO/scripts/exp_lib.sh"

LOG="${F58_CAMPAIGN_LOG:-$REPO/results/f58_scales_campaign.log}"
WATCHDOG_SILENCE_SEC=4500   # 75 min; healthy 10r runs log a line at least every ~40 min

PROFILES=(paper_scale3 paper_scale10)
declare -A ROOTS=(
    [paper_scale3]="$REPO/results/raw/gazebo_f58_scale3_validation"
    [paper_scale10]="$REPO/results/raw/gazebo_f58_scale10_validation"
)
# 3 scenarios x 10 seeds x 2 arms
declare -A TARGETS=(
    [paper_scale3]=60
    [paper_scale10]=60
)

count_done() { find "$1" -name DONE 2>/dev/null | wc -l; }

kill_attempt() {
    local pid="$1"
    echo "[$(date '+%F %T')] watchdog: attempt tree killed (pid $pid)"
    pkill -9 -f "run_f58_gazebo_validation.sh" 2>/dev/null || true
    pkill -9 -f "run_experiments_robust.sh" 2>/dev/null || true
    kill -9 "$pid" 2>/dev/null || true
    cleanup_ros_gz || true
}

# Runs one profile attempt under the hang watchdog. Returns nonzero on
# script failure or watchdog kill; caller judges progress via DONE count.
run_attempt() {
    local profile="$1"
    bash "$REPO/scripts/run_f58_gazebo_validation.sh" "$profile" &
    local pid=$!
    while kill -0 "$pid" 2>/dev/null; do
        sleep 120
        local age=$(( $(date +%s) - $(stat -c %Y "$LOG" 2>/dev/null || date +%s) ))
        if [ "$age" -ge "$WATCHDOG_SILENCE_SEC" ]; then
            echo "[$(date '+%F %T')] watchdog: log ${age}s silent -> hung attempt"
            kill_attempt "$pid"
            return 1
        fi
    done
    wait "$pid"
}

for profile in "${PROFILES[@]}"; do
    root="${ROOTS[$profile]}"
    target="${TARGETS[$profile]}"
    stall=0
    while true; do
        before=$(count_done "$root")
        # No early break on target: even a fully DONE root must go through
        # one (fast, all-skip) script pass so consolidate+compare stats are
        # regenerated after any watchdog-killed attempt.
        echo "[$(date '+%F %T')] $profile: attempt starting (DONE=$before/$target)"
        run_attempt "$profile"
        rc=$?
        after=$(count_done "$root")
        if [ "$after" -ge "$target" ] && [ "$rc" -eq 0 ]; then
            echo "[$(date '+%F %T')] $profile: COMPLETE ($after/$target DONE)"
            break
        fi
        if [ "$after" -gt "$before" ]; then
            stall=0
        else
            stall=$((stall + 1))
        fi
        echo "[$(date '+%F %T')] $profile: attempt ended (rc=$rc, DONE=$after/$target, stall=$stall)"
        if [ "$stall" -ge 3 ]; then
            echo "[$(date '+%F %T')] $profile: no progress in 3 attempts, ABORT" >&2
            exit 1
        fi
        cleanup_ros_gz || true
        sleep 30
    done
done

echo "[$(date '+%F %T')] F58 scale campaign complete (3r + 10r)."
