#!/usr/bin/env python3
"""Gerçek (fiziksel) kararlılık metriklerini loglardan yeniden hesaplar.

Mevcut summary.csv metrik kusurları:
  allocation_instability = alloc_count/(completed+1)  → allocator ÇAĞRI sayısı
  replanning_frequency   = alloc_count/dk             → yine çağrı sayısı
İkisi de atama churn'ünü değil, yöntemin çağrılma kadansını ölçer (olay-tetikli
yöntemler cezalandırılır, commit-once yöntemler ödüllendirilir).

Bu script robot_state_timeseries.csv'deki current_task_id geçişlerinden
yöntem-bağımsız, fiziksel iki metrik çıkarır (tüm eski deneyler için geçerli —
baseline yeniden koşmak gerekmez):

  exec_preemptions : robot, görevi bitirmeden başka göreve geçti (t→u) —
                     Nav2 hedef iptali + yol terki (gerçek fiziksel bedel)
  task_redispatch  : bir görevin ilk denemesinden SONRAKİ yürütme başlangıçları
                     (başka robot veya aynı robotta yeniden deneme)

Kullanım:
  python3 scripts/recompute_stability_metrics.py --raw-dir results/raw/gazebo
  → <raw-dir>/.../true_stability.csv (deney başına) + stdout özet
"""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

import pandas as pd


def compute_for_exp(exp_dir: Path) -> dict | None:
    ts_path = exp_dir / "robot_state_timeseries.csv"
    te_path = exp_dir / "task_events.csv"
    if not ts_path.exists():
        return None
    ts = pd.read_csv(ts_path)
    if "current_task_id" not in ts.columns:
        return None
    ts = ts.sort_values("timestamp_s")

    completed: set = set()
    if te_path.exists():
        te = pd.read_csv(te_path)
        completed = set(te[te.event == "completed"].task_id)

    preemptions = 0
    episodes: dict = defaultdict(int)   # task → yürütme başlangıcı sayısı
    last: dict = {}                      # robot → son current_task_id
    for row in ts.itertuples(index=False):
        rid = row.robot_id
        cur = row.current_task_id if isinstance(row.current_task_id, str) else ""
        prev = last.get(rid, "")
        if cur != prev:
            if prev and cur and prev not in completed:
                # bitirmeden doğrudan başka göreve geçiş
                preemptions += 1
            if cur:
                episodes[cur] += 1
        last[rid] = cur

    redispatch = sum(max(0, n - 1) for n in episodes.values())
    n_exec = max(1, len(episodes))
    return {
        "experiment_id": exp_dir.name,
        "exec_preemptions": preemptions,
        "task_redispatch": redispatch,
        "redispatch_per_task": round(redispatch / n_exec, 4),
        "n_tasks_executed": len(episodes),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", default="results/raw/gazebo")
    ap.add_argument("--pattern", default="exp_*")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    raw = Path(args.raw_dir)
    rows = []
    for d in sorted(raw.glob(args.pattern)):
        if not (d / "DONE").exists():
            continue
        r = compute_for_exp(d)
        if r:
            rows.append(r)
    if not rows:
        print("Hiç deney bulunamadı.")
        return
    out = Path(args.out) if args.out else raw / "true_stability.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    df = pd.DataFrame(rows)
    df["strategy"] = df.experiment_id.str.extract(
        r"exp_(?:[a-z_]+?)_((?:ahe_mrta_v3|big_mrta|rostam_ea|consensus_dbta))_")
    df["scenario"] = df.experiment_id.str.extract(
        r"exp_((?:robot_failure|mixed_stress|deadline_pressure))_")
    g = df.groupby(["scenario", "strategy"])[
        ["exec_preemptions", "task_redispatch", "redispatch_per_task"]].mean().round(2)
    print(g.to_string())
    print(f"\n[OK] {out}  ({len(rows)} deney)")


if __name__ == "__main__":
    main()
