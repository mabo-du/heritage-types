# heritage-types 2.0.2 — Operator Publish Runbook

> **Ownership & authority.** This runbook is for **Mark Bouck**, who
> maintains the heritage-types repository. If a coding agent produced
> this file under a different name, that name is wrong — see
> [`AGENTS.md`](AGENTS.md) for the canonical attribution.
>
> **What this runbook does.** It assembles the exact command(s) to
> publish `heritage-models` and `heritage-vocab` to
> PyPI from this repo via GitHub Actions. The mechanical gate is
> in `.github/workflows/publish-models.yml`; this runbook is the
> human-facing checklist. Current release: **2.0.2**.

## Pre-flight check

Before running anything, confirm:

| Item | Command | Expected |
|------|---------|----------|
| Working tree clean | `git status --short` | no output |
| Branch | `git rev-parse --abbrev-ref HEAD` | `main` |
| All four manifests at 2.0.2 | `grep -n '^version' package.json python/heritage_models/pyproject.toml python/heritage_vocab/pyproject.toml typescript/package.json` | `2.0.2` everywhere |
| Tests green | `pytest tests/ -q` | `76 passed` |
| `tsc` clean | `cd typescript && npx tsc --noEmit -p .` | exit 0, no output |
| Sentinel present | `ls -l RELEASE_NOTIFIED_MARK` | non-empty file |

If any item is wrong, STOP and resolve before continuing.

## Gate A — workflow_dispatch (for breaking bumps)

This is the **only way** to publish a strict-major bump (`models-vN.0.0`)
from `main` without breaking the AGENTS.md gate.
The gate step in CI requires the literal acknowledgement string in the
`major_bump_acknowledged` input — **you type it yourself**, no shortcut.

```bash
gh workflow run publish-models.yml \
    --ref main \
    -f major_bump_acknowledged='I have notified the downstream maintainers' \
    -f tag_to_publish=models-vN.0.0
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

Use Gate A for breaking major bumps. Gate B is reserved for non-major bumps like
`models-v2.0.7` (intra-major patch) where tag-push auto-publishing is
acceptable because there is no breaking-change risk.

## Coordination evidence

The `RELEASE_NOTIFIED_MARK` sentinel file at the repo root contains the
coordination timestamp and a pointer back to this runbook. The CI gate
verifies this file exists in the workflow's checkout tree when a strict
dispatch path so the sentinel is documentation rather than a hard gate.

Drafts of the cross-repo coordination notifications live in
[`coord/`](coord/) and were prepared alongside this runbook:

* `coord/notify-hoard.md` — filed as [HOARD #7](https://github.com/mabo-du/HOARD/issues/7)
* `coord/notify-stratigraph.md` — filed as [StratiGraph #16](https://github.com/mabo-du/stratigraph/issues/16)
* `coord/notify-trowel.md` — filed as [Trowel #14](https://github.com/mabo-du/trowel/issues/14)

Each draft is intended to be opened as an issue (or PR comment) in the
respective downstream repo's coordination channel. These have all been filed.

## Roll-back

If the published release corrupts consumer payloads:

1. Yank from PyPI:

   ```bash
   pip install twine
   twine yank heritage-models 2.0.2
   ```

2. Re-issue under a new *minor* version that restores backwards compat
   by making `schemaVersion: SchemaVer` optional (accept `str` too).

3. File a coordination issue across HOARD / StratiGraph / Trowel so
   consumers can pin to the pre-breaking release (`heritage-models<2.0`).

## Hot-fix / patch path

For a same-day fix to a published release, use workflow_dispatch.
This works for any version (major or patch):

```bash
gh workflow run publish-models.yml \
    --ref main \
    -f major_bump_acknowledged='I have notified the downstream maintainers' \
    -f tag_to_publish=models-v2.0.X
```

## Did this runbook actually run?

- `heritage-models==2.0.2`: https://pypi.org/project/heritage-models/2.0.2/
- `heritage-vocab==2.0.2`: https://pypi.org/project/heritage-vocab/2.0.2/

All three downstream coordination issues filed with version links.

