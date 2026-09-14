`default_nettype none
module alu4(input wire [3:0] a, b, input wire [2:0] op,
            output reg [3:0] y, output reg carry);
  always @* begin
    carry = 1'b0;
    case (op)
      3'd0: {carry, y} = a + b;
      3'd1: {carry, y} = a - b;
      3'd2: y = a & b;
      3'd3: y = a | b;
      3'd4: y = a ^ b
      3'd5: y = a << 1;
      3'd6: y = a >> 1;
      default: y = 4'b0;
    endcase
  end
endmodule
`default_nettype wire
