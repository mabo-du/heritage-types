#!/usr/bin/env python3
"""Generate the heritage-models Python package from the canonical JSON Schema.

Reads the bundled heritage-data-package-v1.json, inlines all external $ref
references to use #/$defs/... instead, then runs datamodel-codegen to produce
Pydantic v2 models.

Usage:
    python scripts/generate_python.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = REPO_ROOT / "schemas"
OUTPUT_DIR = REPO_ROOT / "python" / "heritage_models"


def inline_external_refs(schema: dict) -> dict:
    """Convert external file $ref to internal #/$defs/... references.

    The TypeSpec JSON Schema emitter writes bundled schemas with
    relative-path refs (e.g. "SiteMetadata.json") when models are
    defined in different files or namespaces. This function converts
    those to #/$defs/SiteMetadata format.
    """
    defs = schema.get("$defs", {})

    def _fix_refs(obj):
        if isinstance(obj, dict):
            if "$ref" in obj:
                ref = obj["$ref"]
                # Convert "ModelName.json" -> "#/$defs/ModelName"
                m = re.match(r'^([A-Za-z0-9_]+)\.json$', ref)
                if m:
                    model_name = m.group(1)
                    if model_name in defs:
                        obj["$ref"] = f"#/$defs/{model_name}"
            for v in obj.values():
                _fix_refs(v)
        elif isinstance(obj, list):
            for item in obj:
                _fix_refs(item)
        return obj

    return _fix_refs(schema)


def main() -> None:
    # Load the bundled schema
    schema_path = SCHEMA_DIR / "heritage-data-package-v1.json"
    if not schema_path.exists():
        # Fallback: try the emitted filename
        alt = SCHEMA_DIR / "HeritageDataPackage"
        if alt.exists():
            schema_path = alt
        else:
            print(f"Error: no schema found in {SCHEMA_DIR}")
            print("Found files:", list(SCHEMA_DIR.iterdir()))
            sys.exit(1)

    raw = json.loads(schema_path.read_text())
    schema = inline_external_refs(raw)

    # Write inlined schema to temp location for codegen
    inlined_path = SCHEMA_DIR / "heritage-data-package-inlined.json"
    inlined_path.write_text(json.dumps(schema, indent=2))

    # Run datamodel-codegen
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "__init__.py").write_text(
        '"""heritage-models — Auto-generated Pydantic v2 models from heritage-types schemas."""\n'
        "from heritage_models.models import *\n"
    )

    result = subprocess.run(
        [
            sys.executable, "-m", "datamodel_code_generator",
            "--input", str(inlined_path),
            "--input-file-type", "jsonschema",
            "--output", str(OUTPUT_DIR / "models.py"),
            "--class-name", "HeritageDataPackage",
            "--target-python-version", "3.11",
            "--field-constraints",
        ],
        capture_output=True, text=True,
    )

    if result.returncode != 0:
        print("datamodel-codegen failed:")
        print(result.stderr)
        sys.exit(1)

    print(f"✓ Generated: {OUTPUT_DIR / 'models.py'}")
    print(f"  Lines: {len((OUTPUT_DIR / 'models.py').read_text().splitlines())}")

    # Clean up temp file
    inlined_path.unlink()


if __name__ == "__main__":
    main()
