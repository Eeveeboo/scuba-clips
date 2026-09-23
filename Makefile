# scuba-clips build harness.  Run `make help` for the target list.
#
# The Python sources under constants/, lib/ and models/ are the only source.
# Every render goes through tools/render.py, which writes build/scad/<model>.scad
# and renders with the manifold backend.  A render that warns, that errors, or
# that does not report "Status: NoError" fails the build.  Artefacts land in
# build/ (gitignored), screenshots in docs/images/.
#
# OPENSCAD overrides the binary.  Without it the harness prefers
# /Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD, then `openscad` on PATH.
# A binary older than 2024 is refused: the legacy CGAL backend takes minutes
# per model, the manifold backend about a second.

OPENSCAD ?= $(shell if [ -x /Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD ]; then echo /Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD; else command -v openscad 2>/dev/null; fi)
UV ?= uv
MODELS_DIR ?= models
BASELINE_DIR ?= tools/baseline
BUILD ?= build
IMG_DIR ?= docs/images

RUN := $(UV) run --locked
RENDER := tools/render.py
# Every file a model can read: the lib/ builders plus the constants/ kit.
LIB := $(wildcard lib/*.py) $(wildcard constants/*.py)
# The renderer is an input too.  The camera default lives in tools/render.py, and
# the plates are committed, so a camera, margin or check change there would
# otherwise be skipped: make sees the existing image as newer than the model and
# never calls the renderer.  These prerequisites force the re-export.
RENDER_TOOLS := $(RENDER) tools/trim_png.py tools/png_check.py tools/stl_metrics.py
# The model list comes from models/*.py.  __init__.py holds the package.
MODEL_FILES := $(filter-out $(MODELS_DIR)/__init__.py,$(wildcard $(MODELS_DIR)/*.py))
MODELS := $(patsubst $(MODELS_DIR)/%.py,%,$(MODEL_FILES))
STL_DIR := $(BUILD)/stl
SCAD_DIR := $(BUILD)/scad
STL := $(addprefix $(STL_DIR)/, $(addsuffix .stl, $(MODELS)))
PNG := $(addprefix $(IMG_DIR)/, $(addsuffix .png, $(MODELS)))
SCAD := $(addprefix $(SCAD_DIR)/, $(addsuffix .scad, $(MODELS)))
DRAFT_STL := $(addprefix $(BUILD)/draft/stl/, $(addsuffix .stl, $(MODELS)))
DRAFT_PNG := $(addprefix $(BUILD)/draft/images/, $(addsuffix .png, $(MODELS)))
# `ruff` runs over every Python source this job writes, and over tools/watch.py.
# The older tools/*.py keep their own layout: this job is a port, not a
# reformat (docs/CONVERSION_PLAN.md section 11).
PY_SOURCES ?= constants lib models dev tools/watch.py

export OPENSCAD MODELS_DIR

.PHONY: help watch one all stl png scad preview typecheck lint format save-baseline check-baseline check-env clean

help:
	@echo "scuba-clips make targets:"
	@echo "  make watch       re-render a model when its source changes; PNGs into $(BUILD)/watch/"
	@echo "  make one MODEL=x one model, STL and screenshot"
	@echo "  make all         every model as STL and as screenshot (stl + png)"
	@echo "  make stl         every model as STL in $(STL_DIR)/"
	@echo "  make png         plates in $(IMG_DIR)/: rendered at 900x650, trimmed to the part"
	@echo "  make scad        every generated .scad in $(SCAD_DIR)/"
	@echo "  make preview     fast draft build at fn=36, into $(BUILD)/draft/"
	@echo "  make save-baseline   render all and write $(BASELINE_DIR)/*.json"
	@echo "  make check-baseline  render all and compare against $(BASELINE_DIR)/"
	@echo "  make typecheck   $(UV) run ty check"
	@echo "  make lint        ruff check $(PY_SOURCES)"
	@echo "  make format      ruff format $(PY_SOURCES)"
	@echo "  make clean       remove $(BUILD)/"
	@echo "  make help        this list"
	@echo
	@echo "  OpenSCAD: $(if $(OPENSCAD),$(OPENSCAD),not found)"
	@echo "  models:   $(if $(MODELS),$(MODELS),none in $(MODELS_DIR)/)"

watch: | check-env
	$(RUN) tools/watch.py

# One model, STL and PNG.  It renders every time, so `make one` is also the way
# to re-render one model after the renderer itself changed.
one: | check-env
	@[ -n "$(MODEL)" ] || { echo "make one: set MODEL=x (one of: $(MODELS))"; exit 2; }
	@[ -f "$(MODELS_DIR)/$(MODEL).py" ] || { echo "make one: no $(MODELS_DIR)/$(MODEL).py"; exit 2; }
	@mkdir -p $(STL_DIR) $(IMG_DIR)
	$(RUN) $(RENDER) $(MODELS_DIR)/$(MODEL).py $(STL_DIR) --stl --name $(MODEL)
	$(RUN) $(RENDER) $(MODELS_DIR)/$(MODEL).py $(IMG_DIR) --png --name $(MODEL)

all: stl png

stl: $(STL)
	@[ -n "$(MODELS)" ] || echo "make stl: no models in $(MODELS_DIR)/ yet"

png: $(PNG)
	@[ -n "$(MODELS)" ] || echo "make png: no models in $(MODELS_DIR)/ yet"

scad: $(SCAD)
	@[ -n "$(MODELS)" ] || echo "make scad: no models in $(MODELS_DIR)/ yet"

preview: $(DRAFT_STL) $(DRAFT_PNG)
	@[ -n "$(MODELS)" ] || echo "make preview: no models in $(MODELS_DIR)/ yet"

typecheck:
	$(RUN) ty check

lint:
	$(RUN) ruff check $(PY_SOURCES)

format:
	$(RUN) ruff format $(PY_SOURCES)

save-baseline: | check-env
	BASELINE_DIR=$(BASELINE_DIR) STL_DIR=$(STL_DIR) IMG_DIR=$(IMG_DIR) WORK=$(BUILD)/verify \
	$(RUN) tools/verify.py --save

check-baseline: | check-env
	BASELINE_DIR=$(BASELINE_DIR) STL_DIR=$(STL_DIR) IMG_DIR=$(IMG_DIR) WORK=$(BUILD)/verify \
	$(RUN) tools/verify.py

$(STL_DIR)/%.stl: $(MODELS_DIR)/%.py $(LIB) $(RENDER_TOOLS) | check-env
	@mkdir -p $(@D)
	$(RUN) $(RENDER) $< $(@D) --stl --name $*

$(IMG_DIR)/%.png: $(MODELS_DIR)/%.py $(LIB) $(RENDER_TOOLS) | check-env
	@mkdir -p $(@D)
	$(RUN) $(RENDER) $< $(@D) --png --name $*

$(SCAD_DIR)/%.scad: $(MODELS_DIR)/%.py $(LIB) $(RENDER_TOOLS) | check-env
	@mkdir -p $(@D)
	$(RUN) $(RENDER) $< $(@D) --scad --name $*

$(BUILD)/draft/stl/%.stl: $(MODELS_DIR)/%.py $(LIB) $(RENDER_TOOLS) | check-env
	@mkdir -p $(@D)
	$(RUN) $(RENDER) $< $(@D) --stl --draft --name $*

$(BUILD)/draft/images/%.png: $(MODELS_DIR)/%.py $(LIB) $(RENDER_TOOLS) | check-env
	@mkdir -p $(@D)
	$(RUN) $(RENDER) $< $(@D) --png --draft --name $*

check-env:
	@$(RUN) $(RENDER) --check

clean:
	rm -rf $(BUILD)
