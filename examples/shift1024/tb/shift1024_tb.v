`timescale 1ns/1ps
module shift1024_tb;
  reg clk=0, rst_n=0, serial_in=0;
  wire serial_out;
  reg [1023:0] reference=0;
  integer i;
  shift1024 dut(clk,rst_n,serial_in,serial_out);
  always #5 clk=~clk;
  initial begin
    #2; rst_n=1; #1; rst_n=0; #1;
    if(serial_out !== 1'b0) begin $display("FAILED reset"); $fatal(1); end
    @(negedge clk); rst_n=1;
    for(i=0;i<4096;i=i+1) begin
      serial_in=((i*17 + (i>>3)) & 1);
      @(posedge clk); reference={reference[1022:0],serial_in}; #1;
      if(serial_out !== reference[1023]) begin
        $display("FAILED cycle %0d",i); $fatal(1);
      end
      @(negedge clk);
    end
    $display("TEST PASSED: 4096 cycles through 1024 stages"); $finish;
  end
endmodule
