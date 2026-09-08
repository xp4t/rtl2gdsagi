`timescale 1ns/1ps
`default_nettype none

module mux4to1_tb;

    reg        clk = 1'b0;
    reg        rst_n = 1'b0;
    reg  [7:0] a, b, c, d;
    reg  [1:0] sel;
    wire [7:0] out;
    integer    errors = 0;

    mux4to1 uut (
        .i_clk(clk), .i_rst_n(rst_n),
        .i_a(a), .i_b(b), .i_c(c), .i_d(d),
        .i_sel(sel), .o_out(out)
    );

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
        a = 8'd10; b = 8'd20; c = 8'd30; d = 8'd40;
        sel = 2'b00;

        // Hold reset for two cycles
        @(negedge clk); @(negedge clk);
        check(out, 8'h00, "reset clears output");

        // Release reset, select A
        rst_n = 1'b1; sel = 2'b00;
        @(negedge clk);
        check(out, 8'd10, "selects input A");

        // Select B
        sel = 2'b01;
        @(negedge clk);
        check(out, 8'd20, "selects input B");

        // Select C
        sel = 2'b10;
        @(negedge clk);
        check(out, 8'd30, "selects input C");

        // Select D
        sel = 2'b11;
        @(negedge clk);
        check(out, 8'd40, "selects input D");

        // Change data mid-select
        d = 8'd99;
        @(negedge clk);
        check(out, 8'd99, "tracks new data on D");

        // Reset again
        rst_n = 1'b0;
        @(negedge clk);
        check(out, 8'h00, "reset clears again");

        if (errors == 0) $display("TEST PASSED");
        else             $display("TEST FAILED with %0d error(s)", errors);
        $finish;
    end

endmodule

`default_nettype wire
