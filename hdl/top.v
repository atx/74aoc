
// This is the _old_ solution module, kept for reference. The new solution
// module is exported from solution.ml into solution.v
module solution_old
#(
	parameter INPUT_WIDTH = 10,  // In practice the parameters are <1000 so 10 bits is enough
	parameter OUTPUT_WIDTH = 11,  // A result observed: 1165, so 11 bits would be enough in theory. Every extra bit is kinda expensive, so I am going to keep it tight. This may result in this not working for some inputs
	parameter DIAL_INIT = 50,
	parameter DIAL_MAX = 99,  // Inclusive!
	parameter DIAL_WIDTH = 7  // TODO: logarithmize DIAL_MAX
) (
	input wire clk,
	input wire valid,  // High when the dial input is valid
	input wire step_direction,  // 1 = up, 0 = down
	input wire [INPUT_WIDTH-1:0] step_count,
	output reg [OUTPUT_WIDTH-1:0] zero_count = 0
);

	reg [DIAL_WIDTH-1:0] dial_value = DIAL_INIT; // Initial value specified by the puzzle
	wire [DIAL_WIDTH-1:0] next_dial_value;
	reg [INPUT_WIDTH-1:0] counter = 0;
	reg saved_direction = 0;

	always @(*) begin
		if (saved_direction) begin
			next_dial_value = (dial_value == DIAL_MAX) ? 0 : dial_value + 1'b1;
		end else begin
			next_dial_value = (dial_value == 0) ? DIAL_MAX : dial_value - 1'b1;
		end
	end

	always @(posedge clk) begin
		// TODO: Do we want to handle rst here? I feel that there is no point,
		// we are just going to get the initial values and implement them in
		// hardware (by routing to set/clear pins of the chosen DFF)
		if (valid) begin
			// If the input is valid, we have received a new input value and 
			// should start processing it. The user is responsible for feeding
			// the values at a reasonable rate
			counter <= step_count;
			saved_direction <= step_direction;
		end else if (counter > 0) begin
			// Okay, we now need to process the steps one at a time
			dial_value <= next_dial_value;
			counter <= counter - 1'b1;
			if (counter == 1) begin
				// We have just processed the last step, so we need to check
				// if we are at zero now
				if (next_dial_value == 0) begin
					zero_count <= zero_count + 1'b1;
				end
			end
		end
	end

endmodule

`include "solution.v"


// Top wrapper module with static BEL assignments for IO placement
// Inputs: X=0, starting from Y=0, Z=0 going up
// Outputs: X=12, starting from Y=0, Z=0 going up
module top (
	// Inputs - starting from X0Y0Z0_IO going up Y axis
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
