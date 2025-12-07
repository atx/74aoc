#!/usr/bin/env python3
"""
Translate nets from nextpnr's pnrtop.json to KiCad interconnects schematic.

This script reads the ROUTING information from hdl/pnrtop.json and generates
wires with global labels in pcb/interconnects.kicad_sch.

Run tests: python3 -m pytest translate_nets_to_kicad.py -v
Run script: python3 translate_nets_to_kicad.py
"""

import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

import pytest
from kiutils.items.common import Effects, Font, Position, Stroke
from kiutils.items.schitems import Connection, GlobalLabel, SchematicSymbol
from kiutils.schematic import Schematic

# Architecture constants from hdl/simple.py
GRID_X = 12  # LUT X: 1-11, IO X: 0 (input) and 12 (output)
GRID_Y = 12  # Y: 0-11
LUT_K = 3  # LUT inputs: I0, I1, I2
BITS_PER_IO_CELL = 2  # Z: 0 or 1

# Valid ranges
VALID_LUT_X = range(1, GRID_X)  # 1 to 11
VALID_LUT_Y = range(0, GRID_Y)  # 0 to 11
VALID_IO_Y = range(0, 8)  # 0 to 7 (from io_cell_coords in simple.py)
VALID_IO_Z = range(0, BITS_PER_IO_CELL)  # 0 or 1
VALID_LUT_SUFFIXES = {"Q", "F", "I0", "I1", "I2"}

# Layout constants
WIRE_SPACING_MILS = 1500
WIRE_SPACING_MM = WIRE_SPACING_MILS * 0.0254  # 38.1 mm
LABEL_SPACING_MM = 15.0
STARTING_X_MM = 50.0
STARTING_Y_MM = 50.0
TEXT_OFFSET_Y_MM = 5.0

# Regex patterns for translation
RE_IO_PIN = re.compile(r"^IO_X(\d+)Y(\d+)Z(\d+)_([OI])$")
RE_LUT_PIN = re.compile(r"^X(\d+)Y(\d+)_(Q|F|I[0-2])$")
RE_GLOBAL_WIRE = re.compile(r"^GLOBAL_WIRE_\d+$")
RE_LOCAL_WIRE = re.compile(r"^LOCAL_X\d+Y\d+_X\d+Y\d+_\d+$")
RE_GLOBAL_CLK = re.compile(r"^GLOBAL_CLK$")
RE_CELL_CLK = re.compile(r"^X\d+Y\d+_CLK$")
RE_PIP_FROM = re.compile(r"_FROM_")
RE_PIP_TO = re.compile(r"_TO_")


class TranslationError(ValueError):
    """Raised when a ROUTING element cannot be translated."""

    pass


def translate_net_from_verilog_to_kicad(element: str) -> str | None:
    """
    Translate a single ROUTING element to KiCad global label name.

    Returns:
        str: The KiCad global label name (e.g., "W_IO_I5", "W_X11_Y5_Q")
        None: If the element is internal routing and should be skipped

    Raises:
        TranslationError: If the element doesn't match any known pattern
    """
    # Empty or whitespace
    if not element or not element.strip():
        return None

    element = element.strip()

    # Skip internal routing wires
    if RE_GLOBAL_WIRE.match(element):
        return None
    if RE_LOCAL_WIRE.match(element):
        return None
    if RE_GLOBAL_CLK.match(element):
        return None
    if RE_CELL_CLK.match(element):
        return None

    # Skip PIP names (contain _FROM_ or _TO_)
    if RE_PIP_FROM.search(element):
        return None
    if RE_PIP_TO.search(element):
        return None

    # Skip numeric-only elements (connection flags like "1")
    if element.isdigit():
        return None

    # Try IO pin pattern
    m = RE_IO_PIN.match(element)
    if m:
        x, y, z, direction = int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4)

        # Validate coordinates
        if y not in VALID_IO_Y:
            raise TranslationError(f"IO Y coordinate {y} out of range [0,7]: {element}")
        if z not in VALID_IO_Z:
            raise TranslationError(f"IO Z coordinate {z} out of range [0,1]: {element}")

        # Input IOs (X=0) output signal with _O suffix
        if x == 0:
            if direction != "O":
                raise TranslationError(
                    f"Input IO at X=0 must have _O suffix (output from IO cell): {element}"
                )
            index = y * BITS_PER_IO_CELL + z
            return f"W_IO_I{index}"

        # Output IOs (X=12) receive signal with _I suffix
        if x == GRID_X:
            if direction != "I":
                raise TranslationError(
                    f"Output IO at X={GRID_X} must have _I suffix (input to IO cell): {element}"
                )
            index = y * BITS_PER_IO_CELL + z
            return f"W_IO_O{index}"

        raise TranslationError(f"IO X coordinate must be 0 or {GRID_X}, got {x}: {element}")

    # Try LUT pin pattern
    m = RE_LUT_PIN.match(element)
    if m:
        x, y, suffix = int(m.group(1)), int(m.group(2)), m.group(3)

        # Validate coordinates
        if x not in VALID_LUT_X:
            raise TranslationError(f"LUT X coordinate {x} out of range [1,11]: {element}")
        if y not in VALID_LUT_Y:
            raise TranslationError(f"LUT Y coordinate {y} out of range [0,11]: {element}")
        if suffix not in VALID_LUT_SUFFIXES:
            raise TranslationError(f"Invalid LUT suffix '{suffix}': {element}")

        if suffix.startswith("I"):
            # Increment index for inputs, since the KiCad labels are 1-based
            index = int(suffix[1]) + 1
            suffix = f"I{index}"

        return f"W_X{x - 1}_Y{y}_{suffix}"

    # Unknown pattern - raise exception
    raise TranslationError(f"Unrecognized ROUTING element: {element}")


