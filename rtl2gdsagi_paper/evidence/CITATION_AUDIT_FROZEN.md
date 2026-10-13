# Frozen citation-compliance audit
Checked: 2026-10-13 06:41:37 UTC. Role: ARS academic-paper Phase 5a, citation compliance.
All 13 source identities were checked. All seven printed DOIs returned HTTP 302 redirects to the expected publisher records; three additional arXiv DOIs also resolved. No incorrect author/year/identifier was found for the cited versions. Four conference entries omit confirmed page ranges. Six direct publisher records impose access limits; metadata verification and claim reading are distinguished below.
This audit ran inline in the current Codex conversation under the user's authorization. It is a citation audit, with no independent external review claimed. No corrections were applied to the manuscript. The only outputs are this file and `citation_audit_frozen.json`.
## Scope and evidence limits
The target is generic Springer LNCS. Exact venue criteria were not supplied (`criteria_binding_unavailable`); no venue-specific acceptance, formatting certificate, or submission-readiness verdict is issued. Suggestions preserve numbered LNCS citations; APA ordering and author-abbreviation rules are not imposed.
Claim checks use primary abstracts and named source passages. No complete journal/conference/preprint body read is claimed. DRVerify was inspected through extracted passages from vendor documentation on SemiWiki; it is industry documentation. Publisher-indexed extracts are identified explicitly. Crossref records are freshly read publisher-deposited metadata, not publisher full-text reads. Local empirical logs, generated manuscript inputs, and comprehensive retraction/plagiarism checks are outside this bounded audit.
## Frozen inputs

| Input | SHA-256 |
|---|---|
| `rtl2gdsagi_paper/main.tex` | `0bbaad3584623037b5444701f4c0949ab272717c2e4a340515ea11b20db9b76e` |
| `rtl2gdsagi_paper/evidence/citation_metadata.json` | `6bdecb0c1b12115b4a832352d1b7b43bc1d30752efab6bb48c0db736ffdeccc9` |
| `rtl2gdsagi_paper/evidence/citation_review.md` | `4e99f6f1c4f60aef4a9c929ea23d605b574c2ce64d7691bc14077a6172d1617d` |
| `rtl2gdsagi_paper/evidence/citation_followup.json` | `01344f45e43b3188eaf7de117c590725363724290e115675f5b159df27e7c7fd` |

`main.tex` contains 13 bibliography entries, 14 citation commands and 16 cited-key occurrences. Every reference is cited; no orphan citation keys or uncited bibliography entries occur in this file. Generated `\input` files were not expanded for this inventory.
## Resolution inventory

| # | Key | Resolution and metadata status |
|---|---|---|
| 1 | `ajayi2019` | resolved; identity confirmed by ACM-deposited metadata and primary paper mirror; ACM page blocked |
| 2 | `shalan2020` | resolved; identity confirmed by ACM-deposited metadata; ACM page blocked; IEEE indexed abstract readable |
| 3 | `eqydocs` | resolved; primary YosysHQ documentation readable |
| 4 | `jung2021` | resolved; IEEE-deposited metadata confirmed; IEEE page challenged; primary author PDF abstract readable |
| 5 | `prov2013` | resolved; primary W3C Note readable |
| 6 | `chateda` | resolved; cited journal metadata confirmed; primary arXiv abstract readable; journal page challenged |
| 7 | `orfsagent` | resolved; 2025 conference metadata confirmed; primary arXiv abstract readable; IEEE page challenged |
| 8 | `mcp4eda` | resolved; primary arXiv v1 metadata/abstract confirmed |
| 9 | `flowfixer` | resolved; 2026 journal metadata confirmed; primary publisher-indexed abstract readable; direct page blocked |
| 10 | `edaid` | resolved; primary ACL publisher metadata and abstract confirmed |
| 11 | `audopeda` | resolved; primary 2026 arXiv v2 metadata and abstract confirmed |
| 12 | `chibench` | resolved; primary arXiv v1 metadata and abstract confirmed |
| 13 | `drverify` | resolved; vendor-authored primary document readable on third-party host |

## Per-reference findings

### 1. ajayi2019

**Manuscript:** main.tex:449; citation occurrence(s): main.tex:58, main.tex:359. Claim context: main.tex:56–58; 358–359.

