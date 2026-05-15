#!/usr/bin/env python3
"""
Generate the Nav2 PGM map and SDF obstacle snippet for the AHE-MRTA
obstacle-arena world (ahe_inspection_arena.sdf).

Arena design:
  - 20 m × 20 m enclosed arena (walls at ±9.95 m)
  - Robots start at (0,0), (0,2), (0,-2) — central corridor kept clear
  - 16 box obstacles arranged in a warehouse-shelf pattern
  - 4 cylinder pillars at corners of the central zone

Output:
  src/m_ahe_nav2_config/maps/obstacle_map.pgm
  src/m_ahe_nav2_config/maps/obstacle_map.yaml
  /tmp/obstacle_sdf_snippet.xml   (paste into the SDF world)
"""

import math
import os
import struct

REPO = os.path.join(os.path.dirname(__file__), '..')

# ── Map parameters ──────────────────────────────────────────────────────────
MAP_RESOLUTION = 0.05          # m/pixel
MAP_WIDTH_M    = 20.0          # total map width
MAP_HEIGHT_M   = 20.0
MAP_ORIGIN_X   = -10.0
MAP_ORIGIN_Y   = -10.0
W_PX = int(MAP_WIDTH_M  / MAP_RESOLUTION)   # 400
H_PX = int(MAP_HEIGHT_M / MAP_RESOLUTION)   # 400

FREE  = 254
OCC   = 0
WALL_THICK = 0.12   # m — map wall thickness

# ── Obstacle definitions ─────────────────────────────────────────────────────
# Each entry:  ("box",  cx, cy, size_x, size_y, height)
#              ("cyl",  cx, cy, radius, height)
# Coordinate origin = world centre (0,0).

BOUNDARY_HALF = 9.9   # inner edge of boundary wall

obstacles = []

# ── Outer boundary walls ────────────────────────────────────────────────────
W = WALL_THICK
H = BOUNDARY_HALF
obstacles += [
    ("box",  0,  H + W/2, 2*H + 2*W, W, 0.5),   # North
    ("box",  0, -H - W/2, 2*H + 2*W, W, 0.5),   # South
    ("box",  H + W/2,  0, W, 2*H + 2*W, 0.5),   # East
    ("box", -H - W/2,  0, W, 2*H + 2*W, 0.5),   # West
]

# ── Interior shelves (warehouse-style, 3 rows each side) ────────────────────
# Shelf = 0.3 m deep × 2.0 m wide × 0.5 m tall, oriented along Y
# Corridors along X at x = -5, 0, +5
# Corridors along Y at y ∈ [-1, 1] (robot start zone) and y = 0 (main aisle)

SHELF_DEPTH = 0.3
SHELF_WIDTH = 2.0
SHELF_H     = 0.5

shelf_x_positions = [-7.5, -5.0, 5.0, 7.5]
shelf_y_positions  = [-7.5, -4.5, 3.5, 6.5]   # avoid y ∈ [-2, 2]

for sx in shelf_x_positions:
    for sy in shelf_y_positions:
        obstacles.append(("box", sx, sy, SHELF_DEPTH, SHELF_WIDTH, SHELF_H))

# ── Additional cross-aisle obstacles ────────────────────────────────────────
# Two long divider walls that split the arena into sectors, with gaps
#   Horizontal dividers at y = ±3.0, x ∈ [-8.5, -1.5] and [1.5, 8.5]
DIV_THICK = 0.2
DIV_H = 0.5
for sign in (1, -1):
    obstacles += [
        ("box", -5.0, sign * 3.0, 7.0, DIV_THICK, DIV_H),   # left half
        ("box",  5.0, sign * 3.0, 7.0, DIV_THICK, DIV_H),   # right half
    ]

# ── 4 central pillars (define clear zone for robots) ─────────────────────
PILLAR_R = 0.2
PILLAR_H = 0.5
for px, py in [(-2.5, 5.5), (2.5, 5.5), (-2.5, -5.5), (2.5, -5.5)]:
    obstacles.append(("cyl", px, py, PILLAR_R, PILLAR_H))


# ── Utility: world → pixel ──────────────────────────────────────────────────
def world_to_px(wx, wy):
    col = (wx - MAP_ORIGIN_X) / MAP_RESOLUTION
    row = H_PX - 1 - (wy - MAP_ORIGIN_Y) / MAP_RESOLUTION
    return int(round(col)), int(round(row))

def fill_rect(img, cx, cy, sx, sy):
    """Mark a rectangle centred at (cx,cy) with full size (sx,sy) as OCC."""
    c0, r0 = world_to_px(cx - sx / 2, cy + sy / 2)
    c1, r1 = world_to_px(cx + sx / 2, cy - sy / 2)
    c0, c1 = sorted([c0, c1])
    r0, r1 = sorted([r0, r1])
    for r in range(max(0, r0), min(H_PX, r1 + 1)):
        for c in range(max(0, c0), min(W_PX, c1 + 1)):
            img[r][c] = OCC

