#!/usr/bin/env python3
"""Generate the @heritage/types TypeScript package from canonical JSON Schema.

Reads the bundled heritage-data-package-v1.json and emits:
- TypeScript interfaces for each model
- AJV-compatible JSON Schema validators

Usage:
    python scripts/generate_typescript.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = REPO_ROOT / "schemas"
OUTPUT_DIR = REPO_ROOT / "typescript" / "src"


def inline_external_refs(schema: dict) -> dict:
    """Same inline logic as generate_python.py."""
    defs = schema.get("$defs", {})

    def _fix_refs(obj):
        if isinstance(obj, dict):
            if "$ref" in obj:
                ref = obj["$ref"]
                m = re.match(r'^([A-Za-z0-9_]+)\.json$', ref)
                if m and m.group(1) in defs:
                    obj["$ref"] = f"#/$defs/{m.group(1)}"
            for v in obj.values():
                _fix_refs(v)
        elif isinstance(obj, list):
            for item in obj:
                _fix_refs(item)
        return obj

    return _fix_refs(schema)


def ts_type(prop_name: str, prop_schema: dict, defs: dict) -> str:
    """Map a JSON Schema property to a TypeScript type string."""
    if "$ref" in prop_schema:
        ref = prop_schema["$ref"]
        name = ref.rsplit("/", 1)[-1]
        return name

    if "type" not in prop_schema:
        return "any"

    t = prop_schema["type"]
    if t == "string":
        if "format" in prop_schema and prop_schema["format"] == "date-time":
            return "string  // ISO 8601"
        if "pattern" in prop_schema:
            return "string"
        return "string"
    if t == "integer":
        return "number"
    if t == "number":
        return "number"
    if t == "boolean":
        return "boolean"
    if t == "array":
        items = prop_schema.get("items", {})
        return f"{ts_type(prop_name, items, defs)}[]"
    if t == "object":
        return "Record<string, any>"

    # Handle enums (allOf with const, or enum array)
    if "enum" in prop_schema:
        vals = " | ".join(f"'{v}'" for v in prop_schema["enum"])
        return vals

    return "any"


def generate_interfaces(schema: dict) -> str:
    """Generate TypeScript interfaces from a JSON Schema with $defs."""
    defs = schema.get("$defs", {})
    lines: list[str] = [
        "// Auto-generated from heritage-types TypeSpec source.",
        "// Do not edit directly — edit spec/main.tsp and run `npm run build`.",
        "",
    ]

    for name, model in defs.items():
        if name == "HeritageDataPackage":
            continue  # Skip container, it's generated separately
        lines.append(f"export interface {name} {{")
        props = model.get("properties", {})
        required = set(model.get("required", []))

        for prop_name, prop_schema in props.items():
            is_required = prop_name in required
            ts = ts_type(prop_name, prop_schema, defs)

            # Handle enums
            if "allOf" in prop_schema:
                for sub in prop_schema["allOf"]:
                    if "$ref" in sub:
                        ts = sub["$ref"].rsplit("/", 1)[-1]
                    elif "enum" in sub:
                        vals = " | ".join(f"'{v}'" for v in sub["enum"])
                        ts = vals

            if is_required:
                lines.append(f"  {prop_name}: {ts};")
            else:
                lines.append(f"  {prop_name}?: {ts};")

        lines.append("}")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    schema_path = list(SCHEMA_DIR.glob("heritage-data-package-v*.json"))
    if not schema_path:
        alt = SCHEMA_DIR / "HeritageDataPackage"
        if alt.exists():
            schema_path = [alt]
    if not schema_path:
        print(f"Error: no schema found in {SCHEMA_DIR}")
        sys.exit(1)

    raw = json.loads(schema_path[0].read_text())
    schema = inline_external_refs(raw)
    defs = schema.get("$defs", {})

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = generate_interfaces(schema)
    (OUTPUT_DIR / "index.ts").write_text(output)

    # Also generate package.json
    pkg = {
        "name": "@heritage/types",
        "version": "1.0.0",
        "description": "Auto-generated TypeScript types from heritage-types canonical schemas",
        "main": "src/index.ts",
        "types": "src/index.ts",
        "private": True,
    }
    (OUTPUT_DIR.parent / "package.json").write_text(json.dumps(pkg, indent=2))

    print(f"✓ Generated: {OUTPUT_DIR / 'index.ts'}")
    print(f"  Lines: {len(output.splitlines())}")


if __name__ == "__main__":
    main()
