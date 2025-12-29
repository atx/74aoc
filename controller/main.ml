
type args = {
    trick : bool;
    loop : bool;
    input_file_path: string;
    speed: float;
}

let parse_args () : args =
    let open Cmdliner in

    let make_args trick loop speed input_file_path =
        { trick; loop; speed; input_file_path } in
    let config_term =
        Term.(const make_args
                $ Arg.(value & flag & info ["t"; "trick"] ~doc:"Enable trick mode (non-constant delay)")
                $ Arg.(value & flag & info ["l"; "loop"] ~doc:"Loop forever")
                $ Arg.(value & opt float 1.0 & info ["s"; "speed"] ~doc:"Set speed multiplier (default 1.0)")
                $ Arg.(required & pos 0 (some string) None & info [] ~docv:"INPUT_FILE" ~doc:"Path to the input file")) in

    let cmd = Cmd.v (Cmd.info "controller") config_term in
    match Cmd.eval_value cmd with
    | Ok (`Ok args) -> args
    | Ok (`Version | `Help) -> exit 0
    | Error _ -> exit 1

type instruction = {
    direction : bool; (* true for right, false for left *)
    count : int;
}

let parse_line (line : string) : instruction =
    let c = String.get line 0 in
    let rest = String.sub line 1 (String.length line - 1) in
    let direction = match c with
        | 'R' -> true
        | 'L' -> false
        | _ -> failwith ("Invalid direction character: " ^ String.make 1 c) in
    let count = int_of_string rest in
    { direction; count }

let load_instructions (file_path : string) : instruction Seq.t =
    In_channel.with_open_text file_path (fun ic ->
        In_channel.input_all ic
        |> String.split_on_char '\n'
        |> List.filter (fun line -> String.length line > 0)
        |> List.map parse_line
    ) |> List.to_seq


module Board = struct

    open Gpio

    module P = struct
        let nrst = 17
        let clk = 27

        let dir = 21
        let valid = 20

        let data_bits = [
            26; 19; 16; 13; 6; 12; 5; 25; 24; 23
        ]
    end

    type pins = {
        nrst : Gpio.line;
        clk : Gpio.line;

        dir : Gpio.line;
        valid : Gpio.line;

        data_bits : Gpio.line list;

        chip : Gpio.chip;
    }

    let setup_pins () : pins =
        (* Not sure how to ensure cleanup here... *)
        let chip = Gpio.open_chip () in

        let o num = 
            let line = Gpio.setup_output chip num in
            write line false;
            line in

        {
            nrst = o P.nrst;
            clk = o P.clk;

            dir = o P.dir;
            valid = o P.valid;

            data_bits = List.map o P.data_bits;

            chip;
        }

    type t = {
        speed : float;
        pins : pins;
    }

    let make ~speed : t =
        let pins = setup_pins () in
        { speed; pins }

    let low (line : Gpio.line) : unit =
        write line false

    let high (line : Gpio.line) : unit =
        write line true

    let sleep (board : t) (duration : float) : unit =
        if Float.is_finite board.speed then
            Unix.sleepf (duration /. board.speed)
        else
            ()

    let reset (board : t) : unit =
        low board.pins.clk;  (* Just to be sure *)

        low board.pins.nrst;
        sleep board 0.1;
        high board.pins.nrst;
        sleep board 0.1;
        ()

    let cycle (board : t) : unit =
        high board.pins.clk;
        sleep board 0.01;
        low board.pins.clk;
        sleep board 0.01;
        ()

    let send (board : t) (direction : bool) (value : int) : unit =
        (* Set direction *)
        if direction then
            high board.pins.dir
        else
            low board.pins.dir;

        (* Set data bits *)
        List.iteri (fun i line ->
            let bit = (value lsr i) land 1 in
            if bit = 1 then
                high line
            else
                low line
        ) board.pins.data_bits;

        (* Signal valid *)
        high board.pins.valid;

        (* Wait until everything stabilizes *)
        sleep board 0.001;
        (* Cycle clock to send data *)
        cycle board;
        (* Clear valid signal (no need to wait since we have already done a rising + falling edge... *)
        low board.pins.valid;

        ()


end

let run cfg =
    (* Just print the config in pretty way *)
    Printf.printf "Loading instructions from file: %s\n" cfg.input_file_path;
    let instructions = load_instructions cfg.input_file_path
        |> (if cfg.loop then Seq.cycle else Fun.id) in

    let board = Board.make ~speed:cfg.speed in

    let open Board in

    Printf.printf "Resetting board...\n";

    reset board;

    Seq.iter (fun instr ->
        Printf.printf "Sending instruction: Direction=%s, Count=%d\n%!"
            (if instr.direction then "Right" else "Left")
            instr.count;
        send board instr.direction instr.count;
        (* Sleep for either 2000 cycles (no-trick mode) or for instr.count cycles *)
        let sleep_cycles = if cfg.trick then instr.count + 2 else 2000 in
        for _ = 1 to sleep_cycles do
            cycle board
        done;
    ) instructions;

    ()

let () =
    let cfg = parse_args () in
    run cfg
