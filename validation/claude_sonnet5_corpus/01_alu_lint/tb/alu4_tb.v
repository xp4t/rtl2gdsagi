`timescale 1ns/1ps
module alu4_tb;
  reg [3:0] a, b; reg [2:0] op; wire [3:0] y; wire carry; integer i;
  alu4 dut(.a(a), .b(b), .op(op), .y(y), .carry(carry));
  initial begin
    a=4'd9; b=4'd7;
    for (i=0; i<7; i=i+1) begin
      op=i[2:0]; #1;
      case (i)
        0: if ({carry,y} !== 5'd16) $fatal(1,"FAILED add");
        1: if (y !== 4'd2) $fatal(1,"FAILED sub");
        2: if (y !== 4'd1) $fatal(1,"FAILED and");
        3: if (y !== 4'd15) $fatal(1,"FAILED or");
        4: if (y !== 4'd14) $fatal(1,"FAILED xor");
        5: if (y !== 4'd2) $fatal(1,"FAILED shl");
        6: if (y !== 4'd4) $fatal(1,"FAILED shr");
      endcase
    end
    $display("TEST PASSED"); $finish;
  end
endmodule
