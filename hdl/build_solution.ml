open Hardcaml

let () =
  let module Circuit = Circuit.With_interface(Solution.I)(Solution.O) in
  let circuit = Circuit.create_exn ~name:"solution" Solution.create in
  Rtl.print Verilog circuit
