## rtl2gdsagi — Paper Compilation

This directory contains the IEEE conference paper source.

### Requirements

```bash
# Ubuntu / Debian
sudo apt-get install -y texlive-latex-extra texlive-science \
     texlive-fonts-recommended texlive-bibtex-extra

# macOS (Homebrew)
brew install --cask mactex

# Or use the Docker approach (no local install needed):
make docker
```

### Build

```bash
make          # produces paper.pdf
make clean    # remove build artefacts
make watch    # auto-recompile on save (requires inotifywait)
```

### Structure

```
paper/
├── paper.tex         ← Main LaTeX source (self-contained, no \input{})
├── Makefile          ← Build rules
└── README.md         ← This file
```

The paper uses the **IEEEtran** document class (conference mode) which is
included in `texlive-latex-extra`. No additional `.cls` download is needed.

TikZ is used for Fig. 1 (architecture diagram) — requires `texlive-science`.

### Paper outline (6 pages)

| Section | Content |
|---|---|
| I | Introduction & contributions |
| II | Background & related work (OpenLane2, ML-guided EDA, LLM agents) |
| III | System architecture (state machine, async runner, persistence) |
| IV | Parser layer & agent decision schema |
| V | Strategy sweep controller |
| VI | Evaluation (3 E2E scenarios, parser coverage, sweep results) |
| VII | Discussion & limitations |
| VIII | Conclusion & future work |

12 references covering Yosys, OpenROAD, OpenLane2, Mirhoseini chip placement,
ChipNeMo, ChatEDA, Anthropic tool-use, and ReAct.
