`timescale 1ns/1ps
module shift_register_tb;
  reg clk = 0;
  reg reset = 0;
  reg serial_in = 0;
  wire [3:0] q;
  integer failures = 0;

  shift_register dut(.clk(clk), .reset(reset), .serial_in(serial_in), .q(q));
  always #5 clk = ~clk;

  task expect_q;
    input [3:0] expected;
    begin
      #1;
      if (q !== expected) begin
        $display("FAIL expected q=%b got q=%b at %0t", expected, q, $time);
        failures = failures + 1;
      end
    end
  endtask

  task shift_bit;
    input value;
    input [3:0] expected;
    begin
      serial_in = value;
      @(posedge clk);
      expect_q(expected);
    end
  endtask

  initial begin
    // The RTL declares an asynchronous active-high reset.
    #2 reset = 1;
    expect_q(4'b0000);
    #3 reset = 0;

    shift_bit(1'b1, 4'b0001);
    shift_bit(1'b0, 4'b0010);
    shift_bit(1'b1, 4'b0101);
    shift_bit(1'b1, 4'b1011);

    // q changes only on a positive edge when reset is inactive.
    serial_in = 0;
    @(negedge clk);
    expect_q(4'b1011);

    // Assert reset away from a clock edge to prove asynchronous behavior.
    #2 reset = 1;
    expect_q(4'b0000);
    reset = 0;

    if (failures == 0) $display("PASS shift_register inferred behavior");
    else $display("FAIL %0d check(s)", failures);
    $finish;
  end
endmodule
