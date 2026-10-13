# Citation and build/provenance baseline audit

Freshly checked 13 October 2026. ARS academic-paper Phase 5a citation compliance, executed inline. Proposed corrections only.

## Scope and receipt

Five cited 2025–26 works and the explicitly requested 2024 ChiBench preprint were freshly verified. Nix, Bazel and SLSA official documentation was freshly inspected. The remaining seven manuscript references were not reverified in this run. The prior frozen audit supplied orientation only.

The inspected revised `main.tex` SHA-256 is `a99626997aa4a31d731a72eaf03676dc5bc322e5656b88279b71d0b66d049856` (425 lines; read 2026-10-13T10:29:53.081919+00:00). Its literal citation inventory contains 13 entries, 13 citation commands and 15 cited-key occurrences: no missing or uncited keys. Generated inputs were not expanded. Concurrent manuscript revisions are outside this audit; locators below bind to this hash.

The target is generic Springer LNCS numbered references. Exact venue acceptance criteria were not supplied (`criteria_binding_unavailable`). Publication remains pending and separately authorized; the planned tag is `rtl2gdsagi-paper-baselines-20261013`. The user's 24 scripted native states are in progress; their outcomes are not audited or asserted here. No model-provider API, independent external reviewer or communication to others was used. Public bibliographic HTTP requests are distinguished from model-provider calls.

## Three official references and exact proposed prose

These three proposed bibliography entries cover the claims below. Nix's single entry preserves the content-addressing, build and rebuild-check locators. All are official documentation, not evidence of this manuscript's measured results.

```latex
\bibitem{nixdocs}
Nix project: Nix 2.35.2 Reference Manual: Content-addressing derivation outputs; Building; nix-store --realise.
\url{https://nix.dev/manual/nix/2.35/store/derivation/outputs/content-address.html};
\url{https://nix.dev/manual/nix/2.35/store/building.html};
\url{https://nix.dev/manual/nix/2.35/command-ref/nix-store/realise.html}
(accessed 13 October 2026)

\bibitem{bazeldocs}
Bazel project: Remote Caching. Bazel documentation.
\url{https://bazel.build/remote/caching}
(accessed 13 October 2026)

\bibitem{slsadocs}
SLSA: Build: Provenance. SLSA specification, version 1.2 (Approved).
\url{https://slsa.dev/spec/v1.2/build-provenance}
(accessed 13 October 2026)
```

Proposed short paragraph; insert only through separately authorized manuscript editing:

```latex
Nix supports derivation-based builds, fixed and experimental floating content addressing, and rebuild checks; Bazel maps action hashes to cached results and stores outputs by content~\cite{nixdocs,bazeldocs}. SLSA build provenance binds artifact subjects to build definitions and builder identities~\cite{slsadocs}. RTL2GDSAGI applies these general mechanisms to a runtime release contract that binds native reports to selected GDS and deck bytes, invalidates affected cached evidence, and revalidates lineage and declared checker coverage.
```

