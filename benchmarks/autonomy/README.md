# Autonomy benchmark: injected failures with known ground truth

Each `case_*.yaml` describes one deliberately broken configuration whose true
root cause is known *before* the run. The point is to measure whether the
runtime agent finds the cause we injected — not whether it finds *a* cause.

## Rules

1. **Ground truth is written first and never edited after seeing a response.**
   Each file records the injected defect, where the failure is expected to
   surface, the responsible stage, what must never be touched, and what counts
   as success. If a case turns out to be badly designed, delete it and say so;
   do not retune it to match what the model did.

2. **The defect is always schema-valid configuration.** Nothing here corrupts
   the RTL or the PDK. Every injection is a legal IR value that is simply a bad
   engineering choice, which is exactly the kind of failure a config-level
   agent is allowed to fix.

3. **`same_stage` vs `cross_stage` is the measurement that matters.** A routing
   failure fixed by changing routing knobs is useful. A routing failure whose
   real cause is the floorplan, diagnosed as floorplan, rolled back to
   floorplan and closed, is the claim worth making. They are reported
   separately.

4. **Escalation can be the correct answer.** A case whose `expected_outcome` is
   `escalate` is passed by refusing to act, not by attempting a fix.

## Running a case

```bash
.venv/bin/python benchmarks/autonomy/run_case.py benchmarks/autonomy/case_*.yaml
```

The harness writes `result.json` next to the run directory recording, for every
diagnosis: the evidence presented, the deterministic failure class, the model's
diagnosis and implicated stage, its confidence, the config delta, the safety
verdict, the rollback target actually used, and the resulting EDA metrics.

## Live model required

These cases measure the **runtime** agent reached through the production
diagnostic path (`--model`, `ANTHROPIC_API_KEY`). Running them with `--no-api`
exercises the deterministic machinery — parser, verdict, safety validator,
rollback, re-execution, re-verification — but the diagnosis is scripted, so the
result is **not** autonomy evidence and the harness labels it
`agent: scripted`.
