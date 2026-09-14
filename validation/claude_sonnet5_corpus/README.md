# Claude Sonnet 5 RTL-to-GDS validation corpus

This isolated corpus contains ten synthesizable Verilog designs, ten
self-checking authoritative testbenches, intentionally failing inputs under
`rtl/`, and known-clean references under `golden/`. Existing rtl2gdsagi source,
examples, tests, PDK files, and shell startup files are not modified or read by
the corpus runner.

## Run

From the repository root:

```bash
python3 validation/claude_sonnet5_corpus/run_corpus.py preflight
python3 validation/claude_sonnet5_corpus/run_corpus.py dry-run --pdk-root /path/to/sky130A
python3 validation/claude_sonnet5_corpus/run_corpus.py live --pdk-root /path/to/sky130A
```

Select one or more cases with repeated `--case`. The driver pins
`claude-sonnet-5` internally:

```bash
python3 validation/claude_sonnet5_corpus/run_corpus.py live \
  --case 01_alu_lint --pdk-root /path/to/sky130A
```

Each `run.yaml` also pins `model: claude-sonnet-5` and `repair_policy: auto`.
No configuration contains an API key.

## Expected coverage

Cases 01-05 are deterministic mechanical RTL failures for
`PATCH_WORKING_RTL`: a missing semicolon, undeclared next-state signal, bad
named port, two undeclared FIFO pointer signals, and a procedural assignment to
a wire. Cases 06-10 exercise bounded physical/config repairs at PDN, CTS,
placement/routing, DRC, and timing. See `manifest.yaml` for the complete matrix.

The physical seeds are adversarial test conditions, not promises that every
tool/PDK version will fail at the identical line. The deterministic parser's
actual stage and evidence are authoritative.

## Validation performed on 2026-09-08

- 10/10 clean references passed strict Verilator `-Wall` lint.
- 10/10 clean references passed Yosys hierarchy, synthesis, and `check`.
- 10/10 clean references compiled with Icarus and printed `TEST PASSED`.
- Cases 01-05 failed Verilator for their intended injected defects.
- 10/10 configs completed rtl2gdsagi dry-run rendering against SKY130A.
- Live case 01 was attempted twice with the original fixed 2,048-token limit.
  Both calls spent the allowance on thinking and returned no JSON text.
- After `max_model_tokens` became configurable with an automatic 8,192-token
  minimum, Sonnet returned valid structured JSON using 2,839 output tokens.
  That run then correctly escalated a separate toolchain problem: the installed
  Verilator rejects the flow's unconditional `--timing` option before reading
  the RTL. The preserved runs are under `01_alu_lint/runs/`.

The model transport/token gate is therefore verified. Full repair and physical
signoff remain blocked on the independent Verilator option/version mismatch.
