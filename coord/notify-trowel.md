# Coordination: heritage-types \u2192 Trowel (2.0.3 + 2.0.4 patches)

> **Status:** OUTBOUND \u2014 ready for `gh issue create --repo mabo-du/trowel`.
> Companion playbook: [`PUBLISH_RUNBOOK.md`](https://github.com/mabo-du/heritage-types/blob/main/PUBLISH_RUNBOOK.md).

## TL;DR

`heritage-types` has **published 2.0.3 and 2.0.4** as non-breaking
patch-level releases since the coordinated 2.0.0 cycle.
**No consumer action is required** for Trowel.

- `heritage-models==2.0.3, 2.0.4` \u2014 pure CI-side hardening, no schema or
  model surface changes versus 2.0.2 / 2.0.0.
- `heritage-vocab==2.0.3, 2.0.4` \u2014 same.
- `@mabo-du/heridge-types==2.0.3, 2.0.4` \u2014 same (Trowel is Python
  + Pydantic v2 per `heritage-types/AGENTS.md ## Ecosystem Context`,
  so the npm package is not on the critical path; vendor or
  `pip install` work unchanged).

## What changed in `heritage-models` between 2.0.2 and 2.0.4

Nothing consumer-facing. The full diff is in
`publish-models.yml`, `publish-vocab.yml`, and `publish-typescript.yml`
(all in `https://github.com/mabo-du/heritage-types`):

- `env: SOURCE_DATE_EPOCH: ${{ steps.epoch.outputs.epoch }}` \u2014 wheel
  ZIP mtime is git-committer-time (commit-deterministic).
- `env: TZ: UTC` \u2014 `time.localtime(SOURCE_DATE_EPOCH)` is host-TZ
  reproducible across dispatch and local-rebuild.
- `umask 022` \u2014 `ZipInfo.external_attr` (Unix mode bits) is
  host-umask reproducible.
- `uvx --from build==1.5.0` is pinned on both Python workflows.
- New "Check PyPI registry idempotency" step on both Python
  workflows: the rebuilt wheel's `sha256` is compared against
  PyPI's per-version published `sha256`. `Publish to PyPI`
  exits via `skip=true` when bytes match, and fails with
  `##[error]Aborting publish to prevent silent corruption` when
  bytes drift. Protects immutable PyPI bytes from accidental
  corruption by CI re-runs.
- An analogous gate on `publish-typescript.yml` for the npm
  registry.

## Recommended Trowel action

None. Your existing pin pattern (per
`heritage-types/AGENTS.md ## Ecosystem Context` \u2014 Trowel
treats `heritage-models` as `optional, hoard group`) will pick
up 2.0.3 + 2.0.4 transparently. If you've pinned to
`heritage-models==2.0.0` or `==2.0.2` and want post-hardening:

```toml
"heritage-models>=2.0.4,<3.0",  # or pin to ==2.0.4 for stability
```

The `<3.0` upper bound is unchanged; only breaking changes remain
those communicated with the 2.0.0 release (per
https://github.com/mabo-du/heritage-types/releases/tag/v2.0.0),
notably the `schemaVersion: string \u2192 SchemaVer (REQUIRED)` migration
that Trowel would have absorbed in the 2.0.0 cycle.

## Bit-exact closure proof

A 24-byte archival delta exists between post-hardening local
rebuilds and the 2.0.3 PyPI wheels. It is **not data corruption**
\u2014 it is the gate's protective refusal to overwrite the immutable
2.0.3 PyPI bytes with the hardened pipeline's slightly different
ZIP metadata. `2.0.4` is the first version published against a
clean PyPI registry state, demonstrating bit-exact closure at the
next patch level.

## Reference

- CHANGELOG: https://github.com/mabo-du/heritage-types/blob/main/CHANGELOG.md
- v2.0.3 release: https://github.com/mabo-du/heritage-types/releases/tag/v2.0.3
- v2.0.4 release: https://github.com/mabo-du/heritage-types/releases/tag/v2.0.4

## Separate finding: author metadata check

If `Trowel/pyproject.toml` declares `authors = [{ name = "Marcus Quinn" },]`,
that name is wrong (same substitution as HOARD and Libby).
Update to **Mark Bouck** in a follow-up PR. Independent of this
2.0.4 cycle.
