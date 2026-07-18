#!/usr/bin/env python3
"""Validate that Gazebo and RViz use the same Fig. 7 arena geometry.

The check is deliberately offline: it parses the SDF and occupancy map without
starting ROS 2, Gazebo, RViz, or Nav2.  It also verifies that no continuous
horizontal obstacle crosses the centre of the arena.
"""

from __future__ import annotations

import hashlib
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SDF = ROOT / "src/m_ahe_mrta_gazebo/worlds/ahe_inspection_arena.sdf"
MAP_YAML = ROOT / "src/m_ahe_nav2_config/maps/obstacle_map.yaml"
MAP_PGM = ROOT / "src/m_ahe_nav2_config/maps/obstacle_map.pgm"
GZ_LAUNCH = ROOT / "src/m_ahe_mrta_bringup/launch/multi_robot_gazebo.launch.py"
NAV_LAUNCH = ROOT / "src/m_ahe_mrta_bringup/launch/multi_robot_nav2.launch.py"
SCENARIO_FIGURE_SCRIPT = ROOT / "scripts/generate_scenario_maps.py"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_map_metadata() -> tuple[float, float, float]:
    text = MAP_YAML.read_text(encoding="utf-8")
    resolution = float(re.search(r"^resolution:\s*([0-9.]+)", text, re.M).group(1))
    origin_match = re.search(
        r"^origin:\s*\[\s*([-0-9.]+)\s*,\s*([-0-9.]+)", text, re.M
    )
    return resolution, float(origin_match.group(1)), float(origin_match.group(2))


def rasterise_sdf(
    height: int, width: int, resolution: float, origin_x: float, origin_y: float
) -> tuple[np.ndarray, list[dict[str, float | str]]]:
    expected = np.zeros((height, width), dtype=bool)
    obstacles: list[dict[str, float | str]] = []
    root = ET.parse(SDF).getroot()

    def x_index(value: float) -> int:
        return int(round((value - origin_x) / resolution))

    def y_index(value: float) -> int:
        return int(round((value - origin_y) / resolution))

    for model in root.findall(".//world/model"):
        name = model.get("name", "")
        if not name.startswith("obstacle_"):
            continue
        pose = [float(value) for value in model.findtext("pose").split()]
        cx, cy = pose[:2]
        geometry = model.find("./link/collision/geometry")
        box = geometry.find("box")
        cylinder = geometry.find("cylinder")

        if box is not None:
            sx, sy, _ = [float(value) for value in box.findtext("size").split()]
            ix0 = max(0, x_index(cx - sx / 2.0))
            ix1 = min(width - 1, x_index(cx + sx / 2.0))
            iy0 = max(0, y_index(cy - sy / 2.0))
            iy1 = min(height - 1, y_index(cy + sy / 2.0))
            row0 = height - 1 - iy1
            row1 = height - 1 - iy0
            expected[row0 : row1 + 1, ix0 : ix1 + 1] = True
            obstacles.append(
                {"name": name, "kind": "box", "x": cx, "y": cy, "sx": sx, "sy": sy}
            )
        elif cylinder is not None:
            radius = float(cylinder.findtext("radius"))
            center_x = x_index(cx)
            center_y = y_index(cy)
            radius_px = int(round(radius / resolution))
            for dx in range(-radius_px, radius_px + 1):
                for dy in range(-radius_px, radius_px + 1):
                    if dx * dx + dy * dy > radius_px * radius_px:
                        continue
                    col = center_x + dx
                    row = height - 1 - (center_y + dy)
                    if 0 <= row < height and 0 <= col < width:
                        expected[row, col] = True
            obstacles.append(
                {"name": name, "kind": "cylinder", "x": cx, "y": cy, "r": radius}
            )
        else:
            raise RuntimeError(f"Unsupported obstacle geometry: {name}")

    return expected, obstacles


