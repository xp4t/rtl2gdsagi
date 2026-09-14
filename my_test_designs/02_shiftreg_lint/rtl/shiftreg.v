module shiftreg (
    input clk,
    input rst,
    input din,
    output dout
);
reg [7:0] q;
always @(posedge clk) begin
    if (rst) q <= 0;
    else q <= {q[6:0], d_in}; // d_in instead of din
end
assign dout = q[7];
endmodule
