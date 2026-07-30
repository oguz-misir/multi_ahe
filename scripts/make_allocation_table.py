#!/usr/bin/env python3
"""Generate tab:allocation from the allocation-only campaign summaries.

This table used to be filled in by hand and had drifted from its sources: the
committed version reported 0.982 active Jain, 284.1 m and 0.200 ms for the
10r/50t robot_failure cell where ``f58_allocation_only_10r50t/summary.csv``
says 0.961, 272.7 m and 0.361 ms.  The stale 0.200 ms had also propagated into
the running text as "latency is at most 0.201 ms".  Generating the table closes
that failure mode.

Sources (one per scale), as recorded in results/README.md:
    stats/f58_allocation_only_3r15t/summary.csv
    stats/f58_allocation_only/summary.csv          (5r/25t)
    stats/f58_allocation_only_10r50t/summary.csv

Usage:
    python3 scripts/make_allocation_table.py
"""

from __future__ import annotations

import os

import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATS = os.path.join(REPO, 'results', 'stats')
TABLE_DIR = os.path.join(REPO, 'paper', 'table')

SOURCES = [
    ('3r/15t', 'f58_allocation_only_3r15t'),
    ('5r/25t', 'f58_allocation_only'),
    ('10r/50t', 'f58_allocation_only_10r50t'),
]
SCENARIOS = [
    ('robot_failure', 'Robot failure', 'Robot arızası'),
    ('mixed_stress', 'Mixed stress', 'Karışık stres'),
    ('deadline_pressure', 'Deadline pressure', 'Deadline baskısı'),
]

CAPTION_EN = (
    'AHE-MRTA navigation-independent allocation-only results (100 seeds per '
    'cell). Navigation succeeds deterministically; distance is the geodesic '
    'path length on the shared inflated occupancy map.')
CAPTION_TR = (
    "AHE-MRTA navigasyon-ba\\u{g}\\i ms\\i z allocation-only sonu\\c{c}lar\\i "
    "(h\\\"ucre ba\\c{s}\\i na 100 tohum). Navigasyon belirlenimci olarak "
    "ba\\c{s}ar\\i l\\i d\\i r; mesafe, payla\\c{s}\\i lan \\c{s}i\\c{s}irilmi\\c{s} "
    "doluluk haritas\\i \\\"uzerindeki geodezik yol uzunlu\\u{g}udur.")

HEAD_EN = (r'\textbf{Scale} & \textbf{Scenario} & \textbf{Fit.} & \textbf{CR} & '
           r'\textbf{DVR} & \textbf{Jain$_{active}$} & \textbf{Jain$_{dist}$} & '
           r'\textbf{Delay (s)} & \textbf{Distance} & \textbf{Decision (ms)} \\')
HEAD_TR = (r'\textbf{\"Ol\c{c}ek} & \textbf{Senaryo} & \textbf{Uyg.} & \textbf{CR} & '
           r'\textbf{DVR} & \textbf{Jain$_{aktif}$} & \textbf{Jain$_{mesafe}$} & '
           r'\textbf{Gecikme (s)} & \textbf{Mesafe} & \textbf{Karar (ms)} \\')


def rows():
    for scale, folder in SOURCES:
        path = os.path.join(STATS, folder, 'summary.csv')
        df = pd.read_csv(path)
        df = df[df.strategy == 'ahe_mrta_v3']
        for key, label_en, label_tr in SCENARIOS:
            r = df[df.scenario == key]
            if r.empty:
                raise SystemExit(f'missing {key} in {path}')
            r = r.iloc[0]
            yield scale, label_en, label_tr, (
                f'{r.alloc_fitness:.3f} & {r.completion_rate:.3f} & '
                f'{r.deadline_violation_rate:.3f} & '
                f'{r.workload_balance_active:.3f} & '
                f'{r.travel_distance_balance:.3f} & {r.avg_delay:.1f} & '
                f'{r.total_distance:.1f} & {r.mean_decision_latency_ms:.3f}')


def write(fname: str, caption: str, header: str, turkish: bool) -> None:
    out = [r'\begin{table}[t]', r'\centering', rf'\caption{{{caption}}}',
           r'\label{tab:allocation}', r'\small',
           r'\setlength{\tabcolsep}{3.5pt}',
           r'\resizebox{\textwidth}{!}{%',
           r'\begin{tabular}{llrrrrrrrr}', r'\toprule', header, r'\midrule']
    previous = None
    for scale, label_en, label_tr, cells in rows():
        if previous is not None and scale != previous:
            out.append(r'\midrule')
        previous = scale
        out.append(f'{scale} & {label_tr if turkish else label_en} & {cells} \\\\')
    out += [r'\bottomrule', r'\end{tabular}}', r'\end{table}', '']
    path = os.path.join(TABLE_DIR, fname)
    with open(path, 'w') as fh:
        fh.write('\n'.join(out))
    print(f'[OK] {fname}')


def main() -> None:
    write('allocation_only.tex', CAPTION_EN, HEAD_EN, turkish=False)
    write('allocation_only_tr.tex', CAPTION_TR, HEAD_TR, turkish=True)
    peak = max(r[3].split(' & ')[-1] for r in rows())
    print(f'[note] worst decision latency across all nine cells: {peak} ms')


if __name__ == '__main__':
    main()