def parse_routing(routing_str: str) -> list[str]:
    """
    Parse ROUTING string and extract KiCad label names.

    Returns list of translated labels (no duplicates, preserves order).
    """
    if not routing_str or not routing_str.strip():
        return []

    labels = []
    seen = set()

    for element in routing_str.split(";"):
        translated = translate_net_from_verilog_to_kicad(element)
        if translated is not None and translated not in seen:
            labels.append(translated)
            seen.add(translated)

    return labels


@dataclass
class NetInfo:
    """Information about a net to be drawn in the schematic."""

    name: str
    labels: list[str]


def process_netnames(netnames: dict) -> list[NetInfo]:
    """
    Process all nets and return list of NetInfo.
    Skip clock net and empty routing.
    """
    nets = []

    for net_name, net_data in netnames.items():
        # Skip clock net entirely
        if net_name == "clk":
            continue

        # Validate structure
        if "attributes" not in net_data:
            raise TranslationError(f"Net '{net_name}' missing 'attributes' key")

        attrs = net_data["attributes"]
        if "ROUTING" not in attrs:
            raise TranslationError(f"Net '{net_name}' missing 'ROUTING' attribute")

        routing = attrs["ROUTING"]

        # Skip empty routing (e.g., $PACKER_GND_NET)
        if not routing.strip():
            continue

        # Parse routing and get labels
        labels = parse_routing(routing)

        # Only include nets that have at least one translated label
        if labels:
            nets.append(NetInfo(name=net_name, labels=labels))

    return nets


def clear_schematic(schematic: Schematic) -> None:
    """Remove all wires, global labels, and text from schematic."""
    schematic.graphicalItems = [
        item for item in schematic.graphicalItems if not isinstance(item, Connection)
    ]
    schematic.globalLabels = []
    # Keep only the descriptive text, remove all
    schematic.texts = []
    # Also clear any symbols that might be present
    schematic.schematicSymbols = [
        sym for sym in schematic.schematicSymbols if not isinstance(sym, SchematicSymbol)
    ]


def create_wire(x1: float, x2: float, y: float) -> Connection:
    """Create a horizontal wire from x1 to x2 at height y."""
    return Connection(
        type="wire",
        points=[
            Position(X=x1, Y=y, angle=None),
            Position(X=x2, Y=y, angle=None),
        ],
        stroke=Stroke(width=0, type="default", color=None),
        uuid=str(uuid.uuid4()),
    )


def create_global_label(text: str, x: float, y: float) -> GlobalLabel:
    """Create a global label pointing down to the wire from above."""
    label = GlobalLabel(
        text=text,
        shape="bidirectional",
        position=Position(X=x, Y=y, angle=270),
        fieldsAutoplaced=True,
        effects=Effects(font=Font(height=1.27, width=1.27)),
        uuid=str(uuid.uuid4()),
    )
    # Add the Intersheetrefs property that KiCad expects
    from kiutils.items.common import Property

    label.properties = [
        Property(
            key="Intersheetrefs",
            value="${INTERSHEET_REFS}",
            position=Position(X=x, Y=y - 10, angle=0),
            effects=Effects(font=Font(height=1.27, width=1.27), hide=True),
        )
    ]
    return label


def create_text(text: str, x: float, y: float) -> "Text":
    """Create a text annotation at the given position."""
    from kiutils.items.schitems import Text

    return Text(
        text=text,
        position=Position(X=x, Y=y, angle=0),
        effects=Effects(font=Font(height=1.27, width=1.27)),
        uuid=str(uuid.uuid4()),
    )


