module tiny_cpu (
    input clk,
    input rst,
    input [15:0] instr,
    output reg [15:0] pc,
    output reg [15:0] out_data
);
reg [15:0] regs [0:7];
always @(posedge clk) begin
    if (rst) begin
        pc <= 0;
        out_data <= 0;
    end else begin
        pc <= pc + 1;
        regs[instr[2:0]] <= regs[instr[5:3]] + regs[instr[8:6]] * instr[15:12];
        out_data <= regs[instr[2:0]];
    end
end
endmodule
