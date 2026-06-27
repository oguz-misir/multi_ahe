#!/usr/bin/env python3
"""Render the Nav2 occupancy map (obstacle_map.pgm) to a clean, labelled PNG
for the paper (Figure 6a). Shows the 20x20 m walled inspection arena with
divider walls / pillars / cylinder obstacles, in metric coordinates matching
the map YAML (resolution 0.05 m/px, origin [-10,-10]).
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

PGM = 'src/m_ahe_nav2_config/maps/obstacle_map.pgm'
RES = 0.05
ORIGIN = (-10.0, -10.0)
OUT = 'paper/figure/arena_occupancy_map.png'


def read_pgm(path):
    with open(path, 'rb') as f:
        assert f.readline().strip() == b'P5'
        # skip comments
        line = f.readline()
        while line.startswith(b'#'):
            line = f.readline()
        w, h = map(int, line.split())
        maxval = int(f.readline())
        data = np.frombuffer(f.read(w * h), dtype=np.uint8).reshape(h, w)
    return data


img = read_pgm(PGM)
h, w = img.shape
# metric extent (map origin is bottom-left; pgm row 0 is top)
extent = [ORIGIN[0], ORIGIN[0] + w * RES, ORIGIN[1], ORIGIN[1] + h * RES]

fig, ax = plt.subplots(figsize=(5.0, 5.0))
# occupancy: low pixel = occupied (black), high = free (white). origin='upper'
# with extent gives correct metric axes (flip y so it reads bottom-left origin)
ax.imshow(img, cmap='gray', extent=extent, origin='upper', vmin=0, vmax=255)
ax.set_xlabel('x [m]')
ax.set_ylabel('y [m]')
ax.set_title('Inspection arena occupancy map\n(20$\\times$20 m, 0.05 m/cell)')
ax.set_xticks(np.arange(-10, 11, 5))
ax.set_yticks(np.arange(-10, 11, 5))
ax.grid(True, color='0.7', linewidth=0.4, linestyle=':')
fig.tight_layout()
fig.savefig(OUT, dpi=200, bbox_inches='tight', facecolor='white')
print(f"[OK] {OUT}  ({w}x{h} px -> {w*RES:.0f}x{h*RES:.0f} m)")
