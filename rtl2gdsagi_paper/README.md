# Springer LNCS manuscript and supplementary evidence

`main.tex` is the main report; `supplement.tex` retains the earlier
live episodes, scale observations, control counts and replay reconstruction.
Upload `rtl2gdsagi_overleaf.zip` to Overleaf and compile each with pdfLaTeX.
The ZIP includes only their required generated inputs/figure and the LNCS class.

## Current results and source accounting

The production implementation fingerprint is `af31b39f6782`, also current HEAD's
Python implementation. Fourteen fresh primary runs and twenty complete-state
proposal executions use this frozen snapshot. The recorded proposals originated
on `18d948815ac6`; their original observations remain separate.

- Seven designs pass the 21-stage local contract twice, with exact routed DEF,
  netlists, SPEF and date-normalized GDS in every pair. The main shift1024 uses
  one routing worker; the earlier eight-worker pair is retained as an ablation.
- Six constructed fault classes are blocked in eighteen consistency executions.
- The archived replay failures are spacing 0/3, PDN 0/3, timing 11/14, with two
  unavailable timing target checks. Fresh frozen executions give spacing 0/3,
  PDN 0/3 and timing 14/14 failures (thirteen STA, one placement).
- Eight controlled padding/thread runs identify CTS padding reapplication as
  the source of the narrow timing sign change; worker count has no timing effect
  within that ablation. The frozen code retains the physical spacing calls.
- All four earlier accumulator cases remain in the supplement: zero certifications,
  two controller stops and two incomplete outcomes. They are not pooled into the
  original nine episodes or twenty-state replay.

`evidence/frozen_results.json`, `live_results.json` and `signoff_metrics.csv`
contain the full measured values. The pinned OpenLane invocation audit records
active paired controls, unsupported interface obligations and configuration
limits without treating an inactive engine as a comparative baseline.
`CITATION_AUDIT_FROZEN.md` checks all thirteen references and their resolution.

## Regenerate and compile

From the repository root, with the retained native runs and recorded PDK:

```sh
python3 rtl2gdsagi_paper/generate_live_results.py
python3 scripts/compare_repeated_runs.py
python3 scripts/collect_frozen_results.py
latexmk -cd -pdf -interaction=nonstopmode -halt-on-error rtl2gdsagi_paper/main.tex
latexmk -cd -pdf -interaction=nonstopmode -halt-on-error rtl2gdsagi_paper/supplement.tex
pdftotext -layout rtl2gdsagi_paper/main.pdf rtl2gdsagi_paper/evidence/manuscript.txt
pdftotext -layout rtl2gdsagi_paper/supplement.pdf rtl2gdsagi_paper/evidence/supplement.txt
python3 rtl2gdsagi_paper/evidence/manuscript_audit.py
```

The experiment drivers refuse to overwrite their cohorts. The reconstruction
pilot is retained separately; its omitted curated PDN updates make three states
invalid for replay, so the final cohort was reconstructed and declared afresh.
The frozen source archive includes non-Python resources. Native re-execution
requires the recorded tools, PDK and dependencies; original absolute paths remain
in raw records. Portable archive verification needs only Python.

## Reviews and public artifact

`REVIEW_FROZEN_EVIDENCE.md`, `REVIEW_FROZEN_METHODS.md` and
`REVIEW_FROZEN_PRESENTATION.md` are three internal review contexts in the same
writing workflow, not independent external peer review. Prior numbered/follow-up
reviews retain their historical snapshots. Exact venue criteria were not supplied;
LNCS formatting does not imply publication acceptance.

The public artifact is
https://github.com/xp4t/rtl2gdsagi/releases/tag/rtl2gdsagi-paper-frozen-20261013.
Final source/input/PDF/report bindings and public asset verification are recorded
separately in `review_bindings.json` and `publication_receipt.json`.
