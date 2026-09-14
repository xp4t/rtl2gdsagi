module rr_arbiter(input wire clk,reset_n,input wire[3:0]req,output reg[3:0]grant);
 reg[1:0]last;
 always @* begin
  grant=4'b0;
  case(last)
   0:if(req[1])grant[1]=1;else if(req[2])grant[2]=1;else if(req[3])grant[3]=1;else if(req[0])grant[0]=1;
   1:if(req[2])grant[2]=1;else if(req[3])grant[3]=1;else if(req[0])grant[0]=1;else if(req[1])grant[1]=1;
   2:if(req[3])grant[3]=1;else if(req[0])grant[0]=1;else if(req[1])grant[1]=1;else if(req[2])grant[2]=1;
   default:if(req[0])grant[0]=1;else if(req[1])grant[1]=1;else if(req[2])grant[2]=1;else if(req[3])grant[3]=1;
  endcase
 end
 always @(posedge clk or negedge reset_n) begin
  if(!reset_n)last<=0;
  else if(grant[0])last<=0;else if(grant[1])last<=1;else if(grant[2])last<=2;else if(grant[3])last<=3;
 end
endmodule
