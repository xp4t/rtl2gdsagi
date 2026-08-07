# Makefile for rtl2gdsagi IEEE paper
# Usage: make | make clean | make watch | make docker

PAPER     := paper
TEXFILE   := $(PAPER).tex
PDF       := $(PAPER).pdf
LATEX     := pdflatex
BIBTEX    := bibtex
LATEXOPTS := -interaction=nonstopmode -halt-on-error -file-line-error

.PHONY: all clean watch docker

## ── Default: full build (latex → bibtex → latex → latex) ───────────────────
all: $(PDF)

$(PDF): $(TEXFILE)
	@echo "==> Pass 1: pdflatex"
	$(LATEX) $(LATEXOPTS) $(PAPER)
	@echo "==> Pass 2: bibtex"
	$(BIBTEX) $(PAPER) || true
	@echo "==> Pass 3: pdflatex"
	$(LATEX) $(LATEXOPTS) $(PAPER)
	@echo "==> Pass 4: pdflatex (resolve cross-refs)"
	$(LATEX) $(LATEXOPTS) $(PAPER)
	@echo "==> Done: $(PDF)"

## ── Quick single-pass (no bibliography update) ──────────────────────────────
quick: $(TEXFILE)
	$(LATEX) $(LATEXOPTS) $(PAPER)

## ── Clean build artefacts (keep PDF) ────────────────────────────────────────
clean:
	rm -f $(PAPER).aux $(PAPER).bbl $(PAPER).blg \
	       $(PAPER).log $(PAPER).out $(PAPER).toc \
	       $(PAPER).lof $(PAPER).lot $(PAPER).fls \
	       $(PAPER).fdb_latexmk $(PAPER).synctex.gz

## ── Clean everything including PDF ──────────────────────────────────────────
distclean: clean
	rm -f $(PDF)

## ── Auto-recompile on save (requires inotifywait) ───────────────────────────
watch:
	@which inotifywait > /dev/null 2>&1 || \
	    (echo "Install inotify-tools: sudo apt install inotify-tools" && exit 1)
	@echo "Watching $(TEXFILE) for changes..."
	@while true; do \
	    inotifywait -e close_write $(TEXFILE) 2>/dev/null; \
	    make quick; \
	done

## ── Build inside Docker (no local LaTeX needed) ─────────────────────────────
docker:
	docker run --rm -v "$(PWD)":/workdir -w /workdir \
	    texlive/texlive:latest \
	    bash -c "pdflatex $(LATEXOPTS) $(PAPER) && \
	             bibtex $(PAPER) || true && \
	             pdflatex $(LATEXOPTS) $(PAPER) && \
	             pdflatex $(LATEXOPTS) $(PAPER)"
	@echo "==> Done: $(PDF)"
