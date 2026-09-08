`timescale 1ns/1ps
`default_nettype none

module alu8_tb;

    reg        clk = 1'b0;
    reg        rst_n = 1'b0;
    reg  [7:0] a, b;
    reg  [2:0] op;
    wire [7:0] result;
    wire       carry, zero;
    integer    errors = 0;

    alu8 uut (
        .i_clk(clk), .i_rst_n(rst_n),
        .i_a(a), .i_b(b), .i_op(op),
        .o_result(result), .o_carry(carry), .o_zero(zero)
    );

    always #5 clk = ~clk;

    task check(input [7:0] got_r, input got_c, input got_z,
               input [7:0] want_r, input want_c, input want_z,
               input [255:0] what);
        begin
            if (got_r !== want_r || got_c !== want_c || got_z !== want_z) begin
                $display("FAILED: %0s -- result=%0d(want %0d) carry=%0b(want %0b) zero=%0b(want %0b)",
                         what, got_r, want_r, got_c, want_c, got_z, want_z);
                errors = errors + 1;
            end
        end
    endtask

    initial begin
        a = 8'h00; b = 8'h00; op = 3'b000;

        // Reset
        @(negedge clk); @(negedge clk);
        check(result, carry, zero, 8'h00, 1'b0, 1'b1, "reset state");

        rst_n = 1'b1;

        // ADD: 100 + 50 = 150
        a = 8'd100; b = 8'd50; op = 3'b000;
        @(negedge clk);
        check(result, carry, zero, 8'd150, 1'b0, 1'b0, "ADD 100+50=150");

        // ADD with carry: 200 + 200 = 400 => 144 + carry
        a = 8'd200; b = 8'd200; op = 3'b000;
        @(negedge clk);
        check(result, carry, zero, 8'd144, 1'b1, 1'b0, "ADD 200+200 overflow");

        // SUB: 100 - 50 = 50
        a = 8'd100; b = 8'd50; op = 3'b001;
        @(negedge clk);
        check(result, carry, zero, 8'd50, 1'b0, 1'b0, "SUB 100-50=50");

        // SUB with zero: 42 - 42 = 0
        a = 8'd42; b = 8'd42; op = 3'b001;
        @(negedge clk);
        check(result, carry, zero, 8'd0, 1'b0, 1'b1, "SUB 42-42=0 zero");

        // AND: 0xF0 & 0x3C = 0x30
        a = 8'hF0; b = 8'h3C; op = 3'b010;
        @(negedge clk);
        check(result, carry, zero, 8'h30, 1'b0, 1'b0, "AND F0&3C=30");

        // OR: 0xF0 | 0x0F = 0xFF
        a = 8'hF0; b = 8'h0F; op = 3'b011;
        @(negedge clk);
        check(result, carry, zero, 8'hFF, 1'b0, 1'b0, "OR F0|0F=FF");

        // XOR: 0xAA ^ 0x55 = 0xFF
        a = 8'hAA; b = 8'h55; op = 3'b100;
        @(negedge clk);
        check(result, carry, zero, 8'hFF, 1'b0, 1'b0, "XOR AA^55=FF");

        // NOT: ~0xA5 = 0x5A
        a = 8'hA5; b = 8'h00; op = 3'b101;
        @(negedge clk);
        check(result, carry, zero, 8'h5A, 1'b0, 1'b0, "NOT A5=5A");

        // SHL: 0x81 << 1 = 0x02
        a = 8'h81; b = 8'h00; op = 3'b110;
        @(negedge clk);
        check(result, carry, zero, 8'h02, 1'b0, 1'b0, "SHL 81<<1=02");

        // SHR: 0x81 >> 1 = 0x40
        a = 8'h81; b = 8'h00; op = 3'b111;
        @(negedge clk);
        check(result, carry, zero, 8'h40, 1'b0, 1'b0, "SHR 81>>1=40");

        if (errors == 0) $display("TEST PASSED");
        else             $display("TEST FAILED with %0d error(s)", errors);
        $finish;
    end

endmodule

`default_nettype wire
