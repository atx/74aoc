# 74aoc

<p align="center">
  <img width=600 src="https://github.com/user-attachments/assets/bb97d285-ea2f-4525-89ac-9ac5e4109f97">
</p>


A PCB solving [Advent of Code 2025 Day 1](https://adventofcode.com/2025/day/1) using 125 discrete 74-series logic chips synthesized via an automated Hardcaml -> nextpnr -> KiCad pipeline.

**Full writeup can be found on [my blog](https://atx.name/electronics/hardcaml-to-74-series-logic).**

<p align="center">
  <img width=400 src="https://github.com/user-attachments/assets/123096da-e73e-4578-8398-9c8479562db8">
</p>

Quick orientation guide:

 * `pcb/` contains the KiCad files. For reproducibility, those are "cooked" files that include the solution design loaded and routed (revert the appropriate commits for a fresh blank slate)
 * `hdl/` contains the Hardcaml source code and the Yosys+nextpnr orchestration. Some of the intermediate files are also commited for traceability. 
   * `dune exec ./test_solution.exe` runs the Hardcaml test bench
   * `dune exec ./build_solution.exe` outputs the Verilog source code from the Hardcaml solution
   * `top.v` includes the output of the previous step and wraps it to assign concrete IO pads to the signals
   * `./simulate.sh <preplace|pnr>` runs the Verilog testbench using Verilator, either on pre-placement Verilog or on the placement result from Nextpnr (using the appropriate cell models from nextpnr-generic)
 * The root directory contains several scripts that serve to translate results from `hdl` into `pcb`. Loading new design is done by running `translate_nets_to_kicad.py` and `load_luts_into_kicad.py`.
