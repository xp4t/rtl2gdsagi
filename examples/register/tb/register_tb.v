`timescale 1ns/1ps
`default_nettype none

module register_tb;

    reg        clk = 1'b0;
    reg        rst_n = 1'b0;
    reg  [7:0] data = 8'h00;
    wire [7:0] out;
    integer    errors = 0;

    register uut (.i_clk(clk), .i_rst_n(rst_n), .i_data(data), .o_data(out));

    always #5 clk = ~clk;

    task check(input [7:0] got, input [7:0] want, input [127:0] what);
        begin
            if (got !== want) begin
                $display("FAILED: %0s -- expected %0d, got %0d", what, want, got);
                errors = errors + 1;
            end
        end
    endtask

    initial begin
        @(negedge clk); rst_n = 1'b0;
        @(negedge clk); check(out, 8'h00, "reset clears the output");

        rst_n = 1'b1; data = 8'd10;
        @(negedge clk); check(out, 8'd11, "increments its input");

        data = 8'd200;
        @(negedge clk); check(out, 8'd201, "tracks a new input");

        data = 8'hFF;
        @(negedge clk); check(out, 8'h00, "wraps around at 255");

        rst_n = 1'b0;
        @(negedge clk); check(out, 8'h00, "reset clears it again");

        if (errors == 0) $display("TEST PASSED");
        else             $display("TEST FAILED with %0d error(s)", errors);
        $finish;
    end

endmodule

`default_nettype wire
