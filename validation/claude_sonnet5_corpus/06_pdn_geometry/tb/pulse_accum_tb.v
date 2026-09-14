`timescale 1ns/1ps
module pulse_accum_tb;
 reg clk=0,reset_n=0,pulse=0,clear=0;wire[7:0]count;wire active;pulse_accum dut(.*);always #5 clk=~clk;
 initial begin #12;reset_n=1;pulse=1;repeat(5)@(posedge clk);#1;pulse=0;
  if(count!==5||!active)$fatal(1,"FAILED accumulate");clear=1;@(posedge clk);#1;
  if(count!==0||active)$fatal(1,"FAILED clear");$display("TEST PASSED");$finish;end
endmodule
