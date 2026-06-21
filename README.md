# heritage-types

<!-- aidevops:badges:start -->
<!-- managed by aidevops badges; edit the template, not this block -->
<!-- Build & Quality Status -->

<!-- License & Legal -->
[![License](https://img.shields.io/badge/license-see%20file-yellow.svg)](https://github.com/mabo-du/heritage-types/blob/main/LICENSE)

<!-- Repository Metrics -->
[![Lines of code](https://raw.githubusercontent.com/mabo-du/heritage-types/main/.github/badges/loc-total.svg)](https://github.com/mabo-du/heritage-types)
[![Languages by lines of code](https://raw.githubusercontent.com/mabo-du/heritage-types/main/.github/badges/loc-languages.svg)](https://github.com/mabo-du/heritage-types)

<!-- Project Links -->
[![GitHub repository](https://img.shields.io/badge/github-repository-181717.svg?logo=github)](https://github.com/mabo-du/heritage-types)
<!-- aidevops:badges:end -->

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
- `Find` — artefact records
- `Sample` — environmental/C14/isotopic sample data
- `Chronology` — calibrated radiocarbon dates
- `StratigraphicRelationship` — stratigraphic relationships (cuts, fills, equals)
- `DigitalAsset` — photographs, drawings, GIS layers
- `SiteMetadata` — project-level metadata
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

### TypeScript: `@heritage/types`

TypeScript interfaces for web-based tools (StratiGraph, Libby frontend). Published from this repository's `typescript/` directory.

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
