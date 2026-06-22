# Changelog

## [2.0.1] — 2026-06-22

### Fixed

- **PyPI wheel packaging**: both `heritage-models` and `heritage-vocab` wheels
  were placing source files at the wheel root instead of inside the package
  namespace directory (e.g. `models.py` at root vs `heritage_models/models.py`).
  This caused `pip install` to succeed but `import heritage_models` to fail
  with `ModuleNotFoundError`. Fixed by adding `[tool.setuptools.packages]` and
  `[tool.setuptools.package-dir]` mappings to both `pyproject.toml` files.

## [2.0.0] — 2026-06-22

### ⚠️ BREAKING — coordinate with HOARD, StratiGraph, Trowel before tagging

> Per `AGENTS.md`, this is a major version bump because `HeritageDataPackage.schemaVersion` is now **required** and its **type changed** from `string` to `SchemaVer`. Existing on-disk serialisations of `HeritageDataPackage` that omit `schemaVersion` will **fail Pydantic validation** after this release. Downstream tool maintainers (HOARD, StratiGraph, Trowel) must be notified before this is tagged to PyPI / npm.

### Changed

- `HeritageDataPackage.schemaVersion`:
  - was optional `string`
  - now **required** `SchemaVer` (regex `^\d+-\d+-\d+$`, e.g. `"1-0-0"`)
- `HeritageDataPackage` adds optional fields:
  - `updatedAt: datetime` — last modification timestamp
  - `provenanceLog: ProvenanceRecord[]` — append-only assertion log
- `ProvenanceRecord.confidence` now constrained to `0.0–1.0` (was unbounded float)
- `DigitalAsset.fileSizeBytes` is now emitted as the JSON Schema `string` type
  (TypeSpec `int64` has no JSON analogue) — consumers should parse with
  `int(value, 10)` for arithmetic.

### Added

- **`SchemaVer` scalar** — pattern `^\d+-\d+-\d+$` for MODEL-REVISION-ADDITION
  semver.
- **`ProvenanceAgent`** — `Human`, `AIModel`, or `Software` agent identity.
- **`ProvenanceActivity`** — named activity performed by an agent.
- **`ProvenanceRecord`** — entity-and-attribution record (W3C PROV-O inspired).

### Fixed

- Codegen: `HeritageDataPackage` was getting silently renamed to
  `HeritageDataPackage1` by `datamodel-codegen` (class-name collision). The
  canonical name is now preserved via `--class-name HDP` for the wrapper
  (resolves: `from heritage_models import HeritageDataPackage` now returns the
  real model, not a `RootModel[Any]` shell).
- TS codegen: previously emitted bare names `uuid`, `datetime`, `SchemaVer`,
  `AgentType`, etc. with no declarations, which would fail `tsc`. The
  generator now emits `type` aliases for scalares and `enum` declarations for
  enums.
- Published JSON Schema: nested scalars/enums are now hoisted to root
  `$defs`, so `#/$defs/uuid` etc. actually resolve under strict validators.
- `make compile`: failures from `tsp compile` no longer silently cascade —
  the `mv` step now errors out if `schemas/HeritageDataPackage` is missing.
- Makefile temp artefacts: codegen script now uses `tempfile.NamedTemporaryFile`
  (outside `schemas/`) so an interrupted build cannot poison the next run.
- `python/heritage_vocab/service.py`:
  - Opens the Cache & Carry SQLite database **read-only** via SQLite URI
    (`file:...?mode=ro`) so a compromised sibling process can't poison
    query results.
  - `LIMIT` parameter is bound (`LIMIT ?`) instead of f-string interpolated.
  - Negative/zero `limit` raises `ValueError` instead of silently becoming
    "no limit".
  - `_create_sample_db` now uses named-column `INSERT` so adding a column
    no longer silently misaligns parameters.
  - `_fallback_builtin` outputs are tagged `source="aat-fallback-unverified"`
    so downstream code can detect that the URI came from the in-memory
    fallback (not Cache & Carry) and the URIs have been **flagged as
    unverified**.
- `.gitignore`: added `https:/` (artefacts from the TypeSpec emitter
  treating `bundleId` as a relative URL), `*.vocab_cache.db`,
  `.claude/`, and `.ctx/` (local dev artifacts).
- `tspconfig.yaml`: `bundleId` now `"HeritageDataPackage"` — consistent
  with Makefile/CI overrides, eliminating the `https:/` artifact directory
  when `tsp compile` is run directly.
- `Makefile clean`: removed dead `rm -rf typescript/dist/` (the TypeScript
  target never produces a `dist/` directory).
- `package.json`: pinned `@typespec/compiler` and `@typespec/json-schema`
  from `"latest"` to `"^1.12"`; lockfile refreshed.
- `normalise_period` now applies the same `_label_similar` guard as
  `normalise_material` to non-exact FTS5 results, rejecting false prefix
  matches (e.g. searching "sto" matching "flint stone" via FTS5).
- Tests: added `_label_similar` guard regression tests for both
  `normalise_period` (happy path, false prefix match rejection, unknown
  term) and `normalise_material` (same three scenarios). Total: 76 tests.

### Removed

- TypeScript package no longer advertises `npm install @heritage/types` in
  CI (the package remains `private: true`); see `M4` in REVIEW.md for the
  followup.

### Build / CI

- New `make test` target runs `pytest tests/` and `tsc --noEmit`.
- New `.github/workflows/ci.yml` runs the same on every push.
- `publish-models.yml`: tags `models-vN.M.K` now derive their major version
  into the published filename (`schemas/heritage-data-package-vN.M.K.json`).

## [1.0.0] — 2026-06-09

### Added

- **TypeSpec source models** (`spec/main.tsp`) defining 8 core data types.
- **Compiled JSON Schema** (`schemas/heritage-data-package-v1.json`) — Draft 2020-12.
- **Python package** (`python/heritage_models/`) — Pydantic v2 models.
- **TypeScript package** (`typescript/`) — TypeScript interfaces.
- **Vocabulary service** (`python/heritage_vocab/`) — offline Getty AAT/ULAN/TGN
  vocabulary lookup with FTS5-backed search and built-in fallback.
- **Build pipeline** — Makefile (`compile → python → typescript`).

[1.0.0]: https://github.com/mabo-du/heritage-types/releases/tag/v1.0.0
