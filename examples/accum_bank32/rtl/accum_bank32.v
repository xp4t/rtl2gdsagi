module accum8(input wire clk, input wire rst_n, input wire enable,
 input wire [7:0] data, output reg [7:0] value);
 always @(posedge clk or negedge rst_n)
  if(!rst_n) value<=0; else if(enable) value<=value+data;
endmodule
module accum_bank32(input wire i_clk, input wire i_rst_n,
 input wire [31:0] i_enable, input wire [7:0] i_data,
 input wire [4:0] i_read, output wire [7:0] o_data);
 wire [255:0] values;
 genvar lane;
 generate for(lane=0;lane<32;lane=lane+1) begin: lanes
  accum8 u(.clk(i_clk),.rst_n(i_rst_n),.enable(i_enable[lane]),
    .data(i_data),.value(values[8*lane+:8]));
 end endgenerate
 assign o_data=values[8*i_read+:8];
endmodule
