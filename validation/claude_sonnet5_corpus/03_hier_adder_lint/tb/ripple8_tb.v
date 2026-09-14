`timescale 1ns/1ps
module ripple8_tb;
 reg [7:0] a,b; reg cin; wire [7:0] sum; wire cout; integer i;
 ripple8 dut(.*);
 initial begin
   for(i=0;i<100;i=i+1) begin a=i*17; b=i*29; cin=i[0]; #1;
     if({cout,sum} !== ({1'b0,a}+{1'b0,b}+cin)) $fatal(1,"FAILED vector %0d",i);
   end
   $display("TEST PASSED"); $finish;
 end
endmodule
