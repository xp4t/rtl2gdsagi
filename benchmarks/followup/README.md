# Reviewer follow-up experiments

`run_followup_experiments.py` registers twelve executions before launching them:

- Three fresh RTL-through-signoff runs of the repaired 3 ns ALU configuration using the archived original repair source.
- Three executions of that identical configuration using the current controller.
- Two shift1024 executions with one routing worker, with other typed settings preserved.
- Two live model-assisted accumulator spacing cases and two live antenna cases, retaining every outcome and provider error.

These are separate from the original nine-episode repair cohort. Native failures in the current-source ALU arm are retained, rather than treated as source-equivalent repeats of the archived result. The source archive's non-Python resources are checked against the original Git base before execution.

From an interactive shell with a configured Anthropic key:

```sh
source ~/.bashrc
/path/to/eda-venv/bin/python3 scripts/run_followup_experiments.py
```

The command refuses to overwrite an existing cohort. Exact commands, code fingerprints, declared cases and final states are in `runs/reviewer_followup_20261013/experiment_manifest.json`. Live cases use Claude Sonnet 5 from Anthropic and the declared three-attempt stage policy. The full denominator is preserved regardless of success or escalation.

`collect_followup_results.py` revalidates completed candidate/gate evidence, retains failed checks and generates supplemental tables and text. `implementation_identity.py` computes a non-certifying timestamp-neutral implementation fingerprint; raw release/gate identities retain exact hashes.
