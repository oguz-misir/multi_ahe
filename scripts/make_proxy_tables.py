#!/usr/bin/env python3
"""Generate the three simulator-plane tables from their canonical sources.

tab:fitness, tab:scalability and tab:ablation were the last hand-maintained
data tables in the paper, and hand maintenance is what put ablation.tex months
out of step with the file it was supposed to summarise.  They are now written
from `results/processed/` in both languages, so the numbers cannot disagree
with the data or with each other.

Sources
    sim_fitness.csv, sim_fitness_seedwise.csv   -> tab:fitness  (right half)
    sim_fitness_ideal.csv                       -> tab:fitness  (left half)
    sim_scalability.csv                         -> tab:scalability
    ablation_edps_100_geodesic.txt              -> tab:ablation

Usage:  python3 scripts/make_proxy_tables.py
"""

import collections
import csv
import os
import re
import sys

try:
    from scipy.stats import wilcoxon
except ImportError:
    sys.exit("scipy is required: pip install scipy")

PROC = 'results/processed'
TBL = 'paper/table'
AHE = 'ahe_mrta_v3'
METHODS = [(AHE, r'\textbf{AHE-MRTA*}'), ('big_mrta', 'BiG-MRTA'),
           ('rostam_ea', 'RoSTAM-EA'), ('consensus_dbta', 'Cons-DBTA')]
SCEN = ['robot_failure', 'mixed_stress', 'deadline_pressure']
SCEN_SHORT = ['RF', 'MS', 'DP']


def read_fitness(name):
    out = {}
    with open(os.path.join(PROC, name)) as f:
        for r in csv.DictReader(f):
            out[(r['scenario'], r['strategy'])] = float(r['fitness_mean'])
    return out


def read_seedwise(name):
    out = collections.defaultdict(dict)
    with open(os.path.join(PROC, name)) as f:
        for r in csv.DictReader(f):
            out[(r['scenario'], r['strategy'])][int(r['seed'])] = \
                float(r['alloc_fitness'])
    return out


def paired_p(sw, scenario, other):
    """AHE against one baseline on common seeds."""
    a, b = sw[(scenario, AHE)], sw[(scenario, other)]
    seeds = sorted(set(a) & set(b))
    x = [a[s] for s in seeds]
    y = [b[s] for s in seeds]
    if not seeds or all(u == v for u, v in zip(x, y)):
        return 1.0
    return wilcoxon(x, y).pvalue


def fmt(v, best, digits=3):
    s = f'{v:.{digits}f}'
    return rf'\textbf{{{s}}}' if abs(v - best) < 1e-9 else s


def table_fitness(lang):
    ideal, stoch = read_fitness('sim_fitness_ideal.csv'), read_fitness('sim_fitness.csv')
    sw = read_seedwise('sim_fitness_seedwise.csv')
    n = len(next(iter(sw.values())))
    worst = min(min(paired_p(sw, s, m) for m, _ in METHODS[1:]) for s in SCEN)
    best_p = max(max(paired_p(sw, s, m) for m, _ in METHODS[1:]) for s in SCEN)
    cap_en = (
        rf'Allocation fitness (priority-weighted on-time completion), {n} seeds, '
        r'5 robots / 25 tasks. \textbf{Left:} perfect-navigation plane, which '
        r'isolates allocation quality. \textbf{Right:} the stochastic navigation '
        r'proxy, where Nav2 goal failure can also cost a task. AHE-MRTA leads '
        r'every scenario on both planes; every paired-Wilcoxon comparison against '
        rf'a baseline is significant except one (all $p<{best_p:.3f}$ except '
        r'AHE--BiG under robot failure, which is a tie). '
        r'\textbf{Bold} marks the best per column.')
    cap_tr = (
        rf'Tahsis uygunluğu (öncelik-ağırlıklı zamanında tamamlama), {n} tohum, '
        r'5 robot / 25 görev. \textbf{Sol:} mükemmel-navigasyon düzlemi, tahsis '
        r'kalitesini yalıtır. \textbf{Sağ:} stokastik navigasyon vekili; burada '
        r'Nav2 hedef arızası da bir göreve mal olabilir. AHE-MRTA her iki düzlemde '
        r've her senaryoda öndedir; temel yöntemlere karşı eşli Wilcoxon '
        r'karşılaştırmalarının biri dışında hepsi anlamlıdır (arıza senaryosunda '
        r'AHE--BiG beraberedir). \textbf{Kalın} sütun en iyisidir.')
    rows = []
    for m, label in METHODS:
        cells = []
        for src in (ideal, stoch):
            for s in SCEN:
                best = max(src[(s, mm)] for mm, _ in METHODS)
                cells.append(fmt(src[(s, m)], best))
        rows.append(f'{label} & ' + ' & '.join(cells) + r' \\')
    head = (r'\textbf{Method} & ' if lang == 'en' else r'\textbf{Yöntem} & ') + \
        ' & '.join(SCEN_SHORT * 2) + r' \\'
    grp = ((r'& \multicolumn{3}{c}{\textbf{Perfect nav (alloc.\ quality)}} & '
            r'\multicolumn{3}{c}{\textbf{Stochastic nav (resil.)}} \\')
           if lang == 'en' else
           (r'& \multicolumn{3}{c}{\textbf{Mükemmel nav (tahsis kalitesi)}} & '
            r'\multicolumn{3}{c}{\textbf{Stokastik nav (dayanıklılık)}} \\'))
    return wrap('tab:fitness', cap_en if lang == 'en' else cap_tr,
                'l ccc ccc', [grp, r'\cmidrule(lr){2-4}\cmidrule(lr){5-7}', head,
                              r'\midrule'] + rows)


