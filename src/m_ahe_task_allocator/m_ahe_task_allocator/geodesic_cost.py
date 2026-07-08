"""Cached obstacle-aware distances on the shared static occupancy map.

This is intentionally ROS-independent so Plane A and Plane B can use exactly
the same distance oracle.  The source map and inflation mask come from
``placement`` -- the same data used to validate robot/task positions.
"""

from __future__ import annotations

import heapq
import math
from functools import lru_cache
from typing import Tuple

import numpy as np

from .placement import RESOLUTION, _occ, _world_to_rc

Pos = Tuple[float, float]

_COARSE = {}
_GRAPHS = {}
_NEIGHBORS = (
    (-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
    (-1, -1, math.sqrt(2.0)), (-1, 1, math.sqrt(2.0)),
    (1, -1, math.sqrt(2.0)), (1, 1, math.sqrt(2.0)),
)


def _grid(factor: int):
    """Return a conservative downsampled occupancy mask."""
    factor = max(1, int(factor))
    if factor not in _COARSE:
        occ, width, height = _occ()
        hc, wc = height // factor, width // factor
        trimmed = occ[:hc * factor, :wc * factor]
        coarse = trimmed.reshape(hc, factor, wc, factor).any(axis=(1, 3))
        _COARSE[factor] = (coarse, width, height)
    return _COARSE[factor]


def _nearest_free(mask: np.ndarray, cell: tuple, radius: int = 5):
    r0, c0 = cell
    h, w = mask.shape
    if 0 <= r0 < h and 0 <= c0 < w and not mask[r0, c0]:
        return r0, c0
    for rad in range(1, radius + 1):
        candidates = []
        for dr in range(-rad, rad + 1):
            for dc in (-rad, rad):
                candidates.append((r0 + dr, c0 + dc))
        for dc in range(-rad + 1, rad):
            for dr in (-rad, rad):
                candidates.append((r0 + dr, c0 + dc))
        for r, c in candidates:
            if 0 <= r < h and 0 <= c < w and not mask[r, c]:
                return r, c
    return None


def _cell(pos: Pos, factor: int):
    mask, _, height = _grid(factor)
    row, col = _world_to_rc(float(pos[0]), float(pos[1]), height)
    return _nearest_free(mask, (row // factor, col // factor))


def _graph(factor: int):
    """Build a sparse free-space graph once; scipy evaluates Dijkstra in C."""
    if factor in _GRAPHS:
        return _GRAPHS[factor]
    try:
        from scipy.sparse import coo_matrix
    except Exception:
        _GRAPHS[factor] = None
        return None
    mask, _, _ = _grid(factor)
    h, w = mask.shape
    rows, cols, data = [], [], []
    for r in range(h):
        for c in range(w):
            if mask[r, c]:
                continue
            src = r * w + c
            for dr, dc, edge in _NEIGHBORS:
                nr, nc = r + dr, c + dc
                if not (0 <= nr < h and 0 <= nc < w) or mask[nr, nc]:
                    continue
                if dr and dc and (mask[r, nc] or mask[nr, c]):
                    continue
                rows.append(src)
                cols.append(nr * w + nc)
                data.append(edge * RESOLUTION * factor)
    graph = coo_matrix((data, (rows, cols)), shape=(h * w, h * w)).tocsr()
    _GRAPHS[factor] = graph
    return graph


@lru_cache(maxsize=256)
def _distance_field(start: tuple, factor: int):
    graph = _graph(factor)
    if graph is None:
        return None
    from scipy.sparse.csgraph import dijkstra
    mask, _, _ = _grid(factor)
    source = start[0] * mask.shape[1] + start[1]
    return dijkstra(graph, directed=False, indices=source)


@lru_cache(maxsize=65536)
def _astar(start: tuple, goal: tuple, factor: int) -> float:
    if start == goal:
        return 0.0
    mask, _, _ = _grid(factor)
    h, w = mask.shape
    step_m = RESOLUTION * factor
    best = {start: 0.0}
    heap = [(0.0, 0.0, start[0], start[1])]
    gr, gc = goal
    while heap:
        _, cost, r, c = heapq.heappop(heap)
        if cost > best.get((r, c), float('inf')) + 1e-12:
            continue
        if (r, c) == goal:
            return cost * step_m
        for dr, dc, edge in _NEIGHBORS:
            nr, nc = r + dr, c + dc
            if not (0 <= nr < h and 0 <= nc < w) or mask[nr, nc]:
                continue
            # Do not cut diagonally through an occupied corner.
            if dr and dc and (mask[r, nc] or mask[nr, c]):
                continue
            new_cost = cost + edge
            if new_cost + 1e-12 >= best.get((nr, nc), float('inf')):
                continue
            best[(nr, nc)] = new_cost
            heuristic = math.hypot(gr - nr, gc - nc)
            heapq.heappush(heap, (new_cost + heuristic, new_cost, nr, nc))
    return float('inf')


def geodesic_distance(start: Pos, goal: Pos, resolution: float = 0.10) -> float:
    """Shortest collision-free path length, or infinity when disconnected."""
    factor = max(1, int(round(float(resolution) / RESOLUTION)))
    a, b = _cell(start, factor), _cell(goal, factor)
    if a is None or b is None:
        return float('inf')
    # The graph is undirected.  Anchor the distance field at the requested
    # goal, which is normally a static task position, rather than at the
    # continuously moving robot pose.  All robots querying the same task then
    # share one C-level Dijkstra evaluation instead of building one field per
    # pose/cell; the returned distance is mathematically identical.
    field = _distance_field(b, factor)
    if field is not None:
        mask, _, _ = _grid(factor)
        grid_d = float(field[a[0] * mask.shape[1] + a[1]])
    else:
        # The static map is undirected; canonicalisation doubles fallback reuse.
        if b < a:
            a, b = b, a
        grid_d = _astar(a, b, factor)
    if not math.isfinite(grid_d):
        return grid_d
    # Preserve sub-cell endpoint distance without ever dropping below Euclid.
    return max(math.hypot(goal[0] - start[0], goal[1] - start[1]), grid_d)


def clear_geodesic_cache() -> None:
    _astar.cache_clear()
    _distance_field.cache_clear()


def geodesic_cache_info():
    return {'astar': _astar.cache_info(), 'fields': _distance_field.cache_info()}
