.PHONY: all compile python typescript clean

all: compile python typescript

compile:
	npx tsp compile . --emit @typespec/json-schema --option "@typespec/json-schema.file-type=json" --option "@typespec/json-schema.bundleId=HeritageDataPackage"
	mv schemas/HeritageDataPackage schemas/heritage-data-package-v1.json

python: compile
	python scripts/generate_python.py

typescript: compile
	python scripts/generate_typescript.py

clean:
	rm -rf schemas/*.json schemas/*.yaml
	rm -rf python/heritage_models/__pycache__
	rm -rf typescript/dist/
