#!/usr/bin/env python3
"""Visualize FPGA cell usage from nextpnr output using rough.py"""

import argparse
import json
import re
from pathlib import Path

import rough
from rough import Options


# Grid dimensions from simple.py
LUT_X_MIN, LUT_X_MAX = 1, 11
LUT_Y_MIN, LUT_Y_MAX = 0, 11
IO_Y_MIN, IO_Y_MAX = 0, 7
IO_Z_COUNT = 2

# Regex patterns for parsing BEL names
SLICE_PATTERN = re.compile(r"X(\d+)Y(\d+)_SLICE")
IO_PATTERN = re.compile(r"X(\d+)Y(\d+)Z(\d+)_IO")


def parse_pnrtop(path: Path) -> tuple[set[tuple[int, int]], set[tuple[int, int]], set[tuple[int, int, int]]]:
    """Parse pnrtop.json and extract used cell coordinates.

    Returns:
        Tuple of (used_slices_lut, used_slices_dff, used_ios) where:
        - used_slices_lut: set of (x, y) tuples for SLICE cells using LUT only
        - used_slices_dff: set of (x, y) tuples for SLICE cells using DFF
        - used_ios: set of (x, y, z) tuples for used IO cells
    """
    with open(path) as f:
        data = json.load(f)

    cells = data["modules"]["top"]["cells"]
    used_slices_lut = set()
    used_slices_dff = set()
    used_ios = set()

    for cell_name, cell_data in cells.items():
        bel = cell_data.get("attributes", {}).get("NEXTPNR_BEL")
        if not bel:
            continue

        if match := SLICE_PATTERN.match(bel):
            x, y = int(match.group(1)), int(match.group(2))
            # Check if DFF is used (FF_USED parameter ends with 1)
            ff_used = cell_data.get("parameters", {}).get("FF_USED", "0")
            if ff_used.endswith("1"):
                used_slices_dff.add((x, y))
            else:
                used_slices_lut.add((x, y))
        elif match := IO_PATTERN.match(bel):
            x, y, z = int(match.group(1)), int(match.group(2)), int(match.group(3))
            used_ios.add((x, y, z))

    return used_slices_lut, used_slices_dff, used_ios


def get_all_cells() -> tuple[set[tuple[int, int]], set[tuple[int, int, int]]]:
    """Generate sets of all possible cell coordinates.

    Returns:
        Tuple of (all_slices, all_ios)
    """
    all_slices = {
        (x, y)
        for x in range(LUT_X_MIN, LUT_X_MAX + 1)
        for y in range(LUT_Y_MIN, LUT_Y_MAX + 1)
    }

    all_ios = set()
    # Left edge (inputs): X=0
    for y in range(IO_Y_MIN, IO_Y_MAX + 1):
        for z in range(IO_Z_COUNT):
            all_ios.add((0, y, z))
    # Right edge (outputs): X=12
    for y in range(IO_Y_MIN, IO_Y_MAX + 1):
        for z in range(IO_Z_COUNT):
            all_ios.add((12, y, z))

    return all_slices, all_ios


