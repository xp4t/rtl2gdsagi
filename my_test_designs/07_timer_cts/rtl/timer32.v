module timer32 (
    input clk,
    input rst,
    input en,
    output reg [31:0] count
);
always @(posedge clk) begin
    if (rst) count <= 0;
    else if (en) count <= count + 1;
end
endmodule
