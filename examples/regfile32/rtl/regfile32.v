`timescale 1ns / 1ps

// 32 x 32, one synchronous write port and one registered read port.
module regfile32 (
    input  wire        clk,
    input  wire        write_enable,
    input  wire [4:0]  write_address,
    input  wire [31:0] write_data,
    input  wire [4:0]  read_address,
    output reg  [31:0] read_data
);
    reg [31:0] storage [0:31];

    always @(posedge clk) begin
        if (write_enable)
            storage[write_address] <= write_data;
        read_data <= storage[read_address];
    end
endmodule
