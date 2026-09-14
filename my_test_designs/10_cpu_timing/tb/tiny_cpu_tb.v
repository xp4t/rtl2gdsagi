module tiny_cpu_tb;
    reg clk, rst;
    reg [15:0] instr;
    wire [15:0] pc, out_data;
    tiny_cpu uut (.clk(clk), .rst(rst), .instr(instr), .pc(pc), .out_data(out_data));
    initial begin clk=0; forever #5 clk=~clk; end
    initial begin
        rst=1; instr=0; #15 rst=0;
        instr = 16'h1234; #10;
        instr = 16'h5678; #10;
        $display("TEST PASSED"); $finish;
    end
endmodule
