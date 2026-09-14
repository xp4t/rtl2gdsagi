module shiftreg_tb;
    reg clk, rst, din;
    wire dout;
    shiftreg uut (.clk(clk), .rst(rst), .din(din), .dout(dout));
    initial begin clk=0; forever #5 clk=~clk; end
    initial begin
        rst=1; din=0; #15 rst=0; din=1;
        #10 din=0;
        #100 $display("TEST PASSED"); $finish;
    end
endmodule
