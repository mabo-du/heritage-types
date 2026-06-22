# Coordination: heritage-types → StratiGraph (2.0.3 + 2.0.4 patches)

> **Status:** OUTBOUND — direct-channel only. The StratiGraph repository is
> **private** per `AGENTS.md ## Ecosystem Context`, so the only coord
> channel is direct (email / DM to the StratiGraph maintainer). The
> 2.0.0 break cycle was filed as [stratigraph#16](https://github.com/mabo-du/stratigraph/issues/16)
> when the repo profile was different; for 2.0.3 + 2.0.4 there is no
> public-issue path.
>
> Companion playbook: [`PUBLISH_RUNBOOK.md`](https://github.com/mabo-du/heritage-types/blob/main/PUBLISH_RUNBOOK.md).
> Original 2.0.0-cycle DRAFT (now superseded): `coord/notify-stratigraph.md.archived-2.0.0`.

## TL;DR

`heritage-types` has published **2.0.3 and 2.0.4** as non-breaking
patch-level releases. **No consumer change is required** for
StratiGraph.

The TypeScript package is now public on npm since v2.0.1 — see
[`AGENTS.md ## Ecosystem Context`](AGENTS.md). StratiGraph can either
continue vendoring `typescript/src/index.ts` (legacy path) or switch
to `npm install @mabo-du/heritage-types` (current path). Both are
first-class per AGENTS.md.

## What changed in `heritage-types` between 2.0.0 and 2.0.4

Nothing structurally for the 2.0.3 + 2.0.4 cycle (pure CI-side
hardening). The on-disk schema shape, the `HeritageDataPackage`
field set, and the lib types are unchanged. The 2.0.0 break
(`schemaVersion: string → SchemaVer (REQUIRED)`) was already
coordinated via stratigraph#16.

StratiGraph's vendored `typescript/src/index.ts` does NOT need to be
re-vendored for the 2.0.3 + 2.0.4 cycle unless the StratiGraph team
wants the post-hardening npm-tarball bytes (which differ from any
prior local regenerate only by the SOURCE_DATE_EPOCH-stamped tar
entry mtime, NOT by TS type content).

## Recommended StratiGraph action

None required. Optional follow-ups:

- If re-vendoring with deterministic bytes is desired, mirror the
  post-hardened discipline:

  ```bash
  cd ~/Projects/heritage-types    # this repo
  export SOURCE_DATE_EPOCH=$(git log -1 --format=%ct)
  export TZ=UTC
  umask 022
  make all
  cp typescript/src/index.ts /path/to/stratigraph/.../heritage-types.ts
  ```

- If collapsing the manual re-vendor step entirely by switching to
  `npm install @mabo-du/heritage-types`, the path is:

  ```bash
  # in the StratiGraph repo
  git rm path/to/vendored/heritage-types.ts
  npm install --save @mabo-du/heritage-types@^2.0.4
  # replace all imports of `heritage-types` with `@mabo-du/heritage-types`
  ```

  This is independent of the 2.0.3 + 2.0.4 cycle and can ship in its
  own PR.

## Reference

- CHANGELOG: https://github.com/mabo-du/heritage-types/blob/main/CHANGELOG.md
- v2.0.3 release: https://github.com/mabo-du/heritage-types/releases/tag/v2.0.3
- v2.0.4 release: https://github.com/mabo-du/heritage-types/releases/tag/v2.0.4
- npm package: https://www.npmjs.com/package/@mabo-du/heritage-types
- `heritage-models` 2.0.4: https://pypi.org/project/heritage-models/2.0.4/
- `heritage-vocab` 2.0.4: https://pypi.org/project/heritage-vocab/2.0.4/

## Separate finding: author metadata check

If `StratiGraph/package.json` (or any StratiGraph configuration file)
declares an author other than **Mark Bouck** (the canonical
attribution per `AGENTS.md ## Naming note for downstream agents`),
the substitution is a bug to revert. The `Mark Bouck` only
attribution canon was added to AGENTS.md after automated tooling
hallucinated `Marcus Quinn` across HOARD / Trowel / Libby
pyproject.toml files. Fix in a separate follow-up PR. Independent
of the 2.0.3 + 2.0.4 cycle.