def table_scalability(lang):
    fit = collections.defaultdict(dict)
    lat = collections.defaultdict(dict)
    with open(os.path.join(PROC, 'sim_scalability.csv')) as f:
        for r in csv.DictReader(f):
            n = int(float(r['robot_count']))
            fit[(n, r['strategy'])].setdefault('v', []).append(float(r['fitness']))
            lat[(n, r['strategy'])].setdefault('v', []).append(float(r['latency']))
    scales = sorted({k[0] for k in fit})
    cap_en = (r'Scalability (stochastic navigation proxy, geodesic execution '
              r'oracle, 100 seeds, fixed density 5 tasks/robot, mean over '
              r'scenarios). Fitness $\uparrow$, latency (ms) $\downarrow$. '
              r'Best per scale \textbf{bold}. Physical Gazebo validation: 3r, '
              r'5r, and 10r confirmed.')
    cap_tr = (r'Ölçeklenebilirlik (stokastik navigasyon vekili, geodezik yürütme '
              r'kâhini, 100 tohum, sabit yoğunluk 5 görev/robot, senaryolar '
              r'üzerinden ortalama). Uygunluk $\uparrow$, gecikme (ms) '
              r'$\downarrow$. Ölçek başına en iyi \textbf{kalın}. Fiziksel '
              r'Gazebo doğrulaması: 3r, 5r ve 10r.')
    rows = []
    for m, label in METHODS:
        cells = []
        for n in scales:
            fv = sum(fit[(n, m)]['v']) / len(fit[(n, m)]['v'])
            lv = sum(lat[(n, m)]['v']) / len(lat[(n, m)]['v'])
            bf = max(sum(fit[(n, mm)]['v']) / len(fit[(n, mm)]['v'])
                     for mm, _ in METHODS)
            bl = min(sum(lat[(n, mm)]['v']) / len(lat[(n, mm)]['v'])
                     for mm, _ in METHODS)
            cells += [fmt(fv, bf), fmt(lv, bl, 2)]
        rows.append(f'{label} & ' + ' & '.join(cells) + r' \\')
    grp = '& ' + ' & '.join(rf'\multicolumn{{2}}{{c}}{{\textbf{{{n} robots}}}}'
                            for n in scales) + r' \\'
    mid = ''.join(rf'\cmidrule(lr){{{2 + 2 * i}-{3 + 2 * i}}}'
                  for i in range(len(scales)))
    head = (r'\textbf{Method} & ' if lang == 'en' else r'\textbf{Yöntem} & ') + \
        ' & '.join(['Fit. & Lat.'] * len(scales)) + r' \\'
    return wrap('tab:scalability', cap_en if lang == 'en' else cap_tr,
                'l ' + 'cc ' * len(scales), [grp, mid, head, r'\midrule'] + rows)


