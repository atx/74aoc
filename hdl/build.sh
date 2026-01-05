#! /usr/bin/env bash

set -ex

dune exec ./build_solution.exe > solution.v

yosys -p "tcl ./synth_generic.tcl top.json" top.v
nextpnr-generic \
	--pre-pack simple.py \
	--pre-place simple_timing.py \
	--json top.json \
	--post-route bitstream.py \
	--write pnrtop.json \
	--top top \
	--no-tmdriv

# Output placed-and-routed Verilog for inspection
yosys -p "read_json pnrtop.json; write_verilog -noattr -norename pnrtop.v"
