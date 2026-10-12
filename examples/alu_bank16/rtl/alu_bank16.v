module alu_bank16(
 input wire i_clk, input wire i_rst_n,
 input wire [127:0] i_a, i_b,
 input wire [47:0] i_op,
 output wire [127:0] o_result,
 output wire [15:0] o_carry, o_zero);
 genvar lane;
 generate for (lane=0; lane<16; lane=lane+1) begin: lanes
  alu8 unit_alu(.i_clk(i_clk), .i_rst_n(i_rst_n),
   .i_a(i_a[8*lane+:8]), .i_b(i_b[8*lane+:8]), .i_op(i_op[3*lane+:3]),
   .o_result(o_result[8*lane+:8]), .o_carry(o_carry[lane]), .o_zero(o_zero[lane]));
 end endgenerate
endmodule
