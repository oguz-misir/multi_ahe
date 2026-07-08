#!/usr/bin/env python3
"""Per-seed paired F45 vs F58/P1R Nav2-independent (allocation-only) campaign.

Both variants execute on the same geodesic measurement oracle
(``AHE_SIM_GEODESIC_EXECUTION=1``) with ``ideal_nav=True``; only the allocator
feature gate differs.  F53 is forced off in both arms, matching
``scripts/validate_f45_allocation.py``.  Statistics: per-seed paired Wilcoxon
signed-rank with a Holm family of the 10 metrics per cell x scenario, plus a
paired sign-based Cliff's delta.

Usage:
    python3 scripts/validate_f58_nav2free_paired.py run       # all 4 cells
    python3 scripts/validate_f58_nav2free_paired.py analyze   # REPORT.md
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

sys.path.insert(0, str(Path(__file__).resolve().parent))
import simulate_and_tune as sim  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "results/stats/f58_p1r_nav2free_compare"
SCENARIOS = ["robot_failure", "mixed_stress", "deadline_pressure"]
# (label, robots, tasks, seed_start, n_seeds, csv name)
CELLS = [
    ("5r/25g ana (seed 1-100)", 5, 25, 1, 100, "per_seed_5r25t_main.csv"),
    ("3r/15g (seed 1-100)", 3, 15, 1, 100, "per_seed_3r15t.csv"),
    ("10r/50g (seed 1-100)", 10, 50, 1, 100, "per_seed_10r50t.csv"),
    ("5r/25g holdout (seed 501-600)", 5, 25, 501, 100,
     "per_seed_5r25t_holdout.csv"),
]
# metric -> (label, higher_is_better)
METRICS = {
    "alloc_fitness": ("Fitness", True),
    "completion_rate": ("CR", True),
    "avg_delay": ("Delay (s)", False),
    "deadline_violation_rate": ("DVR", False),
    "workload_balance": ("Jain(all)", True),
    "workload_balance_active": ("Jain(active)", True),
    "travel_distance_balance": ("Distance-Jain", True),
    "total_distance": ("Distance (m)", False),
    "allocation_instability": ("Churn", False),
    "mean_decision_latency_ms": ("Latency (ms)", False),
}
VARIANT_ENV = {
    "f45": {"AHE_F58_GEODESIC": "0", "AHE_F58_FAIR_REPAIR": "0"},
    "f58": {"AHE_F58_GEODESIC": "1", "AHE_F58_FAIR_REPAIR": "1"},
}


def run_cell(robots: int, tasks: int, seed_start: int, n_seeds: int,
             out_csv: Path) -> None:
    os.environ["AHE_FAIR_ANTI_IDLE"] = "0"
    os.environ["AHE_SIM_GEODESIC_EXECUTION"] = "1"
    registry = sim._make_allocators()
    t0 = time.time()
    rows = []
    for scenario in SCENARIOS:
        for seed in range(seed_start, seed_start + n_seeds):
            for variant, env in VARIANT_ENV.items():
                os.environ.update(env)
                alloc = registry["ahe_mrta_v3"]()
                eco = sim.EcosystemSimulator()
                r = sim.run_simulation(
                    alloc, scenario, seed,
                    n_robots=robots, n_tasks=tasks,
                    exp_duration=900.0, eco=eco, ideal_nav=True,
                )
                row = {"robots": robots, "tasks": tasks,
                       "scenario": scenario, "seed": seed, "variant": variant}
                row.update({m: r[m] for m in METRICS})
                rows.append(row)
        print(f"[{time.time()-t0:7.1f}s] {scenario} done", flush=True)
    with out_csv.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"WROTE {out_csv} ({len(rows)} rows)")


def cliffs_delta(a: np.ndarray, b: np.ndarray) -> float:
    d = a - b
    return float((np.sum(d > 0) - np.sum(d < 0)) / len(d))


def holm(pvals: list[float]) -> list[float]:
    order = np.argsort(pvals)
    adj = np.empty(len(pvals))
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, (len(pvals) - rank) * pvals[idx])
        adj[idx] = min(1.0, running)
    return adj.tolist()


def analyze() -> None:
    lines = [
        "# F58/P1R vs F45 — Nav2-bağımsız (allocation-only) eşlenik karşılaştırma",
        "",
        "Her iki varyant aynı geodezik yürütme oracle'ında "
        "(`AHE_SIM_GEODESIC_EXECUTION=1`), `ideal_nav=True`, F53 kapalı. "
        "Eşleştirme: aynı seed, aynı senaryo. Test: Wilcoxon signed-rank + "
        "Holm (hücre×senaryo başına 10 metrik ailesi); etki: eşlenik Cliff's Δ "
        "(fark işaret oranı). Pozitif Δort her zaman 'F58 daha iyi' yönünde "
        "raporlanır.",
        "",
    ]
    total_sig = 0
    total_tests = 0
    for cell_label, *_rest, fname in CELLS:
        df = pd.read_csv(OUT / fname)
        lines += [f"## {cell_label}", ""]
        for scenario in SCENARIOS:
            sub = df[df.scenario == scenario]
            f45 = sub[sub.variant == "f45"].sort_values("seed").reset_index(drop=True)
            f58 = sub[sub.variant == "f58"].sort_values("seed").reset_index(drop=True)
            assert (f45.seed.values == f58.seed.values).all()
            rows, pvals = [], []
            for m, (label, hib) in METRICS.items():
                a, b = f58[m].to_numpy(float), f45[m].to_numpy(float)
                diff = a - b
                if np.allclose(diff, 0.0):
                    p = 1.0
                else:
                    p = float(wilcoxon(a, b, zero_method="wilcox").pvalue)
                imp = float(np.mean(diff)) * (1 if hib else -1)
                delta = cliffs_delta(a, b) * (1 if hib else -1)
                rows.append([label, float(np.mean(b)), float(np.mean(a)),
                             imp, delta])
                pvals.append(p)
            padj = holm(pvals)
            lines += [
                f"### {scenario}", "",
                "| Metrik | F45 | F58/P1R | Δiyileşme (F58 lehine +) | "
                "Cliff's Δ | p (Holm) | Anlamlı |",
                "|---|---:|---:|---:|---:|---:|:--:|",
            ]
            for (label, mb, ma, imp, delta), pa in zip(rows, padj):
                sig = "**EVET**" if pa < 0.05 else "hayır"
                if pa < 0.05:
                    total_sig += 1
                total_tests += 1
                lines.append(
                    f"| {label} | {mb:.4f} | {ma:.4f} | {imp:+.4f} | "
                    f"{delta:+.3f} | {pa:.4g} | {sig} |")
            lines.append("")
    lines += [f"Toplam test: {total_tests}; Holm sonrası p<0.05: {total_sig}.", ""]
    (OUT / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Report: {OUT / 'REPORT.md'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["run", "analyze"])
    args = ap.parse_args()
    if args.command == "run":
        OUT.mkdir(parents=True, exist_ok=True)
        for _label, robots, tasks, seed_start, n_seeds, fname in CELLS:
            run_cell(robots, tasks, seed_start, n_seeds, OUT / fname)
    analyze()


if __name__ == "__main__":
    main()
