# Synthesis Design Constraints for riscv_alu
# Target: sky130hd, 100 MHz (10 ns clock period)

# ── Clock definition ─────────────────────────────────────────────────────────
create_clock -name clk -period 10.000 [get_ports clk]

# ── Input / Output delays ─────────────────────────────────────────────────────
# Assume 20% of clock period for input arrival (after clock edge)
set_input_delay -clock clk -max 2.0 [get_ports {alu_op[*]}]
set_input_delay -clock clk -max 2.0 [get_ports {operand_a[*]}]
set_input_delay -clock clk -max 2.0 [get_ports {operand_b[*]}]
set_input_delay -clock clk -max 0.5 [get_ports rst_n]

# Assume 10% of clock period for output setup before capture
set_output_delay -clock clk -max 1.0 [get_ports {result[*]}]
set_output_delay -clock clk -max 0.5 [get_ports zero]
set_output_delay -clock clk -max 0.5 [get_ports overflow]

# ── False paths ───────────────────────────────────────────────────────────────
# Async reset is not a timing path
set_false_path -from [get_ports rst_n]

# ── Clock uncertainty ─────────────────────────────────────────────────────────
set_clock_uncertainty -setup 0.1 [get_clocks clk]
set_clock_uncertainty -hold  0.05 [get_clocks clk]

# ── Transition constraints ────────────────────────────────────────────────────
set_max_transition 0.5 [current_design]
