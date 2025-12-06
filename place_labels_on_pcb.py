#!/usr/bin/env python3
"""Replicate F, Q, and coordinate labels across the PCB grid."""

import re
import sys
from pathlib import Path

import pcbnew

STEP_MM_X = 15.0
STEP_MM_Y = 16.0
PCB_PATH = Path(__file__).parent / "pcb" / "74aoc.kicad_pcb"
LABELS = ["F", "Q", "X0 Y0"]


def parse_cell_coords(sheet_name: str) -> tuple[int, int] | None:
    """Parse 'CELL X# Y#' from sheet path and return (x, y) or None."""
    match = re.search(r"CELL X(\d+) Y(\d+)", sheet_name)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None


def find_labels(board: pcbnew.BOARD) -> dict[str, pcbnew.PCB_TEXT]:
    """Find the target labels and return a dict of text -> PCB_TEXT."""
    found: dict[str, list[pcbnew.PCB_TEXT]] = {label: [] for label in LABELS}

    for item in board.GetDrawings():
        if not isinstance(item, pcbnew.PCB_TEXT):
            continue
        text = item.GetText()
        if text in LABELS:
            found[text].append(item)

    # Validate exactly one of each
    labels = {}
    for label, items in found.items():
        if len(items) == 0:
            print(f"ERROR: Label '{label}' not found")
            sys.exit(1)
        if len(items) > 1:
            print(f"ERROR: Found {len(items)} instances of label '{label}', expected 1")
            sys.exit(1)
        labels[label] = items[0]

    return labels


def get_grid_dimensions(board: pcbnew.BOARD) -> tuple[int, int]:
    """Get max X and Y from footprint cell coordinates."""
    max_x = 0
    max_y = 0

    for fp in board.GetFootprints():
        coords = parse_cell_coords(fp.GetSheetname())
        if coords:
            max_x = max(max_x, coords[0])
            max_y = max(max_y, coords[1])

    return max_x, max_y


def clone_text(board: pcbnew.BOARD, source: pcbnew.PCB_TEXT, new_text: str | None = None) -> pcbnew.PCB_TEXT:
    """Clone a PCB_TEXT item, optionally with different text."""
    new = pcbnew.PCB_TEXT(board)
    new.SetText(new_text if new_text else source.GetText())
    new.SetPosition(source.GetPosition())
    new.SetLayer(source.GetLayer())
    new.SetTextSize(source.GetTextSize())
    new.SetTextThickness(source.GetTextThickness())
    new.SetBold(source.IsBold())
    new.SetItalic(source.IsItalic())
    new.SetHorizJustify(source.GetHorizJustify())
    new.SetVertJustify(source.GetVertJustify())
    new.SetTextAngle(source.GetTextAngle())
    new.SetIsKnockout(source.IsKnockout())
    return new


def main():
    print(f"Loading PCB: {PCB_PATH}")
    board = pcbnew.LoadBoard(str(PCB_PATH))

    labels = find_labels(board)
    print(f"Found all {len(labels)} labels")

    max_x, max_y = get_grid_dimensions(board)
    print(f"Grid dimensions: X0-X{max_x}, Y0-Y{max_y}")

    # Get reference positions
    ref_positions = {label: text.GetPosition() for label, text in labels.items()}

    # Replicate labels
    created = 0
    for x in range(max_x + 1):
        for y in range(max_y + 1):
            if x == 0 and y == 0:
                continue

            offset_x = pcbnew.FromMM(x * STEP_MM_X)
            offset_y = -pcbnew.FromMM(y * STEP_MM_Y)

            for label, source in labels.items():
                ref_pos = ref_positions[label]
                new_x = ref_pos.x + offset_x
                new_y = ref_pos.y + offset_y

                # For coordinate label, update the text
                if label == "X0 Y0":
                    new_text = f"X{x} Y{y}"
                else:
                    new_text = None

                new_label = clone_text(board, source, new_text)
                new_label.SetPosition(pcbnew.VECTOR2I(new_x, new_y))
                board.Add(new_label)
                created += 1

    print(f"Created {created} labels")
    board.Save(str(PCB_PATH))
    print(f"Saved to {PCB_PATH}")


if __name__ == "__main__":
    main()
