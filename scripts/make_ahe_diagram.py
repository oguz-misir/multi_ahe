#!/usr/bin/env python3
"""Detailed AHE-MRTA method diagram.

Single layout spec -> rendered two ways:
  (1) results/figures/ahe_method_detailed.png   matplotlib xkcd (hand-drawn,
      Excalidraw-style) — for direct \\includegraphics in the .tex
  (2) docs/ahe_method_diagram.excalidraw         genuine Excalidraw JSON source,
      openable/editable at full fidelity in excalidraw.com

Layout is auto-sized: every box is made wide enough for its longest line and
tall enough for its line count, so text never overflows; the main pipeline is a
single centred column with straight vertical arrows, side panels are connected
with aligned horizontal dotted links, and the performance-feedback loop is a
clean orthogonal route in the left margin.
"""
import json, os, random, time

# ---------------------------------------------------------------------------
# Geometry constants (Excalidraw screen coords: x right, y down)
# ---------------------------------------------------------------------------
TITLE_FS, BOX_TFS, BODY_FS = 15, 13, 11
SIDE_TFS, SIDE_FS = 12, 10.5
PAD_X, TITLE_H, LINE_H, PAD_BOT = 18, 30, 21, 16
CHAR_W = 0.62          # monospace char width as fraction of font size (pt)

COL = {
    'in':  '#e9ecef', 'ctx': '#a5d8ff', 'dyn': '#b2f2bb', 'disp': '#ffd8a8',
    'para': '#d0bfff', 'cost': '#96f2d7', 'out': '#ffec99', 'side': '#f8f9fa',
}
LEFT_MARGIN = 230
COL_X = LEFT_MARGIN + 40
V_GAP, SIDE_GAP = 64, 70


def _text_w(lines, fs):
    return max((len(s) for s in lines), default=0) * fs * CHAR_W

def box(bid, title, lines, fill, fs=BODY_FS):
    h = TITLE_H + len(lines) * LINE_H + PAD_BOT
    w = max(_text_w(lines, fs), len(title) * BOX_TFS * CHAR_W) + 2 * PAD_X
    return dict(id=bid, w=w, h=h, title=title, lines=lines, fill=fill, fs=fs)


# ---- main pipeline column (top -> bottom) ---------------------------------
SPECS = [
    box('input', 'Fleet + Task state   @ event t_k', [
        'robots  R = {r_1 .. r_n}   (pose, battery, status)',
        'open tasks  T(t_k)   (pos, deadline d, priority pi, capability c)',
    ], COL['in']),
    box('ctx', 'Operating State Vector   c(t_k) in [0,1]^4', [
        'c1  task density        = min(1, m / n)',
        'c2  robot availability  = |R_av| / n',
        'c3  deadline pressure   = #{near-deadline tasks} / m',
        'c4  failure rate        = |R_fail| / n',
    ], COL['ctx']),
    box('dyn', 'Ecosystem dominance dynamics   D(t) in R^5', [
        'Lotka-Volterra competition  ==  online hyper-heuristic',
        'compatibility  v_i = cos(V_i, c)      ( V = state prototypes )',
        'performance    p   = (CR - FR) . v    boost b = failure spike',
        'D(t+1) = normalize( clip_[0,1](',
        '         a.D + eta.A.D - lam.S.D + beta.p + gam.v + del.b ) )',
        'a=.85  eta=lam=.12  beta=.25  gam=.20  del=.20   =>  ||D||_1 = 1',
    ], COL['dyn']),
    box('disp', 'EDPS dispatch   ->   selected paradigm  p*', [
        'override 1:  c4 (failure)  > 0.05  =>  H_RECOV',
        'override 2:  c3 (deadline) > 0.50  =>  H_TEMP',
        'otherwise:   p* = argmax_i D_i    (default H_TEMP if D flat)',
    ], COL['disp']),
    box('para', 'Paradigm library   (5 hormones -> 5 allocators; ONE selected)', [
        'H_SPATIAL  spatial_greedy : nearest-feasible + reject',
        'H_CRIT     priority_first : priority-tiered LSA',
        'H_TEMP     edf_strict     : EDF bipartite + cheapest-insert  (default)',
        'H_STAB     commit_once    : hard sticky, no reassign',
        'H_RECOV    orphan_first   : orphan rescue pass, then bipartite',
    ], COL['para']),
    box('cost', 'Cost matrix  C^(p)   +   LSA assignment', [
        'C[r,t] = w_d.T + w_u.u^-1 + w_pi.pi^-1 + w_e.e + w_rho.rho',
        'feasibility mask (arrival > deadline => inf);  queue cap  sum x <= Q',
        'x* = argmin_x  sum C^(p)[r,t] . x[r,t]      (Hungarian, O(N^3))',
    ], COL['cost']),
    box('out', 'Publish per-robot task queues   ->   Nav2 execution', [
        'work-conserving: no idle robot while feasible work remains',
        'a disturbance costs at most a re-attempt, never a lost task',
    ], COL['out']),
]

