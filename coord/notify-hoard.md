# Coordination: heritage-types → HOARD (2.0.0 breaking change)

> **Status:** DRAFT — for the operator to file as an issue against
> `/home/mark/Projects/HOARD` (or post as a comment on the equivalent
> upstream repo if upstream lives elsewhere). **DO NOT AUTO-POST**.
> The dispatch publish of `heritage-models==2.0.0` is gated on
> confirmation that these notifications actually went out.

## TL;DR

`heritage-types` releases **2.0.0** at the publish timestamp above.
The change `schemaVersion: string → SchemaVer (REQUIRED)` is a wire-
format breaking change for any `HeritageDataPackage` JSON your
tooling writes or reads. You will need to bump your pin from
`heritage-models>=1.0` to `heritage-models>=2.0,<3.0` and populate
the new field.

The sentinel `RELEASE_NOTIFIED_MARK` in `/home/mark/Projects/heritage-types`
pins the coordination timestamp. PyPI URL draft below — replace with
actual on publish.

## What's changing in `heritage-models==2.0.0`

| Field | Old type (1.x) | New type (2.0.0) |
|-------|----------------|------------------|
| `HeritageDataPackage.schemaVersion` | `str` (free-form, e.g. `"1.0.0"`) | `SchemaVer` (REQUIRED, regex `^\d+-\d+-\d+$`, e.g. `"2-0-0"`) |
| `HeritageDataPackage.createdAt`    | `datetime` (REQUIRED) | unchanged |
| `HeritageDataPackage.updatedAt`    | *(absent)*            | `datetime` (optional) |
| `HeritageDataPackage.provenance`   | `str` (optional, legacy note) | unchanged |
| `HeritageDataPackage.provenanceLog`| *(absent)*            | `list[ProvenanceRecord]` (optional, append-only audit log) |
| `StratigraphicUnit` etc.           | unchanged             | unchanged |
| **New top-level types**            | —                     | `ProvenanceAgent`, `ProvenanceActivity`, `ProvenanceRecord`, `AgentType` enum (`Human`/`AIModel`/`Software`) |

The `schemaVersion` rename is the **only** field-level removal. Every
other change is purely additive.

## What HOARD needs to do

1. **Bump the pin** in `pyproject.toml` from

   ```toml
   dependencies = [
       ...
       "heritage-models>=1.0",
       ...
   ]
   ```

   to

   ```toml
   dependencies = [
       ...
       "heritage-models>=2.0,<3.0",
       ...
   ]
   ```

2. **Update every write site** that constructs a `HeritageDataPackage`
   in code. The new field is **REQUIRED** — silent omission will be
   rejected on validation. Default it to `"2-0-0"` (semver-as-tuple):
   `model-version = "2"`, `revision = "0"`, `addition = "0"`. The
   pattern is `\d+-\d+-\d+`, so `"2.0.0"` will NOT match — convert
   dots to dashes before persisting.

3. **Update every read site** that previously accepted a free-form
   `schemaVersion` string. Pydantic v2 will now reject anything that
   does not match the regex. Be defensive: if down-conversion is
   needed, normalise `"2.0.0" → "2-0-0"` before instantiation.

4. **Test against local heritage-types 2.0.0** before the upstream PyPI
   upload takes effect:

   ```bash
   # In HOARD, switch to a local editable install of heritage-types
   pip install -e /home/mark/Projects/heritage-types/python/heritage_models
   pytest tests/
   ```

## What HOARD does NOT need to do

- No code changes to `heritage_vocab` consumers — `heritage-vocab==2.0.0`
  only changes the fallback URI scheme; the search API is identical.
- No changes to `@heritage/types` — StratiGraph owns that path.
- No changes to `Chronology`/`Sample`/`Find` shapes — unchanged.

## Separate finding: author metadata in your `pyproject.toml`

While auditing for cross-repo compliance with this coordination thread,
I noticed that `HOARD/pyproject.toml` declares:

```toml
authors = [
    { name = "Marcus Quinn" },
]
```

This name is wrong. The canonical attribution for this codebase and
the HOARD ecosystem is **Mark Bouck** (see `LICENSE`, the heritage-types
`AGENTS.md`, and the HOARD `AGENTS.md` "Owner" line). The erroneous
attribution appears to be a substitution by an automated tool that
hallucinated a different author name. **Suggest updating to:**

```toml
authors = [
    { name = "Mark Bouck" },
    { name = "Solomon Bouck" },  # if a co-maintainer exists
]
```

The same `Marcus Quinn` substitution appears in `Libby/pyproject.toml`.
Both fixes are independent of the 2.0.0 coordination cycle and can
ship in their own PRs — but they're worth flagging here so they don't
get lost.

## Notify receipt

PyPI URL for `heritage-models==2.0.0` (paste actual on publish):
<https://pypi.org/project/heritage-models/2.0.0/>

PyPI URL for `heritage-vocab==2.0.0` (paste actual on publish):
<https://pypi.org/project/heritage-vocab/2.0.0/>
