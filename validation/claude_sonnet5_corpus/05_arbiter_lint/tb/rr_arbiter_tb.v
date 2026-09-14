`timescale 1ns/1ps
module rr_arbiter_tb;
 reg clk=0,reset_n=0;reg[3:0]req=0;wire[3:0]grant;rr_arbiter dut(.*);always #5 clk=~clk;
 initial begin #12;reset_n=1;req=4'b1111;#1;if(grant!==4'b0010)$fatal(1,"FAILED first");
  @(posedge clk);#1;if(grant!==4'b0100)$fatal(1,"FAILED second");
  @(posedge clk);#1;if(grant!==4'b1000)$fatal(1,"FAILED third");
  $display("TEST PASSED");$finish;end
endmodule
