# ARS internal review pass: EVIDENCE

Date: 14 October 2026. ARS-Codex 3.23.0, academic-paper Phase 6; peer_reviewer_agent.md field-general criteria.

criteria_binding_unavailable
calibration_status: NOT_CALIBRATED

Execution: one of three sequential internal review passes by the same Codex assistant in this writing session. Three initially requested worker contexts produced no completed reports and are not counted. This is author-side internal review, not independent external peer review, a blinded panel, or venue acceptance. No numerical score or ranking is assigned.

## Final revision identity

- `main.tex`: `83cd4ba381f8fbf74aec6ddaacde98c47c5c3357c9cc8021a0432bbe76370436`
- `supplement.tex`: `70973b40eef369a1e42523be13395f1043efb931035aef8594e6d35bb5871242`
- `main.pdf`: `38f73a8425abdc5d0dd7f5b7e3a87a296506ebbc931521a67d9d1e26eb29ec64`
- `supplement.pdf`: `f6445a6dfc48ce4b1fc39f5c0c9694bb18d844470ff0bc5eadeb3bdaf3a64e6a`

Scope: this clarification revision and its retained evidence. Earlier full evaluations and citation audits keep their prior limitations. No new paid model calls, full RTL-to-GDS runs, or signoff certificates are attributed to this review. Public availability is a separate delivery gate.

## Pass 1: numerical evidence and source accounting

The complete current main and supplementary LaTeX sources were read. The native numerical/source audit passed. All 73 guardband CSV rows were compared with their JSON rows and last recorded post-CTS/routed native result events; log hashes match. The three gated slacks are finite when reached, and the comparison is inclusive at 0.05 ns using unrounded values. Missing checkpoints stay unavailable. Eligibility additionally requires an existing g=0 certification, so spacing padding 0 cannot pass through a timing-only calculation.

All eight diagnostic logs identify OpenROAD 41a51eaf4ca2171c92ff38afb91eb37bbd3f36da. The setup-enter/return markers occur in order; before/after values match parsed native output. All stored DEF/netlist snapshot hashes were independently rehashed. Before/after DEF equality and original final CTS equality corroborate the native no-op. Source/input/script/log identities match retained records.

Findings resolved: the user expectation that all seven primary designs clear 50 ps is incorrect. Both shift1024 repeats have routed hold 0.049477201514033384 ns, below 0.05 ns by 0.000522798485966616 ns; post-CTS hold is 0.06532552461647623 ns. Therefore 12/14 runs (six designs) qualify. Archived timing repair has setup 0.0015860646578364705 ns and fails the stronger threshold. The other separately reported certification counts are archived live 6/7, frozen replay 6/6, scripted baseline 5/5, and padding ablation 0/4.

The abstract leads with archived timing 11/14 confirmed failures, two unavailable target checks, one pass. It names the generation snapshot and marks the frozen 14/14 comparison source-confounded. It does not attribute all fourteen failures to the known CTS effect or count unavailable archived targets as failures. Body keeps the twelve setup plus one placement breakdown after excluding the CTS-affected pass. Historical 20 trace reconstructions and seven independent complete-IR matches stay distinct.

## Criterion-local assessment

| Criterion (ARS field-general rubric) | Assessment | Anchor and limit |
|---|---|---|
| Originality | NOT_ASSESSED | No renewed priority or exhaustive literature assessment; Ghose overlap is acknowledged. |
| Methodological rigor | MEETS | Main guardband paragraph; supplementary guardband and diagnostic sections distinguish computed eligibility, diagnostics and certificates. |
| Evidence sufficiency | MEETS | 73 raw-record comparisons; eight native trace/snapshot sets; precision retained before threshold comparison. |
| Argument coherence | MEETS | Archived-first abstract, frozen replay qualifier and source-specific table captions agree. |
| Writing quality | MEETS | Final threshold counts correct the user's premise and preserve unavailable outcomes. |

Verdict: **Accept within the requested clarification scope**. No unresolved numerical correction remains. This does not imply industrial signoff, statistical generalization, or publication acceptance. Full historical archive rehash and remote availability are separate delivery checks.
