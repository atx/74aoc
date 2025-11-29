#! /usr/bin/env bash

set -ex

yosys -p "tcl ./synth_generic.tcl top.json" top.v
nextpnr-generic \
	--pre-pack simple.py \
	--pre-place simple_timing.py \
	--json top.json \
	--post-route bitstream.py \
	--write pnrtop.json

# TODO: Do we need this for anything?
#yosys -p "read_verilog -lib ./prims.v; read_json pnrtop.json; dump -o top.il; show -format png -prefix top"

# Simulate the result
yosys -p "read_json pnrtop.json; write_verilog -noattr -norename pnrtop.v"
iverilog -o top_simtest ./prims.v  ./top_tb.v ./pnrtop.v
vvp -N ./top_simtest

