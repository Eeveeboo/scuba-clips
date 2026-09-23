# scuba-clips build harness.  Run `make help` for the target list.
#
# Every render uses the manifold backend (--backend=manifold --render=true).
# A render that warns, that errors, or that does not report "Status: NoError"
# fails the build.  Artefacts land in build/ (gitignored), screenshots in
# docs/images/.
#
# OPENSCAD overrides the binary.  Without it the harness prefers
# /Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD, then `openscad` on PATH.
# A binary older than 2024 is refused: the legacy CGAL backend takes minutes
# per model, the manifold backend about a second.

OPENSCAD ?= $(shell if [ -x /Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD ]; then echo /Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD; else command -v openscad 2>/dev/null; fi)
MODELS_DIR ?= models
BUILD ?= build
IMG_DIR ?= docs/images
PYTHON ?= python3

RENDER := tools/render.sh
LIB := $(wildcard lib/*.scad)
MODELS := $(patsubst $(MODELS_DIR)/%.scad,%,$(wildcard $(MODELS_DIR)/*.scad))
STL_DIR := $(BUILD)/stl
STL := $(addprefix $(STL_DIR)/, $(addsuffix .stl, $(MODELS)))
PNG := $(addprefix $(IMG_DIR)/, $(addsuffix .png, $(MODELS)))
DRAFT_STL := $(addprefix $(BUILD)/draft/stl/, $(addsuffix .stl, $(MODELS)))
DRAFT_PNG := $(addprefix $(BUILD)/draft/images/, $(addsuffix .png, $(MODELS)))

export OPENSCAD MODELS_DIR

.PHONY: help all stl png preview verify check-env clean

help:
	@echo "scuba-clips make targets:"
	@echo "  make all       every model as STL and as screenshot (stl + png)"
	@echo "  make stl       every model as STL in $(STL_DIR)/"
	@echo "  make png       plates in $(IMG_DIR)/: rendered at 900x650, trimmed to the part"
	@echo "  make preview   fast draft build at MODEL_FN=36, into $(BUILD)/draft/"
	@echo "  make verify    build everything and compare against tools/baseline/"
	@echo "  make clean     remove $(BUILD)/"
	@echo "  make help      this list"
	@echo
	@echo "  OpenSCAD: $(if $(OPENSCAD),$(OPENSCAD),not found)"
	@echo "  models:   $(if $(MODELS),$(MODELS),none in $(MODELS_DIR)/)"

all: stl png

stl: $(STL)
	@[ -n "$(MODELS)" ] || echo "make stl: no models in $(MODELS_DIR)/ yet"

png: $(PNG)
	@[ -n "$(MODELS)" ] || echo "make png: no models in $(MODELS_DIR)/ yet"

preview: $(DRAFT_STL) $(DRAFT_PNG)
	@[ -n "$(MODELS)" ] || echo "make preview: no models in $(MODELS_DIR)/ yet"

$(STL_DIR)/%.stl: $(MODELS_DIR)/%.scad $(LIB) | check-env
	@mkdir -p $(@D)
	$(RENDER) $< $(@D) --stl --name $*

$(IMG_DIR)/%.png: $(MODELS_DIR)/%.scad $(LIB) | check-env
	@mkdir -p $(@D)
	$(RENDER) $< $(@D) --png --name $*

$(BUILD)/draft/stl/%.stl: $(MODELS_DIR)/%.scad $(LIB) | check-env
	@mkdir -p $(@D)
	$(RENDER) $< $(@D) --stl --draft --name $*

$(BUILD)/draft/images/%.png: $(MODELS_DIR)/%.scad $(LIB) | check-env
	@mkdir -p $(@D)
	$(RENDER) $< $(@D) --png --draft --name $*

verify: | check-env
	MODELS_DIR=$(MODELS_DIR) BASELINE_DIR=$(BASELINE_DIR) STL_DIR=$(STL_DIR) IMG_DIR=$(IMG_DIR) \
	WORK=$(BUILD)/verify tools/verify.sh

check-env:
	@$(RENDER) --check

clean:
	rm -rf $(BUILD)
