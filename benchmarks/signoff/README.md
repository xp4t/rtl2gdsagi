# Complete signoff validation

The current manuscript selects paired native runs in
`runs/padding_release_pair_a/` and `runs/padding_release_pair_b/` for register,
mux4to1, alu8, counter, shift_reg and fifo_buf, plus `runs/shift_scale_pair_a/`
and `runs/shift_scale_pair_b/` for shift1024. All selected runs complete 21 stages.
`rtl2gdsagi_paper/evidence/experiment_manifest.json` is the selection authority.
Earlier `signoff_final_v3` runs remain historical records.

Reproduce the suite from the repository root:

```sh
python3 scripts/run_signoff_benchmark.py --run-root runs/reproduce_signoff \
  --pdk-root /path/to/sky130A --eda-bin /path/to/eda/bin \
  --designs register mux4to1 alu8 counter shift_reg fifo_buf
```

The default ALU example uses the two-site placement padding verified by the
live repair. `alu8_unpadded.yaml` preserves the initial configuration for a
model-assisted reproduction; set ANTHROPIC_API_KEY in the environment, then
run the CLI with that config and `--repair-policy auto`. Never put a key in YAML.

`scripts/extract_signoff_metrics.py` validates candidate and gate evidence,
rehashes the final files, and exports the paper tables, plot, CSV and JSON.
