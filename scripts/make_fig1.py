#!/usr/bin/env python3
"""Figure 1 -- the two-level selector and the allocation path.

Replaces the drawio export.  The old figure was authored in drawio units and
rasterised at an arbitrary scale, so its body text landed at 2.5--5.1 pt in
print: unreadable, and not fixable without redrawing, because the width was set
by four stages side by side.  Here the figure is drawn at exactly the width it
is included at and font sizes are given in points, so 8 pt is 8 pt on the page
-- the same discipline the other fifteen figures already follow
(scripts/plot_results.py).

The content follows the method section after the A2 restructure: the override
cascade is the upper level and carries the decisions, the dominance dynamic is
a subordinate fallback, and the geodesic ETA and terminal repair shape the cost
rather than the choice.  The old diagram still drew "Dominance Dynamics" as
stage two of four, with its Lotka--Volterra coefficients spelled out, which is
the emphasis the paper no longer claims.

Output: paper/figure/fig1.pdf (vector; text stays text).
"""

import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

TEXTWIDTH_IN = 516.0 / 72.27          # \textwidth measured from the class
FIG_W = TEXTWIDTH_IN                  # included at width=\textwidth
FIG_H = 3.55

# Point sizes, as printed.
FS_STAGE = 8.5      # stage headings
FS_BODY = 7.6       # box body text
FS_NOTE = 6.8       # annotations
FS_NUM = 7.5        # stage numbers

INK = '#1a1a1a'
MUTED = '#6b6b6b'
ACCENT = '#0b4f6c'      # the load-bearing path
FALLBACK = '#9aa5ab'    # the tier that rarely decides

plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'pdf.fonttype': 42,
    'text.color': INK,
})


def box(ax, x, y, w, h, *, fc='white', ec=INK, lw=0.8, ls='-', r=0.012, z=2):
    p = FancyBboxPatch((x, y), w, h,
                       boxstyle=f'round,pad=0,rounding_size={r}',
                       linewidth=lw, edgecolor=ec, facecolor=fc,
                       linestyle=ls, zorder=z, mutation_aspect=1)
    ax.add_patch(p)
    return p


def text(ax, x, y, s, *, size=FS_BODY, weight='normal', color=INK,
         ha='center', va='center', z=4, style='normal'):
    ax.text(x, y, s, fontsize=size, fontweight=weight, color=color,
            ha=ha, va=va, zorder=z, style=style, linespacing=1.35)


def arrow(ax, x1, y1, x2, y2, *, color=ACCENT, lw=0.9, z=3, style='-|>',
          conn='arc3,rad=0', ls='-'):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                                 mutation_scale=7, linewidth=lw, color=color,
                                 connectionstyle=conn, zorder=z, linestyle=ls,
                                 shrinkA=0, shrinkB=0))


def stage(ax, n, x, y, label):
    """Numbered stage heading sitting above a column."""
    ax.add_patch(plt.Circle((x, y), 0.011, transform=ax.transData,
                            facecolor=ACCENT, edgecolor='none', zorder=5))
    text(ax, x, y, str(n), size=FS_NUM, color='white', weight='bold', z=6)
    text(ax, x + 0.019, y, label, size=FS_STAGE, weight='bold', ha='left')


