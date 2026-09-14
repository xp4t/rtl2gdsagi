`timescale 1ns/1ps
module timer32_tb;
 reg clk=0,reset_n=0,enable=0;reg[31:0]limit=3;wire tick;wire[31:0]value;timer32 dut(.*);always #5 clk=~clk;
 initial begin #12;reset_n=1;enable=1;repeat(4)@(posedge clk);#1;
  if(!tick||value!==0)$fatal(1,"FAILED timer");@(posedge clk);#1;
  if(tick||value!==1)$fatal(1,"FAILED restart");$display("TEST PASSED");$finish;end
endmodule
