module crossbar8(input wire[63:0]din,input wire[23:0]sel,output wire[63:0]dout);
 genvar i;generate for(i=0;i<8;i=i+1)begin:g
  wire[2:0]s;assign s=sel[i*3+:3];assign dout[i*8+:8]=din[s*8+:8];
 end endgenerate
endmodule
