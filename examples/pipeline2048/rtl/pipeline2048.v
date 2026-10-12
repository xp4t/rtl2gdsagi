`timescale 1ns / 1ps

// 2048-cycle serial delay pipeline. The state is intentionally exposed only
// through serial_out; this exercises sequential equivalence over a large bank.
module pipeline2048 (
    input  wire clk,
    input  wire reset,
    input  wire serial_in,
    output wire serial_out
);
    reg [2047:0] pipeline;
    always @(posedge clk or posedge reset) begin
        if (reset)
            pipeline <= 2048'b0;
        else
            pipeline <= {pipeline[2046:0], serial_in};
    end
    assign serial_out = pipeline[2047];
endmodule
