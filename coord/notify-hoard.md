# Coordination: heritage-types \u2192 HOARD (2.0.3 + 2.0.4 patches)

> **Status:** OUTBOUND \u2014 ready for `gh issue create --repo mabo-du/HOARD`.
> Companion playbook: [`PUBLISH_RUNBOOK.md`](https://github.com/mabo-du/heritage-types/blob/main/PUBLISH_RUNBOOK.md).

## TL;DR

`heritage-types` has **published 2.0.3 and 2.0.4** as non-breaking
patch-level releases since the coordinated 2.0.0 cycle. **No
consumer action is required** for HOARD.

- `heritage-models==2.0.3, 2.0.4` \u2014 pure CI-side hardening, no schema or
  model surface changes versus 2.0.2 / 2.0.0.
- `heritage-vocab==2.0.3, 2.0.4` \u2014 same.
- `@mabo-du/heritage-types==2.0.3, 2.0.4` \u2014 same (vendor path or
  `npm install` path; both are first-class per AGENTS.md).

## What changed in `heritage-models` between 2.0.2 and 2.0.4

Nothing consumer-facing. The full diff is in
`publish-models.yml`, `publish-vocab.yml`, and `publish-typescript.yml`:

- `env: SOURCE_DATE_EPOCH: ${{ steps.epoch.outputs.epoch }}` \u2014 wheel
  ZIP mtime is git-committer-time (commit-deterministic).
- `env: TZ: UTC` \u2014 `time.localtime(SOURCE_DATE_EPOCH)` is host-TZ
  reproducible across dispatch and local-rebuild.
- `umask 022` \u2014 `ZipInfo.external_attr` (Unix mode bits) is
  host-umask reproducible.
- `uvx --from build==1.5.0` is pinned on both Python workflows
  so the wheel archive writer is version-stable.
- A new "Check PyPI registry idempotency" step in
  `publish-models.yml` and `publish-vocab.yml` compares the
  rebuilt wheel's `sha256` against PyPI's per-version published
  `sha256`. `Publish to PyPI` exits via `skip=true` (`conclusion
  = success`, no overwrite) when bytes match, and fails with
  `##[error]Aborting publish to prevent silent corruption` when
  bytes drift. This protects immutable PyPI release bytes from
  accidental corruption by CI re-runs across environments.
- An analogous gate on `publish-typescript.yml` for the npm
  registry (`dist.shasum` comparison against
  `registry.npmjs.org/@mabo-du%2Fheritage-types/<version>`).

## Recommended HOARD action

None. `heritage-models>=2.0,<3.0` already in your pin will pick
up 2.0.3 + 2.0.4 transparently. If you're pinned to
`heritage-models==2.0.0` or `heritage-models==2.0.2` and want
the post-hardening releases, you can opt in:

```toml
"heritage-models>=2.0.4,<3.0",  # or pin to ==2.0.4 for stability
```

The `<3.0` upper bound is unchanged from prior guidance; the
only breaking changes remain those communicated with the 2.0.0
release (per https://github.com/mabo-du/heritage-types/releases/tag/v2.0.0).

## Bit-exact closure proof (operational detail)

The 24-byte archival delta observed on `2.0.3` wheels relative
to pre-hardening builds is **not data corruption** \u2014 it is the
gate's protective refusal to overwrite immutable 2.0.3 PyPI
bytes with the hardened pipeline's slightly different ZIP
metadata. `2.0.4` is the first version published against a
clean PyPI registry state, so the gate emits `proceeding with
publish` (`skip=false`) on first dispatch, and reduces to
`skip=true; conclusion=success` on a re-dispatch against the
same commit. This proves bit-exact closure of the prior drift.

## Reference

- CHANGELOG: https://github.com/mabo-du/heritage-types/blob/main/CHANGELOG.md
- v2.0.3 release: https://github.com/mabo-du/heritage-types/releases/tag/v2.0.3
- v2.0.4 release: https://github.com/mabo-du/heritage-types/releases/tag/v2.0.4
- `heritage-models` 2.0.4: https://pypi.org/project/heritage-models/2.0.4/
- `heritage-vocab` 2.0.4: https://pypi.org/project/heritage-vocab/2.0.4/

## Separate finding: author metadata in your `pyproject.toml`

While auditing cross-repo compliance, I noticed
`HOARD/pyproject.toml` declares:

```toml
authors = [
    { name = "Marcus Quinn" },
]
```

This name is wrong. The canonical attribution is **Mark Bouck**
per `LICENSE`, `heritage-types/AGENTS.md`, and your own
`HOARD/AGENTS.md` "Owner" line. The erroneous name appears to
be a substitution by an automated tool that hallucinated
a different author. Update to:

```toml
authors = [
    { name = "Mark Bouck" },
    # any co-maintainers
]
```

This is independent of the 2.0.4 cycle and can ship in its own
PR.
