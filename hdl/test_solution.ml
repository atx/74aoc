open Hardcaml

module Simulator = Cyclesim.With_interface(Solution.I)(Solution.O)

(* Data type for a single instruction *)
type instruction = {
  direction : bool;  (* true = Right, false = Left *)
  count : int;
}

let parse_line (line : string) : instruction =
  let c = String.get line 0 in
  let rest = String.sub line 1 (String.length line - 1) in
  { direction = (c = 'R'); count = int_of_string rest }

(* Read and parse all instructions from a file *)
let load_instructions filename =
  In_channel.with_open_text filename (fun ic ->
    In_channel.input_all ic
    |> String.split_on_char '\n'
    |> List.filter (fun s -> String.length s > 0)
    |> List.map parse_line
  )

let testbench create =
  let sim = Simulator.create create in
  let inputs = Cyclesim.inputs sim in
  let outputs = Cyclesim.outputs sim in

  Cyclesim.reset sim;

  for _ = 0 to 10 do
    Cyclesim.cycle sim
  done;

  let instructions = load_instructions "my_input" in
  Printf.printf "Loaded %d instructions\n" (List.length instructions);

  List.iter (fun instr ->
    (* Shove data inside *)
    inputs.valid := Bits.vdd;
    inputs.step_direction := if instr.direction then Bits.vdd else Bits.gnd;
    inputs.step_count := Bits.of_int_trunc ~width:Solution.Config.input_width instr.count;
    (* shove *)
    Cyclesim.cycle sim;

    (* Drop the valid *)
    inputs.valid := Bits.gnd;

    for _ = 0 to 2000 do
      Cyclesim.cycle sim;
    done;

  ) instructions;

  (* And finally print out the result *)
  let final_position = Bits.to_int_trunc !(outputs.zero_count) in
  Printf.printf "Final position: %d\n" final_position;

  ()

let () = testbench Solution.create
