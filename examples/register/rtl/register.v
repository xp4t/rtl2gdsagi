// The smallest useful thing: an 8-bit register that increments its input.
//
// This is the "does my whole toolchain work?" design. One clock, one
// active-low asynchronous reset, no memories, no vendor primitives.
`default_nettype none

module register (
    input  wire       i_clk,
    input  wire       i_rst_n,
    input  wire [7:0] i_data,
    output reg  [7:0] o_data
);

    always @(posedge i_clk or negedge i_rst_n) begin
        if (!i_rst_n) o_data <= 8'h00;
        else          o_data <= i_data + 8'h01;
    end

endmodule

`default_nettype wire
