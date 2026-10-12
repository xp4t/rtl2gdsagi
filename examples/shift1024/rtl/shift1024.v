module shift1024(input wire clk, input wire rst_n, input wire serial_in,
                 output wire serial_out);
  reg [1023:0] state;
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) state <= 1024'b0;
    else state <= {state[1022:0], serial_in};
  end
  assign serial_out = state[1023];
endmodule
