# Changelog

## [1.0.0] — 2026-06-09

### Added

- **TypeSpec source models** (`spec/main.tsp`) defining 8 core data types:
  `SiteMetadata`, `StratigraphicUnit`, `StratigraphicRelationship`, `Find`,
  `Sample`, `Chronology`, `DigitalAsset`, `HeritageDataPackage`
- **Compiled JSON Schema** (`schemas/heritage-data-package-v1.json`) — Draft 2020-12,
  bundled with all `$defs` for self-contained validation
- **Python package** (`python/heritage_models/`) — Pydantic v2 models auto-generated
  via `datamodel-code-generator`, published as `heritage-models` on PyPI
- **TypeScript package** (`typescript/`) — TypeScript interfaces auto-generated
  from the canonical schemas, published as `@heritage/types`
- **Vocabulary service** (`python/heritage_vocab/`) — offline Getty AAT/ULAN/TGN
  term lookup with FTS5-backed search, material/period normalisation helpers,
  and built-in fallback covering 10+ common archaeological terms
- **Build pipeline** — Makefile (compile → python → typescript), TypeSpec compiler
  v1.12.0, datamodel-code-generator integration

[1.0.0]: https://github.com/mabo-du/heritage-types/releases/tag/v1.0.0
