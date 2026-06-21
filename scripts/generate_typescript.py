#!/usr/bin/env python3
"""Generate the @heritage/types TypeScript package from canonical JSON Schema.

Reads the bundled heritage-data-package-v1.json and emits:
- TypeScript interface declarations for each model
- `type` aliases for every scalar (uuid, datetime, fieldId, SchemaVer, ...)
- `enum` declarations for every TypeSpec enum
- AJV-compatible JSON Schema fragments are NOT emitted (the input JSON Schema
  is itself AJV-compatible and is published alongside this generated TS).

Usage:
    python scripts/generate_typescript.py
"""

from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

# Make sibling imports work when run directly.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _inline_schema import (  # noqa: E402
    collect_scalars_and_enums,
    hoist_scalars_and_enums,
    inline_external_refs,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = REPO_ROOT / "schemas"
OUTPUT_DIR = REPO_ROOT / "typescript" / "src"


# ── TypeScript emission ────────────────────────────────────────────────────


_HEADER = """\
// Auto-generated from heritage-types TypeSpec source.
// Do not edit directly — edit spec/main.tsp and run `npm run build`.
//
// Scalars and enums are hoisted to root-level declarations so every
// interface below resolves unambiguously. Custom format / pattern hints
// are preserved as `// comments`.

"""


def _scalar_comment(schema: dict) -> str:
    if schema.get("format") == "date-time":
        return "  // ISO 8601 datetime"
    if schema.get("format") == "uuid":
        return "  // RFC 4122 UUID"
    if "pattern" in schema:
        return f"  // pattern: {schema['pattern']}"
    return ""


def _scalar_lines(scalars: dict[str, dict]) -> list[str]:
    out: list[str] = []
    for name, sch in sorted(scalars.items()):
        out.append(f"export type {name} = string;{_scalar_comment(sch)}")
    out.append("")
    return out


def _enum_lines(enums: dict[str, dict]) -> list[str]:
    out: list[str] = []
    for name, sch in sorted(enums.items()):
        out.append(f"export enum {name} {{")
        for v in sch.get("enum", []):
            out.append(f"  {v} = \"{v}\",")
        out.append("}")
        out.append("")
    return out


def _ts_type(prop_schema: dict) -> str:
    """Render a JSON Schema property into a TypeScript type string."""
    if "$ref" in prop_schema:
        return prop_schema["$ref"].rsplit("/", 1)[-1]
    if "allOf" in prop_schema:
        # allOf with $ref + enum is how TypeSpec enums are emitted.
        for sub in prop_schema["allOf"]:
            if "$ref" in sub:
                return sub["$ref"].rsplit("/", 1)[-1]
            if "enum" in sub:
                return " | ".join(f"'{v}'" for v in sub["enum"])
    t = prop_schema.get("type")
    if t == "string":
        return "string"
    if t == "integer" or t == "number":
        return "number"
    if t == "boolean":
        return "boolean"
    if t == "array":
        items = prop_schema.get("items", {})
        return f"({_ts_type(items)})[]"
    if t == "object":
        return "Record<string, any>"
    if "enum" in prop_schema:
        return " | ".join(f"'{v}'" for v in prop_schema["enum"])
    return "any"


def _interface_lines(name: str, model: dict) -> list[str]:
    """Render an interface from a JSON Schema object definition."""
    out: list[str] = [f"export interface {name} {{"]
    props = model.get("properties", {}) or {}
    required = set(model.get("required", []) or [])

    for prop_name, prop_schema in props.items():
        ts = _ts_type(prop_schema)
        suffix = "" if prop_name in required else "?"
        # Strip any stray comment that leaked from ts_type (kept None for safety).
        out.append(f"  {prop_name}{suffix}: {ts};")
    out.append("}")
    out.append("")
    return out


def generate_typescript(schema: dict) -> str:
    """Render the entire `index.ts` from an inlined JSON Schema."""
    defs = schema.get("$defs", {}) or {}
    scalars, enums = collect_scalars_and_enums(defs)
    hoist_scalars_and_enums(schema)

    lines: list[str] = [_HEADER]
    lines.extend(_scalar_lines(scalars))
    lines.extend(_enum_lines(enums))

    # Emit each object model as an interface.
    # Skip the root-level `HeritageDataPackage` if it has no `properties`
    # (the schema duplicates it as a $defs and at the root; both are
    # equivalent). We always emit one canonical interface per model name.
    seen: set[str] = set()
    for name, model in defs.items():
        if not isinstance(model, dict):
            continue
        if model.get("type") != "object" or "properties" not in model:
            continue
        if name in seen:
            continue
        seen.add(name)
        lines.extend(_interface_lines(name, model))

    return "\n".join(lines)


def main() -> None:
    schema_path = next(iter(SCHEMA_DIR.glob("heritage-data-package-v*.json")), None)
    if schema_path is None:
        alt = SCHEMA_DIR / "HeritageDataPackage"
        if alt.exists():
            schema_path = alt
    if schema_path is None:
        print(f"Error: no schema found in {SCHEMA_DIR}")
        sys.exit(1)

    raw = json.loads(schema_path.read_text())
    schema = inline_external_refs(raw)
    output = unicodedata.normalize("NFC", generate_typescript(schema))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "index.ts").write_text(output)

    # Derive version + description from the matching root package.json so
    # we never silently regress the published tag (re: REVIEW.md CRITICAL #1).
    root_pkg_path = REPO_ROOT / "package.json"
    if root_pkg_path.exists():
        root_pkg = json.loads(root_pkg_path.read_text())
        version = root_pkg.get("version", "2.0.0")
        description = root_pkg.get(
            "description",
            "Auto-generated TypeScript types from heritage-types canonical schemas",
        )
    else:
        version = "2.0.0"
        description = "Auto-generated TypeScript types from heritage-types canonical schemas"

    pkg = {
        "name": "@heritage/types",
        "version": version,
        "description": description,
        "main": "src/index.ts",
        "types": "src/index.ts",
        "private": True,
    }
    (OUTPUT_DIR.parent / "package.json").write_text(json.dumps(pkg, indent=2))

    print(f"✓ Generated: {OUTPUT_DIR / 'index.ts'}")
    print(f"  Lines: {len(output.splitlines())}")


if __name__ == "__main__":
    main()
