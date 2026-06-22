"""Idempotency test for ``scripts/generate_typescript.py``.

Purpose
-------
Two regressions in particular are guarded here:

1. The generator must leave ``typescript/src/index.ts`` byte-identical
   to its pre-run state (a single-run snapshot diff is equivalent to a
   two-run equality check — same input ⇒ same output ⇒ idempotent).
   Non-determinism in codegen produces phantom diffs that confuse
   reviewers and trigger noisy CI re-builds.

2. The generator must NOT clobber committed fields in
   ``typescript/package.json`` — beyond ``version`` and ``description``
   (which it derives from the root ``package.json``), every other
   field (``name``, ``scripts``, ``publishConfig``, ``devDependencies``,
   ``repository``, etc.) is hand-maintained and must survive every
   regeneration.

   This is the live regression guard for REVIEW.md CRITICAL #1, where
   the script previously hardcoded ``"private": true`` and
   ``"name": "@heritage/types"`` on every run and clobbered the
   publish-configured package.json.

The test snapshots both files before invoking the generator, runs it,
asserts the invariants, and restores the originals so the working
tree stays clean after pytest exits.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GENERATOR = REPO_ROOT / "scripts" / "generate_typescript.py"
TS_INDEX_TS = REPO_ROOT / "typescript" / "src" / "index.ts"
TS_PKG_JSON = REPO_ROOT / "typescript" / "package.json"

# Fields the generator is *allowed* to overwrite on regeneration.
# Anything else is a regression (REVIEW.md CRITICAL #1).
ALLOWED_MUTATIONS: frozenset[str] = frozenset({"version", "description"})


def _run_generator() -> None:
    """Invoke the generator via ``subprocess.run`` and surface any failure."""
    result = subprocess.run(
        [sys.executable, str(GENERATOR)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(
            f"generate_typescript.py exited {result.returncode}:\n"
            f"--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )


@pytest.mark.skipif(not GENERATOR.exists(), reason="generator script not present")
@pytest.mark.skipif(
    not TS_INDEX_TS.exists() or not TS_PKG_JSON.exists(),
    reason="typescript/ artifacts not generated yet (run `make all`)",
)
def test_generator_index_ts_is_byte_identical_across_runs() -> None:
    """``typescript/src/index.ts`` content must survive a second generation
    unchanged. This catches sources of non-determinism like unset
    timestamps, unstable dict iteration, or order-sensitive concatenation."""
    backup_text = TS_INDEX_TS.read_text(encoding="utf-8")
    try:
        _run_generator()
        after_text = TS_INDEX_TS.read_text(encoding="utf-8")
        assert after_text == backup_text, (
            "Generator produced different content for typescript/src/index.ts "
            "between two consecutive runs. Likely cause: nondeterministic "
            "ordering (e.g. iterating over an unsorted mapping), a timestamp "
            "embedded in the output, or a side-effecting global lookup. "
            "Fix: sort the relevant iteration source and remove any clock "
            "dependencies."
        )
    finally:
        TS_INDEX_TS.write_text(backup_text, encoding="utf-8")


@pytest.mark.skipif(not GENERATOR.exists(), reason="generator script not present")
@pytest.mark.skipif(
    not TS_INDEX_TS.exists() or not TS_PKG_JSON.exists(),
    reason="typescript/ artifacts not generated yet (run `make all`)",
)
def test_generator_does_not_clobber_typescript_package_json() -> None:
    """``typescript/package.json`` must only mutate ``version`` and
    ``description`` during regeneration. Any other field change
    indicates a clobber regression — see REVIEW.md CRITICAL #1."""
    backup_text = TS_PKG_JSON.read_text(encoding="utf-8")
    backup_pkg = json.loads(backup_text)
    try:
        _run_generator()
        after_text = TS_PKG_JSON.read_text(encoding="utf-8")
        after_pkg = json.loads(after_text)

        # Distinguish added vs removed vs changed vs silently-equal.
        # ``backup_pkg.get(field)`` returns ``None`` for both a missing
        # field and a literal ``"x": null`` value, so it cannot tell
        # those cases apart; we split the union explicitly instead.
        backup_keys = set(backup_pkg.keys())
        after_keys = set(after_pkg.keys())

        added = sorted(after_keys - backup_keys)
        removed = sorted(backup_keys - after_keys)
        assert not added, (
            f"Generator ADDED fields to typescript/package.json: {added!r}. "
            f"Only `version` and `description` should change during "
            f"regeneration. This is REVIEW.md CRITICAL #1 regressing."
        )
        assert not removed, (
            f"Generator REMOVED fields from typescript/package.json: "
            f"{removed!r}. Only the version+description fields may differ; "
            f"every other field is hand-maintained and must survive."
        )

        for field in sorted(backup_keys & after_keys):
            if field in ALLOWED_MUTATIONS:
                # Generator is allowed (and expected) to overwrite this.
                continue
            assert backup_pkg[field] == after_pkg[field], (
                f"Generator mutated typescript/package.json field "
                f"{field!r}: {backup_pkg[field]!r} -> {after_pkg[field]!r}. "
                f"Only `version` and `description` should change during "
                f"regeneration. This is REVIEW.md CRITICAL #1 regressing."
            )
    finally:
        TS_PKG_JSON.write_text(backup_text, encoding="utf-8")
