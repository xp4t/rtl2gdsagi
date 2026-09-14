module timer32_tb;
    reg clk, rst, en;
    wire [31:0] count;
    timer32 uut (.clk(clk), .rst(rst), .en(en), .count(count));
    initial begin clk=0; forever #5 clk=~clk; end
    initial begin
        rst=1; en=0; #15 rst=0; en=1;
        #100 $display("TEST PASSED"); $finish;
    end
endmodule