def create_visualization(
    used_slices_lut: set[tuple[int, int]],
    used_slices_dff: set[tuple[int, int]],
    used_ios: set[tuple[int, int, int]],
) -> tuple[rough.RoughCanvas, int, int]:
    """Create the rough.py visualization canvas."""

    # Layout constants
    cell_size = 40
    cell_gap = 2
    rect_fill = 0.7  # Cells fill 70% of grid square
    rect_size = cell_size * rect_fill
    rect_offset = (cell_size - rect_size) / 2  # Center offset
    io_width = 16  # Narrow IO cells
    io_rect_size = io_width * rect_fill
    io_rect_offset = (io_width - io_rect_size) / 2
    padding = 30

    # Calculate canvas dimensions
    lut_cols = LUT_X_MAX - LUT_X_MIN + 1  # 11
    lut_rows = LUT_Y_MAX - LUT_Y_MIN + 1  # 12

    grid_width = lut_cols * (cell_size + cell_gap) - cell_gap
    grid_height = lut_rows * (cell_size + cell_gap) - cell_gap

    # IO columns: single column per edge, 16 cells stacked (8 Y × 2 Z)
    # IO cells are smaller and bunched at bottom (0.3x scale)
    io_rows = (IO_Y_MAX - IO_Y_MIN + 1) * IO_Z_COUNT  # 16
    io_scale = 0.5
    io_cell_height = cell_size * lut_rows / io_rows * io_scale
    io_total_height = io_cell_height * io_rows  # Total height of IO column
    io_col_gap = 15

    canvas_width = padding + io_width + io_col_gap + grid_width + io_col_gap + io_width + padding
    canvas_height = padding + grid_height + padding

    canvas = rough.canvas(canvas_width, canvas_height)

    # Pastel color palette
    # LUT only: soft peach
    used_lut_style = Options(
        stroke="#e5989b",
        strokeWidth=1.5,
        fill="#ffb4a2",
        fillStyle="solid",
        roughness=1.5,
        bowing=1,
    )

    # DFF marker: small black square inside cell
    dff_marker_style = Options(
        stroke="#333",
        strokeWidth=1,
        fill="#555",
        fillStyle="solid",
        roughness=1.0,
        bowing=0.5,
    )

    # Unused: very light gray
    unused_lut_style = Options(
        stroke="#ccc",
        strokeWidth=1,
        fill="#f0f0f0",
        fillStyle="hachure",
        hachureGap=6,
        hachureAngle=-45,
        roughness=1.5,
        bowing=1,
    )

    # IO used: soft mint
    used_io_style = Options(
        stroke="#457b9d",
        strokeWidth=1.5,
        fill="#a8dadc",
        fillStyle="solid",
        roughness=1.5,
        bowing=1,
    )

    # IO unused: light outline
    unused_io_style = Options(
        stroke="#ddd",
        strokeWidth=1,
        fill="none",
        roughness=1.5,
        bowing=1,
    )

    # Get all cells
    all_slices, all_ios = get_all_cells()

    # Draw LUT grid (Y=0 at bottom - Cartesian coordinates)
    lut_x_offset = padding + io_width + io_col_gap
    lut_y_offset = padding

    # DFF marker size and position (in third quarter of cell)
    dff_marker_size = rect_size * 0.25
    dff_marker_x_offset = (rect_size - dff_marker_size) / 2  # Centered horizontally
    dff_marker_y_offset = rect_size * 0.55  # In the third quarter (lower half)

    for x, y in all_slices:
        # Map grid coords to canvas coords
        # X goes left to right, Y inverted (Y=0 at bottom)
        cx = lut_x_offset + (x - LUT_X_MIN) * (cell_size + cell_gap) + rect_offset
        cy = lut_y_offset + (LUT_Y_MAX - y) * (cell_size + cell_gap) + rect_offset

        if (x, y) in used_slices_dff:
            canvas.rectangle(cx, cy, rect_size, rect_size, used_lut_style)
            # Draw DFF marker in third quarter
            canvas.rectangle(
                cx + dff_marker_x_offset,
                cy + dff_marker_y_offset,
                dff_marker_size,
                dff_marker_size,
                dff_marker_style,
            )
        elif (x, y) in used_slices_lut:
            canvas.rectangle(cx, cy, rect_size, rect_size, used_lut_style)
        else:
            canvas.rectangle(cx, cy, rect_size, rect_size, unused_lut_style)

    # Draw IO cells - stacked linearly (Z=0 first, then Z=1 for each Y)
    # Left column (X=0) - inputs
    left_io_x = padding + io_rect_offset
    # Right column (X=12) - outputs
    right_io_x = padding + io_width + io_col_gap + grid_width + io_col_gap + io_rect_offset

    # IO rect sizing (70% of IO cell height)
    io_rect_height = io_cell_height * rect_fill
    io_rect_y_offset = (io_cell_height - io_rect_height) / 2

    # Position IO cells at the bottom of the grid
    io_y_base = lut_y_offset + grid_height - io_total_height

    for x, y, z in all_ios:
        io_x = left_io_x if x == 0 else right_io_x

        # Flatten Y and Z: row_index = y * 2 + z (Z=0 before Z=1)
        row_index = y * IO_Z_COUNT + z
        # Invert Y axis (row 0 at bottom of IO column)
        io_y = io_y_base + (io_rows - 1 - row_index) * io_cell_height + io_rect_y_offset

        style = used_io_style if (x, y, z) in used_ios else unused_io_style
        canvas.rectangle(io_x, io_y, io_rect_size, io_rect_height, style)

    return canvas, canvas_width, canvas_height


def main():
    parser = argparse.ArgumentParser(
        description="Visualize FPGA cell usage from nextpnr output"
    )
    parser.add_argument("input", type=Path, help="Path to pnrtop.json")
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("cells.svg"),
        help="Output SVG file (default: cells.svg)",
    )
    args = parser.parse_args()

    # Parse input
    used_slices_lut, used_slices_dff, used_ios = parse_pnrtop(args.input)
    print(f"Found {len(used_slices_lut)} LUT-only cells")
    print(f"Found {len(used_slices_dff)} LUT+DFF cells")
    print(f"Found {len(used_ios)} used IO cells")

    # Create visualization
    canvas, width, height = create_visualization(used_slices_lut, used_slices_dff, used_ios)

    # Export SVG
    svg = canvas.as_svg(width, height)
    args.output.write_text(svg)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
