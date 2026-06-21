"""Shared JSON-Schema transforms for the heritage-types build pipeline.

The TypeSpec JSON-Schema emitter writes a bundled document, but:

* cross-model references are emitted as relative paths (``"SiteMetadata.json"``)
* scalar and enum definitions are nested *inside* each model that uses them
  (e.g. ``SiteMetadata.$defs.uuid``), while property refs resolve against the
  *root* ``$defs``.

These transforms rewrite the published schema so it is self-contained and
validates with strict JSON Schema validators (no external file refs, every
``#/$defs/<scalar>`` actually exists at the root).

Importable from ``generate_python.py``, ``generate_typescript.py``, and
the Makefile-driven publish step.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


_EXTERNAL_REF_RE = re.compile(r"^([A-Za-z0-9_]+)\.json$")


def inline_external_refs(schema: dict) -> dict:
    """Rewrite ``"ModelName.json"`` refs to ``"#/$defs/ModelName"``."""

    defs = schema.get("$defs", {})

    def _fix_refs(obj: Any) -> Any:
        if isinstance(obj, dict):
            if "$ref" in obj:
                ref = obj["$ref"]
                m = _EXTERNAL_REF_RE.match(ref)
                if m and m.group(1) in defs:
                    obj["$ref"] = f"#/$defs/{m.group(1)}"
            for v in obj.values():
                _fix_refs(v)
        elif isinstance(obj, list):
            for item in obj:
                _fix_refs(item)
        return obj

    return _fix_refs(schema)


_SCALAR_TYPES = {"string", "integer", "number"}


def collect_scalars_and_enums(defs: dict) -> tuple[dict[str, dict], dict[str, dict]]:
    """Walk every model's nested ``$defs`` to surface scalars and enums once."""
    scalars: dict[str, dict] = {}
    enums: dict[str, dict] = {}

    for model in defs.values():
        if not isinstance(model, dict):
            continue
        inner = model.get("$defs", {})
        for name, schema in inner.items():
            if not isinstance(schema, dict):
                continue
            if "enum" in schema:
                enums.setdefault(name, schema)
            elif schema.get("type") in _SCALAR_TYPES:
                scalars.setdefault(name, schema)
    return scalars, enums


def hoist_scalars_and_enums(schema: dict) -> dict:
    """Copy nested scalars/enums into the root ``$defs`` so published refs resolve."""
    defs = schema.setdefault("$defs", {})
    scalars, enums = collect_scalars_and_enums(defs)
    for name, sch in scalars.items():
        defs.setdefault(name, sch)
    for name, sch in enums.items():
        defs.setdefault(name, sch)
    return schema


def publish_in_place(path: Path) -> None:
    """Read the TypeSpec-emitted schema at *path*, rewrite it, write it back."""
    raw = json.loads(path.read_text())
    schema = inline_external_refs(raw)
    schema = hoist_scalars_and_enums(schema)
    path.write_text(json.dumps(schema, indent=2))


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("usage: inline_schema.py <path/to/HeritageDataPackage.json>",
              file=sys.stderr)
        sys.exit(2)
    publish_in_place(Path(sys.argv[1]))
