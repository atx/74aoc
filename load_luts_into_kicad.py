#!/usr/bin/env python3
"""
Script to load LUT INIT values from nextpnr output into KiCad schematic.

Reads cells from hdl/pnrtop.json, extracts INIT parameters, and sets
MUX_N_0 and MUX_N_1 properties on corresponding hierarchical sheets
in pcb/74aoc.kicad_sch.

For each bit N of the 8-bit INIT:
  - If bit N = 1: MUX_N_0 = "0", MUX_N_1 = "1"
  - If bit N = 0: MUX_N_0 = "1", MUX_N_1 = "0"

Bit ordering: rightmost character of INIT string = bit 0
(verified from prims.v: assign Q = INIT[I_pd])
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from kiutils.items.common import Effects, Font, Position, Property
from kiutils.schematic import Schematic


@dataclass
class CellInfo:
    """Information about a placed GENERIC_SLICE cell.

    Coordinates:
      - pnr_x, pnr_y: nextpnr coordinates (from simple.py: X in 1..11, Y in 0..11)
      - kicad_x, kicad_y: KiCad schematic coordinates (X in 0..10, Y in 0..10)

    Mapping (from simple.py):
      - LUT cells in nextpnr start at X=1 (X=0 is reserved for IO)
      - KiCad schematic starts at X=0
      - So: kicad_x = pnr_x - 1, kicad_y = pnr_y
    """

    pnr_x: int
    pnr_y: int
    init: str

    @property
    def kicad_x(self) -> int:
        return self.pnr_x - 1

    @property
    def kicad_y(self) -> int:
        return self.pnr_y


class LutLoadError(ValueError):
    """Raised when LUT loading fails."""

    pass


RE_BEL_SLICE = re.compile(r"^X(\d+)Y(\d+)_SLICE$")


def parse_pnrtop(pnrtop_path: Path) -> list[CellInfo]:
    """
    Parse pnrtop.json and extract GENERIC_SLICE cells.

    Returns list of CellInfo with coordinates and INIT values.
    """
    with open(pnrtop_path) as f:
        data = json.load(f)

    cells = data["modules"]["top"]["cells"]
    result = []

    for cell_name, cell_data in cells.items():
        if cell_data.get("type") != "GENERIC_SLICE":
            continue

        bel = cell_data.get("attributes", {}).get("NEXTPNR_BEL")
        if bel is None:
            raise LutLoadError(f"Cell {cell_name} has no NEXTPNR_BEL attribute")

        match = RE_BEL_SLICE.match(bel)
        if match is None:
            raise LutLoadError(f"Cell {cell_name} has invalid BEL format: {bel}")

        pnr_x = int(match.group(1))
        pnr_y = int(match.group(2))

        init = cell_data.get("parameters", {}).get("INIT")
        if init is None:
            raise LutLoadError(f"Cell {cell_name} has no INIT parameter")

        if len(init) != 8 or not all(c in "01" for c in init):
            raise LutLoadError(
                f"Cell {cell_name} has invalid INIT format: {init!r} "
                "(expected 8 binary digits)"
            )

        result.append(CellInfo(pnr_x=pnr_x, pnr_y=pnr_y, init=init))

    return result


def build_sheet_lookup(schematic: Schematic) -> dict[str, object]:
    """
    Build a lookup from sheet name to sheet object.
    """
    lookup = {}
    for sheet in schematic.sheets:
        name = sheet.sheetName.value
        lookup[name] = sheet
    return lookup


def init_to_mux_properties(init: str, sheet_position: Position) -> list[Property]:
    """
    Convert an 8-bit INIT string to MUX properties.

    init: 8-character binary string, rightmost = bit 0
    Returns: list of 16 Property objects (MUX_0_0 through MUX_7_1)
    """
    properties = []

    # Iterate through bits 0-7
    # Rightmost character is bit 0, so we reverse the string
    for bit_idx in range(8):
        # Index from the right: bit 0 is init[-1], bit 1 is init[-2], etc.
        bit_value = init[7 - bit_idx]

        if bit_value == "1":
            mux_0_val = "0"
            mux_1_val = "1"
        elif bit_value == "0":
            mux_0_val = "1"
            mux_1_val = "0"
        else:
            assert False, "Should not reach here due to prior validation"

        # Create properties with hidden effects (they don't need to be visible)
        for suffix, value in [("0", mux_0_val), ("1", mux_1_val)]:
            prop = Property(
                key=f"MUX_{bit_idx}_{suffix}",
                value=value,
                position=Position(X=sheet_position.X, Y=sheet_position.Y, angle=0),
                effects=Effects(font=Font(height=1.27, width=1.27), hide=True),
            )
            properties.append(prop)

    return properties


def clear_existing_mux_properties(sheet) -> None:
    """
    Remove any existing MUX_*_* properties from a sheet.
    """
    if not hasattr(sheet, "properties"):
        return

    # Keep only non-MUX properties
    sheet.properties = [
        p for p in sheet.properties if not p.key.startswith("MUX_")
    ]


def main():
    script_dir = Path(__file__).parent
    pnrtop_path = script_dir / "hdl" / "pnrtop.json"
    schematic_path = script_dir / "pcb" / "74aoc.kicad_sch"

    print(f"Loading pnrtop.json from: {pnrtop_path}")
    cells = parse_pnrtop(pnrtop_path)
    print(f"Found {len(cells)} GENERIC_SLICE cells")

    print(f"Loading schematic from: {schematic_path}")
    schematic = Schematic.from_file(str(schematic_path))

    sheet_lookup = build_sheet_lookup(schematic)
    print(f"Found {len(sheet_lookup)} sheets in schematic")

    cells_processed = 0

    for cell in cells:
        sheet_name = f"CELL X{cell.kicad_x} Y{cell.kicad_y}"

        if sheet_name not in sheet_lookup:
            raise LutLoadError(
                f"No sheet found for nextpnr cell at pnr=({cell.pnr_x}, {cell.pnr_y}) "
                f"-> kicad=({cell.kicad_x}, {cell.kicad_y}): "
                f"expected sheet named {sheet_name!r}"
            )

        sheet = sheet_lookup[sheet_name]

        # Clear any existing MUX properties
        clear_existing_mux_properties(sheet)

        # Add new MUX properties
        mux_props = init_to_mux_properties(cell.init, sheet.position)

        if not hasattr(sheet, "properties"):
            sheet.properties = []

        sheet.properties.extend(mux_props)
        cells_processed += 1

        # Print progress for verification
        print(f"  {sheet_name} (pnr X{cell.pnr_x}Y{cell.pnr_y}): INIT={cell.init}")

    print(f"\nProcessed {cells_processed} cells")
    print(f"Saving schematic to: {schematic_path}")
    schematic.to_file(str(schematic_path))
    print("Done!")


if __name__ == "__main__":
    main()
