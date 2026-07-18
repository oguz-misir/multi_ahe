#!/usr/bin/env bash
# Conservative host-load gate for ROS 2 / Gazebo / RViz workloads.

set -u

label="${1:-command}"
max_load="${LOAD_GUARD_MAX_LOAD:-8.0}"
min_mem_mb="${LOAD_GUARD_MIN_MEM_MB:-6144}"
max_heavy="${LOAD_GUARD_MAX_HEAVY:-0}"

load1="$(awk '{print $1}' /proc/loadavg)"
mem_available_kb="$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)"
swap_total_kb="$(awk '/^SwapTotal:/ {print $2}' /proc/meminfo)"
swap_free_kb="$(awk '/^SwapFree:/ {print $2}' /proc/meminfo)"
mem_available_mb=$((mem_available_kb / 1024))
swap_used_mb=$(((swap_total_kb - swap_free_kb) / 1024))

heavy_processes="$({
    ps -eo comm= 2>/dev/null || true
} | awk '
    /^(ros2|gz|gzserver|gzclient|rviz2|component_cont|parameter_bridg|controller_serv|planner_server|behavior_server|bt_navigator|waypoint_followe|velocity_smooth|map_server|amcl|lifecycle_mana|robot_state_pub|experiment_runn)/ {n++}
    END {print n + 0}
')"

printf '[load-guard] %s: load1=%s (max %s), MemAvailable=%s MiB (min %s), swap-used=%s MiB, heavy-processes=%s (max %s)\n' \
    "$label" "$load1" "$max_load" "$mem_available_mb" "$min_mem_mb" \
    "$swap_used_mb" "$heavy_processes" "$max_heavy"

failed=0
if ! awk -v current="$load1" -v limit="$max_load" 'BEGIN {exit !(current <= limit)}'; then
    echo "[load-guard] RED: bir dakikalık sistem yükü sınırı aşıyor." >&2
    failed=1
fi
if ((mem_available_mb < min_mem_mb)); then
    echo "[load-guard] RED: kullanılabilir bellek güvenli eşiğin altında." >&2
    failed=1
fi
if ((heavy_processes > max_heavy)); then
    echo "[load-guard] RED: başka bir ağır ROS/Gazebo/Nav2 süreci çalışıyor." >&2
    failed=1
fi

if ((failed)); then
    exit 75
fi

echo '[load-guard] GREEN: komut güvenle başlatılabilir.'

