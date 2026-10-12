module mul32(input wire [31:0] a, input wire [31:0] b, output wire [63:0] p);
  assign p = a * b;
endmodule
