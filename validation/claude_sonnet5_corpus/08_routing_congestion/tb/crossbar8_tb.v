`timescale 1ns/1ps
module crossbar8_tb;
 reg[63:0]din;reg[23:0]sel;wire[63:0]dout;integer i;crossbar8 dut(.*);
 initial begin din=64'h7766554433221100;sel=0;for(i=0;i<8;i=i+1)sel[i*3+:3]=7-i;#1;
  if(dout!==64'h0011223344556677)$fatal(1,"FAILED reverse");
  for(i=0;i<8;i=i+1)sel[i*3+:3]=i;#1;
  if(dout!==din)$fatal(1,"FAILED identity");$display("TEST PASSED");$finish;end
endmodule
