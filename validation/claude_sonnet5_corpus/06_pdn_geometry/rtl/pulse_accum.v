module pulse_accum(input wire clk,reset_n,pulse,clear,output reg[7:0]count,output wire active);
 assign active=|count;
 always @(posedge clk or negedge reset_n)
  if(!reset_n)count<=0;else if(clear)count<=0;else if(pulse)count<=count+1'b1;
endmodule
