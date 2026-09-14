module crossbar4x4 (
    input [31:0] in0, in1, in2, in3,
    input [1:0] sel0, sel1, sel2, sel3,
    output reg [31:0] out0, out1, out2, out3
);
always @(*) begin
    out0 = (sel0==0)?in0:(sel0==1)?in1:(sel0==2)?in2:in3;
    out1 = (sel1==0)?in0:(sel1==1)?in1:(sel1==2)?in2:in3;
    out2 = (sel2==0)?in0:(sel2==1)?in1:(sel2==2)?in2:in3;
    out3 = (sel3==0)?in0:(sel3==1)?in1:(sel3==2)?in2:in3;
end
endmodule