**Verified identity:** INVITED: Toward an Open-Source Digital Flow: First Learnings from the OpenROAD Project. Authors: Tutu Ajayi; Vidya A. Chhabria; Mateus Fogaça; Soheil Hashemi; Abdelrahman Hosny; Andrew B. Kahng; Minsoo Kim; Jeongsup Lee; Uday Mallappa; Marina Neseem; Geraldo Pradipta; Sherief Reda; Mehdi Saligane; Sachin S. Sapatnekar; Carl Sechen; Mohamed Shalan; William Swartz; Lutong Wang; Zhehong Wang; Mingyu Woo; Bangqi Xu. Year: 2019. Venue: Proceedings of the 56th Annual Design Automation Conference 2019. Pages 1–4. 

**DOI resolution:** [10.1145/3316781.3326334](https://doi.org/10.1145/3316781.3326334) → HTTP 302 → [publisher record](https://dl.acm.org/doi/10.1145/3316781.3326334). This confirms resolver routing; the target's reading limits are listed below.

**Sources and locators:**

- [publisher deposited metadata](https://api.crossref.org/works/10.1145/3316781.3326334) — JSON message.title, message.subtitle (where present), message.author, message.published, message.container-title, message.volume/issue/page, message.resource.primary.URL. Access: HTTP 200; freshly read. Read scope: Bibliographic metadata only; no article body.
- [primary publisher](https://dl.acm.org/doi/10.1145/3316781.3326334) — DOI target. Access: HTTP 403 in browser. Read scope: No publisher body accessed.
- [primary paper mirror](https://par.nsf.gov/servlets/purl/10171025) — PDF p.1 title/author block, Abstract, ACM Reference Format and DOI footer. Access: HTTP 200 via Python; browser fetch timed out. Read scope: Only page 1 extracted and read; remaining pages not read.
- [author institution record](https://fount.aucegypt.edu/faculty_book_chapters/159/) — Title; authors; Publication Date; Publisher; Recommended Citation. Access: Readable. Read scope: Metadata only; site explicitly has no abstract.

**Claim alignment:** The OpenROAD abstract describes an open flow spanning synthesis, placement and routing. The 2019 paper describes an alpha release and goals; it does not certify current tool behavior or this manuscript's signoff results. Crossref separates title/subtitle and omits INVITED; the paper title block includes it. Both identify the same source.

**Narrow wording:** OpenROAD describes an open tool flow spanning synthesis and physical implementation.

**Recommended corrections:** [recommended; pages] Add pp. 1–4. [optional; title] Include INVITED: to reproduce the paper's title block; its omission is not a source-identity error.

**Suggested reference:** Ajayi, T., et al.: INVITED: Toward an Open-Source Digital Flow: First Learnings from the OpenROAD Project. In: Proceedings of the 56th Annual Design Automation Conference 2019, pp. 1–4 (2019). https://doi.org/10.1145/3316781.3326334

### 2. shalan2020

**Manuscript:** main.tex:453; citation occurrence(s): main.tex:58, main.tex:359. Claim context: main.tex:56–58; 358–359.

**Verified identity:** Building OpenLANE: a 130nm openroad-based tapeout-proven flow. Authors: Mohamed Shalan; Tim Edwards. Year: 2020. Venue: Proceedings of the 39th International Conference on Computer-Aided Design. Pages 1–6. 

**DOI resolution:** [10.1145/3400302.3415735](https://doi.org/10.1145/3400302.3415735) → HTTP 302 → [publisher record](https://dl.acm.org/doi/10.1145/3400302.3415735). This confirms resolver routing; the target's reading limits are listed below.

**Sources and locators:**

- [publisher deposited metadata](https://api.crossref.org/works/10.1145/3400302.3415735) — JSON message.title, message.subtitle (where present), message.author, message.published, message.container-title, message.volume/issue/page, message.resource.primary.URL. Access: HTTP 200; freshly read. Read scope: Bibliographic metadata only; no article body.
- [primary publisher](https://dl.acm.org/doi/10.1145/3400302.3415735) — DOI target. Access: HTTP 403 in browser. Read scope: No publisher article body accessed.
- [primary publisher indexed record](https://ieeexplore.ieee.org/abstract/document/9256623/?signout=success) — Title; Abstract; Published in; Date of Conference. Access: Publisher-indexed search extract readable; direct open HTTP 418; /document/9256623 challenge. Read scope: Abstract and metadata from publisher-indexed result only.

**Claim alignment:** IEEE abstract describes an open SoC implemented with an open tool flow and open PDK, from concept to silicon validation. No body-level evaluation or current-version behavior verified. IEEE record adds Invited Paper; ACM title/subtitle variant matches the manuscript. A different record does not justify replacing the valid ACM DOI.

**Narrow wording:** OpenLane describes an open tool flow demonstrated on a 130 nm SoC.

**Recommended corrections:** [recommended; pages] Add pp. 1–6. [recommended; venue] Use Proceedings of the 39th International Conference on Computer-Aided Design for the cited ACM record, or consistently retain its ICCAD abbreviation.

**Suggested reference:** Shalan, M., Edwards, T.: Building OpenLANE: A 130nm OpenROAD-based tapeout-proven flow. In: Proceedings of the 39th International Conference on Computer-Aided Design, pp. 1–6 (2020). https://doi.org/10.1145/3400302.3415735

### 3. eqydocs

**Manuscript:** main.tex:458; citation occurrence(s): main.tex:93, main.tex:378. Claim context: main.tex:92–93; 160–169 (configuration context); 378.

**Verified identity:** Equivalence Checking with Yosys (EQY) Documentation. Authors: YosysHQ. Year: undated living documentation; no publication year inferred. Type: living tool documentation.

**URL resolution:** [cited source](https://yosyshq.readthedocs.io/projects/eqy/en/latest/) is readable (HTTP 200). No DOI was stated or identified in the inspected document; a DOI is not invented.

**Sources and locators:**

- [primary tool docs](https://yosyshq.readthedocs.io/projects/eqy/en/latest/) — Main heading and opening description. Access: HTTP 200. Read scope: Introductory documentation.
- [primary tool docs](https://yosyshq.readthedocs.io/projects/eqy/en/latest/config.html#options-section) — Options section: splitnets; Match sections; Collect sections: group/nogroup and bind/nobind. Access: Readable. Read scope: Named configuration sections only.

**Claim alignment:** Documentation identifies a Yosys equivalence driver and describes vector splitting, net matching and fragment grouping. Docs establish configuration semantics, not local PASS/FAIL outcomes or correctness of this controller's particular grouping. The /latest/ URL is mutable. Copyright 2026 is not a publication year. The author's earlier access date is not independently attested by this audit.

**Narrow wording:** EQY provides Yosys-based equivalence checking; its configuration supports splitting vector nets and grouping matched signals.

**Recommended corrections:** [recommended; version] Add the EQY revision/documentation version used for experiments if retained. [conditional; accessed] Keep 12 October if it is the author's actual access; use 13 October only if adopting this audit's access event.

**Suggested reference:** YosysHQ: Equivalence Checking with Yosys (EQY) Documentation. https://yosyshq.readthedocs.io/projects/eqy/en/latest/ (accessed 13 October 2026 for this audit; retain the author's original access date when appropriate).

### 4. jung2021

**Manuscript:** main.tex:461; citation occurrence(s): main.tex:360. Claim context: main.tex:359–360.

**Verified identity:** METRICS2.1 and Flow Tuning in the IEEE CEDA Robust Design Flow and OpenROAD ICCAD Special Session Paper. Authors: Jinwook Jung; Andrew B. Kahng; Seungwon Kim; Ravi Varadarajan. Year: 2021. Venue: 2021 IEEE/ACM International Conference On Computer Aided Design (ICCAD). Pages 1–9. 

**DOI resolution:** [10.1109/ICCAD51958.2021.9643541](https://doi.org/10.1109/ICCAD51958.2021.9643541) → HTTP 302 → [publisher record](https://ieeexplore.ieee.org/document/9643541/). This confirms resolver routing; the target's reading limits are listed below.

**Sources and locators:**

- [publisher deposited metadata](https://api.crossref.org/works/10.1109/iccad51958.2021.9643541) — JSON message.title, message.subtitle (where present), message.author, message.published, message.container-title, message.volume/issue/page, message.resource.primary.URL. Access: HTTP 200; freshly read. Read scope: Bibliographic metadata only; no article body.
- [primary publisher](https://ieeexplore.ieee.org/document/9643541) — Title in indexed publisher record; DOI target. Access: Direct page shows JavaScript anti-bot challenge. Read scope: Title/challenge only; article body unread.
- [primary author paper](https://vlsicad.ucsd.edu/Publications/Conferences/388/c388.pdf) — PDF p.1 title/authors and Abstract; p.2 Section II METRICS2.1. Access: Readable PDF. Read scope: First-page abstract/introduction and visible Section II excerpt; remaining body not systematically read.

**Claim alignment:** Abstract proposes a metrics structure and discusses parameter autotuning; Section II describes hierarchical metrics. This does not independently validate this manuscript's JSON records or measured QoR.

**Narrow wording:** METRICS2.1 proposes a structured format for flow metrics and supports parameter autotuning.

**Recommended corrections:** [recommended; pages] Add pp. 1–9.

**Suggested reference:** Jung, J., Kahng, A.B., Kim, S., Varadarajan, R.: METRICS2.1 and Flow Tuning in the IEEE CEDA Robust Design Flow and OpenROAD: ICCAD Special Session Paper. In: 2021 IEEE/ACM International Conference On Computer Aided Design (ICCAD), pp. 1–9 (2021). https://doi.org/10.1109/ICCAD51958.2021.9643541

### 5. prov2013

**Manuscript:** main.tex:466; citation occurrence(s): main.tex:361. Claim context: main.tex:360–361.

**Verified identity:** PROV-Overview: An Overview of the PROV Family of Documents. Authors: W3C. Editors: Paul Groth; Luc Moreau. Year: 2013. Date: 2013-04-30. Type: W3C Working Group Note; non-normative overview.

**URL resolution:** [cited source](https://www.w3.org/TR/prov-overview/) is readable (HTTP 200). No DOI was stated or identified in the inspected document; a DOI is not invented.

**Sources and locators:**

- [primary standards org](https://www.w3.org/TR/prov-overview/) — Header date/type and Editors; Abstract; Section 1 Introduction; Section 2 Document Roadmap. Access: HTTP 200. Read scope: Header and named sections; no claim of reading all linked PROV specifications.

**Claim alignment:** Overview discusses entities, activities, attribution and derivation as provenance concepts. The overview is a Working Group Note, not itself a Recommendation; it does not prove hash-based release correctness.

**Narrow wording:** The W3C PROV overview describes general provenance relationships among entities, activities and agents.

**Recommended corrections:** [optional; url] Use the dated 30 April 2013 Note URL for a stable edition. [optional; editors] Include Groth and Moreau as editors if the bibliography uses named editors; W3C corporate attribution is acceptable.

**Suggested reference:** W3C: PROV-Overview: An Overview of the PROV Family of Documents. W3C Working Group Note, 30 April 2013. https://www.w3.org/TR/2013/NOTE-prov-overview-20130430/

### 6. chateda

**Manuscript:** main.tex:469; citation occurrence(s): main.tex:362. Claim context: main.tex:361–362.

**Verified identity:** ChatEDA: A Large Language Model Powered Autonomous Agent for EDA. Authors: Haoyuan Wu; Zhuolun He; Xinyun Zhang; Xufeng Yao; Su Zheng; Haisheng Zheng; Bei Yu. Year: 2024. Venue: IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems. Volume 43(10). Pages 3184–3197. 

**DOI resolution:** [10.1109/TCAD.2024.3383347](https://doi.org/10.1109/TCAD.2024.3383347) → HTTP 302 → [publisher record](https://ieeexplore.ieee.org/document/10485372/). This confirms resolver routing; the target's reading limits are listed below.

**Sources and locators:**

- [publisher deposited metadata](https://api.crossref.org/works/10.1109/tcad.2024.3383347) — JSON message.title, message.subtitle (where present), message.author, message.published, message.container-title, message.volume/issue/page, message.resource.primary.URL. Access: HTTP 200; freshly read. Read scope: Bibliographic metadata only; no article body.
- [primary publisher](https://ieeexplore.ieee.org/document/10485372/) — DOI target. Access: JavaScript anti-bot challenge; abstract URL HTTP 418. Read scope: No journal article body accessed.
- [primary arxiv](https://arxiv.org/abs/2308.10204) — Title; Authors; Abstract; Cite as / related DOI; Submission history. Access: Readable primary landing page. Read scope: Metadata and abstract only; paper body not read.

**Claim alignment:** The arXiv abstract describes these three functions and explicitly links the cited journal DOI. Journal deposition lists Wu then He; arXiv lists He then Wu. Keep the journal author order for the journal citation. arXiv began in 2023; that does not invalidate the journal's 2024 publication year.

**Narrow wording:** ChatEDA describes LLM-assisted task decomposition, script generation and EDA task execution.

**Recommended corrections:** None required for bibliographic identity; retain the current authors, year and DOI.

**Suggested reference:** Wu, H., He, Z., Zhang, X., Yao, X., Zheng, S., Zheng, H., Yu, B.: ChatEDA: A Large Language Model Powered Autonomous Agent for EDA. IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems 43(10), 3184–3197 (2024). https://doi.org/10.1109/TCAD.2024.3383347

### 7. orfsagent

**Manuscript:** main.tex:474; citation occurrence(s): main.tex:363. Claim context: main.tex:362–363.

**Verified identity:** ORFS-agent: Tool-Using Agents for Chip Design Optimization. Authors: Amur Ghose; Andrew B. Kahng; Sayak Kundu; Zhiang Wang. Year: 2025. Venue: 2025 ACM/IEEE 7th Symposium on Machine Learning for CAD (MLCAD). Pages 1–13. Date: 2025-09-08. 

**DOI resolution:** [10.1109/MLCAD65511.2025.11189204](https://doi.org/10.1109/MLCAD65511.2025.11189204) → HTTP 302 → [publisher record](https://ieeexplore.ieee.org/document/11189204/). This confirms resolver routing; the target's reading limits are listed below.

**Sources and locators:**

- [publisher deposited metadata](https://api.crossref.org/works/10.1109/MLCAD65511.2025.11189204) — JSON message.title, message.subtitle (where present), message.author, message.published, message.container-title, message.volume/issue/page, message.resource.primary.URL. Access: HTTP 200; freshly read. Read scope: Bibliographic metadata only; no article body.
- [primary publisher](https://ieeexplore.ieee.org/document/11189204/) — DOI target. Access: JavaScript anti-bot challenge. Read scope: No conference article body accessed.
- [primary arxiv](https://arxiv.org/abs/2506.08332v2) — Title; Authors; Abstract; Cite as / related DOI; Submission history. Access: Readable primary landing page. Read scope: Metadata and abstract only; paper body not read.
- [primary arxiv](https://arxiv.org/abs/2506.08332) — Submission history; latest v3 dated 30 April 2026. Access: Readable. Read scope: Metadata and abstract only; v3 differs from 2025 version.

**Claim alignment:** The 2025 v2 abstract describes an iterative LLM parameter tuner; cited conference identity is established by IEEE deposition. The unversioned arXiv record now selects v3 (2026), with changed performance claims. Do not silently attribute those results to the 2025 conference paper. The manuscript imports no success-rate or QoR percentage from either version.

**Narrow wording:** ORFS-agent describes iterative LLM-guided parameter tuning in an open chip-design flow.

**Recommended corrections:** [recommended; pages] Add pp. 1–13. [recommended; venue] Use 2025 ACM/IEEE 7th Symposium on Machine Learning for CAD (MLCAD), matching the deposit. [optional; case] Use ORFS-agent (lowercase agent) to match the published title.

**Suggested reference:** Ghose, A., Kahng, A.B., Kundu, S., Wang, Z.: ORFS-agent: Tool-Using Agents for Chip Design Optimization. In: 2025 ACM/IEEE 7th Symposium on Machine Learning for CAD (MLCAD), pp. 1–13 (2025). https://doi.org/10.1109/MLCAD65511.2025.11189204

### 8. mcp4eda

**Manuscript:** main.tex:479; citation occurrence(s): main.tex:365. Claim context: main.tex:363–365.

**Verified identity:** MCP4EDA: LLM-Powered Model Context Protocol RTL-to-GDSII Automation with Backend Aware Synthesis Optimization. Authors: Yiting Wang; Wanghao Ye; Yexiao He; Yiran Chen; Gang Qu; Ang Li. Year: 2025. Version: 2507.19570v1. Date: 2025-07-25. Type: arXiv preprint.

**URL resolution:** [cited source](https://arxiv.org/abs/2507.19570) is readable. Additional [arXiv DOI](https://doi.org/10.48550/arXiv.2507.19570) returned HTTP 302 to [https://arxiv.org/abs/2507.19570](https://arxiv.org/abs/2507.19570).

**Sources and locators:**

- [primary arxiv](https://arxiv.org/abs/2507.19570) — Title; Authors; Abstract; Cite as / related DOI; Submission history. Access: Readable primary landing page. Read scope: Metadata and abstract only; paper body not read.

**Claim alignment:** Abstract describes a unified tool interface and optimization of synthesis scripts using post-layout metrics. Complete RTL-to-GDSII automation in the abstract does not establish foundry signoff, proof completeness, or this study's candidate-binding protections. Keep the preprint designation; no journal or conference publication was verified.

**Narrow wording:** MCP4EDA describes an LLM-accessible RTL-to-GDSII tool interface and synthesis-script refinement using post-layout metrics.

**Recommended corrections:** [optional; doi] Add verified arXiv DOI 10.48550/arXiv.2507.19570; the current arXiv URL already identifies the source. [optional; arxiv_version] Pin v1 for the frozen source.

**Suggested reference:** Wang, Y., Ye, W., He, Y., Chen, Y., Qu, G., Li, A.: MCP4EDA: LLM-Powered Model Context Protocol RTL-to-GDSII Automation with Backend Aware Synthesis Optimization. arXiv:2507.19570v1 (2025). https://doi.org/10.48550/arXiv.2507.19570

### 9. flowfixer

**Manuscript:** main.tex:484; citation occurrence(s): main.tex:367. Claim context: main.tex:365–367.

**Verified identity:** FlowFixer-EDA: A Tool-Feedback-Augmented Large Language Model Agent for Automated Diagnosis and Repair of Open-Source RTL-to-GDS Design Flow Failures. Authors: Ke Dong; Ruidong Wang; Fang Yuan; Baichun An; Xia Zhang. Year: 2026. Venue: IEEE Access. Volume 14. Pages 140412–140428. Date: 2026-09-08. 

**DOI resolution:** [10.1109/ACCESS.2026.3730896](https://doi.org/10.1109/ACCESS.2026.3730896) → HTTP 302 → [publisher record](https://ieeexplore.ieee.org/document/11683937/). This confirms resolver routing; the target's reading limits are listed below.

**Sources and locators:**

- [publisher deposited metadata](https://api.crossref.org/works/10.1109/access.2026.3730896) — JSON message.title, message.subtitle (where present), message.author, message.published, message.container-title, message.volume/issue/page, message.resource.primary.URL. Access: HTTP 200; freshly read. Read scope: Bibliographic metadata only; no article body.
- [primary publisher indexed record](https://ieeexplore.ieee.org/abstract/document/11683937/) — Abstract framework description and repair-acceptance sentence; Published in; Page(s); Date of Publication; DOI. Access: Readable publisher-indexed search extract; direct browser open HTTP 418. Read scope: Publisher abstract and bibliographic record only; full article body unread.

**Claim alignment:** Publisher abstract explicitly lists stage-aware parsing, patch validation and EDA reruns as the repair acceptance mechanism. Do not inherit benchmark success rates or claim matched comparative evidence; neither full methods nor benchmark body were read. A previous Crossref 429 and direct 418 are access failures, not evidence the DOI is invalid. Fresh lowercase DOI metadata request returned HTTP 200.

**Narrow wording:** FlowFixer-EDA describes stage-aware log parsing, patch validation and iterative repair in which EDA tool reruns determine acceptance.

**Recommended corrections:** None required for bibliographic identity; retain the current authors, year and DOI.

**Suggested reference:** Dong, K., Wang, R., Yuan, F., An, B., Zhang, X.: FlowFixer-EDA: A Tool-Feedback-Augmented Large Language Model Agent for Automated Diagnosis and Repair of Open-Source RTL-to-GDS Design Flow Failures. IEEE Access 14, 140412–140428 (2026). https://doi.org/10.1109/ACCESS.2026.3730896

### 10. edaid

**Manuscript:** main.tex:489; citation occurrence(s): main.tex:369. Claim context: main.tex:368–370.

**Verified identity:** Divergent Thoughts toward One Goal: LLM-based Multi-Agent Collaboration System for Electronic Design Automation. Authors: Haoyuan Wu; Haisheng Zheng; Zhuolun He; Bei Yu. Year: 2025. Venue: Proceedings of the 2025 Conference of the Nations of the Americas Chapter of the Association for Computational Linguistics: Human Language Technologies (Volume 1: Long Papers). Pages 1710–1721. Date: 2025-04. 

**DOI resolution:** [10.18653/v1/2025.naacl-long.83](https://doi.org/10.18653/v1/2025.naacl-long.83) → HTTP 302 → [publisher record](https://aclanthology.org/2025.naacl-long.83). This confirms resolver routing; the target's reading limits are listed below.

**Sources and locators:**

- [primary publisher](https://aclanthology.org/2025.naacl-long.83/) — Title/author block; Abstract; Volume; Year; Pages; DOI; exported BibTeX. Access: Readable. Read scope: Publisher landing-page metadata and abstract only; PDF body not read.

**Claim alignment:** Abstract presents ChipLlama-controlled collaboration and reports advantages over single-agent systems. Frame improved execution as a result reported by the authors; this audit did not inspect the full experiments.

**Narrow wording:** EDAid describes multi-agent EDA collaboration and reports improvements over single-agent systems.

**Recommended corrections:** [recommended; venue] Expand NAACL-HLT vol. 1 to the publisher's full 2025 proceedings title and Volume 1: Long Papers, or a clear consistent abbreviation.

**Suggested reference:** Wu, H., Zheng, H., He, Z., Yu, B.: Divergent Thoughts toward One Goal: LLM-based Multi-Agent Collaboration System for Electronic Design Automation. In: Proceedings of NAACL 2025: Human Language Technologies, Volume 1: Long Papers, pp. 1710–1721 (2025). https://doi.org/10.18653/v1/2025.naacl-long.83

### 11. audopeda

**Manuscript:** main.tex:494; citation occurrence(s): main.tex:372. Claim context: main.tex:370–372.

**Verified identity:** Automated QoR improvement in OpenROAD with coding agents. Authors: Amur Ghose; Junyeong Jang; Andrew B. Kahng; Jakang Lee. Year: 2026. Version: 2601.06268v2. Version date: 2026-02-09. Date: 2026-01-09. Type: arXiv preprint.

**URL resolution:** [cited source](https://arxiv.org/abs/2601.06268v2) is readable. Additional [arXiv DOI](https://doi.org/10.48550/arXiv.2601.06268) returned HTTP 302 to [https://arxiv.org/abs/2601.06268](https://arxiv.org/abs/2601.06268).

**Sources and locators:**

- [primary arxiv](https://arxiv.org/abs/2601.06268v2) — Title; Authors; Abstract; Cite as / related DOI; Submission history. Access: Readable primary landing page. Read scope: Metadata and abstract only; paper body not read.

**Claim alignment:** The v2 abstract describes executable diffs and reports evaluations of QoR changes. The DOI points to the base arXiv record; retain the v2 URL/identifier when adding the DOI. Keep preprint designation; no body-level replication or journal publication was verified.

**Narrow wording:** AuDoPEDA proposes executable OpenROAD code changes and reports measured QoR improvements.

**Recommended corrections:** [optional; doi] Add arXiv DOI 10.48550/arXiv.2601.06268 while retaining v2; no mandatory source-identity correction.

**Suggested reference:** Ghose, A., Jang, J., Kahng, A.B., Lee, J.: Automated QoR improvement in OpenROAD with coding agents. arXiv:2601.06268v2 (2026). https://arxiv.org/abs/2601.06268v2. DOI: https://doi.org/10.48550/arXiv.2601.06268

### 12. chibench

**Manuscript:** main.tex:498; citation occurrence(s): main.tex:375. Claim context: main.tex:374–375; adjacency to inference at 376–378.

**Verified identity:** ChiBench: a Benchmark Suite for Testing Electronic Design Automation Tools. Authors: Rafael Sumitani; João Victor Amorim; Augusto Mafra; Mirlaine Crepalde; Fernando Magno Quintão Pereira. Year: 2024. Version: 2406.06550v1. Date: 2024-05-24. Type: arXiv preprint.

**URL resolution:** [cited source](https://arxiv.org/abs/2406.06550) is readable. Additional [arXiv DOI](https://doi.org/10.48550/arXiv.2406.06550) returned HTTP 302 to [https://arxiv.org/abs/2406.06550](https://arxiv.org/abs/2406.06550).

**Sources and locators:**

- [primary arxiv](https://arxiv.org/abs/2406.06550) — Title; Authors; Abstract; Cite as / related DOI; Submission history. Access: Readable primary landing page. Read scope: Metadata and abstract only; paper body not read.

**Claim alignment:** Abstract describes a curated Verilog corpus and tool-testing applications. ChiBench supports software-tool testing, not physical-verification runset completeness or LLM-agent performance. Tie the zero-DRC-marker inference specifically to DRVerify rather than to ChiBench collectively.

**Narrow wording:** ChiBench supplies a curated Verilog corpus for testing EDA software.

**Recommended corrections:** [optional; doi] Add verified arXiv DOI 10.48550/arXiv.2406.06550. [optional; arxiv_version] Pin v1 for the frozen source.

**Suggested reference:** Sumitani, R., Amorim, J.V., Mafra, A., Crepalde, M., Pereira, F.M.Q.: ChiBench: a Benchmark Suite for Testing Electronic Design Automation Tools. arXiv:2406.06550v1 (2024). https://doi.org/10.48550/arXiv.2406.06550

### 13. drverify

**Manuscript:** main.tex:502; citation occurrence(s): main.tex:376. Claim context: main.tex:375–378.

**Verified identity:** DRVerify: The Verification of Physical Verification. Authors: Sage Design Automation, Inc.. Year: 2018 (2018 copyright on PDF pages, corroborating the citation year). Type: vendor technical white paper hosted by SemiWiki.

**URL resolution:** [cited source](https://semiwiki.com/wp-content/uploads/2018/06/sage_DRVerify_WP_v2-3-1.pdf) is readable (HTTP 200). No DOI was stated or identified in the inspected document; a DOI is not invented.

**Sources and locators:**

- [primary vendor document on mirror](https://semiwiki.com/wp-content/uploads/2018/06/sage_DRVerify_WP_v2-3-1.pdf) — PDF p.1 title/corporate author/copyright and Who checks the checker?; pp.1–2 passing/failing structures; p.4 DRVerify paragraph. Access: HTTP 200; readable PDF text; screenshot tool failed. Read scope: Named passages inspected in extracted text; no claim of comprehensive full-body or figure inspection.

**Claim alignment:** White paper describes PASS/FAIL test generation and the distinction between executable runsets and intended design rules. This is vendor documentation, not a peer-reviewed efficacy study. SemiWiki is the host, not the author/publisher identity. The zero-marker inference is an interpretation of the cited rationale; it is not a reported result about this study's 211-rule deck.

**Narrow wording:** Sage's DRVerify white paper describes runset testing with passing and failing layout structures. This illustrates why rule intent and coverage require testing beyond a clean report on one layout.

**Recommended corrections:** [optional; corporate_author] Use Sage Design Automation, Inc., exactly as shown in the PDF. [recommended; main.tex:376–378] Attribute the rule-intent/coverage inference specifically to the vendor white paper and separate it from ChiBench.

**Suggested reference:** Sage Design Automation, Inc.: DRVerify: The Verification of Physical Verification. Technical white paper (2018). https://semiwiki.com/wp-content/uploads/2018/06/sage_DRVerify_WP_v2-3-1.pdf

## Associated wording recommendations

- **main.tex:358–359 (Optional narrowing; no false attribution established):** 2019 OpenROAD article describes an alpha flow; cited sources establish infrastructure context, not current signoff certification. Suggested wording: “OpenROAD describes an open tool flow spanning synthesis and physical implementation; OpenLane demonstrates an open implementation flow on a 130 nm SoC.”

- **main.tex:367–368 (Recommended precision):** Verified feedback may imply formal correctness across every cited controller; only narrow tool execution/feedback methods were checked. Suggested wording: “These studies use tool execution and feedback in LLM-assisted EDA. FlowFixer-EDA explicitly bases repair acceptance on EDA tool reruns.”

- **main.tex:368–372 (Optional attribution qualification):** Improvements are reported by the cited authors; the full experiments were not audited. Suggested wording: “EDAid reports improved EDA execution through multi-agent collaboration. AuDoPEDA proposes executable OpenROAD code changes and reports measured QoR improvements.”

- **main.tex:374–378 (Recommended attribution narrowing):** ChiBench concerns EDA software testing; rule-intent and coverage rationale comes from vendor runset documentation. Suggested wording: “ChiBench supplies a curated Verilog corpus for testing EDA tools. Sage's DRVerify white paper describes runset testing with passing and failing layout structures, illustrating why rule intent and coverage require tests beyond a clean report on one layout.”

## Handoff

Recommended bibliography work is limited to adding pages for `ajayi2019` (1–4), `shalan2020` (1–6), `jung2021` (1–9), and `orfsagent` (1–13); normalizing conference names; and optionally adding the three resolved arXiv DOIs and stable document/version locators. OpenROAD's `INVITED:` prefix is visible in the primary paper, while ACM's deposited title/subtitle omits it; this is a title variant, not a mismatched citation. ChatEDA's journal record places Wu before He, unlike arXiv; the manuscript correctly follows the journal deposit. ORFS-agent's 2026 arXiv v3 changes the performance description; the 2025 citation is retained, and no later numerical claim is imported.

The earlier metadata file contains 429 errors for ORFS-agent and FlowFixer-EDA. Fresh requests succeeded for both. The prior review/follow-up files were used as context, not accepted as verification receipts. W3C and EQY documentation, the DRVerify PDF, and the OpenROAD primary paper mirror returned HTTP 200. Browser 403/418 and JavaScript challenges remain recorded as access limits. Full-paper methods, current source retraction status, and local signoff outcomes are not certified by this audit.

The JSON companion supplies per-field checks, actual resolver responses, source URLs/locators, input hashes, reading limits and proposed corrections. Freeze applies to the recorded snapshot and evidence time; it does not make remote pages immutable.

