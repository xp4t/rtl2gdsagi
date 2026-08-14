// Self-checking testbench for counter.
//
// Self-checking matters: a testbench that runs without printing a verdict
// proves only that the design elaborates. This one states PASSED or FAILED.
`timescale 1ns/1ps
`default_nettype none

module counter_tb;

    localparam WIDTH = 8;

    reg              clk = 1'b0;
    reg              rst_n = 1'b0;
    reg              enable = 1'b0;
    reg              load = 1'b0;
    reg  [WIDTH-1:0] value = {WIDTH{1'b0}};
    wire [WIDTH-1:0] count;
    wire             overflow;

    integer errors = 0;

    counter #(.WIDTH(WIDTH)) uut (
        .i_clk      (clk),
        .i_rst_n    (rst_n),
        .i_enable   (enable),
        .i_load     (load),
        .i_value    (value),
        .o_count    (count),
        .o_overflow (overflow)
    );

    always #5 clk = ~clk;

    task check(input [WIDTH-1:0] got, input [WIDTH-1:0] want, input [127:0] what);
        begin
            if (got !== want) begin
                $display("FAILED: %0s -- expected %0d, got %0d", what, want, got);
                errors = errors + 1;
            end
        end
    endtask

    initial begin
        @(negedge clk); rst_n = 1'b0;
        @(negedge clk); rst_n = 1'b1;
        check(count, 8'd0, "reset clears the counter");

        enable = 1'b1;
        repeat (5) @(negedge clk);
        check(count, 8'd5, "counts up while enabled");

        enable = 1'b0;
        repeat (3) @(negedge clk);
        check(count, 8'd5, "holds its value while disabled");

        load = 1'b1; value = 8'd250;
        @(negedge clk);
        load = 1'b0;
        check(count, 8'd250, "loads a value");

        enable = 1'b1;
        repeat (5) @(negedge clk);
        check(count, 8'd255, "saturates at the top before wrapping");
        if (overflow !== 1'b1) begin
            $display("FAILED: overflow should be high at 255");
            errors = errors + 1;
        end

        @(negedge clk);
        check(count, 8'd0, "wraps to zero");

        if (errors == 0) $display("TEST PASSED");
        else             $display("TEST FAILED with %0d error(s)", errors);
        $finish;
    end

endmodule

`default_nettype wire
