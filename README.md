<p align="center">
  <img src="docs/brand/project-lockup.svg" alt="Dig:Tools" width="720">
</p>

# heritage-types

> Canonical, generated data models for interoperable digital-heritage tools.

[![License: MIT](https://img.shields.io/badge/license-MIT-2ea44f.svg)](LICENSE)
[![npm](https://img.shields.io/npm/v/@mabo-du/heritage-types?logo=npm)](https://www.npmjs.com/package/@mabo-du/heritage-types)
[![GitHub](https://img.shields.io/badge/GitHub-dig--tools%2Fheritage--types-181717?logo=github)](https://github.com/dig-tools/heritage-types)

`heritage-types` is infrastructure, not an end-user application. It defines one
TypeSpec source model and generates JSON Schema, Pydantic models, and TypeScript
interfaces so Dig:Tools applications can exchange records without redefining
contexts, finds, samples, dates, assets, or provenance.

## Packages and artefacts

| Output | Use |
|---|---|
| `schemas/heritage-data-package-v*.json` | Language-neutral validation with JSON Schema 2020-12 |
| `heritage-models` | Generated Pydantic v2 models for Python |
| `heritage-vocab` | Offline vocabulary normalisation service |
| `@mabo-du/heritage-types` | Generated TypeScript interfaces |

The npm scope remains `@mabo-du` for package-name stability even though the
source repository is owned by the `dig-tools` GitHub organisation.

## Core model

`HeritageDataPackage` combines site metadata, stratigraphic units and
relationships, finds, samples, chronologies, digital assets, and explicit
provenance agents/activities/records. See [`spec/main.tsp`](spec/main.tsp) for
the authoritative definitions.

## Generation flow

```text
spec/main.tsp
    ↓ TypeSpec
schemas/*.json
    ├─→ python/heritage_models/
    └─→ typescript/src/

python/heritage_vocab/ is maintained alongside the generated models.
```

Do not hand-edit generated schema, Pydantic, or TypeScript output. Change
`spec/main.tsp`, regenerate all targets, inspect the diff, and run the full tests.

```bash
git clone https://github.com/dig-tools/heritage-types.git
cd heritage-types
npm ci
python -m pip install -r requirements-dev.txt
make all
make test
```

See [USER_GUIDE.md](USER_GUIDE.md) for consumer examples and versioning guidance,
and [PUBLISH_RUNBOOK.md](PUBLISH_RUNBOOK.md) for maintainer release operations.

## Versioning

Additive optional fields normally require a minor version. Removing or renaming
an existing field is a coordinated breaking change and requires a major version.
Generated outputs and consumer notification are part of the change, not follow-up
work.

## Licence

MIT. See [LICENSE](LICENSE).