def dilate_one(mask: np.ndarray) -> np.ndarray:
    padded = np.pad(mask, 1, mode="constant", constant_values=False)
    result = np.zeros_like(mask)
    for row_offset in range(3):
        for col_offset in range(3):
            result |= padded[
                row_offset : row_offset + mask.shape[0],
                col_offset : col_offset + mask.shape[1],
            ]
    return result


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []
    resolution, origin_x, origin_y = parse_map_metadata()
    map_array = np.asarray(Image.open(MAP_PGM).convert("L"))
    map_occupied = map_array == 0
    height, width = map_occupied.shape
    expected, obstacles = rasterise_sdf(
        height, width, resolution, origin_x, origin_y
    )

    require(len(obstacles) == 28, f"SDF obstacle count is {len(obstacles)}, expected 28", failures)
    require(map_array.shape == (400, 400), f"Map size is {map_array.shape}, expected 400x400", failures)
    require(set(np.unique(map_array)) == {0, 254}, "Map is not a binary 0/254 occupancy map", failures)

    intersection = int(np.count_nonzero(map_occupied & expected))
    union = int(np.count_nonzero(map_occupied | expected))
    exact_iou = intersection / union
    map_outside_tolerance = int(np.count_nonzero(map_occupied & ~dilate_one(expected)))
    sdf_outside_tolerance = int(np.count_nonzero(expected & ~dilate_one(map_occupied)))
    require(exact_iou >= 0.99, f"SDF/map IoU is only {exact_iou:.6f}", failures)
    require(
        map_outside_tolerance == 0,
        f"{map_outside_tolerance} map pixels lie >1 pixel outside SDF geometry",
        failures,
    )
    require(
        sdf_outside_tolerance == 0,
        f"{sdf_outside_tolerance} SDF pixels lie >1 pixel outside the map",
        failures,
    )

    def row_for_world_y(y_value: float) -> int:
        iy = int(round((y_value - origin_y) / resolution))
        return height - 1 - iy

    def col_for_world_x(x_value: float) -> int:
        return int(round((x_value - origin_x) / resolution))

    centre_row = row_for_world_y(0.0)
    inner_left = col_for_world_x(-9.8)
    inner_right = col_for_world_x(9.8)
    centre_strip_pixels = int(
        np.count_nonzero(map_occupied[centre_row, inner_left : inner_right + 1])
    )
    require(
        centre_strip_pixels == 0,
        f"A horizontal obstacle crosses y=0 ({centre_strip_pixels} occupied pixels)",
        failures,
    )

    gap_left = col_for_world_x(-1.45)
    gap_right = col_for_world_x(1.45)
    for barrier_y in (-3.0, 3.0):
        barrier_row = row_for_world_y(barrier_y)
        gap_pixels = int(
            np.count_nonzero(map_occupied[barrier_row, gap_left : gap_right + 1])
        )
        require(
            gap_pixels == 0,
            f"The intended central gap at y={barrier_y:g} is blocked",
            failures,
        )

    gz_launch_text = GZ_LAUNCH.read_text(encoding="utf-8")
    nav_launch_text = NAV_LAUNCH.read_text(encoding="utf-8")
    scenario_script_text = SCENARIO_FIGURE_SCRIPT.read_text(encoding="utf-8")
    require(
        "ahe_inspection_arena.sdf" in gz_launch_text,
        "Gazebo launch does not select ahe_inspection_arena.sdf",
        failures,
    )
    require(
        "obstacle_map.yaml" in nav_launch_text,
        "Nav2 launch does not select obstacle_map.yaml",
        failures,
    )
    require(
        "obstacle_map.pgm" in scenario_script_text,
        "The previous scenario figure is not sourced from obstacle_map.pgm",
        failures,
    )

    boxes = sum(obstacle["kind"] == "box" for obstacle in obstacles)
    cylinders = sum(obstacle["kind"] == "cylinder" for obstacle in obstacles)
    print(f"SDF obstacles: {len(obstacles)} ({boxes} boxes, {cylinders} cylinders)")
    print(f"RViz map: {width}x{height}, {resolution:.2f} m/pixel, origin=({origin_x:g}, {origin_y:g})")
    print(f"SDF/map exact IoU: {exact_iou:.6f}")
    print(f">1-pixel mismatches: map={map_outside_tolerance}, sdf={sdf_outside_tolerance}")
    print(f"Centre y=0 occupied pixels (excluding boundary): {centre_strip_pixels}")
    print("Intended horizontal barriers: y=-3 and y=+3, each split by a 3.0 m central gap")
    print(f"SDF SHA-256: {sha256(SDF)}")
    print(f"PGM SHA-256: {sha256(MAP_PGM)}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("PASS: Gazebo, RViz, and the previous scenario figure use the same arena geometry.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