def generate_schematic_content(schematic: Schematic, nets: list[NetInfo]) -> None:
    """Generate wires, labels, and text for all nets."""
    for i, net in enumerate(nets):
        y = STARTING_Y_MM + i * WIRE_SPACING_MM

        # Calculate wire length
        num_labels = len(net.labels)
        wire_length = (num_labels - 1) * LABEL_SPACING_MM if num_labels > 1 else LABEL_SPACING_MM
        x_start = STARTING_X_MM
        x_end = x_start + wire_length

        # Create wire
        wire = create_wire(x_start, x_end, y)
        schematic.graphicalItems.append(wire)

        # Create global labels along the wire
        for j, label_text in enumerate(net.labels):
            label_x = x_start + j * LABEL_SPACING_MM
            label = create_global_label(label_text, label_x, y)
            schematic.globalLabels.append(label)

        # Create text label below the wire (net name)
        text = create_text(net.name, x_start, y + TEXT_OFFSET_Y_MM)
        schematic.texts.append(text)


def list_all_input_nets() -> list[str]:
    """Generate a list of all possible input net names"""
    return [
        f"W_X{x - 1}_Y{y}_I{i + 1}"
        for x in range(1, GRID_X)
        for y in range(GRID_Y)
        for i in range(LUT_K)
    ]


def collect_unused_input_nets(nets: list[NetInfo]) -> set[str]:
    """Collect all input nets that are not used in the given nets."""
    result = set(list_all_input_nets())
    for net in nets:
        for label in net.labels:
            result.discard(label)

    return result


def make_gnd_net(unused_inputs: set[str]) -> NetInfo:
    """Create a special GND net that connects all unused inputs to GND."""
    gnd_labels = list(unused_inputs)
    gnd_labels.append("W_GND")
    return NetInfo(name="SPECIAL_GND_NET", labels=gnd_labels)


def main():
    script_dir = Path(__file__).parent

    # Load pnrtop.json
    pnrtop_path = script_dir / "hdl" / "pnrtop.json"
    print(f"Loading: {pnrtop_path}")

    with open(pnrtop_path) as f:
        pnrtop = json.load(f)

    # Validate structure
    if "modules" not in pnrtop:
        raise TranslationError("pnrtop.json missing 'modules' key")
    if "top" not in pnrtop["modules"]:
        raise TranslationError("pnrtop.json missing 'top' module")
    if "netnames" not in pnrtop["modules"]["top"]:
        raise TranslationError("pnrtop.json missing 'netnames' in top module")

    netnames = pnrtop["modules"]["top"]["netnames"]

    # Process all nets
    print(f"Processing {len(netnames)} nets...")
    nets = process_netnames(netnames)
    print(f"Found {len(nets)} nets with routing to translate")

    # Load schematic
    schematic_path = script_dir / "pcb" / "interconnects.kicad_sch"
    print(f"Loading: {schematic_path}")
    schematic = Schematic.from_file(str(schematic_path))

    # Clear existing content
    print("Clearing existing wires, labels, and text...")
    clear_schematic(schematic)

    # Garbage collect unused inputs and wire them to GND by a special net
    print("Collecting unused input nets for GND connection...")
    unused_inputs = collect_unused_input_nets(nets)
    print(f"Found {len(unused_inputs)} unused input nets to connect to GND")
    for unused in list(unused_inputs):
        print(f"  Unused input net: {unused}")
    nets.append(make_gnd_net(unused_inputs))

    # Generate new content
    print("Generating schematic content...")
    generate_schematic_content(schematic, nets)

    # Save schematic
    print(f"Saving: {schematic_path}")
    schematic.to_file(str(schematic_path))

    print(f"Done! Generated {len(nets)} net wires with {sum(len(n.labels) for n in nets)} labels")


# =============================================================================
# TESTS - run with: python3 -m pytest translate_nets_to_kicad.py -v
# =============================================================================


