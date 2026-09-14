module decoder3to8 (
    input [2:0] in,
    input en,
    output reg [7:0] out
);
always @(*) begin
    if (en) begin
        out = 8'b1 << in // Missing semicolon
    end else begin
        out = 8'b0;
    end
end
endmodule
