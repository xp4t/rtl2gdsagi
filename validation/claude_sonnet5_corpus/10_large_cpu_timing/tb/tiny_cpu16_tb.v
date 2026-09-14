`timescale 1ns/1ps
module tiny_cpu16_tb;
 reg clk=0,reset_n=0,valid=0;reg[31:0]instruction=0;reg[2:0]debug_addr=0;
 wire[15:0]debug_data,pc;wire zero;tiny_cpu16 dut(.*);always #5 clk=~clk;
 task issue(input[3:0]op,input[2:0]rd,ra,src_b_addr,input[15:0]imm);begin
  instruction={op,rd,ra,src_b_addr,imm[15:13],imm[12:0],3'b0};valid=1;@(posedge clk);#1;valid=0;end endtask
 task check(input[2:0]addr,input[15:0]expected);begin debug_addr=addr;#1;
  if(debug_data!==expected)$fatal(1,"FAILED r%0d got %h",addr,debug_data);end endtask
 initial begin #12;reset_n=1;issue(0,1,0,0,16'd3);issue(0,2,0,0,16'd4);
  issue(1,3,1,2,0);check(3,7);issue(8,4,3,2,0);check(4,28);
  issue(5,5,4,1,0);check(5,31);if(pc!==10)$fatal(1,"FAILED pc");
  $display("TEST PASSED");$finish;end
endmodule
