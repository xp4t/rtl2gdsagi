// An 8-bit bidirectional shift register with parallel load.
//
// Tests a slightly more complex sequential design: shift left, shift right,
// parallel load, and hold. One clock, active-low async reset.
`default_nettype none

module shift_reg (
    input  wire       i_clk,
    input  wire       i_rst_n,
    input  wire [1:0] i_mode,     // 00=hold, 01=shift left, 10=shift right, 11=load
    input  wire       i_serial_in,
    input  wire [7:0] i_parallel,
    output reg  [7:0] o_data,
    output wire       o_serial_out
);

    assign o_serial_out = o_data[7];

    always @(posedge i_clk or negedge i_rst_n) begin
        if (!i_rst_n)
            o_data <= 8'h00;
        else begin
            case (i_mode)
                2'b00: o_data <= o_data;                          // hold
                2'b01: o_data <= {o_data[6:0], i_serial_in};     // shift left
                2'b10: o_data <= {i_serial_in, o_data[7:1]};     // shift right
                2'b11: o_data <= i_parallel;                      // parallel load
            endcase
        end
    end

endmodule

`default_nettype wire