def fill_circle(img, cx, cy, radius):
    px_radius = int(math.ceil(radius / MAP_RESOLUTION))
    col_c, row_c = world_to_px(cx, cy)
    for dr in range(-px_radius - 1, px_radius + 2):
        for dc in range(-px_radius - 1, px_radius + 2):
            wdist = math.sqrt((dr * MAP_RESOLUTION)**2 + (dc * MAP_RESOLUTION)**2)
            if wdist <= radius:
                r, c = row_c + dr, col_c + dc
                if 0 <= r < H_PX and 0 <= c < W_PX:
                    img[r][c] = OCC


# ── Build image ──────────────────────────────────────────────────────────────
img = [[FREE] * W_PX for _ in range(H_PX)]

for obs in obstacles:
    kind = obs[0]
    if kind == "box":
        _, cx, cy, sx, sy, _ = obs
        fill_rect(img, cx, cy, sx, sy)
    elif kind == "cyl":
        _, cx, cy, r, _ = obs
        fill_circle(img, cx, cy, r)


# ── Write PGM ────────────────────────────────────────────────────────────────
map_dir = os.path.join(REPO, 'src', 'm_ahe_nav2_config', 'maps')
pgm_path  = os.path.join(map_dir, 'obstacle_map.pgm')
yaml_path = os.path.join(map_dir, 'obstacle_map.yaml')

with open(pgm_path, 'wb') as f:
    f.write(f"P5\n{W_PX} {H_PX}\n255\n".encode())
    for row in img:
        f.write(bytes(row))

print(f"[OK] PGM  → {pgm_path}  ({W_PX}×{H_PX} px, {MAP_RESOLUTION} m/px)")

with open(yaml_path, 'w') as f:
    f.write(f"image: obstacle_map.pgm\n")
    f.write(f"mode: trinary\n")
    f.write(f"resolution: {MAP_RESOLUTION}\n")
    f.write(f"origin: [{MAP_ORIGIN_X}, {MAP_ORIGIN_Y}, 0.0]\n")
    f.write(f"negate: 0\n")
    f.write(f"occupied_thresh: 0.65\n")
    f.write(f"free_thresh: 0.196\n")

print(f"[OK] YAML → {yaml_path}")


# ── Generate SDF obstacle snippet ────────────────────────────────────────────
sdf_lines = ['  <!-- ================================================================',
             '       BOUNDARY WALLS + INTERIOR OBSTACLES (auto-generated)',
             '       Do not hand-edit — regenerate with scripts/generate_obstacle_map.py',
             '  ================================================================ -->']

for idx, obs in enumerate(obstacles):
    name = f"obstacle_{idx:03d}"
    kind = obs[0]

    if kind == "box":
        _, cx, cy, sx, sy, sh = obs
        sdf_lines += [
            f'    <model name="{name}">',
            f'      <static>true</static>',
            f'      <pose>{cx} {cy} {sh/2} 0 0 0</pose>',
            f'      <link name="link">',
            f'        <collision name="col">',
            f'          <geometry><box><size>{sx} {sy} {sh}</size></box></geometry>',
            f'        </collision>',
            f'        <visual name="vis">',
            f'          <geometry><box><size>{sx} {sy} {sh}</size></box></geometry>',
            f'          <material><ambient>0.5 0.5 0.5 1</ambient><diffuse>0.5 0.5 0.5 1</diffuse></material>',
            f'        </visual>',
            f'      </link>',
            f'    </model>',
        ]
    elif kind == "cyl":
        _, cx, cy, r, sh = obs
        sdf_lines += [
            f'    <model name="{name}">',
            f'      <static>true</static>',
            f'      <pose>{cx} {cy} {sh/2} 0 0 0</pose>',
            f'      <link name="link">',
            f'        <collision name="col">',
            f'          <geometry><cylinder><radius>{r}</radius><length>{sh}</length></cylinder></geometry>',
            f'        </collision>',
            f'        <visual name="vis">',
            f'          <geometry><cylinder><radius>{r}</radius><length>{sh}</length></cylinder></geometry>',
            f'          <material><ambient>0.6 0.4 0.1 1</ambient><diffuse>0.6 0.4 0.1 1</diffuse></material>',
            f'        </visual>',
            f'      </link>',
            f'    </model>',
        ]

sdf_snippet = '\n'.join(sdf_lines)
snippet_path = '/tmp/obstacle_sdf_snippet.xml'
with open(snippet_path, 'w') as f:
    f.write(sdf_snippet)

print(f"[OK] SDF snippet → {snippet_path}  ({len(obstacles)} obstacles)")
print()
print("Obstacle summary:")
for idx, obs in enumerate(obstacles):
    print(f"  {idx:3d}  {obs}")