@pytest.mark.parametrize(
    "element,expected",
    [
        # IO inputs (X=0, _O suffix means output from IO cell = input to design)
        ("IO_X0Y0Z0_O", "W_IO_I0"),
        ("IO_X0Y0Z1_O", "W_IO_I1"),
        ("IO_X0Y1Z0_O", "W_IO_I2"),
        ("IO_X0Y1Z1_O", "W_IO_I3"),
        ("IO_X0Y2Z1_O", "W_IO_I5"),
        ("IO_X0Y7Z1_O", "W_IO_I15"),
        # IO outputs (X=12, _I suffix means input to IO cell = output from design)
        ("IO_X12Y0Z0_I", "W_IO_O0"),
        ("IO_X12Y0Z1_I", "W_IO_O1"),
        ("IO_X12Y5Z0_I", "W_IO_O10"),
        ("IO_X12Y7Z1_I", "W_IO_O15"),
        # LUT pins
        ("X11Y5_Q", "W_X10_Y5_Q"),
        ("X2Y2_I1", "W_X1_Y2_I2"),
        ("X9Y4_F", "W_X8_Y4_F"),
        ("X1Y0_I0", "W_X0_Y0_I1"),
        ("X11Y11_I2", "W_X10_Y11_I3"),
        # Skip cases (return None)
        ("GLOBAL_WIRE_11", None),
        ("GLOBAL_WIRE_0", None),
        ("GLOBAL_WIRE_63", None),
        ("LOCAL_X11Y5_X11Y8_1", None),
        ("LOCAL_X2Y8_X2Y9_2", None),
        ("GLOBAL_CLK", None),
        ("X1Y1_CLK", None),
        ("X11Y5_CLK", None),
        ("GLOBAL_WIRE_11_FROM_IO_X0Y2Z1", None),
        ("GLOBAL_WIRE_11_TO_LUT_X2Y2_I1", None),
        ("LOCAL_X2Y8_X2Y9_2_FROM_X2Y9_F", None),
        ("LOCAL_X2Y8_X2Y9_2_TO_X2Y8_I2", None),
        ("IO_X0Y0Z0_TO_GLOBAL_CLK", None),
        ("GLOBAL_CLK_TO_X1Y1_CLK", None),
        ("", None),
        ("   ", None),
        ("1", None),
    ],
)
def test_translate_net(element: str, expected: str | None):
    result = translate_net_from_verilog_to_kicad(element)
    assert result == expected, f"translate({element!r}) = {result!r}, expected {expected!r}"


@pytest.mark.parametrize(
    "element",
    [
        # Wrong direction for IO side
        "IO_X0Y0Z0_I",  # Input side should have _O
        "IO_X12Y0Z0_O",  # Output side should have _I
        # Invalid X coordinate
        "IO_X5Y0Z0_O",
        "IO_X1Y0Z0_I",
        # Invalid Y coordinate for IO
        "IO_X0Y8Z0_O",
        "IO_X0Y10Z0_O",
        # Invalid Z coordinate
        "IO_X0Y0Z2_O",
        "IO_X0Y0Z3_O",
        # Invalid LUT coordinates
        "X0Y0_Q",  # X=0 is IO, not LUT
        "X12Y0_Q",  # X=12 is IO, not LUT
        "X13Y0_Q",  # Out of range
        "X1Y12_Q",  # Y out of range
        # Invalid LUT suffix
        "X1Y1_I3",
        "X1Y1_X",
        # Unknown patterns
        "UNKNOWN_WIRE",
        "X1Y1",
        "IO_X0Y0Z0",
    ],
)
def test_translate_net_errors(element: str):
    with pytest.raises(TranslationError):
        translate_net_from_verilog_to_kicad(element)


def test_parse_routing_simple():
    routing = "IO_X0Y2Z1_O;;1;GLOBAL_WIRE_11;GLOBAL_WIRE_11_FROM_IO_X0Y2Z1;1;X2Y2_I1;GLOBAL_WIRE_11_TO_LUT_X2Y2_I1;1"
    labels = parse_routing(routing)
    assert labels == ["W_IO_I5", "W_X1_Y2_I2"]


def test_parse_routing_complex():
    routing = "LOCAL_X11Y5_X11Y8_1;LOCAL_X11Y5_X11Y8_1_FROM_X11Y5_Q;1;X11Y5_I2;LOCAL_X11Y5_X11Y8_1_TO_X11Y5_I2;1;X11Y5_Q;;1;GLOBAL_WIRE_33;GLOBAL_WIRE_33_FROM_LUT_X11Y5_Q;1;IO_X12Y5Z0_I;GLOBAL_WIRE_33_TO_IO_X12Y5Z0;1"
    labels = parse_routing(routing)
    assert labels == ["W_X10_Y5_I3", "W_X10_Y5_Q", "W_IO_O10"]


def test_parse_routing_empty():
    assert parse_routing("") == []
    assert parse_routing("   ") == []


def test_parse_routing_dedup():
    # Simulate a routing where the same label appears multiple times
    routing = "X1Y1_Q;;1;X1Y1_Q;;1"
    labels = parse_routing(routing)
    assert labels == ["W_X0_Y1_Q"]  # Should deduplicate


if __name__ == "__main__":
    main()
