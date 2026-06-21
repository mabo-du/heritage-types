# heritage-types 2.0.0 — Operator Publish Runbook

> **Ownership & authority.** This runbook is for **Mark Bouck**, who
> maintains the heritage-types repository. If a coding agent produced
> this file under a different name, that name is wrong — see
> [`AGENTS.md`](AGENTS.md) for the canonical attribution.
>
> **What this runbook does.** It assembles the exact command(s) to
> publish `heritage-models==2.0.0` and `heritage-vocab==2.0.0` to
> PyPI from this repo via GitHub Actions. The mechanical gate is
> in `.github/workflows/publish-models.yml`; this runbook is the
> human-facing checklist.

## Pre-flight check

Before running anything, confirm:

| Item | Command | Expected |
|------|---------|----------|
| Working tree clean | `git status --short` | no output |
| Branch | `git rev-parse --abbrev-ref HEAD` | `main` |
| All four manifests at 2.0.0 | `grep -n '^version' package.json python/heritage_models/pyproject.toml python/heritage_vocab/pyproject.toml typescript/package.json` | `2.0.0` everywhere |
| Tests green | `pytest tests/ -q` | `33 passed` (now `38` once `tests/test_gate_verifier.py` is in scope) |
| `tsc` clean | `cd typescript && npx tsc --noEmit -p .` | exit 0, no output |
| Sentinel present | `ls -l RELEASE_NOTIFIED_MARK` | non-empty file |

If any item is wrong, STOP and resolve before continuing.

## Gate A — workflow_dispatch (RECOMMENDED for v2.0.0)

This is the **only way** to publish a strict-major bump (`models-v2.0.0`,
`models-v11.0.0`, etc.) from `main` without breaking the AGENTS.md gate.
The gate step in CI requires the literal acknowledgement string in the
`major_bump_acknowledged` input — **you type it yourself**, no shortcut.

```bash
gh workflow run publish-models.yml \
    --ref main \
    -f major_bump_acknowledged='I have notified the downstream maintainers' \
    -f tag_to_publish=models-v2.0.0
```

After running, watch the run:

```bash
gh run watch --exit-status
```

The workflow will:
1. Validate the acknowledgement substring.
2. Re-derive the schema-versioned filename from `tag_to_publish`.
3. Re-generate Pydantic + TypeScript from `spec/main.tsp`.
4. Run the codegen smoke guard (catches `RootModel[UUID]` /
   `RootModel[AwareDatetime]` drift).
5. Build a `pyproject-build` distribution.
6. Publish to PyPI via `pypa/gh-action-pypi-publish`.

If any step fails, the workflow fails before the publish step.

## Gate B — tag-push (NOT applicable to v2.0.0)

A `git push --tags models-v2.0.0` will be **rejected** by the gate even
though the workflow file has `on.push.tags: 'models-v*.*.*'`. That's the
intended behaviour: the gate step matches `^models-v[0-9]+\.0\.0$` and
exits 1 with an actionable error pointing to this runbook.

Use Gate A for v2.0.0. Gate B is reserved for non-major bumps like
`models-v2.0.7` (intra-major patch) where tag-push auto-publishing is
acceptable because there is no breaking-change risk.

## Coordination evidence

The `RELEASE_NOTIFIED_MARK` sentinel file at the repo root contains the
coordination timestamp and a pointer back to this runbook. The CI gate
verifies this file exists in the workflow's checkout tree when a strict
major bump is detected via tag push — but for v2.0.0 we are using the
dispatch path so the sentinel is documentation rather than a hard gate.

Drafts of the cross-repo coordination notifications live in
[`coord/`](coord/) and were prepared alongside this runbook:

* `coord/notify-hoard.md`
* `coord/notify-stratigraph.md`
* `coord/notify-trowel.md`

Each draft is intended to be opened as an issue (or PR comment) in the
respective downstream repo's coordination channel. They do **not** auto-
post; that's a human action.

## Roll-back

If the published release corrupts consumer payloads (pre-existing
`HeritageDataPackage` JSON where `schemaVersion` was a free-form string):

1. Yank from PyPI (one-time action, not reversible, but safe):

   ```bash
   pip install twine
   twine yank heritage-models 2.0.0
   ```

2. Re-issue under a new *minor* version that restores backwards compat
   by making `schemaVersion: SchemaVer` optional (accept `str` too).

3. File a coordination issue across HOARD / StratiGraph / Trowel so
   consumers can pin to the pre-breaking release (`heritage-models<2.0`).

## Hot-fix / patch path

For a same-day fix to a published release:

```bash
git tag models-v2.0.1 -m 'hotfix: <short description>'
git push --tags
```

The workflow will auto-publish because `models-v2.0.1` does **not**
match `^models-v[0-9]+\.0\.0$`. No dispatch needed.

## Did this runbook actually run?

After publishing, paste the PyPI URL of `heritage-models==2.0.0` and
`heritage-vocab==2.0.0` into the `coord/` issue threads as the
"coordinated and shipped" receipt.
