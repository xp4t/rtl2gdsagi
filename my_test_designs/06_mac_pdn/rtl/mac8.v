module mac8 (
    input clk,
    input rst,
    input [7:0] a,
    input [7:0] b,
    output reg [15:0] acc
);
always @(posedge clk) begin
    if (rst) acc <= 0;
    else acc <= acc + (a * b);
end
endmodule
