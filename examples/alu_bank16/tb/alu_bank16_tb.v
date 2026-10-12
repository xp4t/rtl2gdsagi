`timescale 1ns/1ps
module alu_bank16_tb;
 reg i_clk=0, i_rst_n=0;
 reg [127:0] i_a=0, i_b=0;
 reg [47:0] i_op=0;
 wire [127:0] o_result;
 wire [15:0] o_carry, o_zero;
 integer cycle,lane;
 reg [8:0] expected;
 reg [7:0] a,b;
 reg [2:0] op;
 alu_bank16 dut(.*);
 always #5 i_clk=~i_clk;
 function [8:0] result;
 input [7:0] a,b; input [2:0] op;
 begin case(op)
 0: result={1'b0,a}+{1'b0,b};
 1: result={1'b0,a}-{1'b0,b};
 2: result={1'b0,a&b};
 3: result={1'b0,a|b};
 4: result={1'b0,a^b};
 5: result={1'b0,~a};
 6: result={1'b0,a<<1};
 7: result={1'b0,a>>1};
 endcase end
 endfunction
 initial begin
 repeat(2) @(negedge i_clk);
 if(o_result!==0 || o_carry!==0 || o_zero!==16'hffff) begin
  $display("FAILED: reset"); $fatal(1);
 end
 i_rst_n=1;
 for(cycle=0;cycle<64;cycle=cycle+1) begin
  for(lane=0;lane<16;lane=lane+1) begin
   i_a[8*lane+:8]=$random; i_b[8*lane+:8]=$random;
   i_op[3*lane+:3]=(cycle+lane)%8;
  end
  @(posedge i_clk); #1;
  for(lane=0;lane<16;lane=lane+1) begin
   a=i_a[8*lane+:8]; b=i_b[8*lane+:8]; op=i_op[3*lane+:3]; expected=result(a,b,op);
   if(o_result[8*lane+:8]!==expected[7:0] || o_carry[lane]!==expected[8] || o_zero[lane] !== (expected[7:0]==0)) begin
    $display("FAILED: lane=%0d cycle=%0d",lane,cycle); $fatal(1);
   end
  end
  @(negedge i_clk);
 end
 $display("TEST PASSED: 1024 lane transactions and reset"); $finish;
 end
endmodule