def build():
    fig = plt.figure(figsize=(FIG_W, FIG_H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    # ---------------- row A: selection -----------------------------------
    yA = 0.60                      # baseline of the top row
    hA = 0.30

    # (1) event + context
    box(ax, 0.010, yA, 0.192, hA)
    stage(ax, 1, 0.027, yA + hA + 0.045, 'Context sensing')
    text(ax, 0.106, yA + hA - 0.045, 'allocation event', size=FS_BODY,
         weight='bold')
    text(ax, 0.106, yA + hA - 0.105,
         'task arrival · robot failure\ndeadline alarm · replan',
         size=FS_NOTE, color=MUTED)
    text(ax, 0.106, yA + 0.115, r'$c(t)\in[0,1]^4$', size=FS_BODY)
    text(ax, 0.106, yA + 0.045,
         '$c_1$ density    $c_2$ availability\n'
         '$c_3$ deadline    $c_4$ failure',
         size=FS_NOTE - 0.4, color=MUTED)

    arrow(ax, 0.202, yA + 0.15, 0.220, yA + 0.15)

    # (2) override cascade -- the load-bearing layer
    box(ax, 0.220, yA, 0.327, hA, ec=ACCENT, lw=1.5, fc='#f2f8fb')
    stage(ax, 2, 0.237, yA + hA + 0.045, 'Context-override cascade')
    text(ax, 0.3795, yA + hA - 0.048,
         'deterministic, checked in this order', size=FS_NOTE, color=MUTED)
    box(ax, 0.228, yA + 0.152, 0.303, 0.062, ec=ACCENT, lw=0.9)
    text(ax, 0.3795, yA + 0.183,
         r'$c_4>0.05$   $\rightarrow$   H_RECOV (orphan-first)',
         size=FS_BODY)
    box(ax, 0.228, yA + 0.082, 0.303, 0.062, ec=ACCENT, lw=0.9)
    text(ax, 0.3795, yA + 0.113,
         r'$c_3>0.50$   $\rightarrow$   H_TEMP (EDF-strict)',
         size=FS_BODY)
    text(ax, 0.3795, yA + 0.037, 'decides 75.2 % of events',
         size=FS_NOTE, color=ACCENT, weight='bold')

    arrow(ax, 0.547, yA + 0.15, 0.574, yA + 0.15)

    # (3) fallback -- drawn subordinate on purpose
    box(ax, 0.574, yA + 0.030, 0.175, 0.215, ec=FALLBACK, lw=0.8, ls=(0, (3, 2)))
    stage(ax, 3, 0.591, yA + hA + 0.045, 'Fallback')
    text(ax, 0.6615, yA + 0.196, r'else  $\arg\max_i D_i(t)$', size=FS_BODY,
         color=MUTED)
    text(ax, 0.6615, yA + 0.130,
         'dominance dynamic\n(cooperation / suppression)',
         size=FS_NOTE, color=MUTED)
    text(ax, 0.6615, yA + 0.062, 'changes 3 of 9 989\nselections',
         size=FS_NOTE, color=MUTED, style='italic')

    arrow(ax, 0.749, yA + 0.15, 0.776, yA + 0.15)

    # (4) dwell + selected paradigm
    box(ax, 0.776, yA, 0.214, hA)
    stage(ax, 4, 0.793, yA + hA + 0.045, 'Dwell + dispatch')
    text(ax, 0.883, yA + hA - 0.055, r'hold $\rho=4$ events', size=FS_BODY)
    text(ax, 0.883, yA + hA - 0.110, 'H_RECOV bypasses the hold',
         size=FS_NOTE, color=MUTED)
    box(ax, 0.793, yA + 0.048, 0.180, 0.072, ec=ACCENT, lw=1.2, fc='#f2f8fb')
    text(ax, 0.883, yA + 0.084, r'active paradigm  $p^\ast$', size=FS_BODY,
         weight='bold')

    # p* carries the choice into row B.  It lands on the portfolio box itself
    # (x clear of the stage-5 heading) rather than stopping in white space.
    arrow(ax, 0.883, yA + 0.048, 0.883, 0.500, style='-')
    arrow(ax, 0.883, 0.500, 0.290, 0.500, style='-')
    arrow(ax, 0.290, 0.500, 0.290, 0.405)
    text(ax, 0.305, 0.455, r'$p^\ast$', size=FS_NOTE, color=ACCENT, ha='left')

    # ---------------- row B: allocation ----------------------------------
    yB = 0.115
    hB = 0.29

    # (5) portfolio
    box(ax, 0.045, yB, 0.289, hB)
    stage(ax, 5, 0.062, yB + hB + 0.045, 'Paradigm portfolio')
    rows = [('H_SPATIAL', 'nearest-feasible greedy'),
            ('H_CRIT', 'priority-tiered LSA'),
            ('H_TEMP', 'EDF-strict, 3-phase'),
            ('H_STAB', 'commit-once, no reassign'),
            ('H_RECOV', 'orphan rescue then bipartite')]
    for i, (h, d) in enumerate(rows):
        yy = yB + hB - 0.040 - i * 0.049
        text(ax, 0.061, yy, h, size=FS_NOTE, ha='left', weight='bold')
        text(ax, 0.143, yy, d, size=FS_NOTE, ha='left', color=MUTED)

    arrow(ax, 0.334, yB + 0.145, 0.360, yB + 0.145)

    # (6) cost oracle
    box(ax, 0.360, yB, 0.227, hB, ec=ACCENT, lw=1.2)
    stage(ax, 6, 0.377, yB + hB + 0.045, 'Cost oracle')
    text(ax, 0.4735, yB + hB - 0.048, 'cached geodesic ETA', size=FS_BODY,
         weight='bold')
    text(ax, 0.4735, yB + hB - 0.103,
         'traversable map distance,\nnot straight line',
         size=FS_NOTE, color=MUTED)
    text(ax, 0.4735, yB + 0.068, 'feasibility mask', size=FS_BODY)
    text(ax, 0.4735, yB + 0.028, r'arrival $>$ deadline $\Rightarrow$ rejected',
         size=FS_NOTE, color=MUTED)

    arrow(ax, 0.587, yB + 0.145, 0.613, yB + 0.145)

    # (7) assignment + repair
    box(ax, 0.613, yB, 0.227, hB)
    stage(ax, 7, 0.630, yB + hB + 0.045, 'Assign + repair')
    text(ax, 0.7265, yB + hB - 0.050,
         r'$x^\ast=\arg\min\sum_{r,\tau} C^{(p)}$', size=FS_BODY)
    text(ax, 0.7265, yB + hB - 0.100, 'single-owner, in-flight lock',
         size=FS_NOTE, color=MUTED)
    box(ax, 0.630, yB + 0.030, 0.193, 0.078, ec=ACCENT, lw=0.9, fc='#f2f8fb')
    text(ax, 0.7265, yB + 0.081, r'terminal $\epsilon$-load repair',
         size=FS_BODY)
    text(ax, 0.7265, yB + 0.046, 'non-regression guarded',
         size=FS_NOTE, color=MUTED)

    arrow(ax, 0.840, yB + 0.145, 0.866, yB + 0.145)

    # (8) queues
    box(ax, 0.866, yB, 0.124, hB)
    stage(ax, 8, 0.883, yB + hB + 0.045, 'Publish')
    text(ax, 0.9280, yB + 0.190, 'per-robot\ntask queues', size=FS_BODY)
    text(ax, 0.9280, yB + 0.085, 'own queue only;\nno negotiation\nprotocol',
         size=FS_NOTE, color=MUTED)

    # feedback loop back to context sensing
    # Feedback updates the context, i.e. stage 1 -- it must not appear to feed
    # the portfolio.  It therefore runs along the bottom, up the left margin
    # opened by shifting row B right, and into the context box from below.
    fb_y = 0.052
    fb_x = 0.020
    arrow(ax, 0.9280, yB, 0.9280, fb_y, style='-', color=MUTED, lw=0.8)
    arrow(ax, 0.9280, fb_y, fb_x, fb_y, style='-', color=MUTED, lw=0.8)
    arrow(ax, fb_x, fb_y, fb_x, yA + 0.15, style='-', color=MUTED, lw=0.8)
    arrow(ax, fb_x, yA + 0.15, 0.010, yA + 0.15, color=MUTED, lw=0.8)
    text(ax, 0.530, fb_y - 0.028,
         'execution feedback — completions, failures, poses, queue state',
         size=FS_NOTE, color=MUTED)

    return fig


def main():
    out_dir = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), 'paper', 'figure')
    os.makedirs(out_dir, exist_ok=True)
    fig = build()
    pdf = os.path.join(out_dir, 'fig1.pdf')
    fig.savefig(pdf, format='pdf', bbox_inches=None)
    plt.close(fig)
    print(f'OK  {pdf}  {FIG_W:.2f}x{FIG_H:.2f} in '
          f'(drawn at \\textwidth; body text {FS_BODY} pt)')


if __name__ == '__main__':
    main()
