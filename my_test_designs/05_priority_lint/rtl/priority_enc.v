module priority_enc (
    input [3:0] in,
    output wire [1:0] out, // wire instead of reg for procedural assignment
    output reg valid
);
always @(*) begin
    valid = 1;
    if (in[3]) out = 3;
    else if (in[2]) out = 2;
    else if (in[1]) out = 1;
    else if (in[0]) out = 0;
    else begin out = 0; valid = 0; end
end
endmodule
