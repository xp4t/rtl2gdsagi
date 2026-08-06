// RISC-V ALU Slice  —  Demo design for rtl2gdsagy
// Supports all RV32I ALU operations
// Top module: riscv_alu
`timescale 1ns/1ps

module riscv_alu (
    input  wire        clk,
    input  wire        rst_n,
    // ALU operation select (matches RISC-V funct3 + funct7[5])
    input  wire [3:0]  alu_op,
    // Operands
    input  wire [31:0] operand_a,
    input  wire [31:0] operand_b,
    // Outputs
    output reg  [31:0] result,
    output reg         zero,
    output reg         overflow
);

    // ALU operation encoding
    localparam ALU_ADD  = 4'b0000;
    localparam ALU_SUB  = 4'b0001;
    localparam ALU_AND  = 4'b0010;
    localparam ALU_OR   = 4'b0011;
    localparam ALU_XOR  = 4'b0100;
    localparam ALU_SLL  = 4'b0101;
    localparam ALU_SRL  = 4'b0110;
    localparam ALU_SRA  = 4'b0111;
    localparam ALU_SLT  = 4'b1000;
    localparam ALU_SLTU = 4'b1001;
    localparam ALU_LUI  = 4'b1010;
    localparam ALU_AUIPC= 4'b1011;

    wire signed [31:0] signed_a = $signed(operand_a);
    wire signed [31:0] signed_b = $signed(operand_b);

    wire [32:0] add_result = {1'b0, operand_a} + {1'b0, operand_b};
    wire [32:0] sub_result = {1'b0, operand_a} - {1'b0, operand_b};

    reg  [31:0] alu_result;
    reg         alu_overflow;

    always @(*) begin
        alu_overflow = 1'b0;
        case (alu_op)
            ALU_ADD:  begin
                alu_result   = add_result[31:0];
                // Signed overflow: same-sign operands produce opposite-sign result
                alu_overflow = (~operand_a[31] & ~operand_b[31] & alu_result[31]) |
                               ( operand_a[31] &  operand_b[31] & ~alu_result[31]);
            end
            ALU_SUB:  begin
                alu_result   = sub_result[31:0];
                alu_overflow = (~operand_a[31] &  operand_b[31] & alu_result[31]) |
                               ( operand_a[31] & ~operand_b[31] & ~alu_result[31]);
            end
            ALU_AND:  alu_result = operand_a & operand_b;
            ALU_OR:   alu_result = operand_a | operand_b;
            ALU_XOR:  alu_result = operand_a ^ operand_b;
            ALU_SLL:  alu_result = operand_a << operand_b[4:0];
            ALU_SRL:  alu_result = operand_a >> operand_b[4:0];
            ALU_SRA:  alu_result = $signed(operand_a) >>> operand_b[4:0];
            ALU_SLT:  alu_result = (signed_a < signed_b) ? 32'd1 : 32'd0;
            ALU_SLTU: alu_result = (operand_a < operand_b) ? 32'd1 : 32'd0;
            ALU_LUI:  alu_result = operand_b;           // pass B (upper imm)
            ALU_AUIPC:alu_result = operand_a + operand_b; // PC + upper imm
            default:  alu_result = 32'hDEAD_BEEF;
        endcase
    end

    // Registered outputs for clean timing closure
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            result   <= 32'h0;
            zero     <= 1'b0;
            overflow <= 1'b0;
        end else begin
            result   <= alu_result;
            zero     <= (alu_result == 32'h0);
            overflow <= alu_overflow;
        end
    end

endmodule
