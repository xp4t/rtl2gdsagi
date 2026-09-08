// A 4-to-1 multiplexer — pure combinational, no clock, no reset.
// Tests file-type conversion on a simple combinational design.
`default_nettype none

module mux4to1 (
    input  wire       i_clk,
    input  wire       i_rst_n,
    input  wire [7:0] i_a,
    input  wire [7:0] i_b,
    input  wire [7:0] i_c,
    input  wire [7:0] i_d,
    input  wire [1:0] i_sel,
    output reg  [7:0] o_out
);

    always @(posedge i_clk or negedge i_rst_n) begin
        if (!i_rst_n)
            o_out <= 8'h00;
        else begin
            case (i_sel)
                2'b00:   o_out <= i_a;
                2'b01:   o_out <= i_b;
                2'b10:   o_out <= i_c;
                2'b11:   o_out <= i_d;
                default: o_out <= 8'hxx;
            endcase
        end
    end

endmodule

`default_nettype wire
