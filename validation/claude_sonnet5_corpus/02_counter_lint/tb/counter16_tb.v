`timescale 1ns/1ps
module counter16_tb;
  reg clk=0, reset_n=0, enable=0, load=0; reg [15:0] load_data=0; wire [15:0] count;
  counter16 dut(.*); always #5 clk=~clk;
  initial begin
    #12; reset_n=1; enable=1; repeat(3) @(posedge clk); #1;
    if(count!==16'd3) $fatal(1,"FAILED count");
    load=1; load_data=16'hfffe; @(posedge clk); #1; load=0;
    if(count!==16'hfffe) $fatal(1,"FAILED load");
    repeat(2) @(posedge clk); #1;
    if(count!==16'd0) $fatal(1,"FAILED wrap");
    $display("TEST PASSED"); $finish;
  end
endmodule
