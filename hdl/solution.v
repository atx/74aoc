module solution (
    step_direction,
    clk,
    step_count,
    valid,
    zero_count
);

    input step_direction;
    input clk;
    input [9:0] step_count;
    input valid;
    output [10:0] zero_count;

    wire [10:0] _47;
    wire [10:0] _48;
    wire [6:0] _45;
    wire [6:0] _30;
    wire [6:0] _31;
    wire [6:0] _28;
    wire _29;
    wire [6:0] _33;
    wire [6:0] _25;
    wire [6:0] _19;
    wire [6:0] _35;
    wire [6:0] _36;
    wire [6:0] _1;
    reg [6:0] _20 = 7'b0110010;
    wire _23;
    wire [6:0] _27;
    wire _3;
    wire _37;
    wire _4;
    reg _21;
    wire [6:0] _34;
    wire _46;
    wire [10:0] _49;
    wire [9:0] _43;
    wire _44;
    wire [10:0] _50;
    wire [9:0] _16;
    wire _6;
    wire [9:0] _8;
    wire [9:0] _39;
    wire [9:0] _40;
    wire [9:0] _41;
    wire [9:0] _9;
    reg [9:0] _15 = 10'b0000000000;
    wire _17;
    wire _18;
    wire [10:0] _51;
    wire _11;
    wire [10:0] _52;
    wire [10:0] _12;
    reg [10:0] _42;
    assign _47 = 11'b00000000001;
    assign _48 = _42 + _47;
    assign _45 = 7'b0000000;
    assign _30 = 7'b0000001;
    assign _31 = _20 + _30;
    assign _28 = 7'b1100011;
    assign _29 = _20 == _28;
    assign _33 = _29 ? _45 : _31;
    assign _25 = _20 - _30;
    assign _19 = 7'b0110010;
    assign _35 = _18 ? _34 : _20;
    assign _36 = _11 ? _20 : _35;
    assign _1 = _36;
    always @(posedge _6) begin
        _20 <= _1;
    end
    assign _23 = _20 == _45;
    assign _27 = _23 ? _28 : _25;
    assign _3 = step_direction;
    assign _37 = _11 ? _3 : _21;
    assign _4 = _37;
    always @(posedge _6) begin
        _21 <= _4;
    end
    assign _34 = _21 ? _33 : _27;
    assign _46 = _34 == _45;
    assign _49 = _46 ? _48 : _42;
    assign _43 = 10'b0000000001;
    assign _44 = _15 == _43;
    assign _50 = _44 ? _49 : _42;
    assign _16 = 10'b0000000000;
    assign _6 = clk;
    assign _8 = step_count;
    assign _39 = _15 - _43;
    assign _40 = _18 ? _39 : _15;
    assign _41 = _11 ? _8 : _40;
    assign _9 = _41;
    always @(posedge _6) begin
        _15 <= _9;
    end
    assign _17 = _15 == _16;
    assign _18 = ~ _17;
    assign _51 = _18 ? _50 : _42;
    assign _11 = valid;
    assign _52 = _11 ? _42 : _51;
    assign _12 = _52;
    always @(posedge _6) begin
        _42 <= _12;
    end
    assign zero_count = _42;

endmodule
