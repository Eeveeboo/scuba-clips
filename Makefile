# scuba-clips build harness.  Run `make help` for the target list.
#
# The Python sources under lib/ and models/ are the only source, plus the
# optional config.toml that lib/config.py reads.
# Every render goes through tools/render.py, which writes the generated source to
# build/<model>.scad and renders it with the manifold backend.  A render that
# warns, that errors, or that does not report "Status: NoError" fails the build.
# Every artefact lands in build/ (gitignored) as <name>.<ext>: one model writes
# build/<name>.stl, build/<name>.png, build/<name>.scad and build/<name>.log.
#
# The tools default to models/, build/ and tools/baseline/.  Only the binary and
# this file take a setting.
#
# OPENSCAD overrides the binary.  Without it the harness prefers
# /Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD, then `openscad` on PATH.
# A binary older than 2024 is refused: the legacy CGAL backend takes minutes
# per model, the manifold backend about a second.

OPENSCAD ?= $(shell if [ -x /Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD ]; then echo /Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD; else command -v openscad 2>/dev/null; fi)
export OPENSCAD

RUN := uv run --locked
RENDER := tools/render.py

# Every file a model can read: the lib/ builders and the kit config.
LIB := $(wildcard lib/*.py) $(wildcard config.toml)
# The renderer is an input too.  The camera default lives in tools/render.py, and
# the plates are committed, so a camera, margin or check change there would
# otherwise be skipped: make sees the existing image as newer than the model and
# never calls the renderer.  These prerequisites force the re-export.
RENDER_TOOLS := $(RENDER) tools/trim_png.py tools/png_check.py tools/stl_metrics.py
# The model list comes from every .py under models/, at any depth, so a dev
# model such as models/dev/print_tests.py is model dev/print_tests and lands in
# build/dev/.  Every __init__.py holds a package, not a model.
MODELS := $(patsubst models/%.py,%,$(filter-out %__init__.py,$(shell find models -name '*.py')))
STL := $(addprefix build/, $(addsuffix .stl, $(MODELS)))
PNG := $(addprefix build/, $(addsuffix .png, $(MODELS)))
SCAD := $(addprefix build/, $(addsuffix .scad, $(MODELS)))
# `ruff` runs over every Python source this job writes, and over tools/watch.py.
# The older tools/*.py keep their own layout: this job is a port, not a
# reformat (docs/CONVERSION_PLAN.md section 11).
PY := lib models tools/watch.py

# A target's `## ` comment becomes its help line; an unannotated target such as
# check-env stays hidden.  See the help recipe.
.DEFAULT_GOAL := help

.PHONY: help all watch typecheck lint format config-example save-baseline check-baseline clean check-env

help: ## this list
	@echo "scuba-clips make targets:"
	@awk 'BEGIN { FS = ":.*## " } /^[a-z][a-zA-Z0-9_-]*:.*## / { printf "  make %-17s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo
	@echo "  OpenSCAD: $(if $(OPENSCAD),$(OPENSCAD),not found)"
	@echo "  models:   $(if $(MODELS),$(MODELS),none in models/)"

all: clean $(STL) $(SCAD) $(PNG) ## render every model into build/
	@[ -n "$(MODELS)" ] || echo "make all: no models in models/ yet"

watch: | check-env ## re-render a model when its source changes
	$(RUN) tools/watch.py

typecheck: ## run ty check
	$(RUN) ty check

lint: ## ruff check the Python sources
	$(RUN) ruff check $(PY)

format: ## ruff format the Python sources
	$(RUN) ruff format $(PY)

config-example: ## write config.example.toml from lib/config.py
	$(RUN) python -m lib.config --example

check-baseline: | check-env ## render all and compare against tools/baseline/
	$(RUN) tools/verify.py

save-baseline: | check-env ## render all and write tools/baseline/*.json
	$(RUN) tools/verify.py --save

clean: ## remove build/
	rm -rf build

# One render writes a model's STL, screenshot, generated source and log, so one
# pattern rule names all three artefacts and make runs the recipe once.
build/%.stl build/%.png build/%.scad: models/%.py $(LIB) $(RENDER_TOOLS) | check-env
	@mkdir -p $(@D)
	$(RUN) $(RENDER) $< $(@D) --name $(notdir $*)

check-env:
	@$(RUN) $(RENDER) --check
