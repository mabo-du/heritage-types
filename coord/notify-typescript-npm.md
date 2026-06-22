# Coordination: heritage-types → HOARD / StratiGraph / Trowel (@mabo-du/heritage-types npm availability)

> **Status:** DRAFT — for the operator to file as an announcement (or
> minor issue thread) in the relevant downstream maintainer coordination
> channels. **DO NOT AUTO-POST.** This is an informational notice, not
> a breaking-change triage.
>
> This draft is intentionally consolidated into a single file because
> the npm publication is a single ecosystem event. The breaking-change
> draft set (`notify-hoard.md`, `notify-stratigraph.md`,
> `notify-trowel.md`) still applies to the 2.0.0 → 2.0.1 schema cycle
> and is independent of this notice.

## TL;DR

`heritage-types` now publishes the TypeScript model package to the
public npm registry as a workaround for the missing `@heritage` scope:

```bash
npm install @mabo-du/heritage-types@2.0.1
```

The published package contains the same TypeScript types as
`heritage-types/typescript/src/index.ts` (built from the same
`spec/main.tsp` source of truth, regenerated on every release). It is
purely additive — the previously recommended vendoring path is still
first-class and is **not** deprecated.

## What's changing

| Aspect | Before | After |
|--------|--------|-------|
| `typescript/package.json` `private` field | `"private": true` | not set (publishable) |
| npm install path | none (vendoring required) | `npm install @mabo-du/heritage-types@2.0.1` |
| Scope name | — | `@mabo-du/` |
| Scope rationale | — | Personal-scope workaround for the unregistered `@heritage/` scope on npmjs. See "Future scope migration (tentative)" below. |
| Version coupling | — | tracks the root `heritage-types/package.json` `version` field (currently 2.0.1) |

**No breaking change** to the TypeScript types themselves in the
2.0.0 → 2.0.1 cycle. The schema-version rename
(`schemaVersion: string → SchemaVer`) was already coordinated and
shipped in 2.0.0. This notice only makes the npm install path
available alongside the existing vendoring path.

## What each downstream consumer should know

### StratiGraph (TypeScript — primary affected)

StratiGraph vendors `typescript/src/index.ts` directly today (no path
or npm dependency on `heritage-types`). With the npm publication,
StratiGraph has **two equally viable paths** going forward:

1. **Continue vendoring** (no change required). Run
   `make all VERSION=N` in heritage-types, then copy
   `typescript/src/index.ts` into StratiGraph as before.

2. **Switch to the npm install path:**

   ```bash
   npm install @mabo-du/heritage-types@^2.0 --save
   ```

   then replace the vendored file's surface with
   `import { … } from '@mabo-du/heritage-types'`.

The choice is StratiGraph's. If maintained today, both paths will
remain first-class until the canonical `@heritage/types` scope lands
on npmjs.

**Recommend forward-compatible pin:**

```jsonc
// In StratiGraph package.json, prefer either:
"@mabo-du/heritage-types": "^2.0"
```

…over an exact pin, because the npm scope may switch to
`@heritage/types` in a future minor. A `^2.0` semver range is
resilient to ordinary patch-level fixes once that migration happens.

### HOARD (Python — informational only)

`heritage-models` is the canonical Python consumer artifact and is
unchanged by this notice. **No action required.** This notification is
filed only because HOARD maintainers may want to coordinate the
*parallel* TypeScript publication for cross-repo clarity.

### Trowel (Python — informational only)

`heritage-models` is the canonical Python consumer artifact and is
unchanged by this notice. **No action required.**

### Libby (Python — informational only)

`heritage-models` is the upstream for `Chronology` output types and is
unchanged by this notice. **No action required.**

> **Note for the operator:** The existing `coord/notify-*.md`
> convention covers HOARD / StratiGraph / Trowel only. If a separate
> Libby notice is desired, file it in its own
> `coord/notify-libby.md` rather than expanding this already-
> consolidated draft.

## Future scope migration (tentative — not yet committed)

> The `@mabo-du/` scope is a workaround; the canonical `@heritage/`
> scope is not registered on npmjs as of this writing. **Nothing
> below is a public commitment** — this section is sketched for
> downstream awareness only.

The high-level plan for moving off the workaround scope, *not yet
chartered*:

1. Register `@heritage` (or equivalent) on npmjs under an organic
   organisation account.
2. Publish the same tarball under `@heritage/types@2.0.1`.
3. Mark `@mabo-du/heritage-types` as deprecated with a redirect.
4. Update this notice + `coord/notify-stratigraph.md` once the
   migration is complete.

Until then `@mabo-du/heritage-types@2.0.1` is the canonical published
location. Any consumer pinning behaviour should treat the scope name
itself as fluid.

## Notify receipt

npm URL for `@mabo-du/heritage-types@2.0.1`:
<https://www.npmjs.com/package/@mabo-du/heritage-types/v/2.0.1>

<!-- TODO(operator): paste cross-repo issue links here once this
     notice is filed against HOARD / StratiGraph / Trowel channels.
     The existing breaking-change drafts use:
       HOARD        https://github.com/mabo-du/HOARD/issues/7
       StratiGraph  https://github.com/mabo-du/stratigraph/issues/16
       Trowel       https://github.com/mabo-du/trowel/issues/14
     For this *informational* notice, file a low-priority thread
     (not a breaking-change triage) in each channel.
-->
