# RTL2GDSAGI Springer manuscript and live evidence

The current manuscript is `main.tex`, using Springer's LNCS proceedings class.
Upload `rtl2gdsagi_overleaf.zip` to Overleaf, select `main.tex`, and use pdfLaTeX.
The ZIP contains all generated inputs, the plotted figure, and the LNCS class.
The manuscript's authors and affiliations are preserved from the supplied draft.

## Build

```sh
cd rtl2gdsagi_paper
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

## Experiment records

`evidence/experiment_manifest.json` selects the final paired baseline runs.
`evidence/live_results.json` and `signoff_metrics.csv` contain full-precision QoR,
constraints, physical parameters, native gate results and certification IDs.
`evidence/native_fault_injection.json` covers six author-constructed fault classes,
with three consistency executions per class. This is detection coverage, not
18 independent trials or a controlled external-flow performance comparison.
`evidence/external_fault_coverage.json` records separately executed actual
OpenLane checks and explicit unsupported obligations.
`evidence/repair_study.json` contains all nine declared repair episodes, all
accepted proposals and their native rechecks, plus the separate catalog of
retained earlier live API runs and transport failures. Episode and proposal
counts have different denominators. The model is Claude Sonnet 5 via Anthropic.
`evidence/reviewer_followup.json` adds six source-sensitive timing repetitions,
a one-worker shift1024 pair, four declared large live repair episodes, and
non-certifying implementation fingerprints. These outcomes are separate from
the original nine repair episodes.
`evidence/reproducibility_final.json` preserves complete paired hashes and
normalizes only GDS library/structure date payloads.
`evidence/pytest_followup_release.xml` records 955 passes, 15 skips, no failures.
`evidence/REVIEW_FOLLOWUP_EVIDENCE.md`, `REVIEW_FOLLOWUP_METHODS.md`, and
`REVIEW_FOLLOWUP_PRESENTATION.md` document three internal reviews of this revision.
They are separate review workers in the same automated writing workflow,
not independent external peer reviews. The numbered reviews retain the prior
version's findings. `evidence/REVIEW.md` records both review cohorts.

## Regenerate

With the retained native runs and exact PDK installation available:

```sh
python3 rtl2gdsagi_paper/generate_live_results.py
python3 scripts/compare_repeated_runs.py
python3 scripts/generate_extended_results.py
python3 scripts/generate_external_coverage.py
python3 scripts/collect_followup_results.py
cd rtl2gdsagi_paper
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
python3 evidence/manuscript_audit.py
```

Cached TeX inputs compile on Overleaf without EDA tools. The public experiment
archive provides portable file-hash verification through `verify_artifact.py`.
Raw run records retain the original absolute paths; native re-execution requires
the recorded tool versions, PDK revision and Python dependencies. Source snapshots
for the final implementation and earlier repair cohort are both included.

## Public artifact

Repository: https://github.com/xp4t/rtl2gdsagi

Paper and experiment release:
https://github.com/xp4t/rtl2gdsagi/releases/tag/rtl2gdsagi-paper-20261013

This is LNCS proceedings formatting. No exact Springer journal or conference
track was specified, so the reviews use disclosed generic academic criteria.
