`default_nettype none
module sync_fifo #(parameter W=8, D=4)(input wire clk,reset_n,wr_en,rd_en,
 input wire [W-1:0] wr_data, output reg [W-1:0] rd_data, output wire full,empty);
 reg [W-1:0] mem[0:D-1]; reg [2:0] wr_ptr,rd_ptr; reg [2:0] count;
 assign full=(count==D); assign empty=(count==0);
 always @(posedge clk or negedge reset_n) begin
  if(!reset_n) begin wr_ptr<=0;rd_ptr<=0;count<=0;rd_data<=0;end
  else begin
   if(wr_en&&!full) begin mem[wr_ptr[1:0]]<=wr_data;wr_ptr<=wr_ptr_next;end
   if(rd_en&&!empty) begin rd_data<=mem[rd_ptr[1:0]];rd_ptr<=rd_ptr_next;end
   case({wr_en&&!full,rd_en&&!empty})
    2'b10:count<=count+1'b1; 2'b01:count<=count-1'b1; default:count<=count;
   endcase
  end
 end
 assign wr_ptr_next=wr_ptr+1'b1; assign rd_ptr_next=rd_ptr+1'b1;
endmodule
`default_nettype wire
