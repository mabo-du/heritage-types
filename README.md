# heritage-types

**Canonical data models for the HOARD heritage science ecosystem.**

This repository is not a standalone product. It is an infrastructure dependency that provides shared data type definitions used by multiple projects in the ecosystem. End users should never need to interact with this repository directly — the Python package (`heritage-models`) is installed automatically as a dependency of HOARD.

## What This Provides

### Python: `heritage-models`

```bash
# Installed automatically with HOARD
pip install hoard

# Or install standalone
pip install heritage-models
```

Provides Pydantic v2 models for all core heritage data types:
- `StratigraphicUnit` — archaeological context sheet data
- `StratigraphicRelationship` — stratigraphic relationships (cuts, fills, equals)
- `Find` — artefact records
- `Sample` — environmental/C14/isotopic sample data
- `Chronology` — calibrated radiocarbon dates
- `DigitalAsset` — photographs, drawings, GIS layers
- `SiteMetadata` — project-level metadata
- `ProvenanceAgent` — agent identity (Human / AIModel / Software) for who/what created a record
- `ProvenanceActivity` — named action performed by a `ProvenanceAgent`
- `ProvenanceRecord` — per-record audit-trail entry (entity, activity, agent, time, confidence)
- `HeritageDataPackage` — full project container for cross-tool exchange

### Python: `heritage-vocab`

Optional offline vocabulary service for Getty AAT/ULAN/TGN term normalisation. Provides material and period standardisation with a built-in fallback covering common archaeological terms.

```python
from heritage_vocab import VocabularyService

svc = VocabularyService()
result = svc.normalise_material("flint")
# → VocabTerm(id="http://vocab.getty.edu/aat/300011754",
#             preferred_label="Flint/Chert")
```

### TypeScript: `@mabo-du/heritage-types`

> **Status: published to npm since v2.0.1.** The `typescript/` directory
> contains auto-generated TypeScript interfaces for web-based tools
> (StratiGraph, Libby frontend). Published at
> [`@mabo-du/heritage-types`](https://www.npmjs.com/package/@mabo-du/heritage-types)
> under the package-author's personal npm scope (since the `@heritage/`
> npm scope is unregistered on npmjs; will move to `@heritage/types`
> when the scope lands — see [RELEASE.md](RELEASE.md) for the migration
> plan). Consumers can either `npm install @mabo-du/heritage-types` or
> continue vendoring `typescript/src/index.ts`; both paths are
> first-class per [`AGENTS.md ## Ecosystem Context`](AGENTS.md).

### JSON Schema

Canonical JSON Schema files in `schemas/` — language-agnostic, usable from any programming environment for data validation.

## Source of Truth

All models are defined in TypeSpec (`spec/main.tsp`) and compiled to JSON Schema Draft 2020-12. Python and TypeScript packages are auto-generated from the compiled schemas.

```
spec/main.tsp  (TypeSpec)
       │
       ▼
schemas/*.json  (JSON Schema)
       │
       ├──► python/heritage_models/  (Pydantic v2, auto-generated)
       ├──► python/heritage_vocab/   (vocabulary service)
       └──► typescript/              (TypeScript interfaces)
```

## Development

```bash
make all        # Full build: compile → python → typescript
make compile    # TypeSpec → JSON Schema only
make python     # Regenerate Python models
make typescript # Regenerate TypeScript types
```

## Repository Architecture

This is one of three infrastructure repositories that support the HOARD ecosystem:

| Repository | Purpose | User-facing |
|------------|---------|-------------|
| **HOARD** | Main archaeological report pipeline | Yes — `pip install hoard` |
| **heritage-types** | Shared data models (this repo) | No — pulled in as dependency |
| **heritage-cli** | Unified ecosystem CLI | Optional — `pip install heritage-cli` |

## License

MIT
