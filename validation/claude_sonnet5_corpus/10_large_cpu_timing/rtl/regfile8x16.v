module regfile8x16(input wire clk,reset_n,we,input wire[2:0]waddr,raddr_a,raddr_b,dbg_addr,
 input wire[15:0]wdata,output wire[15:0]rdata_a,rdata_b,dbg_data);
 reg[15:0]r[0:7];integer i;
 assign rdata_a=(raddr_a==0)?0:r[raddr_a];assign rdata_b=(raddr_b==0)?0:r[raddr_b];
 assign dbg_data=(dbg_addr==0)?0:r[dbg_addr];
 always @(posedge clk or negedge reset_n)begin
  if(!reset_n)for(i=0;i<8;i=i+1)r[i]<=0;else if(we&&waddr!=0)r[waddr]<=wdata;
 end
endmodule
