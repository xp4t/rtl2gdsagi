module lfsr32(input wire clk,reset_n,enable,output reg[31:0]state);
 wire fb=state[31]^state[21]^state[1]^state[0];
 always @(posedge clk or negedge reset_n)
  if(!reset_n)state<=32'h1;else if(enable)state<={state[30:0],fb};
endmodule
