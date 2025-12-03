#!/usr/bin/env python3
"""Place MC74HC151ADTR2G footprints in grid pattern based on cell coordinates."""

import re
from pathlib import Path

import pcbnew

STEP_MM_X = 15.0
STEP_MM_Y = 16.0
PCB_PATH = Path(__file__).parent / "pcb" / "74aoc.kicad_pcb"


def parse_cell_coords(sheet_name: str) -> tuple[int, int] | None:
    """Parse 'CELL X# Y#' from sheet path and return (x, y) or None."""
    match = re.search(r"CELL X(\d+) Y(\d+)", sheet_name)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None


def main():
    print(f"Loading PCB: {PCB_PATH}")
    board = pcbnew.LoadBoard(str(PCB_PATH))

    # Find all MC74HC151ADTR2G footprints and group by cell
    mux_footprints: dict[tuple[int, int], pcbnew.FOOTPRINT] = {}
    for fp in board.GetFootprints():
        if fp.GetValue() != "MC74HC151ADTR2G":
            continue

        sheet_name = fp.GetSheetname()
        coords = parse_cell_coords(sheet_name)

        if coords:
            print(f"Found {fp.GetReference()}: {sheet_name} -> X{coords[0]} Y{coords[1]}")
            mux_footprints[coords] = fp
        else:
            print(f"WARNING: {fp.GetReference()} has no valid cell coords (sheet='{sheet_name}')")

    print(f"\nFound {len(mux_footprints)} MC74HC151ADTR2G footprints with valid cell coordinates")

    # Find reference cell (X0 Y0)
    ref_fp = mux_footprints.get((0, 0))
    if not ref_fp:
        print("ERROR: Could not find X0 Y0 reference cell")
        return

    ref_pos = ref_fp.GetPosition()
    print(f"Reference position (X0 Y0): ({pcbnew.ToMM(ref_pos.x):.2f}, {pcbnew.ToMM(ref_pos.y):.2f}) mm\n")

    # Place other cells relative to reference
    updated = 0
    for (x, y), fp in sorted(mux_footprints.items()):
        if x == 0 and y == 0:
            continue

        # X grows right (positive), Y grows up (negative in KiCad coords)
        new_x = ref_pos.x + pcbnew.FromMM(x * STEP_MM_X)
        new_y = ref_pos.y - pcbnew.FromMM(y * STEP_MM_Y)

        print(f"CELL X{x} Y{y}: moving to ({pcbnew.ToMM(new_x):.2f}, {pcbnew.ToMM(new_y):.2f}) mm")
        fp.SetPosition(pcbnew.VECTOR2I(new_x, new_y))
        updated += 1

    board.Save(str(PCB_PATH))
    print(f"\nUpdated {updated} footprints, saved to {PCB_PATH}")


if __name__ == "__main__":
    main()
