# heritage-types — Canonical Heritage Science Data Models

**Single source of truth** for shared data types across the HOARD ecosystem (HOARD, StratiGraph, Trowel, Libby, Dibble, Cache & Carry, DIG, and others).

## Architecture

```
spec/main.tsp  (TypeSpec — source of truth)
       │
       │  tsp compile --emit @typespec/json-schema
       ▼
schemas/heritage-data-package-v1.json  (JSON Schema Draft 2020-12)
       │
       ├── datamodel-code-generator ──► python/heritage_models/  (Pydantic v2)
       └── custom script          ──► typescript/src/index.ts  (TypeScript interfaces)
```

## Usage

### Python (heritage-models)

```bash
pip install ./python/heritage_models

# In your code:
from heritage_models import StratigraphicUnit, Find, HeritageDataPackage

su = StratigraphicUnit(
    id="123e4567-e89b-12d3-a456-426614174000",
    contextNumber="[101]",
    unitType="Deposit",
)
```

### TypeScript (@heritage/types)

```typescript
import { StratigraphicUnit, HeritageDataPackage } from '@heritage/types';

const su: StratigraphicUnit = {
    id: "123e4567-e89b-12d3-a456-426614174000",
    contextNumber: "[101]",
    unitType: "Deposit",
};
```

### Direct JSON Schema (any language)

```bash
# Reference the schema directly for validation
assert_against_schema(heritage-data-package-v1.json, my_data)
```

## Models

| Model | Description | Used By |
|-------|-------------|---------|
| `SiteMetadata` | Project-level metadata | All projects |
| `StratigraphicUnit` | Archaeological context / stratigraphic unit | HOARD, StratiGraph, Trowel |
| `StratigraphicRelationship` | Stratigraphic relationship (cuts, fills, equals) | HOARD, StratiGraph, Trowel |
| `Find` | Artefact recovered during excavation | HOARD, Trowel, Dibble |
| `Sample` | Scientific sample (C14, environmental, isotopic) | HOARD, Libby, IsoMap |
| `Chronology` | Calibrated radiocarbon / luminescence date | Libby, HOARD, Fritts |
| `DigitalAsset` | Photo, drawing, GIS layer | HOARD, Trowel, DIG |
| `HeritageDataPackage` | Full project data container for exchange | All projects |

## Development

```bash
# Build everything
make all

# Or individual steps
make compile   # TypeSpec → JSON Schema
make python    # JSON Schema → Pydantic v2
make typescript  # JSON Schema → TypeScript

# Edit the source models
vim spec/main.tsp
make all
```

## License

MIT
