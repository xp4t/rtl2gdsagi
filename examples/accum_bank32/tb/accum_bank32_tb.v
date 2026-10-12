`timescale 1ns/1ps
module accum_bank32_tb;
 reg i_clk=0,i_rst_n=0;
 reg [31:0] i_enable=0;
 reg [7:0] i_data=0;
 reg [4:0] i_read=0;
 wire [7:0] o_data;
 reg [7:0] expected[0:31];
 integer cycle,lane;
 accum_bank32 dut(.*);
 always #5 i_clk=~i_clk;
 initial begin
 for(lane=0;lane<32;lane=lane+1) expected[lane]=0;
 repeat(2) @(negedge i_clk);
 for(lane=0;lane<32;lane=lane+1) begin
  i_read=lane; #0.1;
  if(o_data!==0) begin $display("FAILED: reset lane %0d",lane);$fatal(1);end
 end
 i_rst_n=1;
 for(cycle=0;cycle<64;cycle=cycle+1) begin
  i_enable=$random; i_data=$random;
  @(posedge i_clk);
  for(lane=0;lane<32;lane=lane+1)
   if(i_enable[lane]) expected[lane]=expected[lane]+i_data;
  #1;
  for(lane=0;lane<32;lane=lane+1) begin
   i_read=lane; #0.1;
   if(o_data!==expected[lane]) begin
    $display("FAILED: cycle=%0d lane=%0d",cycle,lane);$fatal(1);
   end
  end
  @(negedge i_clk);
 end
 $display("TEST PASSED: reset and 2048 accumulator observations");$finish;
 end
endmodule
