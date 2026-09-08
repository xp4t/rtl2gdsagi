`timescale 1ns/1ps
`default_nettype none

module toggle_ff_tb;

    reg        clk = 1'b0;
    reg        rst_n = 1'b0;
    reg        toggle;
    wire [3:0] count;
    integer    errors = 0;

    toggle_ff uut (
        .i_clk(clk), .i_rst_n(rst_n),
        .i_toggle(toggle), .o_count(count)
    );

    always #5 clk = ~clk;

    task check(input [3:0] got, input [3:0] want, input [255:0] what);
        begin
            if (got !== want) begin
                $display("FAILED: %0s -- expected %0d, got %0d", what, want, got);
                errors = errors + 1;
            end
        end
    endtask

    initial begin
        toggle = 1'b0;

        @(negedge clk); @(negedge clk);
        check(count, 4'h0, "reset clears count");

        rst_n = 1'b1; toggle = 1'b1;
        @(negedge clk);
        check(count, 4'h1, "first toggle increments");

        @(negedge clk);
        check(count, 4'h2, "second toggle increments");

        toggle = 1'b0;
        @(negedge clk);
        check(count, 4'h2, "hold when toggle=0");

        toggle = 1'b1;
        repeat(13) @(negedge clk);
        check(count, 4'hF, "count reaches 15");

        @(negedge clk);
        check(count, 4'h0, "count wraps to 0");

        if (errors == 0) $display("TEST PASSED");
        else             $display("TEST FAILED with %0d error(s)", errors);
        $finish;
    end

endmodule

`default_nettype wire
