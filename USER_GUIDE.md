# heritage-types Consumer Guide

Most end users never install this repository directly. Application developers and
data integrators use its published models to validate and exchange heritage data.

## Choose an interface

| Environment | Recommended interface |
|---|---|
| Python application | `heritage-models` Pydantic package |
| TypeScript application | `@mabo-du/heritage-types` npm package |
| Other language or integration service | Versioned JSON Schema in `schemas/` |
| Offline term normalisation | `heritage-vocab` Python package |

## Python

```bash
python -m pip install heritage-models
```

```python
from heritage_models import HeritageDataPackage

package = HeritageDataPackage.model_validate(payload)
portable_json = package.model_dump_json(indent=2)
```

Treat validation errors as data-quality information. Do not discard unknown,
uncertain, or unavailable observations by inventing placeholder values.

## TypeScript

The stable published name remains under the maintainer’s npm scope:

```bash
npm install @mabo-du/heritage-types
```

Import the required interfaces from the package. TypeScript types provide compile-
time checking; validate untrusted runtime JSON against the matching JSON Schema.

## JSON Schema

Pin a schema version instead of following an unversioned file:

```python
import json
from jsonschema import Draft202012Validator

schema = json.load(open("schemas/heritage-data-package-v1.json"))
Draft202012Validator(schema).validate(payload)
```

Preserve the package’s schema-version field when storing or transferring records.
When an ingest fails, report the JSON path and validation message to the data
producer rather than silently dropping the field.

## Vocabulary service

```python
from heritage_vocab import VocabularyService

service = VocabularyService()
term = service.normalise_material("flint")
print(term.preferred_label, term.id)
```

Normalisation should retain the submitted label beside the controlled identifier
where auditability matters. A vocabulary match assists cataloguing; it does not
replace specialist judgement.

## Maintaining the schema

Only edit [`spec/main.tsp`](spec/main.tsp) for generated model changes. Then run:

```bash
npm ci
make all
make test
git diff --check
```

Review changes in all generated targets. Add tests for the new contract and test at
least one real downstream consumer before release. Do not edit generated outputs to
make a single language pass—the next build will overwrite the edit.

## Compatibility checklist

- Is the new field optional where older producers cannot supply it?
- Are names, units, enumerations, and nullability unambiguous?
- Can old payloads still validate?
- Have Python, TypeScript, and JSON Schema outputs all changed consistently?
- Does the schema version express the compatibility boundary?
- Have affected Dig:Tools consumers been tested and notified?

See [PUBLISH_RUNBOOK.md](PUBLISH_RUNBOOK.md) for releases. Report schema issues at
[dig-tools/heritage-types](https://github.com/dig-tools/heritage-types/issues) with
a minimal redacted payload and the exact schema/package version.
