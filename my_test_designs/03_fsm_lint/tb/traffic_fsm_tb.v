module traffic_fsm_tb;
    reg clk, rst;
    wire [1:0] state;
    traffic_fsm uut (.clk(clk), .rst(rst), .state(state));
    initial begin clk=0; forever #5 clk=~clk; end
    initial begin
        rst=1; #15 rst=0;
        #50 $display("TEST PASSED"); $finish;
    end
endmodule
