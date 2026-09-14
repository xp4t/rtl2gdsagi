module pwm_core (
    input clk,
    input rst,
    input [7:0] duty,
    output reg pwm_out
);
reg [7:0] counter;
always @(posedge clk) begin
    if (rst) begin
        counter <= 0;
        pwm_out <= 0;
    end else begin
        counter <= counter + 1;
        pwm_out <= (counter < duty);
    end
end
endmodule
