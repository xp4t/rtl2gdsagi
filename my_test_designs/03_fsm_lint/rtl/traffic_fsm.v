module traffic_fsm (
    input clk,
    input rst,
    output reg [1:0] state
);
reg [1:0] next_state;
always @(posedge clk) begin
    if (rst) state <= 0;
    else state <= next_st; // next_st instead of next_state
end
always @(*) begin
    next_state = state + 1;
end
endmodule
