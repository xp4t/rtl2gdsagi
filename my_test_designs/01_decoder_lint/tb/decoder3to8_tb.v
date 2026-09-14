module decoder3to8_tb;
    reg [2:0] in;
    reg en;
    wire [7:0] out;
    decoder3to8 uut (.in(in), .en(en), .out(out));
    initial begin
        in = 0; en = 0;
        #10 en = 1;
        #10 if (out !== 8'b00000001) $fatal(1, "Fail");
        #10 in = 3;
        #10 if (out !== 8'b00001000) $fatal(1, "Fail");
        $display("TEST PASSED");
        $finish;
    end
endmodule
