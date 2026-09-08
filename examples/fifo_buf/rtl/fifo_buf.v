// A small FIFO-like buffer — intentionally has a Verilator lint error:
// undeclared signal 'wr_ptr_next' used in the always block.
// The self-healing should patch the working RTL copy to declare it.
`default_nettype none

module fifo_buf (
    input  wire       i_clk,
    input  wire       i_rst_n,
    input  wire       i_wr_en,
    input  wire       i_rd_en,
    input  wire [7:0] i_data,
    output reg  [7:0] o_data,
    output wire       o_full,
    output wire       o_empty
);

    reg [7:0] mem [0:3];
    reg [1:0] wr_ptr;
    reg [1:0] rd_ptr;
    reg [2:0] count;

    assign o_full  = (count == 3'd4);
    assign o_empty = (count == 3'd0);

    // BUG: wr_ptr_next and rd_ptr_next are never declared
    assign wr_ptr_next = wr_ptr + 2'd1;
    assign rd_ptr_next = rd_ptr + 2'd1;

    always @(posedge i_clk or negedge i_rst_n) begin
        if (!i_rst_n) begin
            wr_ptr <= 2'd0;
            rd_ptr <= 2'd0;
            count  <= 3'd0;
            o_data <= 8'd0;
        end else begin
            if (i_wr_en && !o_full) begin
                mem[wr_ptr] <= i_data;
                wr_ptr <= wr_ptr_next;
                count <= count + 3'd1;
            end
            if (i_rd_en && !o_empty) begin
                o_data <= mem[rd_ptr];
                rd_ptr <= rd_ptr_next;
                count <= count - 3'd1;
            end
        end
    end

endmodule

`default_nettype wire
