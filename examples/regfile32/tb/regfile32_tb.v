`timescale 1ns / 1ps
module regfile32_tb;
    reg clk = 0;
    reg write_enable = 0;
    reg [4:0] write_address = 0;
    reg [31:0] write_data = 0;
    reg [4:0] read_address = 0;
    wire [31:0] read_data;
    regfile32 dut (.*);

    always #5 clk = ~clk;

    integer i;
    reg [31:0] expected [0:31];
    initial begin
        for (i = 0; i < 32; i = i + 1) begin
            @(negedge clk);
            write_enable = 1;
            write_address = i;
            write_data = 32'h9e37_0000 ^ (i * 32'h0101_0101);
            expected[i] = write_data;
            @(negedge clk);
        end
        write_enable = 0;
        for (i = 0; i < 32; i = i + 1) begin
            read_address = i;
            @(posedge clk);
            #1;
            if (read_data !== expected[i]) begin
                $display("FAILED address=%0d got=%h expected=%h", i, read_data, expected[i]);
                $fatal(1);
            end
        end
        $display("TEST PASSED: regfile32 32 writes and 32 reads");
        $finish;
    end
endmodule
