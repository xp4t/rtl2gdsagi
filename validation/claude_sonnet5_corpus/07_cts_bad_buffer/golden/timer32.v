module timer32(input wire clk,reset_n,enable,input wire[31:0]limit,
 output reg tick,output reg[31:0]value);
 always @(posedge clk or negedge reset_n) begin
  if(!reset_n)begin value<=0;tick<=0;end else begin tick<=0;
   if(enable)if(value==limit)begin value<=0;tick<=1;end else value<=value+1'b1;
  end
 end
endmodule
