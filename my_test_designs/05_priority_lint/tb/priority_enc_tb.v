module priority_enc_tb;
    reg [3:0] in;
    wire [1:0] out;
    wire valid;
    priority_enc uut (.in(in), .out(out), .valid(valid));
    initial begin
        in = 4'b1000; #10;
        in = 4'b0010; #10;
        $display("TEST PASSED"); $finish;
    end
endmodule
