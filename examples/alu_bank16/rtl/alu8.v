// A simple 8-bit ALU with registered output.
//
// Supports add, subtract, AND, OR, XOR, NOT, shift left, shift right.
// One clock, active-low async reset. Tests wider combinational logic
// with a registered output stage.
`default_nettype none

module alu8 (
    input  wire        i_clk,
    input  wire        i_rst_n,
    input  wire [7:0]  i_a,
    input  wire [7:0]  i_b,
    input  wire [2:0]  i_op,
    output reg  [7:0]  o_result,
    output reg         o_carry,
    output reg         o_zero
);

    reg [8:0] result_wide;

    always @(*) begin
        case (i_op)
            3'b000:  result_wide = {1'b0, i_a} + {1'b0, i_b};   // ADD
            3'b001:  result_wide = {1'b0, i_a} - {1'b0, i_b};   // SUB
            3'b010:  result_wide = {1'b0, i_a & i_b};            // AND
            3'b011:  result_wide = {1'b0, i_a | i_b};            // OR
            3'b100:  result_wide = {1'b0, i_a ^ i_b};            // XOR
            3'b101:  result_wide = {1'b0, ~i_a};                 // NOT A
            3'b110:  result_wide = {1'b0, i_a << 1};             // SHL
            3'b111:  result_wide = {1'b0, i_a >> 1};             // SHR
            default: result_wide = 9'h000;
        endcase
    end

    always @(posedge i_clk or negedge i_rst_n) begin
        if (!i_rst_n) begin
            o_result <= 8'h00;
            o_carry  <= 1'b0;
            o_zero   <= 1'b1;
        end else begin
            o_result <= result_wide[7:0];
            o_carry  <= result_wide[8];
            o_zero   <= (result_wide[7:0] == 8'h00);
        end
    end

endmodule

`default_nettype wire
