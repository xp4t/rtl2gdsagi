module alu16(input wire[15:0]a,b,input wire[3:0]op,output reg[15:0]y,output reg zero);
 reg[15:0]product;
 always @* begin product=a*b;
  case(op)
   0:y=b;1:y=a+b;2:y=a-b;3:y=a&b;4:y=a|b;5:y=a^b;
   6:y=a<<b[3:0];7:y=a>>b[3:0];8:y=product[15:0];
   9:y={15'b0,($signed(a)<$signed(b))};default:y=0;
  endcase zero=(y==0);end
endmodule
