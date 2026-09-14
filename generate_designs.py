import os
import shutil

base_dir = "/home/vlsi/Documents/rtl2gdsagi/my_test_designs"
os.makedirs(base_dir, exist_ok=True)

designs = [
    {
        "id": "01_decoder_lint",
        "top": "decoder3to8",
        "rtl": """module decoder3to8 (
    input [2:0] in,
    input en,
    output reg [7:0] out
);
always @(*) begin
    if (en) begin
        out = 8'b1 << in // Missing semicolon
    end else begin
        out = 8'b0;
    end
end
endmodule
""",
        "tb": """module decoder3to8_tb;
    reg [2:0] in;
    reg en;
    wire [7:0] out;
    decoder3to8 uut (.in(in), .en(en), .out(out));
    initial begin
        in = 0; en = 0;
        #10 en = 1;
        #10 if (out !== 8'b00000001) $fatal(1, "Fail");
        #10 in = 3;
        #10 if (out !== 8'b00001000) $fatal(1, "Fail");
        $display("TEST PASSED");
        $finish;
    end
endmodule
""",
        "ir": ""
    },
    {
        "id": "02_shiftreg_lint",
        "top": "shiftreg",
        "rtl": """module shiftreg (
    input clk,
    input rst,
    input din,
    output dout
);
reg [7:0] q;
always @(posedge clk) begin
    if (rst) q <= 0;
    else q <= {q[6:0], d_in}; // d_in instead of din
end
assign dout = q[7];
endmodule
""",
        "tb": """module shiftreg_tb;
    reg clk, rst, din;
    wire dout;
    shiftreg uut (.clk(clk), .rst(rst), .din(din), .dout(dout));
    initial begin clk=0; forever #5 clk=~clk; end
    initial begin
        rst=1; din=0; #15 rst=0; din=1;
        #10 din=0;
        #100 $display("TEST PASSED"); $finish;
    end
endmodule
""",
        "ir": ""
    },
    {
        "id": "03_fsm_lint",
        "top": "traffic_fsm",
        "rtl": """module traffic_fsm (
    input clk,
    input rst,
    output reg [1:0] state
);
reg [1:0] next_state;
always @(posedge clk) begin
    if (rst) state <= 0;
    else state <= next_st; // next_st instead of next_state
end
always @(*) begin
    next_state = state + 1;
end
endmodule
""",
        "tb": """module traffic_fsm_tb;
    reg clk, rst;
    wire [1:0] state;
    traffic_fsm uut (.clk(clk), .rst(rst), .state(state));
    initial begin clk=0; forever #5 clk=~clk; end
    initial begin
        rst=1; #15 rst=0;
        #50 $display("TEST PASSED"); $finish;
    end
endmodule
""",
        "ir": ""
    },
    {
        "id": "04_lfsr_lint",
        "top": "lfsr8",
        "rtl": """module lfsr8 (
    input clk,
    input rst,
    output [7:0] out
);
reg [7:0] state;
wire feedback;
assign feedbak = state[7] ^ state[5] ^ state[4] ^ state[3]; // Typo
always @(posedge clk) begin
    if (rst) state <= 8'h01;
    else state <= {state[6:0], feedback};
end
assign out = state;
endmodule
""",
        "tb": """module lfsr8_tb;
    reg clk, rst;
    wire [7:0] out;
    lfsr8 uut (.clk(clk), .rst(rst), .out(out));
    initial begin clk=0; forever #5 clk=~clk; end
    initial begin
        rst=1; #15 rst=0;
        #50 $display("TEST PASSED"); $finish;
    end
endmodule
""",
        "ir": ""
    },
    {
        "id": "05_priority_lint",
        "top": "priority_enc",
        "rtl": """module priority_enc (
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
""",
        "tb": """module priority_enc_tb;
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
""",
        "ir": ""
    },
    {
        "id": "06_mac_pdn",
        "top": "mac8",
        "rtl": """module mac8 (
    input clk,
    input rst,
    input [7:0] a,
    input [7:0] b,
    output reg [15:0] acc
);
always @(posedge clk) begin
    if (rst) acc <= 0;
    else acc <= acc + (a * b);
end
endmodule
""",
        "tb": """module mac8_tb;
    reg clk, rst;
    reg [7:0] a, b;
    wire [15:0] acc;
    mac8 uut (.clk(clk), .rst(rst), .a(a), .b(b), .acc(acc));
    initial begin clk=0; forever #5 clk=~clk; end
    initial begin
        rst=1; a=0; b=0; #15 rst=0; a=2; b=3;
        #10 a=4; b=5;
        #20 $display("TEST PASSED"); $finish;
    end
endmodule
""",
        "ir": """  floorplan: {core_utilization: 0.90}
  pdn: {strap_width_um: 30.0, strap_pitch_um: 150.0, strap_offset_um: 150.0, core_ring: true}"""
    },
    {
        "id": "07_timer_cts",
        "top": "timer32",
        "rtl": """module timer32 (
    input clk,
    input rst,
    input en,
    output reg [31:0] count
);
always @(posedge clk) begin
    if (rst) count <= 0;
    else if (en) count <= count + 1;
end
endmodule
""",
        "tb": """module timer32_tb;
    reg clk, rst, en;
    wire [31:0] count;
    timer32 uut (.clk(clk), .rst(rst), .en(en), .count(count));
    initial begin clk=0; forever #5 clk=~clk; end
    initial begin
        rst=1; en=0; #15 rst=0; en=1;
        #100 $display("TEST PASSED"); $finish;
    end
endmodule
""",
        "ir": """  cts: {root_buffer: "sky130_fd_sc_hd__clkbuf_99"}"""
    },
    {
        "id": "08_crossbar_route",
        "top": "crossbar4x4",
        "rtl": """module crossbar4x4 (
    input [31:0] in0, in1, in2, in3,
    input [1:0] sel0, sel1, sel2, sel3,
    output reg [31:0] out0, out1, out2, out3
);
always @(*) begin
    out0 = (sel0==0)?in0:(sel0==1)?in1:(sel0==2)?in2:in3;
    out1 = (sel1==0)?in0:(sel1==1)?in1:(sel1==2)?in2:in3;
    out2 = (sel2==0)?in0:(sel2==1)?in1:(sel2==2)?in2:in3;
    out3 = (sel3==0)?in0:(sel3==1)?in1:(sel3==2)?in2:in3;
end
endmodule
""",
        "tb": """module crossbar4x4_tb;
    reg [31:0] in0, in1, in2, in3;
    reg [1:0] sel0, sel1, sel2, sel3;
    wire [31:0] out0, out1, out2, out3;
    crossbar4x4 uut (.in0(in0), .in1(in1), .in2(in2), .in3(in3),
                     .sel0(sel0), .sel1(sel1), .sel2(sel2), .sel3(sel3),
                     .out0(out0), .out1(out1), .out2(out2), .out3(out3));
    initial begin
        in0=1; in1=2; in2=3; in3=4;
        sel0=0; sel1=1; sel2=2; sel3=3;
        #10 $display("TEST PASSED"); $finish;
    end
endmodule
""",
        "ir": """  floorplan: {core_utilization: 0.99}
  routing: {droute_iters: 2}"""
    },
    {
        "id": "09_pwm_drc",
        "top": "pwm_core",
        "rtl": """module pwm_core (
    input clk,
    input rst,
    input [7:0] duty,
    output reg pwm_out
);
reg [7:0] counter;
always @(posedge clk) begin
    if (rst) begin
        counter <= 0;
        pwm_out <= 0;
    end else begin
        counter <= counter + 1;
        pwm_out <= (counter < duty);
    end
end
endmodule
""",
        "tb": """module pwm_core_tb;
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
""",
        "ir": """  routing: {insert_filler: false}"""
    },
    {
        "id": "10_cpu_timing",
        "top": "tiny_cpu",
        "rtl": """module tiny_cpu (
    input clk,
    input rst,
    input [15:0] instr,
    output reg [15:0] pc,
    output reg [15:0] out_data
);
reg [15:0] regs [0:7];
always @(posedge clk) begin
    if (rst) begin
        pc <= 0;
        out_data <= 0;
    end else begin
        pc <= pc + 1;
        regs[instr[2:0]] <= regs[instr[5:3]] + regs[instr[8:6]] * instr[15:12];
        out_data <= regs[instr[2:0]];
    end
end
endmodule
""",
        "tb": """module tiny_cpu_tb;
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
""",
        "ir": """  sdc: {default_clock_period_ns: 0.1}
  floorplan: {core_utilization: 0.85}"""
    }
]

for d in designs:
    d_dir = os.path.join(base_dir, d['id'])
    
    # Clean old wrong tb files if exist
    for f in os.listdir(os.path.join(d_dir, "tb")):
        os.remove(os.path.join(d_dir, "tb", f))
        
    with open(os.path.join(d_dir, "rtl", d['top'] + ".v"), "w") as f:
        f.write(d['rtl'])
        
    with open(os.path.join(d_dir, "tb", d['top'] + "_tb.v"), "w") as f:
        f.write(d['tb'])
        
    yaml_content = f"""top: {d['top']}
rtl: my_test_designs/{d['id']}/rtl
model: claude-sonnet-5
repair_policy: auto
retry_limit: 4
run_root: my_test_designs/{d['id']}/runs
ir:
  sim: {{testbench_dir: my_test_designs/{d['id']}/tb}}
"""
    if d['ir']:
        yaml_content += d['ir'] + "\n"
        
    with open(os.path.join(d_dir, "run.yaml"), "w") as f:
        f.write(yaml_content)

print("Updated 10 designs in", base_dir)
