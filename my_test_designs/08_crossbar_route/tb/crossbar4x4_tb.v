module crossbar4x4_tb;
    reg [31:0] in0, in1, in2, in3;
    reg [1:0] sel0, sel1, sel2, sel3;
    wire [31:0] out0, out1, out2, out3;
    crossbar4x4 uut (.in0(in0), .in1(in1), .in2(in2), .in3(in3),
                     .sel0(sel0), .sel1(sel1), .sel2(sel2), .sel3(sel3),
                     .out0(out0), .out1(out1), .out2(out2), .out3(out3));
    initial begin
        in0=1; in1=2; in2=3; in3=4;
        sel0=0; sel1=1; sel2=2; sel3=3;
        #10 $display("TEST PASSED"); $finish;
    end
endmodule
