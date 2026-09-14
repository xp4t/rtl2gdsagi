module tiny_cpu16(input wire clk,reset_n,valid,input wire[31:0]instruction,
 input wire[2:0]debug_addr,output wire[15:0]debug_data,output reg[15:0]pc,output wire zero);
 wire[3:0]op;wire[2:0]rd,rs1,rs2;wire[15:0]imm,a,src_b,b,result;
 assign op=instruction[31:28];assign rd=instruction[27:25];assign rs1=instruction[24:22];
 assign rs2=instruction[21:19];assign imm=instruction[18:3];assign b=(op==0)?imm:src_b;
 alu16 u_alu(.a(a),.b(b),.op(op),.y(result),.zero(zero));
 regfile8x16 u_rf(.clk(clk),.reset_n(reset_n),.we(valid),.waddr(rd),.raddr_a(rs1),
  .raddr_b(rs2),.dbg_addr(debug_addr),.wdata(result),.rdata_a(a),.rdata_b(src_b),.dbg_data(debug_data));
 always @(posedge clk or negedge reset_n)if(!reset_n)pc<=0;else if(valid)pc<=pc+16'd2+{13'b0,instruction[2:0]};
endmodule
