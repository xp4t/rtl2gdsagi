`default_nettype none
module counter16(input wire clk, reset_n, enable, load,
                 input wire [15:0] load_data, output reg [15:0] count);
  wire [15:0] count_next;
  always @(posedge clk or negedge reset_n) begin
    if (!reset_n) count <= 16'b0;
    else if (load) count <= load_data;
    else if (enable) count <= count_next;
  end
  assign count_next = count + 16'd1;
endmodule
`default_nettype wire
