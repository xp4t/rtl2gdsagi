module mul32_tb;
  reg [31:0] a, b;
  wire [63:0] p;
  reg [63:0] expected;
  integer i;
  mul32 dut(.a(a), .b(b), .p(p));
  initial begin
    a=0; b=0; #1;
    if (p !== 0) begin $display("FAILED: zero product mismatch"); $fatal(1); end
    for (i=0; i<256; i=i+1) begin
      a = $random; b = $random; expected = a * b; #1;
      if (p !== expected) begin $display("FAILED: product mismatch at %0d", i); $fatal(1); end
    end
    $display("TEST PASSED: 257 multiplier vectors");
    $finish;
  end
endmodule
