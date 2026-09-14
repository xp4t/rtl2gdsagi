module lfsr8 (
    input clk,
    input rst,
    output [7:0] out
);
reg [7:0] state;
wire feedback;
assign feedbak = state[7] ^ state[5] ^ state[4] ^ state[3]; // Typo
always @(posedge clk) begin
    if (rst) state <= 8'h01;
    else state <= {state[6:0], feedback};
end
assign out = state;
endmodule
