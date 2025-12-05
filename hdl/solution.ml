open Hardcaml
open Hardcaml.Signal

(* Just constants, no need to actually parametrize here... *)
module Config = struct
    let input_width = 10 (* In practice, the parameters are <1000 so 10 bits is enough *)
    let output_width = 11 (* A result observed: 1165, so 11 bits is enough in theory. Extending to 12 bits needs quite a bit of extra slices... *)
    let dial_init = 50
    let dial_max = 99 (* Inclusive *)
    let dial_width = int_of_float (floor ((log (float_of_int dial_max)) /. log 2.)) + 1
end

module I = struct
    type 'a t = 
      { clk : 'a
      ; valid : 'a
      ; step_direction : 'a
      ; step_count : 'a [@bits Config.input_width]
      }

    [@@deriving hardcaml]
end

module O = struct
    type 'a t =
      { zero_count : 'a [@bits Config.output_width]
      }

    [@@deriving hardcaml]
end

let create (i : _ I.t) =
    let spec = Reg_spec.create ~clock:i.clk () in

    (* Okay, this is basically a very "raw" translation of the original Verilog code
       This is not very Hardcaml-y for now...
     *)

    (* Tracks the value of the dial *)
    let dial_value = Always.Variable.reg spec ~enable:vdd ~width:Config.dial_width 
        ~initialize_to:(of_int_trunc ~width:Config.dial_width Config.dial_init) in
    (* This counts how many times we have stopped at zero, that is, this is our result *)
    let zero_count = Always.Variable.reg spec ~enable:vdd ~width:Config.output_width in
    (* Internal "how many clicks we have remaining" counter *)
    let counter = Always.Variable.reg spec ~enable:vdd ~width:Config.input_width
        ~initialize_to:(of_int_trunc ~width:Config.input_width 0) in
    (* 1 = up, 0 = down *)
    let saved_direction = Always.Variable.reg spec ~enable:vdd ~width:1 in

    (* TODO: This can be exported to a saturating counter subfunction I think *)
    let next_dial_value =
        mux2 saved_direction.value
            (mux2 (dial_value.value ==:. Config.dial_max)
                (of_int_trunc ~width:Config.dial_width 0)
                (dial_value.value +:. 1))
            (mux2 (dial_value.value ==:. 0)
                (of_int_trunc ~width:Config.dial_width Config.dial_max)
                (dial_value.value -:. 1)) in

    Always.(compile [
        if_ (i.valid) [
            (* This means that the host is feeding us data.
               We handle this by unconditionally overwriting our internal state
               even if something is in progress. The host is responsible for
               waiting at least 2000 cycles between writes.
            *)
            counter <-- i.step_count;
            saved_direction <-- i.step_direction;
        ] @@ elif (counter.value <>: (of_int_trunc ~width:Config.input_width 0)) [
            (* We have some steps to process,
               so we do one step of the dial
             *)
            dial_value <-- next_dial_value;
            counter <-- counter.value -:. 1;
            when_ (counter.value ==: (of_int_trunc ~width:Config.input_width 1)) [
                (* This was the last step, so we check if we are at zero now *)
                when_ (next_dial_value ==: (of_int_trunc ~width:Config.dial_width 0)) [
                    zero_count <-- zero_count.value +:. 1
                ]
            ]
        ] [
            (* No operation *)
        ]
    ]);

    { O.zero_count = zero_count.value }
