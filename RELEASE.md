# Releasing heritage-types

> **Owner of this repository: Mark Bouck** (canonical attribution — see
> [`AGENTS.md`](AGENTS.md)). When a coding agent or external tool
> substitutes another name (e.g. "Mark Quinn", "Marcus Quinn",
> "aidevops"), that substitution is a bug and must be reverted.

This runbook describes the procedure for shipping a new release of
`heritage-models` and `heritage-vocab` to PyPI, plus the
`@heritage/types` typescript package status.

## Versioning rule

`AGENTS.md` `## Versioning Rule` is the source of truth:

| Change kind | Bump |
|-------------|------|
| Additive (new optional fields, new types) | minor |
| Removal or rename of existing fields, or any change that makes a previously valid payload invalid | **major — also notify the user** |

A release that breaks wire compatibility *must* come with coordination
across HOARD, StratiGraph, and Trowel. Without coordination the
release will silently corrupt any pre-existing `HeritageDataPackage`
JSON document those tools already wrote to disk.

## Publish flow

### 1. Pre-flight for breaking (major) bumps

If the planned release is a major bump you **must**:

- Open a coordination issue / PR thread against HOARD, StratiGraph,
  and Trowel asking for `+1` on the schema breaking-change before the
  PyPI upload.
- Wait for all three maintainers to ack.
- Write the `RELEASE_NOTIFIED_MARK` sentinel file:

  ```bash
  echo "Mark notified for ${VERSION} on $(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    > RELEASE_NOTIFIED_MARK
  git add RELEASE_NOTIFIED_MARK RELEASE.md CHANGELOG.md
  git commit -m "release: notify-Mark sentinel for ${VERSION}"
  ```

### 2. Bump versions

Update all four manifests in lockstep:

- `python/heritage_models/pyproject.toml` (`version` field)
- `python/heritage_vocab/pyproject.toml` (`version` field)
- `typescript/package.json` (`version` field)
- `package.json` (`version` field, the root)

### 3. Add CHANGELOG entry

Top of `CHANGELOG.md` under `[X.Y.Z]`. Include a `### BREAKING` section
listing every payload that will now fail validation, plus the new
`SchemaVer` value the consumer must populate.

### 4. Build and verify locally

```bash
make clean
make all VERSION=2          # bump to match the new version
make test                  # pytest + tsc --noEmit
```

All 30 tests should pass; `tsc --noEmit` should be clean; the codegen
smoke guard (`tests/test_models_codegen_health.py`) should detect no
`RootModel[UUID]` / `RootModel[AwareDatetime]` drift.

### 5. Tag

```bash
git tag models-vX.Y.Z -m 'notify Mark'
git push --tags
```

### 6. CI gating

`publish-models.yml` then runs:

| Trigger | Behaviour |
|---------|-----------|
| `git push --tags` of `models-v0.y.z` or `models-v1.y.z` … `models-v9.y.z` | tag-triggered publish if `RELEASE_NOTIFIED_MARK` exists in the tag's commit history |
| `models-vN.0.z` (any major bump) | tag-triggered publishes are **rejected** if `RELEASE_NOTIFIED_MARK` is missing |
| Workflow dispatch with `major_bump_acknowledged` containing "I have notified the downstream maintainers" | always publishes |

This is the mechanical read of the social AGENTS.md notification
policy. Tagging without sending notifications costs you the explicit
text acknowledgement in the dispatch UI; tagging a major bump
without `RELEASE_NOTIFIED_MARK` fails the gate.

## `@mabo-du/heritage-types` TypeScript package

The TypeScript package is **public on npm since v2.0.1**. Published
at [`@mabo-du/heritage-types`](https://www.npmjs.com/package/@mabo-du/heritage-types)
under the `mabo-du` (the maintainer's) personal npm scope. This is a
workaround because the `@heritage/` npm scope does not yet exist on
npmjs; when it does, the package will move to `@heritage/types`
(requires a coordinated cross-consumer migration per
[`AGENTS.md ## Versioning Rule`](AGENTS.md)).

The publish workflow is
[`.github/workflows/publish-typescript.yml`](.github/workflows/publish-typescript.yml),
which mirrors `publish-models.yml`:

- `Derive commit epoch` step exposes `steps.epoch.outputs.epoch`.
- `SOURCE_DATE_EPOCH` is bound on **both** the Build step and the
  "Check npm registry idempotency" step (GH Actions `env:` is
  step-scoped, so both bindings are required for `npm pack`'s tar
  entry mtime stamping to be reproducible across re-runs).
- "Check npm registry idempotency" step compares the rebuilt
  tarball's `dist.shasum` against npm's stored one; publish exits
  via `skip=true` (`conclusion=success`, no overwrite) when bytes
  match.

Consumers can either:

- `npm install @mabo-du/heritage-types` — npm path (current, preferred
  for new projects).
- Continue vendoring `typescript/src/index.ts` directly — vendor path
  (legacy; pre-2.0.1 only).

Both paths are first-class per [`AGENTS.md ## Ecosystem Context`](AGENTS.md).

### Future migration to `@heritage/types`

When the `@heritage/` npm scope is granted to the maintainer:

1. Update `typescript/package.json` `name` field to `@heritage/types`.
2. Bump in lockstep with Python manifests. This is a cross-package
   rename; [`AGENTS.md ## Versioning Rule`](AGENTS.md) requires
   coordinated updates across HOARD, StratiGraph, Trowel.
3. Refresh `coord/notify-typescript-npm.md` for the migration.

Until then, the `@mabo-du/heritage-types` path remains canonical.

## Hot-fix path

For a same-day fix to a published release:

1. Branch from the tag commit.
2. Cherry-pick or write the fix.
3. Bump the patch version (`models-v1.2.3`).
4. Tag + push. The workflow handles the rest.

## Roll-back

If a published release corrupts consumer payloads:

1. Yank from PyPI:

   ```bash
   pip install twine
   twine yank --help  # yank specific version
   ```

2. Re-issue under a new minor version that restores backwards compat.

3. File a coordination issue across the affected consumer repos
   (HOARD / StratiGraph / Trowel) so consumers can pin to the
   pre-breaking release.
