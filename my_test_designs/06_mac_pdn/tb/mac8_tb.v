module mac8_tb;
    reg clk, rst;
    reg [7:0] a, b;
    wire [15:0] acc;
    mac8 uut (.clk(clk), .rst(rst), .a(a), .b(b), .acc(acc));
    initial begin clk=0; forever #5 clk=~clk; end
    initial begin
        rst=1; a=0; b=0; #15 rst=0; a=2; b=3;
        #10 a=4; b=5;
        #20 $display("TEST PASSED"); $finish;
    end
endmodule
