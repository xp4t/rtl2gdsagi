`timescale 1ns/1ps
`default_nettype none

module shift_reg_tb;

    reg        clk = 1'b0;
    reg        rst_n = 1'b0;
    reg  [1:0] mode;
    reg        serial_in;
    reg  [7:0] parallel;
    wire [7:0] data;
    wire       serial_out;
    integer    errors = 0;

    shift_reg uut (
        .i_clk(clk), .i_rst_n(rst_n),
        .i_mode(mode), .i_serial_in(serial_in),
        .i_parallel(parallel),
        .o_data(data), .o_serial_out(serial_out)
    );

    always #5 clk = ~clk;

    task check8(input [7:0] got, input [7:0] want, input [255:0] what);
        begin
            if (got !== want) begin
                $display("FAILED: %0s -- expected 0x%02h, got 0x%02h", what, want, got);
                errors = errors + 1;
            end
        end
    endtask

    initial begin
        mode = 2'b00; serial_in = 1'b0; parallel = 8'h00;

        // Reset
        @(negedge clk); @(negedge clk);
        check8(data, 8'h00, "reset clears register");

        // Release reset, parallel load
        rst_n = 1'b1; mode = 2'b11; parallel = 8'hA5;
        @(negedge clk);
        check8(data, 8'hA5, "parallel load 0xA5");

        // Hold
        mode = 2'b00;
        @(negedge clk);
        check8(data, 8'hA5, "hold keeps 0xA5");

        // Shift left with serial_in=1
        mode = 2'b01; serial_in = 1'b1;
        @(negedge clk);
        check8(data, 8'h4B, "shift left 0xA5 with 1 => 0x4B");

        // Shift left with serial_in=0
        serial_in = 1'b0;
        @(negedge clk);
        check8(data, 8'h96, "shift left 0x4B with 0 => 0x96");

        // Reload and shift right
        mode = 2'b11; parallel = 8'hC3;
        @(negedge clk);
        check8(data, 8'hC3, "reload 0xC3");

        mode = 2'b10; serial_in = 1'b1;
        @(negedge clk);
        check8(data, 8'hE1, "shift right 0xC3 with 1 => 0xE1");

        serial_in = 1'b0;
        @(negedge clk);
        check8(data, 8'h70, "shift right 0xE1 with 0 => 0x70");

        // Reset mid-operation
        rst_n = 1'b0;
        @(negedge clk);
        check8(data, 8'h00, "reset clears again");

        if (errors == 0) $display("TEST PASSED");
        else             $display("TEST FAILED with %0d error(s)", errors);
        $finish;
    end

endmodule

`default_nettype wire
