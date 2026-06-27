#!/usr/bin/env python3
"""Per-method 'path plan' figure from REAL experiment data (publication grade).

Overlays each robot's actual trajectory + task allocation on the arena
occupancy map. Robust alternative to RViz screenshots (which freeze under
headless software-GL).

AUTO frame-correction (no spawn guessing): the trajectory is anchored to the
ABSOLUTE task coordinates the robot actually visited. Whatever frame the
timeseries logs (already-map vs spawn-relative), the per-robot translation is
derived from data via task anchoring (robust median over visited tasks), so
trajectories always align with the map. Spurious uninitialised (~origin) poses
are dropped.

Usage: python3 scripts/plot_method_paths.py <run_dir> <out.png> ["Title"]
  The paper uses paper/figure/grid_r5t25_mixed_stress.png as <out.png>.
"""
import sys, csv, glob, os, math, statistics
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

RUN = sys.argv[1]
OUT = sys.argv[2]
TITLE = sys.argv[3] if len(sys.argv) > 3 else RUN.rstrip('/').split('/')[-1]
PGM = 'src/m_ahe_nav2_config/maps/obstacle_map.pgm'
RES, ORG = 0.05, (-10.0, -10.0)
ROBOT_COLORS = ['#1f77b4', '#2ca02c', '#d62728', '#9467bd', '#ff7f0e',
                '#17becf', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22']


def read_pgm(p):
    with open(p, 'rb') as f:
        assert f.readline().strip() == b'P5'
        l = f.readline()
        while l.startswith(b'#'):
            l = f.readline()
        w, h = map(int, l.split()); int(f.readline())
        return np.frombuffer(f.read(w * h), dtype=np.uint8).reshape(h, w)


def _find(run, name):
    f = glob.glob(os.path.join(run, 'exp_*', name))
    if f:
        return f[0]
    p = os.path.join(run, name)
    return p if os.path.exists(p) else None


def load_rows(run):
    f = _find(run, 'robot_state_timeseries.csv')
    return list(csv.DictReader(open(f))) if f else [], f


def load_tasks(run):
    f = _find(run, 'task_positions.csv')
    out = {}
    if not f:
        return out
    for r in csv.DictReader(open(f)):
        try:
            out[r['task_id']] = (float(r['x']), float(r['y']))
        except (KeyError, ValueError):
            pass
    return out


def auto_offset(rows_r, tasks):
    """Per-robot translation that anchors the trajectory to visited tasks.
    Collect the robot pose at each current_task_id transition (robot was
    at/near that task) and take the median (task_coord - pose). Robust to
    failed/reassigned tasks (outliers). Returns (ox, oy)."""
    res = []
    prev = ''
    for i, r in enumerate(rows_r):
        tid = (r.get('current_task_id') or '').strip()
        if prev and tid != prev and prev in tasks and i > 0:
            try:
                px, py = float(rows_r[i - 1]['x']), float(rows_r[i - 1]['y'])
                tx, ty = tasks[prev]
                res.append((tx - px, ty - py))
            except (ValueError, KeyError):
                pass
        prev = tid
    if not res:
        return (0.0, 0.0)
    return (statistics.median(o[0] for o in res),
            statistics.median(o[1] for o in res))


img = read_pgm(PGM)
h, w = img.shape
extent = [ORG[0], ORG[0] + w * RES, ORG[1], ORG[1] + h * RES]
rows, tf = load_rows(RUN)
tasks = load_tasks(RUN)

# group rows by robot, drop uninitialised (~origin) poses
byrobot = {}
for r in rows:
    rid = r['robot_id']
    try:
        x, y = float(r['x']), float(r['y'])
    except (KeyError, ValueError):
        continue
    if abs(x) < 0.15 and abs(y) < 0.15:      # uninitialised (~origin) pose → skip
        continue
    byrobot.setdefault(rid, []).append(r)

traj = {}
offsets = {}
for rid, rr in sorted(byrobot.items()):
    ox, oy = auto_offset([r for r in rows if r['robot_id'] == rid], tasks)
    offsets[rid] = (round(ox, 2), round(oy, 2))
    traj[rid] = [(float(r['x']) + ox, float(r['y']) + oy) for r in rr]
print(f"[auto-align] per-robot offset (task-anchored): {offsets}")

fig, ax = plt.subplots(figsize=(6, 6))
ax.imshow(img, cmap='gray', extent=extent, origin='upper', vmin=0, vmax=255, alpha=0.85)
if tasks:
    tx, ty = zip(*tasks.values())
    ax.scatter(tx, ty, marker='*', s=120, c='gold', edgecolors='k',
               linewidths=0.6, zorder=5, label='tasks')
for i, (rid, pts) in enumerate(sorted(traj.items())):
    if len(pts) < 2:
        continue
    xs, ys = zip(*pts)
    c = ROBOT_COLORS[i % len(ROBOT_COLORS)]
    ax.plot(xs, ys, '-', color=c, lw=2.0, alpha=0.9, zorder=4, label=rid)
    ax.scatter([xs[0]], [ys[0]], marker='s', s=70, color=c, edgecolors='k',
               linewidths=0.8, zorder=6)
    ax.scatter([xs[-1]], [ys[-1]], marker='o', s=45, color=c, edgecolors='k',
               linewidths=0.6, zorder=6)
ax.set_xlim(-10, 10); ax.set_ylim(-10, 10)
ax.set_xlabel('x [m]'); ax.set_ylabel('y [m]')
ax.set_title(TITLE)
ax.legend(loc='upper right', fontsize=8, framealpha=0.9)
ax.set_aspect('equal')
fig.tight_layout()
fig.savefig(OUT, dpi=200, bbox_inches='tight', facecolor='white')
print(f"[OK] {OUT}  (robots={len(traj)}, tasks={len(tasks)}, src={tf})")
