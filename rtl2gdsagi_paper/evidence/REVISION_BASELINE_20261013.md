# Requested revision disposition

1. Main claims remain frozen-source contract, coverage, repeat levels and replay.
   Abstract and limitations distinguish the nine live episodes on 18d948815ac6
   and explicitly say live repair was not re-executed on frozen code.
   The verified-repair keyword is removed.
2. The bounded scripted sweep declares 24 configurations: spacing 3/4, PDN 1/2,
   fixed 3 ns timing 0/16, slower-clock controls 1/2 certify. No model calls occur.
   The study-only first-failure harness retains native gates and complete
   successful certification. The prior CLI pilot and failed bootstrap are
   retained and excluded, with their actual stopping/import reasons.
3. Replay has 20/20 trace consistency and seven independent full-IR comparisons,
   before adding the explicit worker field. No complete independent record for
   the other thirteen states was found in the inspected archive. Excluding the archived
   CTS-affected pass leaves twelve setup-STA failures and one placement failure.
4. The accumulator cohort is exploratory: 0/4 certify; two policy escalations,
   two credit interruptions with unknown eventual outcomes. The largest clean
   design remains the synthetic 1,024-stage shift register.
5. The zero slack guardband is defined separately from clock uncertainty and
   CTS optimization margins. No general model-benefit or robust-margin estimate
   is inferred from the timing observations.
6. Recent references are freshly checked. Official Nix/Bazel/SLSA comparisons,
   FlowFixer rechecking and newer AuDoPEDA manifest/proof overlap are included.
   Table 6 uses not designed for, limited to the audited checker interfaces.
7. The optional local-model study was not included. No second-model result is
   claimed. Current internal reviews and public delivery are separate gates.
