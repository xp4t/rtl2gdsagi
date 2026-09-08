// A simple toggle flip-flop — intentionally has a lint warning
// (width mismatch) to test if the self-healing can patch RTL.
`default_nettype none

module toggle_ff (
    input  wire       i_clk,
    input  wire       i_rst_n,
    input  wire       i_toggle,
    output reg  [3:0] o_count
);

    // BUG: using 5-bit literal for 4-bit register — width mismatch
    always @(posedge i_clk or negedge i_rst_n) begin
        if (!i_rst_n)
            o_count <= 4'h0;
        else if (i_toggle)
            o_count <= o_count + 5'd1;
        else
            o_count <= o_count;
    end

endmodule

`default_nettype wire
