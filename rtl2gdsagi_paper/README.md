# Springer LNCS manuscript and supplementary evidence

`main.tex` is the main report; `supplement.tex` retains the earlier
recorded live case study, exploratory scale observations, control counts,
replay reconstruction and the scripted baseline protocol.
Upload `rtl2gdsagi_overleaf.zip` to Overleaf and compile each with pdfLaTeX.
The ZIP includes only their required generated inputs/figure and the LNCS class.

## Current results and source accounting

The production implementation fingerprint is `af31b39f6782`, also current HEAD's
Python implementation. Fourteen fresh primary runs and twenty complete-state
proposal executions use this frozen snapshot. The recorded proposals originated
on `18d948815ac6`; those nine live episodes are a recorded case study.
Live repair was not re-executed on the frozen source.

- Seven designs pass the 21-stage local contract twice, with exact routed DEF,
  netlists, SPEF and date-normalized GDS in every pair. The main shift1024 uses
  one routing worker; the earlier eight-worker pair is retained as an ablation.
- The 24-state no-model sweep certifies padding 1/2/3 (3/4 spacing states)
  and restored PDN offset 2 (1/2 states). The fixed 3 ns timing grid is 0/16;
  best setup WNS is −0.000653699 ns. Period 3.25 ns fails; period 3.50 ns certifies,
  as a changed requirement rather than fixed-target repair.
- A post-hoc 50 ps guardband retains six of seven primary designs (12/14 runs).
  Both shift1024 repeats fail routed hold at 49.477 ps; the archived +1.586 ps
  setup repair also fails. Original certificates remain at g=0.
- Eight instrumented CTS scripts enter and return from setup repair with
  194.356–274.527 ps pre-repair setup slack, above the 50 ps target. No setup
  violation is present under the logged wire-load fallback; diagnostic final
  CTS DEF hashes match their original candidates.
- Six constructed fault classes are blocked in eighteen consistency executions.
- The archived replay failures are spacing 0/3, PDN 0/3, timing 11/14, with two
  unavailable timing target checks. Fresh frozen executions give spacing 0/3,
  PDN 0/3 and timing 14/14 failures (thirteen STA, one placement). The timing
  comparison is confounded by the CTS-padding source change, which reverses
  the archived pass.
- Eight controlled padding/thread runs identify CTS padding reapplication as
  the source of the narrow timing sign change; worker count has no timing effect
  within that ablation. The frozen code retains the physical spacing calls.
- All four exploratory accumulator cases remain visible: zero certifications,
  two policy escalations and two credit-interrupted cases with unknown outcome. They are not pooled into the
  original nine episodes or twenty-state replay.

`evidence/frozen_results.json`, `live_results.json` and `signoff_metrics.csv`
contain the full measured values. The pinned OpenLane invocation audit records
active paired controls, unsupported interface obligations and configuration
limits without treating an inactive engine as a comparative baseline.
`CITATION_BASELINE_AUDIT.md` freshly checks the recent papers and official
Nix/Bazel/SLSA sources. AuDoPEDA's forthcoming conference manuscript overlaps
in manifest checks; its unresolved future DOI is excluded from our bibliography.
`REPLAY_STRATIFIED_AUDIT.md` separates 20/20 log-consistent reconstruction from
seven independent archived full-IR comparisons. Excluding the CTS-affected
archived pass leaves twelve setup-STA failures and one placement failure.

## Regenerate and compile

From the repository root, with the retained native runs and recorded PDK:

```sh
python3 rtl2gdsagi_paper/generate_live_results.py
python3 scripts/compare_repeated_runs.py
python3 scripts/collect_frozen_results.py
python3 scripts/collect_scripted_baseline.py
python3 scripts/collect_guardband_sensitivity.py
python3 scripts/record_citation_continuity.py
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

`REVIEW_SENSITIVITY_EVIDENCE.md`, `REVIEW_SENSITIVITY_METHODS.md` and
`REVIEW_SENSITIVITY_PRESENTATION.md` are three sequential internal review passes in the same
Codex session, not independent external peer review. Initial worker attempts produced no completed
reports and are not counted. Prior numbered/follow-up
reviews retain their historical snapshots. Exact venue criteria were not supplied;
LNCS formatting does not imply publication acceptance.

The public artifact is
https://github.com/xp4t/rtl2gdsagi/releases/tag/rtl2gdsagi-paper-sensitivity-20261013.
Final source/input/PDF/report bindings and public asset verification are recorded
separately in `review_bindings.json` and `publication_receipt.json`.
