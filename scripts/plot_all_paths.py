#!/usr/bin/env python3
"""Batch path-plot generator: one trajectory-on-map figure per result.

Scans a results dir for exp_* runs, and for each (scenario, method) — by
default a representative seed (lowest) — renders the per-robot trajectory +
task allocation over the arena occupancy map (via plot_method_paths logic).

Usage:
  python3 scripts/plot_all_paths.py <results_dir> <out_dir> [--all-seeds]
"""
import sys, os, glob, re, subprocess

RESDIR = sys.argv[1]
OUTDIR = sys.argv[2]
ALL_SEEDS = '--all-seeds' in sys.argv
os.makedirs(OUTDIR, exist_ok=True)

MLAB = {'ahe_mrta_v3': 'AHE-MRTA', 'big_mrta': 'BiG-MRTA',
        'rostam_ea': 'RoSTAM-EA', 'consensus_dbta': 'Cons-DBTA'}

# exp_<scenario>_<method>_r<R>t<T>_seed<NN>
PAT = re.compile(r'exp_(.+?)_(ahe_mrta_v3|big_mrta|rostam_ea|consensus_dbta)_(r\d+t\d+)_seed(\d+)$')

runs = {}
for d in sorted(glob.glob(os.path.join(RESDIR, 'exp_*'))):
    if not os.path.isdir(d):
        continue
    m = PAT.search(os.path.basename(d))
    if not m:
        continue
    scen, method, scale, seed = m.group(1), m.group(2), m.group(3), int(m.group(4))
    if not os.path.exists(os.path.join(d, 'robot_state_timeseries.csv')):
        continue
    key = (scen, method, scale) if not ALL_SEEDS else (scen, method, scale, seed)
    # keep lowest seed as representative (unless all-seeds)
    if ALL_SEEDS:
        runs[key] = (d, seed)
    elif key not in runs or seed < runs[key][1]:
        runs[key] = (d, seed)

print(f"[batch] {len(runs)} figür üretilecek ({RESDIR})")
n = 0
for key, (d, seed) in sorted(runs.items()):
    scen, method, scale = key[0], key[1], key[2]
    title = f"{MLAB.get(method, method)} — {scen} ({scale}, seed{seed:02d})"
    out = os.path.join(OUTDIR, f"path_{scale}_{scen}_{method}_seed{seed:02d}.png")
    r = subprocess.run([sys.executable, 'scripts/plot_method_paths.py', d, out, title],
                       capture_output=True, text=True)
    ok = '[OK]' in r.stdout
    n += ok
    print(f"  {'✓' if ok else '✗'} {os.path.basename(out)}"
          + ('' if ok else f"  ({r.stdout.strip()[:80]}{r.stderr.strip()[:80]})"))
print(f"[batch] {n}/{len(runs)} figür yazıldı → {OUTDIR}")
