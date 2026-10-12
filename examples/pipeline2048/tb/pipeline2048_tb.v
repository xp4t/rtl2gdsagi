`timescale 1ns / 1ps
module pipeline2048_tb;
    reg clk = 0;
    reg reset = 1;
    reg serial_in = 0;
    wire serial_out;
    pipeline2048 dut (.*);
    reg [2047:0] expected = 0;
    integer i;
    always #5 clk = ~clk;

    initial begin
        repeat (2) @(negedge clk);
        reset = 0;
        for (i = 0; i < 2060; i = i + 1) begin
            serial_in = ((i * 17 + 5) % 11) < 5;
            @(posedge clk);
            expected = {expected[2046:0], serial_in};
            #1;
            if (serial_out !== expected[2047]) begin
                $display("FAILED cycle=%0d got=%b expected=%b", i, serial_out, expected[2047]);
                $fatal(1);
            end
            @(negedge clk);
        end
        $display("TEST PASSED: pipeline2048 2060 serial inputs");
        $finish;
    end
endmodule
