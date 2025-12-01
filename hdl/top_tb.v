`timescale 1ns/1ps

module top_tb;

    // Parameters matching the DUT
    parameter INPUT_WIDTH = 10;
    parameter OUTPUT_WIDTH = 12;
    
    parameter CLK_PERIOD = 10;
    
    // Testbench signals
    reg clk;
    reg valid;
    reg step_direction;
    reg [INPUT_WIDTH-1:0] step_count;
    wire [OUTPUT_WIDTH-1:0] zero_count;
    
    // File handling
    integer fd;
    integer scan_result;
    reg [8*16-1:0] line;
    reg [7:0] dir_char;
    integer count_val;
    integer line_num;
    
    // Instantiate DUT
    top dut (
        .clk(clk),
        .valid(valid),
        .step_direction(step_direction),
        .step_count(step_count),
        .zero_count(zero_count)
    );
    
    // Clock generation
    initial begin
        clk = 0;
        forever #(CLK_PERIOD/2) clk = ~clk;
    end
    
    // VCD dump
    initial begin
        $dumpfile("top_tb.vcd");
        $dumpvars(0, top_tb);
    end
    
    // Main test sequence
    initial begin
        // Initialize
        valid = 0;
        step_direction = 0;
        step_count = 0;
        line_num = 0;
        
        // Wait for a couple cycles
        @(posedge clk);
        @(posedge clk);
        
        // Open input file
        fd = $fopen("my_input", "r");
        if (fd == 0) begin
            $display("ERROR: Could not open my_input (this is the AoC input file)");
            $finish;
        end
        
        // Process each line
        while ($fgets(line, fd)) begin
            scan_result = $sscanf(line, "%c%d", dir_char, count_val);
            line_num = line_num + 1;
            
            // 1-2: Present step_count and step_direction
            // R = right = up = 1, L = left = down = 0
            step_direction = (dir_char == "R") ? 1'b1 : 1'b0;
            step_count = count_val;
            
            // 3: Clock cycle
            @(posedge clk);
            
            // 4: Set valid
            valid = 1;
            
            // 5: Clock cycle
            @(posedge clk);
            
            // 6: Unset valid
            valid = 0;
            
            // 7: Do 2000 clock cycles
            repeat(2000) @(posedge clk);
        end
        
        $fclose(fd);
        
        // Display result
        $display("Processed %0d lines", line_num);
        $display("zero_count = %0d", zero_count);
        
        // End simulation
        repeat(10) @(posedge clk);
        $finish;
    end

endmodule