COL_W = max(s['w'] for s in SPECS)        # uniform column width
BOXES = []
y = 70
for s in SPECS:
    s = dict(s); s['w'] = COL_W; s['x'] = COL_X; s['y'] = y
    BOXES.append(s); y += s['h'] + V_GAP
CANVAS_H = y + 20
BOX_BY_ID = {b['id']: b for b in BOXES}

# ---- side panels (top-aligned to a target row) ---------------------------
SIDE_X = COL_X + COL_W + SIDE_GAP
def side(bid, target, title, lines):
    b = box(bid, title, lines, COL['side'], fs=SIDE_FS)
    b['x'] = SIDE_X; b['y'] = BOX_BY_ID[target]['y']; b['target'] = target
    return b

SIDES = [
    side('Vproto', 'ctx', 'State Prototypes  V_i', [
        '            td   ra   dp   fr',
        'SPATIAL    0.7  0.7  0.1  0.1',
        'CRIT       0.3  0.5  0.8  0.2',
        'TEMP       0.5  0.5  0.9  0.1',
        'STAB       0.3  0.3  0.3  0.8',
        'RECOV      0.3  0.2  0.2  0.9',
    ]),
    side('ASmat', 'dyn', 'Interaction matrices', [
        'A  cooperation (reinforce):',
        '   CRIT -> TEMP    = 0.20',
        '   STAB -> RECOV   = 0.20',
        'S  suppression:',
        '   TEMP -> SPATIAL = 0.30',
    ]),
]

FLOW = ['input', 'ctx', 'dyn', 'disp', 'para', 'cost', 'out']
ARROWS = [(FLOW[i], FLOW[i + 1], 'down') for i in range(len(FLOW) - 1)]
ARROWS.append(('out', 'dyn', 'feedback'))
CANVAS_W = SIDE_X + max(s['w'] for s in SIDES) + 40