def table_ablation(lang):
    path = os.path.join(PROC, 'ablation_edps_100_geodesic.txt')
    rows, spread = [], None
    with open(path) as f:
        for line in f:
            m = re.match(r'^(\S.*?)\s{2,}([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*$',
                         line.rstrip())
            if m:
                rows.append([m.group(1).strip()] + [float(m.group(i)) for i in range(2, 6)])
            s = re.search(r'spread across all variants:\s*([\d.]+)', line)
            if s:
                spread = float(s.group(1))
    if not rows:
        sys.exit(f'could not parse {path}')
    best = max(r[4] for r in rows)
    full = next(r[4] for r in rows if r[0].lower().startswith('full'))
    cap_en = (r'Selector ablation (stochastic navigation proxy, geodesic '
              r'execution oracle, 5r/25t, 100 seeds). On the corrected scenario '
              rf'parameters the variants span {spread:.3f} in mean fitness. '
              r'Removing the context overrides leaves the selector essentially '
              r'unchanged, and fixed spatial-greedy is ahead of it on this '
              r'plane---the closed-loop ablation '
              r'(Section~\ref{sec:gazebo-ablation}) tests both observations.')
    cap_tr = (r'Seçici ablasyonu (stokastik navigasyon vekili, geodezik yürütme '
              r'kâhini, 5r/25g, 100 tohum). Düzeltilmiş senaryo parametreleriyle '
              rf'varyantlar ortalama uygunlukta {spread:.3f} aralığa yayılır. '
              r'Bağlam geçersiz kılmalarını kaldırmak seçiciyi neredeyse hiç '
              r'değiştirmez ve bu düzlemde sabit spatial-greedy onun önündedir; '
              r'her iki gözlem de kapalı-çevrim ablasyonunda '
              r'(Bölüm~\ref{sec:gazebo-ablation}) sınanır.')
    head = ((r'\textbf{Variant} & \textbf{Rob.\ fail.} & \textbf{Deadline} & '
             r'\textbf{Mix.\ stress} & \textbf{Mean} \\') if lang == 'en' else
            (r'\textbf{Varyant} & \textbf{Arıza} & \textbf{Deadline} & '
             r'\textbf{Karışık} & \textbf{Ortalama} \\'))
    body = []
    for name, rf_, dp, ms, mean in rows:
        lbl = name.replace('_', r'\_')
        if name.lower().startswith('full'):
            lbl = rf'\textbf{{{lbl}}}'
        body.append(f'{lbl} & {rf_:.3f} & {dp:.3f} & {ms:.3f} & '
                    f'{fmt(mean, best)} ' + r'\\')
    note = ((rf'\multicolumn{{5}}{{l}}{{\footnotesize Full selector mean '
             rf'{full:.3f}; best variant {best:.3f}.}} \\') if lang == 'en' else
            (rf'\multicolumn{{5}}{{l}}{{\footnotesize Tam seçici ortalaması '
             rf'{full:.3f}; en iyi varyant {best:.3f}.}} \\'))
    return wrap('tab:ablation', cap_en if lang == 'en' else cap_tr,
                'lcccc', [head, r'\midrule'] + body + [r'\midrule', note])


def wrap(label, caption, colspec, lines):
    return '\n'.join([
        '% GENERATED by scripts/make_proxy_tables.py -- do not edit by hand.',
        r'\begin{table}[t]', r'\centering', rf'\caption{{{caption}}}',
        rf'\label{{{label}}}', r'\small', r'\setlength{\tabcolsep}{4pt}',
        rf'\begin{{tabular}}{{{colspec}}}', r'\toprule', *lines,
        r'\bottomrule', r'\end{tabular}', r'\end{table}', ''])


def main():
    for lang, suffix in (('en', ''), ('tr', '_tr')):
        for name, fn in (('fitness', table_fitness),
                         ('scalability', table_scalability),
                         ('ablation', table_ablation)):
            path = os.path.join(TBL, f'{name}{suffix}.tex')
            with open(path, 'w') as f:
                f.write(fn(lang))
            print(f'[OK] {path}')


if __name__ == '__main__':
    main()
