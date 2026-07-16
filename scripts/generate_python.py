#!/usr/bin/env python3
"""Generate the heritage-models Python package from the canonical JSON Schema.

Reads the bundled heritage-data-package-v1.json, inlines all external $ref
references, then runs datamodel-codegen to produce Pydantic v2 models.

Usage:
    python scripts/generate_python.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# Make sibling imports work when run directly: `python scripts/generate_python.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _inline_schema import (  # noqa: E402
    hoist_scalars_and_enums,
    inline_external_refs,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = REPO_ROOT / "schemas"
OUTPUT_DIR = REPO_ROOT / "python" / "heritage_models"


def main() -> None:
    # Load the bundled schema.
    schema_path = SCHEMA_DIR / "heritage-data-package-v1.json"
    if not schema_path.exists():
        alt = SCHEMA_DIR / "HeritageDataPackage"
        if alt.exists():
            schema_path = alt
        else:
            print(f"Error: no schema found in {SCHEMA_DIR}")
            print("Found files:", list(SCHEMA_DIR.iterdir()))
            sys.exit(1)

    raw = json.loads(schema_path.read_text())
    schema = inline_external_refs(raw)
    schema = hoist_scalars_and_enums(schema)

    # Write inlined schema to a temp file outside the persisted `schemas/`
    # directory so an interrupted build never leaves a stale artefact
    # that the next run will pick up by glob.
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, dir=REPO_ROOT
    ) as tmp:
        inlined_path = Path(tmp.name)
        tmp.write(json.dumps(schema, indent=2))

    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / "__init__.py").write_text(
            '"""heritage-models — Auto-generated Pydantic v2 models from heritage-types schemas."""\n'
            "from heritage_models.models import *\n"
        )

        # NOTE: We use `--class-name HDP` deliberately to avoid the name
        # collision between the top-level `HeritageDataPackage` model and
        # its $defs entry. With `--class-name HeritageDataPackage`,
        # datamodel-codegen silently renames the actual schema to
        # `HeritageDataPackage1` and emits a useless `RootModel[Any]`
        # wrapper named `HeritageDataPackage`. Downstream consumers
        # then get the wrapper instead of the real model. Using a
        # separate root name `HDP` keeps the canonical class name
        # `HeritageDataPackage` intact in the generated module.
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "datamodel_code_generator",
                "--input",
                str(inlined_path),
                "--input-file-type",
                "jsonschema",
                "--output",
                str(OUTPUT_DIR / "models.py"),
                "--class-name",
                "HDP",
                "--target-python-version",
                "3.11",
                "--field-constraints",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print("datamodel-codegen failed:")
            print(result.stderr)
            sys.exit(1)

        # Pydantic refuses to apply ``Field(pattern=...)`` to a non-``str``
        # ``RootModel`` type (currently the generated ``UUID`` wrapper) with the
        # message ``TypeError: Unable to apply constraint 'pattern' to
        # supplied value ... for schema of type 'uuid'``. datamodel-codegen
        # emits those wrappers when the JSON Schema uses ``format: uuid`` /
        # ``format: date-time`` *and* ``--field-constraints`` is set. The
        # fix is local: collapse only that wrapper type to ``str`` so the regex
        # pattern can attach. Datetime deliberately remains
        # ``RootModel[AwareDatetime]`` so Pydantic continues enforcing both
        # ISO-8601 syntax and timezone awareness.
        models_path = OUTPUT_DIR / "models.py"
        text = models_path.read_text()
        text = _post_process_models(text)
        models_path.write_text(text)

        print(f"✓ Generated: {models_path}")
        print(f"  Lines: {len(text.splitlines())}")
    finally:
        # Always clean up the temp inlined schema.
        inlined_path.unlink(missing_ok=True)


def _post_process_models(text: str) -> str:
    """Re-shape the constrained ``RootModel[UUID]`` wrapper to ``str``.

    datamodel-codegen's ``--field-constraints`` output exposes a Pydantic
    design choice we don't want: ``Field(pattern=...)`` on a ``RootModel[UUID]``
    raises ``TypeError`` because pattern constraints are only valid for
    string schemas. Rewriting the wrapper to ``RootModel[str]`` lets the
    pattern attach while keeping the ``uuid: ...`` JSON-Schema authority.
    """
    # Drop the non-deterministic header injected by datamodel-codegen:
    #   # generated by datamodel-codegen:
    #   #   filename:  tmp<random>.json
    #   #   timestamp: <wallclock>
    # Without this, models.py bytes differ across every regeneration even
    # when the schema input is byte-identical — the random tempfile suffix
    # alone varies. That drift propagates into the wheel SHA256 and breaks
    # the publish-models.yml registry-idempotency gate (which compares
    # local vs remote wheel SHA256 and aborts on divergence).
    text = re.sub(
        r"\A# generated by datamodel-codegen:[^\n]*\n(?:(?:#[^\n]*\n)*)",
        "",
        text,
    )
    # Re-attach a stable, reproducible module banner so models.py still
    # carries attribution to the heritage-types source-of-truth path.
    text = (
        "# Auto-generated Pydantic v2 models from heritage-types TypeSpec source.\n"
        "# Do not edit directly -- edit spec/main.tsp and run `make all`.\n" + text
    )

    # Uuid: keep the Field but wrap in RootModel[str].
    text = re.sub(
        r"class\s+Uuid\(RootModel\[UUID\]\):\s*\n(\s+)root:\s+UUID\b",
        r"class Uuid(RootModel[str]):\n\1root: str",
        text,
    )
    # Now drop the now-unused imports *without* nuking other symbols
    # sharing the same line (RootModel, BaseModel, Field, …).
    text = re.sub(r"^from\s+uuid\s+import\s+UUID\n", "", text, flags=re.MULTILINE)
    return text


def _drop_import_symbol(text: str, prefix: str, symbol: str) -> str:
    """Remove a single symbol from an ``<prefix> a, b, c`` import line.

    Earlier versions of this file used a whole-line regex that nuked the
    entire import line — which silently dropped ``RootModel`` / ``Field``
    from models.py and crashed every consumer at first import. This
    surgical variant keeps every other symbol on the line intact.
    """
    out_lines: list[str] = []
    for line in text.splitlines():
        if line.startswith(prefix) and symbol in line:
            payload = line[len(prefix) :].strip()
            symbols = [s.strip() for s in payload.split(",") if s.strip()]
            kept = [s for s in symbols if s != symbol]
            if not kept:
                # Whole import is now empty → drop the line entirely.
                continue
            out_lines.append(f"{prefix} {', '.join(kept)}")
        else:
            out_lines.append(line)
    return "\n".join(out_lines)


if __name__ == "__main__":
    main()
