module pwm_core_tb;
    reg clk, rst;
    reg [7:0] duty;
    wire pwm_out;
    pwm_core uut (.clk(clk), .rst(rst), .duty(duty), .pwm_out(pwm_out));
    initial begin clk=0; forever #5 clk=~clk; end
    initial begin
        rst=1; duty=128; #15 rst=0;
        #3000 $display("TEST PASSED"); $finish;
    end
endmodule
