// A small synchronous counter with a synchronous-load input.
//
// Deliberately boring: one clock, one active-low reset, no memories, no
// vendor primitives. If the flow works at all, it works on this.
`default_nettype none

module counter #(
    parameter WIDTH = 8
) (
    input  wire             i_clk,
    input  wire             i_rst_n,
    input  wire             i_enable,
    input  wire             i_load,
    input  wire [WIDTH-1:0] i_value,
    output reg  [WIDTH-1:0] o_count,
    output wire             o_overflow
);

    assign o_overflow = i_enable & (&o_count);

    always @(posedge i_clk or negedge i_rst_n) begin
        if (!i_rst_n)      o_count <= {WIDTH{1'b0}};
        else if (i_load)   o_count <= i_value;
        else if (i_enable) o_count <= o_count + 1'b1;
    end

endmodule

`default_nettype wire