Sentence 1 is supported by [nix_ca](https://nix.dev/manual/nix/2.35/store/derivation/outputs/content-address.html), [nix_build](https://nix.dev/manual/nix/2.35/store/building.html), [nix_rebuild](https://nix.dev/manual/nix/2.35/command-ref/nix-store/realise.html) and [bazel_cache](https://bazel.build/remote/caching). Sentence 2 follows [slsa_provenance](https://slsa.dev/spec/v1.2/build-provenance) and [in_toto_statement](https://raw.githubusercontent.com/in-toto/attestation/7aefca35a0f74a6e0cb397a8c4a76558f54de571/spec/v1/statement.md). Sentence 3 summarizes the local Evidence Contract and revised Related Work; it is not an external-source claim or a fresh implementation validation. Present this as a comparison of the evaluated integration, with no priority claim.

## Identity and narrow claim alignment

| Key | Cited identity | Result / current-version qualification |
|---|---|---|
| `orfsagent` | 2025; conference paper; 10.1109/MLCAD65511.2025.11189204 | verified cited conference identity; supported narrow parameter-tuning description. |
| `mcp4eda` | 2025; arXiv preprint; 2507.19570v1 | verified preprint v1; no later version or journal reference on inspected record; supported narrow backend-feedback description. |
| `flowfixer` | 2026; journal article; 10.1109/ACCESS.2026.3730896 | verified publisher-deposited identity; direct body inaccessible; supported by publisher-indexed abstract; full contract comparison unassessed. |
| `edaid` | 2025; conference paper; 10.18653/v1/2025.naacl-long.83 | verified ACL publisher and PDF identity; supported narrow multi-agent description. |
| `audopeda` | 2026; arXiv preprint; 2601.06268v2 | cited arXiv v2 verified; newer author conference version identified, publisher identity unresolved; supported executable changes/QoR description; avoid generic novelty about gates or manifests. |
| `chibench` | 2024; arXiv preprint; 2406.06550v1 | verified 2024 preprint v1; no newer version/journal reference on inspected record; supported tool-testing corpus claim; physical rule inventory completeness unestablished. |

### ORFS-agent

Manuscript citation line(s): 308; bibliography line 392. Current claim: “ORFS-agent optimizes OpenROAD-flow-scripts parameters.”

Verified identity: **ORFS-agent: Tool-Using Agents for Chip Design Optimization**. Amur Ghose; Andrew B. Kahng; Sayak Kundu; Zhiang Wang. 2025 ACM/IEEE 7th Symposium on Machine Learning for CAD (MLCAD), pp. 1–13 (2025). Primary receipts: [orfs_metadata](https://api.crossref.org/works/10.1109/MLCAD65511.2025.11189204), [orfs_2025_pdf](https://vlsicad.ucsd.edu/Publications/Conferences/417/c417.pdf), [orfs_publisher](https://ieeexplore.ieee.org/document/11189204/), [orfs_v2](https://arxiv.org/abs/2506.08332v2), [orfs_latest](https://arxiv.org/abs/2506.08332).

Normalize title case to ORFS-agent and venue to 2025 ACM/IEEE 7th Symposium on Machine Learning for CAD (MLCAD). Retain the 2025 conference DOI; current arXiv v3 (2026-04-30) changes backend/results details. Do not import v3 numbers into the 2025 attribution.

Suggested reference (proposal only): Ghose, A., Kahng, A.B., Kundu, S., Wang, Z.: ORFS-agent: Tool-Using Agents for Chip Design Optimization. In: 2025 ACM/IEEE 7th Symposium on Machine Learning for CAD (MLCAD), pp. 1–13 (2025). https://doi.org/10.1109/MLCAD65511.2025.11189204

### MCP4EDA

Manuscript citation line(s): 310; bibliography line 397. Current claim: “MCP4EDA connects model interaction to RTL-to-GDS execution and backend synthesis feedback.”

Verified identity: **MCP4EDA: LLM-Powered Model Context Protocol RTL-to-GDSII Automation with Backend Aware Synthesis Optimization**. Yiting Wang; Wanghao Ye; Yexiao He; Yiran Chen; Gang Qu; Ang Li. arXiv preprint (2025); 2507.19570v1. Primary receipts: [mcp_record](https://arxiv.org/abs/2507.19570), [mcp_body](https://arxiv.org/html/2507.19570v1).

Optionally pin v1 and add the arXiv-issued DOI. Avoid adopting its first-system priority claims or numerical improvements as independently established results.

Suggested reference (proposal only): Wang, Y., Ye, W., He, Y., Chen, Y., Qu, G., Li, A.: MCP4EDA: LLM-Powered Model Context Protocol RTL-to-GDSII Automation with Backend Aware Synthesis Optimization. arXiv:2507.19570v1 (2025). https://arxiv.org/abs/2507.19570v1. https://doi.org/10.48550/arXiv.2507.19570

### FlowFixer-EDA

Manuscript citation line(s): 311; bibliography line 402. Current claim: “FlowFixer-EDA uses log extraction, patch validation, and native tool feedback for diagnosis and repair.”

Verified identity: **FlowFixer-EDA: A Tool-Feedback-Augmented Large Language Model Agent for Automated Diagnosis and Repair of Open-Source RTL-to-GDS Design Flow Failures**. Ke Dong; Ruidong Wang; Fang Yuan; Baichun An; Xia Zhang. IEEE Access 14, pp. 140412–140428 (2026). Primary receipts: [flow_metadata](https://api.crossref.org/works/10.1109/ACCESS.2026.3730896), [flow_indexed](https://ieeexplore.ieee.org/abstract/document/11683937/), [flow_publisher](https://ieeexplore.ieee.org/document/11683937/).

Retain identity. The revised paragraph properly acknowledges existing rechecking. Actual tool reruns determine acceptance in the primary abstract; no claim that this work lacks candidate/deck/report/lineage checks follows from the limited read.

Suggested reference (proposal only): Dong, K., Wang, R., Yuan, F., An, B., Zhang, X.: FlowFixer-EDA: A Tool-Feedback-Augmented Large Language Model Agent for Automated Diagnosis and Repair of Open-Source RTL-to-GDS Design Flow Failures. IEEE Access 14, 140412–140428 (2026). https://doi.org/10.1109/ACCESS.2026.3730896

### EDAid

Manuscript citation line(s): 316; bibliography line 407. Current claim: “EDAid uses multiple model-controlled agents for EDA workflow execution.”

Verified identity: **Divergent Thoughts toward One Goal: LLM-based Multi-Agent Collaboration System for Electronic Design Automation**. Haoyuan Wu; Haisheng Zheng; Zhuolun He; Bei Yu. Proceedings of the 2025 Conference of the Nations of the Americas Chapter of the Association for Computational Linguistics: Human Language Technologies (Volume 1: Long Papers), pp. 1710–1721 (2025). Primary receipts: [edaid_record](https://aclanthology.org/2025.naacl-long.83/), [edaid_pdf](https://aclanthology.org/2025.naacl-long.83.pdf).

Replace abbreviated NAACL-HLT volume wording with the publisher's full proceedings title or a consistent short form identifying Volume 1: Long Papers. No certified runtime contract or superiority over this controller was established.

Suggested reference (proposal only): Wu, H., Zheng, H., He, Z., Yu, B.: Divergent Thoughts toward One Goal: LLM-based Multi-Agent Collaboration System for Electronic Design Automation. In: Proceedings of NAACL 2025: Human Language Technologies, Volume 1: Long Papers, pp. 1710–1721 (2025). https://doi.org/10.18653/v1/2025.naacl-long.83

### AuDoPEDA

Manuscript citation line(s): 318; bibliography line 412. Current claim: “Ghose et al. study executable OpenROAD changes and measured quality of results.”

Verified identity: **Automated QoR improvement in OpenROAD with coding agents**. Amur Ghose; Junyeong Jang; Andrew B. Kahng; Jakang Lee. arXiv preprint (2026); 2601.06268v2. Primary receipts: [audo_record](https://arxiv.org/abs/2601.06268v2), [audo_v2_body](https://arxiv.org/html/2601.06268v2), [audo_lab](https://vlsicad.ucsd.edu/Publications/Conferences/), [audo_current_pdf](https://vlsicad.ucsd.edu/Publications/Conferences/431/c431.pdf), [audo_future_doi](https://doi.org/10.1145/3831252.3834240), [audo_future_metadata](https://api.crossref.org/works/10.1145/3831252.3834240), [audo_future_publisher](https://dl.acm.org/doi/10.1145/3831252.3834240).

Retain pinned v2 for its claims. Separately note the newer ICCAD author version when discussing current overlap; it includes formal patch/proof manifests. Its printed DOI returned 404, so do not silently substitute a published proceedings citation.

Suggested reference (proposal only): Ghose, A., Jang, J., Kahng, A.B., Lee, J.: Automated QoR improvement in OpenROAD with coding agents. arXiv:2601.06268v2 (2026). https://arxiv.org/abs/2601.06268v2. https://doi.org/10.48550/arXiv.2601.06268

The author laboratory labels the newer version “to appear” at ICCAD 2026. Its linked PDF gives 8–12 November 2026, 9 pages and DOI `10.1145/3831252.3834240`. DOI resolution and Crossref both returned HTTP 404 on this audit date; the ACM page was inaccessible. This supports identifying an author conference manuscript, without asserting an available published publisher record.

Selected current-version passages describe a patch/snapshot/proof manifest and renewed proxy/signoff checks after changes. These are material overlap for any generic claim about manifests or revalidation. Their presence does not establish equivalence to this manuscript's selected-GDS/deck/native-report/cached-lineage contract; that broader comparison remains unassessed.

### ChiBench

Manuscript citation line(s): 320; bibliography line 416. Current claim: “ChiBench supplies RTL designs for EDA-tool testing.”

Verified identity: **ChiBench: a Benchmark Suite for Testing Electronic Design Automation Tools**. Rafael Sumitani; João Victor Amorim; Augusto Mafra; Mirlaine Crepalde; Fernando Magno Quintão Pereira. arXiv preprint (2024); 2406.06550v1. Primary receipts: [chi_record](https://arxiv.org/abs/2406.06550), [chi_body](https://arxiv.org/html/2406.06550v1).

Prefer curated Verilog corpus over RTL designs for precision. Keep 2024; the 2406 identifier does not override the record's May submission date. Revised singular DRVerify rationale fixes the earlier collective attribution risk.

Suggested reference (proposal only): Sumitani, R., Amorim, J.V., Mafra, A., Crepalde, M., Pereira, F.M.Q.: ChiBench: a Benchmark Suite for Testing Electronic Design Automation Tools. arXiv:2406.06550v1 (2024). https://arxiv.org/abs/2406.06550v1. https://doi.org/10.48550/arXiv.2406.06550

## Baseline claim boundaries

- **Nix (manual 2.35.2, URL series 2.35):** Derivation execution and deterministic build setup; fixed output hash checking; experimental floating content addressing; --check rebuild comparison. Content identity and successful build status require workflow-defined semantic checks for an EDA acceptance decision. Content addressing alone does not guarantee deterministic outputs. Sources: [nix_ca](https://nix.dev/manual/nix/2.35/store/derivation/outputs/content-address.html), [nix_experimental](https://nix.dev/manual/nix/2.35/development/experimental-features.html), [nix_build](https://nix.dev/manual/nix/2.35/store/building.html), [nix_rebuild](https://nix.dev/manual/nix/2.35/command-ref/nix-store/realise.html), [nix_cli](https://nix.dev/manual/nix/2.35/command-ref/nix-build.html).
- **Bazel (living official documentation; no release/date inferred):** Action hashes map to action-result metadata; CAS stores output content; inputs, output names, command line and environment belong to actions. Reuse depends on reproducibility and adequate declared inputs/trust. Native checker and report validation can be explicit build/test actions; no inability to support EDA checking is claimed. Sources: [bazel_cache](https://bazel.build/remote/caching).
- **SLSA (specification 1.2 Approved; build predicate v1; Statement v1):** Artifact subjects carry digests; buildDefinition and runDetails describe the build and builder; verification checks subject, signer/builder and policy expectations. Provenance can support domain-specific build types/checks. Schema conformance alone establishes neither native EDA correctness nor a SLSA level. Sources: [slsa_current](https://slsa.dev/spec/v1.2/), [slsa_provenance](https://slsa.dev/spec/v1.2/build-provenance), [slsa_verify](https://slsa.dev/spec/v1.2/verifying-artifacts), [in_toto_statement](https://raw.githubusercontent.com/in-toto/attestation/7aefca35a0f74a6e0cb397a8c4a76558f54de571/spec/v1/statement.md).

SLSA specification version 1.2 retains build predicate `https://slsa.dev/provenance/v1`, inside `https://in-toto.io/Statement/v1`; the predicate is not “v1.2.” Statement subjects require digests. Required Build L1 fields include `buildDefinition`, `runDetails`, `buildType`, `externalParameters`, `builder` and `builder.id`. Dependencies are best effort at least through L3; metadata and byproducts are optional. Its CUE/protobuf summaries are informative; normative descriptions govern. Artifact verification includes the subject digest, trusted signer/builder and expected build parameters. Sources: [slsa_provenance](https://slsa.dev/spec/v1.2/build-provenance), [slsa_verify](https://slsa.dev/spec/v1.2/verifying-artifacts), [in_toto_statement](https://raw.githubusercontent.com/in-toto/attestation/7aefca35a0f74a6e0cb397a8c4a76558f54de571/spec/v1/statement.md).

These general mechanisms can encode domain-specific checks through declared actions or build contracts. No intrinsic inability to support EDA validation is established. Byte reproducibility, provenance authenticity and native semantic/checker coverage are distinct obligations; the manuscript's local hash ledger does not by itself establish SLSA conformance or protection from a compromised host/tool/PDK.

## Reading and access ledger

All rows are fresh accesses on **13 October 2026**. Browser text does not supply a direct HTTP status; none is inferred. PDF locators below use the web tool's PDF page mapping, not a locally parsed PDF. Whole-source retrieval is not claimed as whole-body reading. No human-read attestation was supplied. Exact HTTP timestamps are in the JSON companion where captured.

- **orfs_metadata** — [primary source](https://api.crossref.org/works/10.1109/MLCAD65511.2025.11189204); authority: IEEE-deposited Crossref metadata. Access: HTTP 200 via urllib. Locator: message.title, author, published, container-title, page, DOI, resource.primary.URL. Read scope: bibliographic metadata. Full-body read: **no**.
- **orfs_publisher** — [primary source](https://ieeexplore.ieee.org/document/11189204/); authority: IEEE publisher. Access: JavaScript/robot challenge. Locator: document 11189204. Read scope: challenge page only; no article body. Full-body read: **no**.
- **orfs_2025_pdf** — [primary source](https://vlsicad.ucsd.edu/Publications/Conferences/417/c417.pdf); authority: author institution UC San Diego. Access: browser-extracted PDF text; 13 pages. Locator: PDF p.1 title/authors, Abstract, Introduction contributions; IEEE 2025 copyright footer. Read scope: selected passages on PDF p.1; remaining body and figures not systematically read. Full-body read: **no**.
- **orfs_v2** — [primary source](https://arxiv.org/abs/2506.08332v2); authority: arXiv author-submitted primary record. Access: readable browser text. Locator: Title, Authors, Abstract, Cite as, Submission history. Read scope: landing metadata and abstract. Full-body read: **no**.
- **orfs_latest** — [primary source](https://arxiv.org/abs/2506.08332); authority: arXiv author-submitted primary record. Access: readable browser text. Locator: Title, Authors, Abstract, Submission history. Read scope: landing metadata and abstract; latest v3 dated 2026-04-30. Full-body read: **no**.
- **mcp_record** — [primary source](https://arxiv.org/abs/2507.19570); authority: arXiv author-submitted primary record. Access: readable browser text. Locator: Title, Authors, Abstract, Cite as, Submission history. Read scope: landing metadata and abstract; only v1 listed. Full-body read: **no**.
- **mcp_body** — [primary source](https://arxiv.org/html/2507.19570v1); authority: arXiv author manuscript. Access: readable browser text. Locator: Introduction contributions; Figure 2 caption, three-phase optimization workflow. Read scope: selected introduction and workflow-caption passages; not complete body/figure inspection. Full-body read: **no**.
- **flow_metadata** — [primary source](https://api.crossref.org/works/10.1109/ACCESS.2026.3730896); authority: IEEE-deposited Crossref metadata. Access: HTTP 200 via urllib. Locator: message.title, author, published, container-title, volume, page, DOI, resource.primary.URL. Read scope: bibliographic metadata. Full-body read: **no**.
- **flow_indexed** — [primary source](https://ieeexplore.ieee.org/abstract/document/11683937/); authority: IEEE publisher, search-indexed primary record. Access: search extract readable; direct publisher page challenged. Locator: Abstract; Published in; Page(s); Date of Publication; DOI. Read scope: publisher-indexed abstract and bibliographic fields only. Full-body read: **no**.
- **flow_publisher** — [primary source](https://ieeexplore.ieee.org/document/11683937/); authority: IEEE publisher. Access: JavaScript/robot challenge. Locator: document 11683937. Read scope: challenge page only; no article body. Full-body read: **no**.
- **edaid_record** — [primary source](https://aclanthology.org/2025.naacl-long.83/); authority: ACL publisher. Access: readable browser text. Locator: Title/Authors; Abstract; Volume; Year; Pages; DOI; exported BibTeX. Read scope: landing metadata and abstract. Full-body read: **no**.
- **edaid_pdf** — [primary source](https://aclanthology.org/2025.naacl-long.83.pdf); authority: ACL publisher. Access: browser-extracted PDF text; 12 pages. Locator: PDF p.1 (printed p.1710) proceedings header/title/authors/abstract; p.2 opening introduction/contributions. Read scope: selected metadata/abstract and introduction passages; not entire experiments or appendix. Full-body read: **no**.
- **audo_record** — [primary source](https://arxiv.org/abs/2601.06268v2); authority: arXiv author-submitted primary record. Access: readable browser text. Locator: Title, Authors, Abstract, Cite as, Submission history. Read scope: landing metadata and abstract; latest arXiv version remains v2. Full-body read: **no**.
- **audo_v2_body** — [primary source](https://arxiv.org/html/2601.06268v2); authority: arXiv author manuscript. Access: readable browser text. Locator: sections 3.3–3.5: acceptance/rollback plan; QoR Gating and Metric Model; Evaluation Protocol and Implementation; Safety and Rollback. Read scope: selected methods paragraphs; numerical experiments not audited. Full-body read: **no**.
- **audo_lab** — [primary source](https://vlsicad.ucsd.edu/Publications/Conferences/); authority: author institution UC San Diego. Access: readable browser text. Locator: publication list entry 431. Read scope: single bibliographic entry and linked PDF identity. Full-body read: **no**.
- **audo_current_pdf** — [primary source](https://vlsicad.ucsd.edu/Publications/Conferences/431/c431.pdf); authority: author institution UC San Diego. Access: browser-extracted PDF text; 9 pages. Locator: PDF p.1 title/authors/abstract/ACM Reference Format; p.4 sections 3.4–3.6; p.7 section 4.4; p.8 section 5.4. Read scope: selected identity, gating, formal manifest and limitations passages; not complete paper or experiments. Full-body read: **no**.
- **audo_future_doi** — [primary source](https://doi.org/10.1145/3831252.3834240); authority: DOI resolver. Access: HTTP 404 via urllib; browser internal error. Locator: identifier printed in c431.pdf. Read scope: no publisher content. Full-body read: **no**.
- **audo_future_metadata** — [primary source](https://api.crossref.org/works/10.1145/3831252.3834240); authority: Crossref registry. Access: HTTP 404 via urllib. Locator: requested work identifier. Read scope: no metadata returned. Full-body read: **no**.
- **audo_future_publisher** — [primary source](https://dl.acm.org/doi/10.1145/3831252.3834240); authority: ACM publisher. Access: not accessible via browser tool. Locator: requested DOI record. Read scope: no publisher content. Full-body read: **no**.
- **chi_record** — [primary source](https://arxiv.org/abs/2406.06550); authority: arXiv author-submitted primary record. Access: readable browser text. Locator: Title, Authors, Abstract, Cite as, Submission history. Read scope: landing metadata and abstract; only v1 listed. Full-body read: **no**.
- **chi_body** — [primary source](https://arxiv.org/html/2406.06550v1); authority: arXiv author manuscript. Access: readable browser text. Locator: sections 3.2 Coverage Analysis and 3.3 Actual Bug Reports. Read scope: selected tool-testing passages; not complete body or figures. Full-body read: **no**.
- **nix_ca** — [primary source](https://nix.dev/manual/nix/2.35/store/derivation/outputs/content-address.html); authority: official Nix manual 2.35.2. Access: readable browser text; requested latest URL redirected to the recorded version. Locator: opening definition; Fixed-output content-addressing; (Floating) Content-Addressing; Purity; Floating versus Fixed. Read scope: named documentation sections. Full-body read: **no**.
- **nix_experimental** — [primary source](https://nix.dev/manual/nix/2.35/development/experimental-features.html); authority: official Nix manual 2.35.2. Access: readable browser text; requested latest URL redirected to the recorded version. Locator: What are experimental features?; ca-derivations. Read scope: two named documentation sections. Full-body read: **no**.
- **nix_build** — [primary source](https://nix.dev/manual/nix/2.35/store/building.html); authority: official Nix manual 2.35.2. Access: readable browser text; requested latest URL redirected to the recorded version. Locator: Building opening definition/determinism paragraphs; build lifecycle; sandbox build directory. Read scope: selected definition, lifecycle and environment passages. Full-body read: **no**.
- **nix_rebuild** — [primary source](https://nix.dev/manual/nix/2.35/command-ref/nix-store/realise.html); authority: official Nix manual 2.35.2. Access: readable browser text. Locator: Options: --check; Special exit codes: 104; Examples deterministic rebuild. Read scope: named option/exit-code/example passages. Full-body read: **no**.
- **nix_cli** — [primary source](https://nix.dev/manual/nix/2.35/command-ref/nix-build.html); authority: official Nix manual 2.35.2. Access: readable browser text. Locator: Description; Special exit codes for build failure, 102 and 104. Read scope: selected build command/exit-code passages. Full-body read: **no**.
- **bazel_cache** — [primary source](https://bazel.build/remote/caching); authority: official Bazel documentation. Access: readable browser text. Locator: Remote Caching introduction/action model; action cache/CAS list; How a build uses remote caching; HTTP caching protocol; write access; Known issues. Read scope: selected caching/action/protocol/trust/concurrent-change passages; setup recipes not comprehensively read. Full-body read: **no**.
- **slsa_current** — [primary source](https://slsa.dev/spec/v1.2/); authority: official SLSA specification. Access: readable browser text; requested latest URL redirected to the recorded version. Locator: Version 1.2; Status: Approved; Attestation formats links. Read scope: version/status/navigation metadata. Full-body read: **no**.
- **slsa_provenance** — [primary source](https://slsa.dev/spec/v1.2/build-provenance); authority: official SLSA specification. Access: readable browser text. Locator: Status; predicateType; Purpose; Model; Parsing rules; Schema/Summary; Provenance; BuildDefinition; RunDetails/Builder; BuildMetadata; Extension fields. Read scope: selected normative and schema field descriptions; CUE/protobuf summaries identified as informative. Full-body read: **no**.
- **slsa_verify** — [primary source](https://slsa.dev/spec/v1.2/verifying-artifacts); authority: official SLSA specification. Access: readable browser text. Locator: Step 1: Check SLSA Build level; Step 2: Check expectations; Step 3: Check dependencies recursively. Read scope: selected artifact digest, signature, trust and policy verification passages. Full-body read: **no**.
- **in_toto_statement** — [primary source](https://raw.githubusercontent.com/in-toto/attestation/7aefca35a0f74a6e0cb397a8c4a76558f54de571/spec/v1/statement.md); authority: official in-toto specification, immutable commit linked by SLSA. Access: readable browser text. Locator: Statement version v1.0; Schema; Fields: _type, subject, predicateType, predicate. Read scope: schema and field descriptions; related linked specifications not fully read. Full-body read: **no**.

## Revision handoff and limits

The reread abstract explicitly separates the nine original live cases from frozen proposal-state replay and says live repair was not rerun on the frozen source. The “verified repair” keyword is removed. Related Work acknowledges FlowFixer's existing rechecking and specifies the selected-GDS/verification-input/native-report/cached-lineage object of study. The rule-coverage rationale is now attributed singularly to DRVerify; ChiBench supports tool-testing corpus context. DRVerify itself was not freshly re-audited in this requested reference subset.

Retain those narrow qualifications. Do not infer missing checks in another controller from an abstract or selected body passage. No unsupported first/only priority, population repair rate, industrial signoff qualification or successful outcome of the pending 24 states is supplied by this audit. No comprehensive retraction/plagiarism check or full experimental replication was performed. ArXiv DOI values were observed in primary records; their resolvers were not separately tested.

Only `CITATION_BASELINE_AUDIT.md` and `citation_baseline_audit.json` are written by this task. No manuscript or script correction is applied. The JSON preserves identities, source/access/read scopes, claim decisions, proposed references/prose and the manuscript receipt.

