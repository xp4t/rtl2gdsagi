module lfsr8_tb;
    reg clk, rst;
    wire [7:0] out;
    lfsr8 uut (.clk(clk), .rst(rst), .out(out));
    initial begin clk=0; forever #5 clk=~clk; end
    initial begin
        rst=1; #15 rst=0;
        #50 $display("TEST PASSED"); $finish;
    end
endmodule
