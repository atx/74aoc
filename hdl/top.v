
`include "solution.v"


// Top wrapper module with static BEL assignments for IO placement
// Inputs: X=0, starting from Y=0, Z=0 going up
// Outputs: X=12, starting from Y=0, Z=0 going up
module top (
	// Inputs - starting from X0Y0Z0_IO going up Y axis
	// Note: the clk input is actually handled specially in the schematic,
	// so in practice this will not be connected
	(* BEL="X0Y0Z0_IO" *)
	input wire clk,
	(* BEL="X0Y0Z1_IO" *)
	input wire valid,
	(* BEL="X0Y1Z0_IO" *)
	input wire step_direction,
	(* BEL="X0Y1Z1_IO" *)
	input wire step_count_0,
	(* BEL="X0Y2Z0_IO" *)
	input wire step_count_1,
	(* BEL="X0Y2Z1_IO" *)
	input wire step_count_2,
	(* BEL="X0Y3Z0_IO" *)
	input wire step_count_3,
	(* BEL="X0Y3Z1_IO" *)
	input wire step_count_4,
	(* BEL="X0Y4Z0_IO" *)
	input wire step_count_5,
	(* BEL="X0Y4Z1_IO" *)
	input wire step_count_6,
	(* BEL="X0Y5Z0_IO" *)
	input wire step_count_7,
	(* BEL="X0Y5Z1_IO" *)
	input wire step_count_8,
	(* BEL="X0Y6Z0_IO" *)
	input wire step_count_9,

	// Outputs - starting from X12Y0Z0_IO going up Y axis
	(* BEL="X12Y0Z0_IO" *)
	output wire zero_count_0,
	(* BEL="X12Y0Z1_IO" *)
	output wire zero_count_1,
	(* BEL="X12Y1Z0_IO" *)
	output wire zero_count_2,
	(* BEL="X12Y1Z1_IO" *)
	output wire zero_count_3,
	(* BEL="X12Y2Z0_IO" *)
	output wire zero_count_4,
	(* BEL="X12Y2Z1_IO" *)
	output wire zero_count_5,
	(* BEL="X12Y3Z0_IO" *)
	output wire zero_count_6,
	(* BEL="X12Y3Z1_IO" *)
	output wire zero_count_7,
	(* BEL="X12Y4Z0_IO" *)
	output wire zero_count_8,
	(* BEL="X12Y4Z1_IO" *)
	output wire zero_count_9,
	(* BEL="X12Y5Z0_IO" *)
	output wire zero_count_10
);

	wire [9:0] step_count_bus = {
		step_count_9, step_count_8, step_count_7, step_count_6, step_count_5,
		step_count_4, step_count_3, step_count_2, step_count_1, step_count_0
	};

	wire [10:0] zero_count_bus;
	assign {zero_count_10, zero_count_9, zero_count_8, zero_count_7, zero_count_6,
	        zero_count_5, zero_count_4, zero_count_3, zero_count_2, zero_count_1, zero_count_0} = zero_count_bus;

	solution sol (
		.clk(clk),
		.valid(valid),
		.step_direction(step_direction),
		.step_count(step_count_bus),
		.zero_count(zero_count_bus)
	);

endmodule
