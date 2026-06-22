# heritage-types 2.0.3 — Operator Publish Runbook

> **Ownership & authority.** This runbook is for **Mark Bouck**, who
> maintains the heritage-types repository. If a coding agent produced
> this file under a different name, that name is wrong — see
> [`AGENTS.md`](AGENTS.md) for the canonical attribution.
>
> **What this runbook does.** It assembles the exact command(s) to
> publish `heritage-models` and `heritage-vocab` to
> PyPI from this repo via GitHub Actions. The mechanical gate is
> in `.github/workflows/publish-models.yml`; this runbook is the
> human-facing checklist. Current release: **2.0.3**.

## Pre-flight check

Before running anything, confirm:

| Item | Command | Expected |
|------|---------|----------|
| Working tree clean | `git status --short` | no output |
| Branch | `git rev-parse --abbrev-ref HEAD` | `main` |
| All four manifests at 2.0.3 | `grep -n '^version' package.json python/heritage_models/pyproject.toml python/heritage_vocab/pyproject.toml typescript/package.json` | `2.0.3` everywhere |
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

## Gate C — PyPI registry idempotency

Every publish-models workflow run executes a "Check PyPI registry
idempotency" step that decides whether to:

* **skip upload** (`skip=true` → publish step exits early, run green);
* **upload** (release not yet on PyPI, or wheel filename not yet uploaded); or
* **abort with `::error`** (existing PyPI wheel bytes differ from local).

The decision is per-wheel. For each `*.whl` in
`python/heritage_models/dist/`, the step pulls
`https://pypi.org/pypi/heritage-models/json` to a local `pypi_info.json`
and runs a `jq` query against it:

```bash
REMOTE_HASH=$(jq -r ".releases[\"${VERSION}\"] // [] | .[] | \
    select(.filename == \"${WHEEL_NAME}\") | \
    .digests.sha256 // empty" pypi_info.json)
```

If `REMOTE_HASH` is empty, the wheel is treated as "not yet on PyPI;
will publish." If it equals the local `sha256sum`, the wheel is treated
as "matching; skip=true." If it differs, the step `::error::`s and aborts.

### `jq` null-safety — DO NOT regress

A previous version of this query used the tautological form
`.releases["${VERSION}"][]` against the same JSON. That **crashes with
`jq: error: Cannot iterate over null (null)` (exit 5)** whenever
`${VERSION}` is absent from `pypi_info.json.releases` — i.e. *exactly
the fresh-version publish case the gate is supposed to advance through
seamlessly*. In practice this caused every first-time `workflow_dispatch`
of a brand-new version to halt at this gate for the wrong reason,
before the if/elif/else chain could choose the "not yet on PyPI;
will publish" branch.

The textbook null-safe idiom is the alternative operator plus an empty
array:

```jq
.releases["<VERSION>"] // []   # alternative: when null → use []
| .[]                          # iterate (possibly empty) array
| select(.filename == "<WHEEL_NAME>")
| .digests.sha256 // empty
```

**Never** revert to `.releases["${VERSION}"][]` — it will re-break every
fresh-version publish. The `// [] | .[]` pair is a hard jq idiom,
not a style choice.

If you need to tweak the gate's filter, dry-run it against the live
PyPI manifest first:

```bash
# fetch live data once
curl -fsSL https://pypi.org/pypi/heritage-models/json -o /tmp/pypi_info.json

# absent-version case (the one that catches the bug)
jq -r '.releases["0.0.0"] // [] | .[] \
    | select(.filename == "heritage_models-0.0.0-py3-none-any.whl") \
    | .digests.sha256 // empty' /tmp/pypi_info.json
# expected: empty output, exit 0

# present-version case (must still return a real sha256)
jq -r '.releases["2.0.3"] // [] | .[] \
    | select(.filename == "heritage_models-2.0.3-py3-none-any.whl") \
    | .digests.sha256 // empty' /tmp/pypi_info.json
# expected: a 64-char hex string
```

If your new query errors on the absent-version case, your change has
reintroduced the bug.

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
   twine yank heritage-models 2.0.3
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

- `heritage-models==2.0.3`: https://pypi.org/project/heritage-models/2.0.3/
- `heritage-vocab==2.0.3`: https://pypi.org/project/heritage-vocab/2.0.3/

All three downstream coordination issues filed with version links.

