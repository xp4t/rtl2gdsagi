`timescale 1ns/1ps
module sync_fifo_tb;
 reg clk=0,reset_n=0,wr_en=0,rd_en=0; reg[7:0]wr_data=0; wire[7:0]rd_data;wire full,empty;
 sync_fifo dut(.*); always #5 clk=~clk;
 task push(input[7:0]d);begin wr_data=d;wr_en=1;@(posedge clk);#1;wr_en=0;end endtask
 task popcheck(input[7:0]d);begin rd_en=1;@(posedge clk);#1;rd_en=0;if(rd_data!==d)$fatal(1,"FAILED fifo");end endtask
 initial begin #12;reset_n=1;push(8'h12);push(8'h34);popcheck(8'h12);popcheck(8'h34);
  if(!empty)$fatal(1,"FAILED empty");$display("TEST PASSED");$finish;end
endmodule
