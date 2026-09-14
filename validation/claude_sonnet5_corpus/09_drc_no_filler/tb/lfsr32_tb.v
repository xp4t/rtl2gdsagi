`timescale 1ns/1ps
module lfsr32_tb;
 reg clk=0,reset_n=0,enable=0;wire[31:0]state;lfsr32 dut(.*);always #5 clk=~clk;
 initial begin #12;reset_n=1;enable=1;@(posedge clk);#1;if(state!==32'h3)$fatal(1,"FAILED step1");
  @(posedge clk);#1;if(state!==32'h6)$fatal(1,"FAILED step2");
  repeat(30)@(posedge clk);#1;if(state===0)$fatal(1,"FAILED lockup");$display("TEST PASSED");$finish;end
endmodule