# ---------------------------------------------------------------------------
# (1) matplotlib xkcd renderer
# ---------------------------------------------------------------------------
def render_png(path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
    import warnings
    warnings.filterwarnings('ignore')

    sc = 0.013
    with plt.xkcd(scale=0.45, length=110, randomness=1):
        fig, ax = plt.subplots(figsize=(CANVAS_W * sc, CANVAS_H * sc))
        ax.set_xlim(0, CANVAS_W); ax.set_ylim(0, CANVAS_H)
        ax.invert_yaxis(); ax.axis('off')

        def draw_box(b, tfs, lfs):
            ax.add_patch(FancyBboxPatch(
                (b['x'], b['y']), b['w'], b['h'],
                boxstyle="round,pad=3,rounding_size=14",
                linewidth=2.2, edgecolor='#1e1e1e',
                facecolor=b['fill'], alpha=0.97, zorder=2))
            ax.text(b['x'] + b['w'] / 2, b['y'] + 16, b['title'], ha='center',
                    va='top', fontsize=tfs, fontweight='bold', zorder=3)
            for i, ln in enumerate(b['lines']):
                ax.text(b['x'] + PAD_X, b['y'] + TITLE_H + 6 + i * LINE_H, ln,
                        ha='left', va='top', fontsize=lfs, family='monospace',
                        zorder=3)

        for b in BOXES:
            draw_box(b, BOX_TFS, b['fs'])
        for s in SIDES:
            draw_box(s, SIDE_TFS, s['fs'])

        # main vertical arrows (straight, centred)
        for (fa, fb, kind) in ARROWS:
            A, B = BOX_BY_ID[fa], BOX_BY_ID[fb]
            if kind == 'down':
                xc = A['x'] + A['w'] / 2
                ax.add_patch(FancyArrowPatch(
                    (xc, A['y'] + A['h']), (xc, B['y']),
                    arrowstyle='-|>', mutation_scale=24, linewidth=2.4,
                    color='#1e1e1e', zorder=1, shrinkA=1, shrinkB=1))

        # feedback loop: clean orthogonal route in the left margin
        A, B = BOX_BY_ID['out'], BOX_BY_ID['dyn']
        y0, y1 = A['y'] + A['h'] / 2, B['y'] + B['h'] / 2
        lx = LEFT_MARGIN - 40
        seg = dict(color='#e8590c', lw=2.2, ls='--', zorder=1)
        ax.plot([A['x'], lx], [y0, y0], **seg)
        ax.plot([lx, lx], [y0, y1], **seg)
        ax.add_patch(FancyArrowPatch((lx, y1), (B['x'], y1),
                     arrowstyle='-|>', mutation_scale=22, linewidth=2.2,
                     color='#e8590c', linestyle='dashed', zorder=1))
        ax.text(lx - 14, (y0 + y1) / 2, 'performance\nfeedback\n(CR - FR)',
                ha='center', va='center', fontsize=10.5, color='#e8590c',
                rotation=90)

        # side connectors: aligned horizontal dotted links
        for s in SIDES:
            T = BOX_BY_ID[s['target']]
            yc = T['y'] + T['h'] / 2
            ax.plot([T['x'] + T['w'], s['x']], [yc, yc],
                    color='#868e96', lw=1.4, ls=':', zorder=1)

        ax.text(CANVAS_W / 2, 30, 'AHE-MRTA  —  Ecosystem-Driven Paradigm '
                'Selection  (per-event cycle)', ha='center', va='top',
                fontsize=TITLE_FS, fontweight='bold')
        fig.tight_layout(pad=0.3)
        fig.savefig(path, dpi=175, bbox_inches='tight', facecolor='white')
        plt.close(fig)
    print(f"[OK] PNG  -> {path}")


# ---------------------------------------------------------------------------
# (2) Excalidraw JSON renderer (genuine editable source)
# ---------------------------------------------------------------------------
def _rid():
    return ''.join(random.choice('abcdefghijklmnopqrstuvwxyz0123456789')
                   for _ in range(16))

def _base(eltype, x, y, w, h, **kw):
    e = dict(id=_rid(), type=eltype, x=x, y=y, width=w, height=h, angle=0,
             strokeColor='#1e1e1e', backgroundColor='transparent',
             fillStyle='solid', strokeWidth=2, strokeStyle='solid',
             roughness=1, opacity=100, groupIds=[], frameId=None,
             roundness=None, seed=random.randint(1, 2**31),
             versionNonce=random.randint(1, 2**31), version=1,
             isDeleted=False, boundElements=[], updated=int(time.time() * 1000),
             link=None, locked=False)
    e.update(kw); return e

def render_excalidraw(path):
    els = [_base('text', COL_X, 20, COL_W, 30,
        text='AHE-MRTA  —  Ecosystem-Driven Paradigm Selection (per-event cycle)',
        fontSize=22, fontFamily=1, textAlign='left', verticalAlign='top',
        originalText='AHE-MRTA  —  Ecosystem-Driven Paradigm Selection (per-event cycle)',
        lineHeight=1.25, baseline=18)]

    def add_box(b, fs):
        els.append(_base('rectangle', b['x'], b['y'], b['w'], b['h'],
                         backgroundColor=b['fill'], fillStyle='solid',
                         roundness=dict(type=3)))
        txt = b['title'] + '\n\n' + '\n'.join(b['lines'])
        els.append(_base('text', b['x'] + 14, b['y'] + 12, b['w'] - 28,
                         b['h'] - 24, text=txt, fontSize=fs, fontFamily=3,
                         textAlign='left', verticalAlign='top',
                         originalText=txt, lineHeight=1.3, baseline=fs))

    for b in BOXES:
        add_box(b, 15)
    for s in SIDES:
        add_box(s, 13)

    def arrow(x0, y0, pts, color='#1e1e1e', dashed=False):
        els.append(_base('arrow', x0, y0, pts[-1][0], pts[-1][1],
                   strokeColor=color,
                   strokeStyle='dashed' if dashed else 'solid',
                   points=pts, startArrowhead=None, endArrowhead='arrow',
                   startBinding=None, endBinding=None))

    for (fa, fb, kind) in ARROWS:
        A, B = BOX_BY_ID[fa], BOX_BY_ID[fb]
        if kind == 'down':
            xc = A['x'] + A['w'] / 2
            arrow(xc, A['y'] + A['h'], [[0, 0], [0, B['y'] - (A['y'] + A['h'])]])
        else:
            y0, y1 = A['y'] + A['h'] / 2, B['y'] + B['h'] / 2
            lx = LEFT_MARGIN - 40
            arrow(A['x'], y0, [[0, 0], [lx - A['x'], 0],
                  [lx - A['x'], y1 - y0], [B['x'] - A['x'], y1 - y0]],
                  color='#e8590c', dashed=True)

    for s in SIDES:
        T = BOX_BY_ID[s['target']]
        yc = T['y'] + T['h'] / 2
        arrow(T['x'] + T['w'], yc, [[0, 0], [s['x'] - (T['x'] + T['w']), 0]],
              color='#868e96', dashed=True)

    doc = dict(type='excalidraw', version=2, source='https://excalidraw.com',
               elements=els,
               appState=dict(gridSize=None, viewBackgroundColor='#ffffff'),
               files={})
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(doc, f, indent=2)
    print(f"[OK] Excalidraw -> {path}  ({len(els)} elements)")


if __name__ == '__main__':
    random.seed(7)
    render_png('results/figures/ahe_method_detailed.png')
    render_excalidraw('docs/ahe_method_diagram.excalidraw')
