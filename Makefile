.PHONY: all compile python typescript test clean

# Comma-separated PATH list so in-tree scripts see each other.
PYTHONPATH := $(CURDIR)/scripts

all: compile python typescript

# `compile` is the ONE step that produces the persisted schema. It:
#   1. Runs the TypeSpec emitter.
#   2. Asserts the emitter produced schemas/HeritageDataPackage.
#   3. Inlines external $refs (ModelName.json → #/$defs/ModelName).
#   4. Hoists scalars/enums nested in each model.$defs to root $defs so
#      that `#/$defs/uuid` etc. actually resolve under strict validators.
#   5. Renames the resulting file to the versioned published filename.
compile:
	npx tsp compile . \
	  --emit @typespec/json-schema \
	  --option "@typespec/json-schema.file-type=json" \
	  --option "@typespec/json-schema.bundleId=HeritageDataPackage"
	@test -f schemas/HeritageDataPackage || (echo "expected schemas/HeritageDataPackage after tsp compile \u2014 emitter output missing" >&2; exit 1)
	PYTHONPATH=$(PYTHONPATH) python -c "from _inline_schema import publish_in_place; from pathlib import Path; publish_in_place(Path('schemas/HeritageDataPackage'))"
	mv schemas/HeritageDataPackage schemas/heritage-data-package-v$(VERSION).json
	@echo "schema persisted at schemas/heritage-data-package-v$(VERSION).json"

python: compile
	PYTHONPATH=$(PYTHONPATH) python scripts/generate_python.py

typescript: compile
	PYTHONPATH=$(PYTHONPATH) python scripts/generate_typescript.py

test: python typescript
	PYTHONPATH=$(PYTHONPATH) python -m pytest tests/ -v
	@echo "\u2192 typechecking generated TypeScript"
	cd typescript && npx --yes -p typescript@5.4 tsc --noEmit -p .

clean:
	rm -f  schemas/heritage-data-package-v*.json
	rm -f  schemas/HeritageDataPackage
	rm -rf python/heritage_models/__pycache__
	rm -rf typescript/dist/
	rm -rf .pytest_cache tests/__pycache__ tests/*/__pycache__
	rm -rf tests/.mypy_cache

# Default version when `make VERSION=2` is omitted.
VERSION ?= 1
