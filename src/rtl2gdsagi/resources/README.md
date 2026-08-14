# Vendored resources

`formal_pdk_proc.py` — preprocessor turning the SkyWater PDK's behavioural cell
models into formal-friendly Verilog.

Copyright (C) 2023 Jannis Harder, ISC licence (see the file header). Taken from
the `eqy` project's `examples/spm`.

Vendored rather than referenced so LEC does not depend on where an `eqy` source
checkout happens to live. It exists because the PDK's `primitives.v` uses
Verilog UDPs (`primitive ... endprimitive`), which Yosys cannot parse — that is
precisely what blocks a naive RTL-vs-netlist equivalence check on SKY130.
