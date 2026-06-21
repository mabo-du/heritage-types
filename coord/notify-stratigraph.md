# Coordination: heritage-types → StratiGraph (2.0.0 breaking change)

> **Status:** DRAFT — for the operator to file as an issue against
> `/home/mark/Projects/StratiGraph` (or post as a comment on the
> equivalent upstream repo). **DO NOT AUTO-POST** — the dispatch
> publish of `heritage-types==2.0.0` is gated on confirmation these
> notifications actually went out.

## TL;DR

`heritage-types` releases **2.0.0** at the timestamp above. The
breaking change is `HeritageDataPackage.schemaVersion: string →
SchemaVer`. StratiGraph vendors `typescript/src/index.ts` directly
(`typescript/package.json` is `private: true`), so the change
ripples through whatever internal TypeScript code constructs a
`HeritageDataPackage` value for export.

If StratiGraph never constructs a `HeritageDataPackage` directly but
instead only *reads* them (e.g. imported from HOARD or from user-
uploaded `.hmatrix.json`), the migration is read-side only.

The `RELEASE_NOTIFIED_MARK` sentinel inside
`/home/mark/Projects/heritage-types` pins the coordination timestamp.
PyPI URL below — replace with actual on publish.

## What's changing in `@heritage/types` from `heritage-types==2.0.0`

(Note: `@heritage/types` is private — vendored, not on npm. The
authors of this repo should re-run `make all` in
`/home/mark/Projects/heritage-types` and re-vendor
`typescript/src/index.ts` into StratiGraph's source tree.)

| TS type | Old shape (1.x) | New shape (2.0.0) |
|---------|-----------------|-------------------|
| `SchemaVer` | *(not a type — emitted as `string`)* | `export type SchemaVer = string;  // pattern: ^\d+-\d+-\d+$` |
| `HeritageDataPackage.schemaVersion` | `schemaVersion: string;` | `schemaVersion: SchemaVer;` (REQUIRED) |
| `HeritageDataPackage.updatedAt` | *(absent)* | `updatedAt?: datetime;` (optional) |
| `HeritageDataPackage.provenanceLog` | *(absent)* | `provenanceLog?: ProvenanceRecord[];` (optional) |
| New `AgentType` enum | *(absent)* | `export enum AgentType { Human = "Human", AIModel = "AIModel", Software = "Software" }` |
| New types | — | `ProvenanceAgent`, `ProvenanceActivity`, `ProvenanceRecord` |

The field-level breakage is one field: `schemaVersion: string →
SchemaVer`. Everything else is additive.

## What StratiGraph needs to do

1. **Re-vendor.** Pull the freshly-generated `index.ts` from
   heritage-types after `make all VERSION=1`:

   ```bash
   cd /home/mark/Projects/heritage-types
   make all VERSION=1
   # The new index.ts is at typescript/src/index.ts
   cp typescript/src/index.ts /path/to/stratigraph/.../heritage-types.ts
   ```

   (Check `app/`, `packages/`, or `src/` in StratiGraph for the
   existing vendored file's location.)

2. **Update write sites.** Any TypeScript code that constructs a
   `HeritageDataPackage` will fail typecheck if `schemaVersion` is
   omitted (it's REQUIRED) or mistyped (must match the pattern
   `^\d+-\d+-\d+$`). Default to `"2-0-0"` (semver-as-tuple, dashes
   not dots).

   ```ts
   const pkg: HeritageDataPackage = {
     schemaVersion: "2-0-0",
     createdAt: new Date().toISOString(),
     contexts: [...],
     relationships: [...],
     finds: [],
     samples: [],
     dates: [],
     assets: [],
   };
   ```

3. **Update read sites.** If StratiGraph reads HOARD-produced
   `.hmatrix.json` files, those files now require
   `schemaVersion: "2-0-0"` (or whatever HOARD pinned). HOARD
   is being notified in parallel — they will update their own
   serialiser as part of the 2.0.0 cycle.

4. **Test.** Run `npm run test` and `npm run lint` against the
   vendored types. If the tsc build fails on a missing
   `schemaVersion`, the typecheck gate will catch every write site.

## What StratiGraph does NOT need to do

- No dependency-version bump — `@heritage/types` is vendored, not a
  package dependency.
- No changes to React component code unless it constructs/reads a
  `HeritageDataPackage` directly. Most UI code operates on the
  matrix DAG, not on the full data package.

## Notify receipt

PyPI URL for `heritage-models==2.0.0` (paste actual on publish):
<https://pypi.org/project/heritage-models/2.0.0/>
