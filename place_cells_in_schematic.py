#!/usr/bin/env python3
"""
Script to replicate CELL X0 Y0 hierarchical sheet instances across an 11x11 grid.
Uses kiutils to manipulate the KiCad schematic file.
"""

import uuid
from pathlib import Path
from copy import deepcopy

from kiutils.schematic import Schematic
from kiutils.items.schitems import (
    HierarchicalSheet,
    HierarchicalPin,
    GlobalLabel,
    HierarchicalSheetProjectInstance,
    HierarchicalSheetProjectPath,
)
from kiutils.items.common import Position, Property, Effects, Stroke, ColorRGBA, Font


# Grid configuration
GRID_SIZE = 11  # 0 to 10 inclusive
SPACING_MILS = 2000
SPACING_MM = SPACING_MILS * 0.0254  # 50.8 mm

# Template cell identifier
TEMPLATE_CELL_NAME = "CELL X0 Y0"
TEMPLATE_LABEL_PREFIX = "W_X0_Y0_"


def cell_name(x: int, y: int) -> str:
    """Generate cell name for given coordinates."""
    return f"CELL X{x} Y{y}"


def label_name(x: int, y: int, suffix: str) -> str:
    """Generate global label name for given coordinates and suffix."""
    return f"W_X{x}_Y{y}_{suffix}"


def find_template_sheet(schematic: Schematic) -> HierarchicalSheet:
    """Find the CELL X0 Y0 template sheet."""
    for sheet in schematic.sheets:
        if sheet.sheetName.value == TEMPLATE_CELL_NAME:
            return sheet
    raise ValueError(f"Template sheet '{TEMPLATE_CELL_NAME}' not found in schematic")


def find_template_labels(schematic: Schematic) -> dict[str, GlobalLabel]:
    """Find all W_X0_Y0_* global labels and return as dict keyed by suffix."""
    labels = {}
    for label in schematic.globalLabels:
        if label.text.startswith(TEMPLATE_LABEL_PREFIX):
            suffix = label.text[len(TEMPLATE_LABEL_PREFIX):]
            labels[suffix] = label
    return labels


def cell_exists(schematic: Schematic, x: int, y: int) -> bool:
    """Check if a cell with the given coordinates already exists."""
    name = cell_name(x, y)
    return any(sheet.sheetName.value == name for sheet in schematic.sheets)


def label_exists(schematic: Schematic, name: str) -> bool:
    """Check if a global label with the given name already exists."""
    return any(label.text == name for label in schematic.globalLabels)


def create_sheet_copy(
    template: HierarchicalSheet, x: int, y: int, offset_x: float, offset_y: float
) -> HierarchicalSheet:
    """Create a copy of the template sheet at the given offset."""
    sheet = deepcopy(template)

    # Update position
    sheet.position.X += offset_x
    sheet.position.Y += offset_y

    # Update sheet name
    sheet.sheetName.value = cell_name(x, y)
    sheet.sheetName.position.X += offset_x
    sheet.sheetName.position.Y += offset_y

    # Update file name position (file stays the same: cell.kicad_sch)
    sheet.fileName.position.X += offset_x
    sheet.fileName.position.Y += offset_y

    # Update pin positions and UUIDs
    for pin in sheet.pins:
        pin.position.X += offset_x
        pin.position.Y += offset_y
        pin.uuid = str(uuid.uuid4())

    # Generate new sheet UUID
    sheet.uuid = str(uuid.uuid4())

    # Update instances with new paths
    for instance in sheet.instances:
        for path in instance.paths:
            # Update the path to include the new sheet UUID
            path.sheetInstancePath = f"/{sheet.uuid}"
            # Page numbers will be assigned by KiCad

    return sheet


def create_label_copy(
    template: GlobalLabel, x: int, y: int, suffix: str, offset_x: float, offset_y: float
) -> GlobalLabel:
    """Create a copy of the template label at the given offset."""
    label = deepcopy(template)

    # Update text
    label.text = label_name(x, y, suffix)

    # Update position
    label.position.X += offset_x
    label.position.Y += offset_y

    # Update UUID
    label.uuid = str(uuid.uuid4())

    # Update property positions (like Intersheetrefs)
    for prop in label.properties:
        prop.position.X += offset_x
        prop.position.Y += offset_y

    return label


def main():
    # Determine schematic path
    script_dir = Path(__file__).parent
    schematic_path = script_dir / "pcb" / "74aoc.kicad_sch"

    print(f"Loading schematic: {schematic_path}")
    schematic = Schematic.from_file(str(schematic_path))

    # Find template elements
    template_sheet = find_template_sheet(schematic)
    template_labels = find_template_labels(schematic)

    print(f"Found template sheet at ({template_sheet.position.X}, {template_sheet.position.Y})")
    print(f"Found {len(template_labels)} template labels: {list(template_labels.keys())}")

    if len(template_labels) != 5:
        print(f"Warning: Expected 5 template labels (I1, I2, I3, F, Q), found {len(template_labels)}")

    # Track statistics
    cells_added = 0
    cells_skipped = 0
    labels_added = 0
    labels_skipped = 0

    # Create grid
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            offset_x = x * SPACING_MM
            offset_y = -y * SPACING_MM  # Y grows upward (negative in KiCad coords)

            # Check and create cell
            if cell_exists(schematic, x, y):
                print(f"Warning: Cell {cell_name(x, y)} already exists, skipping")
                cells_skipped += 1
            else:
                new_sheet = create_sheet_copy(template_sheet, x, y, offset_x, offset_y)
                schematic.sheets.append(new_sheet)
                cells_added += 1

            # Check and create labels
            for suffix, template_label in template_labels.items():
                lname = label_name(x, y, suffix)
                if label_exists(schematic, lname):
                    print(f"Warning: Label {lname} already exists, skipping")
                    labels_skipped += 1
                else:
                    new_label = create_label_copy(template_label, x, y, suffix, offset_x, offset_y)
                    schematic.globalLabels.append(new_label)
                    labels_added += 1

    print(f"\nSummary:")
    print(f"  Cells added: {cells_added}, skipped: {cells_skipped}")
    print(f"  Labels added: {labels_added}, skipped: {labels_skipped}")

    # Save schematic
    print(f"\nSaving schematic to: {schematic_path}")
    schematic.to_file(str(schematic_path))
    print("Done!")


if __name__ == "__main__":
    main()
