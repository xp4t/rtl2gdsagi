`timescale 1ns/1ps
`default_nettype none

module fifo_buf_tb;

    reg        clk = 1'b0;
    reg        rst_n = 1'b0;
    reg        wr_en, rd_en;
    reg  [7:0] data_in;
    wire [7:0] data_out;
    wire       full, empty;
    integer    errors = 0;

    fifo_buf uut (
        .i_clk(clk), .i_rst_n(rst_n),
        .i_wr_en(wr_en), .i_rd_en(rd_en),
        .i_data(data_in), .o_data(data_out),
        .o_full(full), .o_empty(empty)
    );

    always #5 clk = ~clk;

    task check_flags(input got_full, input want_full, input got_empty, input want_empty, input [255:0] what);
        begin
            if (got_full !== want_full || got_empty !== want_empty) begin
                $display("FAILED: %0s -- full=%0b(want %0b) empty=%0b(want %0b)",
                         what, got_full, want_full, got_empty, want_empty);
                errors = errors + 1;
            end
        end
    endtask

    initial begin
        wr_en = 1'b0; rd_en = 1'b0; data_in = 8'h00;

        @(negedge clk); @(negedge clk);
        check_flags(full, 1'b0, empty, 1'b1, "reset: empty, not full");

        rst_n = 1'b1;

        // Write 4 items
        wr_en = 1'b1;
        data_in = 8'hAA; @(negedge clk);
        data_in = 8'hBB; @(negedge clk);
        data_in = 8'hCC; @(negedge clk);
        data_in = 8'hDD; @(negedge clk);
        wr_en = 1'b0;

        check_flags(full, 1'b1, empty, 1'b0, "full after 4 writes");

        // Read all 4
        rd_en = 1'b1;
        @(negedge clk);
        if (data_out !== 8'hAA) begin
            $display("FAILED: first read -- expected 0xAA, got 0x%02h", data_out);
            errors = errors + 1;
        end
        @(negedge clk);
        @(negedge clk);
        @(negedge clk);
        rd_en = 1'b0;

        @(negedge clk);
        check_flags(full, 1'b0, empty, 1'b1, "empty after 4 reads");

        if (errors == 0) $display("TEST PASSED");
        else             $display("TEST FAILED with %0d error(s)", errors);
        $finish;
    end

endmodule

`default_nettype wire
