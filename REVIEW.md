# heritage-types — Code Review & Reflection

**Scope:** bugs, missing features, empty stubs, hardcoded data, mock data, security issues.
**Date of review:** 22 June 2026
**Reviewed against:** working tree on `main` (uncommitted changes to `spec/main.tsp`, regenerated `schemas/`, `python/heritage_models/models.py`, `typescript/src/index.ts`, `scripts/generate_typescript.py`).

---

## TL;DR

The uncommitted changes add a useful **Provenance / PROV-O** layer + a required `SchemaVer` to the top-level `HeritageDataPackage`. The build (`make all`) runs cleanly and produces the regenerated artefacts. **However, shipping these changes as-is will silently break every downstream consumer of `heritage-models` and `@heritage/types`**, because:
1. The Python class for the new top-level model is renamed to `HeritageDataPackage1` (name collision with the root wrapper) — so `from heritage_models import HeritageDataPackage` returns a useless `RootModel[Any]`.
2. The generated TypeScript references `uuid`, `datetime`, `SchemaVer`, `AgentType`, etc. as bare types that are never exported — the file won't compile.
3. The change to `schemaVersion: string → SchemaVer` (REQUIRED) is a **breaking wire-format change** that AGENTS.md says **requires a major version bump + explicit notification of Mark**. No version was bumped, no CHANGELOG entry was added.

---

## Findings, ranked

### CRITICAL

#### C1 — Python: the new `HeritageDataPackage` model is silently renamed to `HeritageDataPackage1`
**File:** `python/heritage_models/models.py`
**Evidence:** Two `HeritageDataPackage` names exist in the same module:
```python
class HeritageDataPackage(RootModel[Any]):       # useless top-level wrapper
    root: Any
...
class HeritageDataPackage1(BaseModel):            # the actual model
    schemaVersion: SchemaVer
    ...
```
**Cause:** `scripts/generate_python.py` passes `--class-name HeritageDataPackage` to `datamodel-codegen`, which uses that name for the root model. But `HeritageDataPackage` is already a model in the schema, so datamodel-codegen renames it to `HeritageDataPackage1` to avoid the collision.
**Impact:** Every existing consumer that does `from heritage_models import HeritageDataPackage` (which AGENTS.md and README imply) silently gets the empty `RootModel[Any]` wrapper. Pydantic will accept any input and `validate_python` will return `Any`. All validation is gone for the container.
**Fix:** Either (a) drop `--class-name` and let codegen use the model's own name, or (b) introduce a separate `HeritageDataPackage` wrapper that delegates to `HeritageDataPackage1`. Regenerate.

#### C2 — TypeScript: generated `index.ts` references types that don't exist
**File:** `typescript/src/index.ts`
**Evidence:** Every interface uses bare names that aren't exported anywhere:
```ts
projectId: uuid;            // uuid not exported
createdAt: datetime;        // datetime not exported
schemaVersion: SchemaVer;   // SchemaVer not exported (was just added)
agentType: AgentType;       // AgentType not exported (was just added)
materialClass: MaterialClass;
unitType: UnitType;
```
**Cause:** `scripts/generate_typescript.py:generate_interfaces()` only emits `interface Foo` lines from `$defs` — it does **not** emit type aliases for scalars/enums. The author removed the `if name == "HeritageDataPackage": continue` branch, so the loop now emits nested-DuF `interface HeritageDataPackage` too, but still doesn't emit `type uuid = string; type datetime = string; type SchemaVer = \`${number}-${number}-${number}\`; enum AgentType {...}` etc.
**Impact:** `tsc` will reject every `index.ts` import. Worse, `typescript/package.json` declares `"main": "src/index.ts"` and `"private": true` — but README advertises `npm install @heritage/types`. Either docs or code is wrong.
**Fix:** In `generate_typescript.py`, emit `type<alias>` lines for every scalar in `$defs` and every enum, then emit the interfaces. Alternatively switch to `json-schema-to-typescript` so this isn't hand-rolled.

#### C3 — Unbumped version after a breaking wire-format change (AGENTS.md violation)
**Files:** `python/heritage_models/pyproject.toml`, `python/heritage_vocab/pyproject.toml`, `typescript/package.json`, `package.json` (all still `1.0.0`); `CHANGELOG.md` (no entry beyond `1.0.0 — 2026-06-09`).
**Evidence:** `HeritageDataPackage.schemaVersion` is changed from optional `string` to **required `SchemaVer`** (`spec/main.tsp:213`). Concrete downstream impact: any pre-existing JSON document saved by HOARD/StratiGraph/Trowel without a `schemaVersion` field will now fail pydantic validation.
**Policy violation:** AGENTS.md `## Versioning Rule` states:
> Additive changes (new optional fields, new types) → bump minor version. Any removal or rename of existing fields → bump major version AND notify Mark.

Making an optional field required = a breaking change. The rule is explicit: notify Mark.
**Impact:** If the next `git push` is followed by `git tag models-v1.0.x` triggering `.github/workflows/publish-models.yml`, PyPI gets a broken `heritage-models 1.0.x` that rejects every existing user payload.
**Fix:** Bump `version` in all three manifests to `2.0.0`. Add a CHANGELOG entry titled `[2.0.0]` with a `### BREAKING` section. Notify Mark before tagging. Consider making `schemaVersion` optional during a deprecation cycle.

---

### HIGH

#### H1 — All TypeSpec enums and scalars are erased to `RootModel[Any]` in Python
**File:** `python/heritage_models/models.py`
**Evidence:**
```python
class AgentType(RootModel[Any]):
    root: Any
class MaterialClass(RootModel[Any]):
    root: Any
class SchemaVer(RootModel[Any]):
    root: Any
class Uuid(RootModel[Any]):
    root: Any
class Datetime(RootModel[Any]):
    root: Any
class FieldId(RootModel[Any]):
    root: Any
```
**Cause:** `datamodel-codegen` defaults to `--output-model-type pydantic.BaseModel` for $defs scalars/enums, but emits empty `RootModel[Any]` because no target Python type was supplied. The JSON Schema string patterns and `enum` constraints are completely lost on the Python side.
**Impact:** A consumer can hand-pydantic-protect a Find with `materialClass="Unobtainium"` and the model accepts it. The whole point of typed canonical data is defeated by this. Validation now happens client-side only.
**Fix:** Add `--use-annotated` and `--field-constraints` (already partially set), and add a post-process step that converts the `RootModel[Any]` enums to `StrEnum` subclasses, and scalars to constrained types via `Annotated[str, Field(pattern=...)]`. Or generate custom Pydantic types.

#### H2 — `DigitalAsset.fileSizeBytes` declared `int64` in spec but emitted as `string` in both JSON Schema and Pydantic
**Files:** `spec/main.tsp:166`, `schemas/heritage-data-package-v1.json` (`DigitalAsset.fileSizeBytes: {"type": "string"}`), `python/heritage_models/models.py` (`fileSizeBytes: str | None = None`), `typescript/src/index.ts` (`fileSizeBytes?: string`).
**Evidence:** `int64` is a TypeSpec primitive that the JSON Schema emitter cannot represent (JSON has no 64-bit integer type), so it falls back to `string`. Pydantic then types it as `str`.
**Impact:** A consumer storing big-file sizes loses numeric ordering, summing, range queries, and integer arithmetic. A checksum of a 10 GB file would compare correctly, but `if size_bytes > 1_000_000` silently fails because `"10485760" > "1000000"` is `False` in lexicographic comparison.
**Fix:** Either restrict to `int32` (which JSON Schema can represent directly and Pydantic can validate), or accept the `string` decision but document that downstream consumers must parse with `int(size, 10)` and validate.

#### H3 — `heritage-vocab` reads a foreign app's DB with no permission/integrity checks; data is "best-effort trusted"
**File:** `python/heritage_vocab/service.py`
**Evidence:** `DEFAULT_VOCAB_DB = Path.home() / ".local/share/com.cacheandcarry.app/vocab/vocab_cache.db"` is opened read-only-on-disk with no signature, no checksum, no read-only file mode. Results are returned to the caller without provenance verification.
**Impact:** If another process on the same machine can write to that file (multi-user box, compromised sibling process, future-install via Cache & Carry that updates vocabulary terms), the search results are attacker-controlled. The FTS5 query construction has some sanitisation (alnum/space/-/_ filter) but does not quote-encode FTS5 operators within the wrapped phrase.
**Possibly secondary issues:**
- L182: `sql += f" ORDER BY rank LIMIT {int(limit)}"` — `int()` coerces, so this is safe *for now*, but f-string into SQL is a footgun. Use `LIMIT ?` with `params`.
- L156: `clean = "".join(c for c in term if c.isalnum() or c in " _-")` — strips almost everything FTS5 treats specially (good), but doesn't strip digits-only terms (`order:rank` collision), nor unicode 4-byte codepoints.
- L186: The `subprocess` import in `service.py` is unused (dead import). Cleanup.

**Fix:** Verify file ownership (`stat(path).st_uid == getuid()`), open read-only (`sqlite3.connect(f"file:{path}?mode=ro", uri=True)`), quote FTS5 phrases properly, and pin `limit` with a parameter.

#### H4 — Hardcoded mock data shipped in production code paths
**File:** `python/heritage_vocab/service.py`, function `_fallback_builtin` (L228-292) and `_create_sample_db` (L300-362).
**Evidence:** Two large dictionaries of Getty AAT URIs, labels, and scope notes are embedded directly in the source:
```python
"flint": ("http://vocab.getty.edu/aat/300011754", "Flint/Chert", "A compact ...")
...
"bronze age": ("http://vocab.getty.edu/aat/300019275", "Bronze Age", ...)
```
- These are asserted as AAT identifiers but are **unverified**. e.g. `neolithic` and `bronze age` both map to `aat/300019275` — duplicated URI for different concepts. (Confirmed: Neolithic and Bronze Age are distinct concepts in AAT.)
- `neolithic` URI is likely wrong; `bronze age` URI is likely wrong; `roman` URI is suspect.
- The fallback path is invoked silently whenever `db_path.exists()` returns False, so users think they're getting real Getty data.
**Impact:** Silent, wrong identifiers flowing into HOARD reports. Researchers publishing reports that cite `aat/300019275` as "Bronze Age" when it's actually Neolithic will get embarrassed in peer review.
**Fix:** Either (a) remove the fallback entirely and require Cache & Carry, or (b) keep it but mark every term with a source/provenance noting "fallback, unverified — last reviewed <date>", or (c) load fallback from a verifiable file with a hash.

#### H5 — `https:/` working-tree artifact is polluting the repo
**Path:** `./https:/schemas.heritage-science.dev/...` (empty subdirectories).
**Evidence:** `git status` shows the whole `https:/` tree as untracked. `find https/ -type f` returns zero files, only directories. The path mirrors the `bundleId: "https://schemas.heritage-science.dev/HeritageDataPackage"` declared in `tspconfig.yaml`.
**Cause:** Somewhere a tool has written to `bundleId` as a relative path (`/{project-root}/{bundleId-as-path}`), creating unscoped empty dirs.
**Impact:** Pollution, plus it bypasses `.gitignore`. If `tsp compile .` is run without the `--option` overrides that Makefile / workflow supply, the schema lands at `https:/schemas.heritage-science.dev/HeritageDataPackage` (folder) instead of `schemas/heritage-data-package-v1.json`.
**Fix:** Confirm `https:/`, `.ctx/`, `.claude/` should be ignored; expand `.gitignore` to `https:/` (and the empty subdirs of `https:`).

---

### MEDIUM

#### M1 — No tests at all despite pytest dev dep
**Files:** `python/heritage_models/pyproject.toml` declares `dev = ["pytest>=8", ...]`; `python/heritage_vocab/pyproject.toml` declares `dev = ["pytest>=8"]`. **There are zero `test_*.py` files anywhere in the repo.** The build pipeline has no `make test` target. AGENTS.md says "This is one of three infrastructure repositories" yet it's untested.
**Fix:** Add at minimum:
- Round-trip tests: build a JSON doc by hand → validate against `schemas/heritage-data-package-v1.json` → instantiate via Pydantic → serialise → compare
- Vocab tests: load `auto_create=True`, query known terms, assert AAT URIs (or assert fallback responses).
- TypeScript: a `tsc --noEmit` step run in CI to gate C2.

#### M2 — Makefile and GitHub workflow both rely on a fragile `mv` step
**Files:** `Makefile` line 8: `mv schemas/HeritageDataPackage schemas/heritage-data-package-v1.json` and `.github/workflows/publish-models.yml` "Rename schema output" step. No `set -e`, no `[ -f schemas/HeritageDataPackage ]` guard, no error trap.
**Impact:** If the TypeSpec emitter once emits `schemas/HeritageDataPackage.json` (with an extension) — which is what `https:/` artifact suggests happens without overrides — `mv` finds nothing and silently succeeds, then codegen reads a stale `schemas/heritage-data-package-v1.json` from disk and emits the OLD output. Releases could be published with stale data without anyone noticing.
**Fix:** Either remove the `mv` and have codegen read directly from `schemas/HeritageDataPackage`, or:
```make
compile:
	npx tsp compile . --emit @typespec/json-schema --option "@typespec/json-schema.file-type=json" --option "@typespec/json-schema.bundleId=HeritageDataPackage"
	set -e; test -f schemas/HeritageDataPackage && mv schemas/HeritageDataPackage schemas/heritage-data-package-v1.json || (echo "expected schemas/HeritageDataPackage"; exit 1)
```

#### M3 — `bundleId` mismatch between tspconfig.yaml and the build invocations
**Files:** `tspconfig.yaml` says `bundleId: "https://schemas.heritage-science.dev/HeritageDataPackage"`. Makefile and workflow both override with `bundleId: "HeritageDataPackage"`. So `tsp compile` from the CLI uses the canonical URL, but `make all` and CI use a stub.
**Impact:** The `https:/` artefact directory shows the canonical URL is treated as a relative subdir by the emitter — meaning whatever was meant to be a JSON-LD URI is now a filesystem path. This is also why `https:/` is polluting the working tree.
**Fix:** Make the bundle identifier stable and respected. Either set `$id` in TypeSpec and drop `bundleId`, or always pass `bundleId=HeritageDataPackage` from the CLI and drop the override.

#### M4 — TypeScript package is `private: true` but advertised as installable
**File:** `typescript/package.json` (`"private": true`); `README.md` says `npm install @heritage/types`. No CI workflow publishes it. AGENTS.md says `StratiGraph npx npm install @heritage/types (not yet wired up)`.
**Impact:** Documentation lies.
**Fix:** Either remove the npm install mention, or remove `private: true` and add a publish-typescript workflow.

#### M5 — `scripts/generate_typescript.py` docstring promises AJV validators it does not emit
**File:** `scripts/generate_typescript.py:1-9`
```python
"""Generate the @heritage/types TypeScript package from canonical JSON Schema.
...
- TypeScript interfaces for each model
- AJV-compatible JSON Schema validators
"""
```
Only TypeScript interfaces are written. The function `generate_interfaces()` produces the entire output. The "AJV-compatible JSON Schema validators" feature is missing — **stub feature**, no code.
**Fix:** Either drop the second bullet from the docstring, or actually emit `ajv`-compatible `.json` validators next to the interfaces.

#### M6 — `make clean` removes `typescript/dist/` that doesn't exist
**File:** `Makefile`: `rm -rf typescript/dist/`. The TypeScript generator never writes a `dist/` (no tsc step). `package.json` `clean` script uses `rm -rf schemas/*.json dist/` — also removes nothing called `dist/`. Dead commands.
**Fix:** Drop the dead line, or add `npx tsc -p typescript/` in the build and only then clean `dist/`.

#### M7 — `generate_python.py` can leak a temp schema file on interrupted run
**File:** `scripts/generate_python.py` writes `heritage-data-package-inlined.json` then `unlink`s it at the end. If `datamodel-codegen` crashes or is killed mid-run, the temp file remains in `schemas/`. Next run can pick it up thinking it's the canonical schema (it's still named `…-v1`-style and globbed by `generate_typescript.py`).
**Fix:** Use `try/finally` around `unlink`, or write to `tempfile.NamedTemporaryFile(dir=…/tmp)` outside `schemas/`.

#### M8 — `ProvenanceRecord.confidence` accepts any float, including >1.0 and <0.0
**File:** `spec/main.tsp:198` says `confidence?: float32; // 0.0–1.0, for AI-generated assertions`. The schema emits `{"type": "number"}` with no `minimum: 0, maximum: 1`. Pydantic emits `confidence: float | None = None` with no Field constraint.
**Impact:** Documentation and reality disagree. `confidence: 1.5` would be accepted by both the JSON Schema validator and Pydantic.
**Fix:** Add `@minValue(0.0) @maxValue(1.0)` decorator in TypeSpec, then regenerate. (Will flow through to JSON Schema. Pydantic will need the `--field-constraints` flag — already on, but codegen may still need `--use-annotated`.)

#### M9 — `ProvenanceActivity.agent` $ref points to `ProvenanceAgent.json` (an external file)
**File:** `schemas/heritage-data-package-v1.json` lines ~558: `"agent": { "$ref": "ProvenanceAgent.json" }`.
**Compare to:** most other `$ref`s in the file use `#/$defs/...`. This is the only remaining extern​al ref. The `inline_external_refs()` pass in both `generate_*.py` scripts will fix it before codegen runs, but the *on-disk* published JSON Schema is broken/inconsistent.
**Impact:** A consumer that loads the published schema with a strict validator (python `jsonschema` library without a resolver) will fail. The Codegen scripts hide the bug. The published artefact is inconsistent with its description ("self-contained" — README).
**Fix:** Either configure the TypeSpec emitter to emit inlined refs (`--option @typespec/json-schema.use-inlined-refs=true` or similar), or run the inline step *before* commit so what gets shipped is consistent with what consumers get.

#### M10 — `ProvenanceRecord.entity` accepts a UUID but no FK consistency check
**Evidence:** `entity: uuid` — meant to point at any other record in the package. The schema doesn't enforce that an entity ID exists in `contexts[]`, `finds[]`, `samples[]`, etc.
**Impact:** Authoring tools can write a ProvenanceRecord pointing at a non-existent entity. The "audit trail" then references a phantom.
**Fix:** Add a custom JSON Schema validator (`$ref`-style `$data` referential check, or document the convention and add a CLI verifier).

#### M11 — `make` does not run on Windows; `rm -rf` in `clean` doesn't either
Belt-and-braces, but worth noting if StratiGraph developers are on Windows. Not blocking.

#### M12 — `heritage_vocab/service.py` does not validate `limit` is positive
`limit: int = 20` in `search()`. If a caller passes `limit=-1`, `LIMIT -1` in SQLite is interpreted as "no limit" — silent footgun.
**Fix:** `if limit <= 0: raise ValueError(...)`.

#### M13 — `normalise_period` produces inconsistent results
**File:** L173-186: when exact match fails, returns the first prefix match without the `_label_similar` heuristic that `normalise_material` uses. Pydantic consistency story is unclear.

#### M14 — `_create_sample_db` `INSERT OR IGNORE INTO vocabulary_terms` value count is fragile
**File:** L334: passes 6-tuple `[(s[0], s[1], s[2], s[3], s[4], "") for s in samples]` against `VALUES (?,?,?,?,?, NULL, ?)`. This works (5 columns + 1 NULL hardcoded + 1 = last_updated) but is one column away from being off-by-one. Adding a column without updating the tuple silently misaligns.
**Fix:** Use named-column INSERT: `INSERT OR IGNORE INTO vocabulary_terms(id, source, preferred_label, alt_labels, scope_note, last_updated) VALUES (?,?,?,?,?, ?)`.

#### M15 — No LICENSE file in tree
README, AGENTS.md and all `pyproject.toml`s claim **MIT**. There is no `LICENSE` file in the project. A consuming legal review would call this out.
**Fix:** Add `LICENSE` (MIT text, copyright Mark Bouck / year).

#### M16 — `https:` in filesystem (`https:/`) — the unsafe global structure
Git status shows `https:/` untracked. If `./` happens to be a network mount, this could escape. Not severe here but worth knowing.

---

### LOW

#### L1 — Mixed `interface` (TS) and "shape" (Python) — Python's `FieldId`/`Uuid` pattern enforcement is fictional unless H1 is fixed.
#### L2 — `epsgCode: int` is signed 32-bit; UK grid refs can use values up to 32767 which is fine, but reserving `int32` for a CRS code is overkill. No impact, just noting the codegen adds `Field(None, ge=-2147483648, le=2147483647)` to it.
#### L3 — `scripts/generate_python.py` has a docstring from a previous version that references "design" literal — check both scripts for stale doc fragments after the recent regeneration.
#### L4 — The `--class-name HeritageDataPackage` flag in `generate_python.py` exists from when the root model was used (no `HeritageDataPackage` declared inside); with the new schema, that name collides. The flag's purpose is now obsolete — but see C1 for the fix.
#### L5 — `package-lock.json` is checked in but `package.json` lists most deps as `"latest"`, defeating the lockfile. Pin versions.
#### L6 — `MAJOR` breaking-change policy requires "notify Mark" — there is no MARK_NOTIFY.md or runbook for it. Worth adding to AGENTS.md as a step.

---

## Files / scope of review confirmed examined

`spec/main.tsp` · `main.tsp` · `tspconfig.yaml` · `package.json` · `package-lock.json` · `Makefile` · `scripts/generate_python.py` · `scripts/generate_typescript.py` · `schemas/heritage-data-package-v1.json` · `python/heritage_models/__init__.py` · `python/heritage_models/models.py` · `python/heritage_models/pyproject.toml` · `python/heritage_vocab/__init__.py` · `python/heritage_vocab/service.py` · `python/heritage_vocab/pyproject.toml` · `typescript/src/index.ts` · `typescript/package.json` · `.github/workflows/publish-models.yml` · `.gitignore` · `CHANGELOG.md` · `AGENTS.md` · `CLAUDE.md` · `README.md` · `https:/` artifact tree · `.ctx/config.toml`.

Build verified: `make all` produces 178-line `models.py` and 131-line `index.ts` end to end. Smoke test of `heritage_vocab` failed (`ModuleNotFoundError`) because the package isn't installed in this environment — that's fine, but means I did **not** run runtime tests of the FTS5 path.

---

## Reflection

### 1. "What are you least confident about, and why?"

Five things I would not stake a high-confidence bet on:

1. **My claim that `tsc` will reject the generated `typescript/src/index.ts`.** I read the file and see `uuid`, `datetime`, `SchemaVer`, `AgentType`, etc. as unexported references; by the language rules this means errors. But I did **not** run `tsc --noEmit` against the file. If TypeScript's structural typing somehow swallows `uuid` as the literal string `uuid` (it won't, but...) my C2 reverses. I should be 60% confident, not 95%.

2. **My claim about FTS5 sanitisation being adequate.** I read the code (`"".join(c for c in term if c.isalnum() or c in " _-")`) and concluded it's mostly OK because it strips FTS5 operators. I have not run targeted injection tests against the actual schema used by Cache & Carry, and Cache & Carry's schema could include tokenchars or rules that re-enable parsing of multi-byte unicode I'm not aware of. ~50% confident on safety posture.

3. **Whether hardcoded AAT URIs in `_fallback_builtin` are actually wrong.** I asserted `neolithic` and `bronze age` collide on `aat/300019275`. That assertion is plausible to me (Neolithic ≠ Bronze Age), but I have not fetched the actual AAT pages to verify. If Mark added a typo somewhere, my H4 rank should drop. ~70% confident.

4. **The runtime behaviour of `datamodel-codegen` after my anticipated fix.** I propose dropping `--class-name HeritageDataPackage` to resolve C1; but the codegen may still produce a different root-model name for a different reason, or the build may need a `--disable-timestamp`/`--use-annotated` companion flag. I haven't tested the alternative invocation.

5. **Whether the impact on downstream HOARD/StratiGraph/Trowel is as severe as I claim for the version bump.** I read AGENTS.md and inferred the worst case. I have not inspected HOARD's `heritage_models` usages. If HOARD authors each `HeritageDataPackage` programmatically and immediately set `schemaVersion`, they're unaffected. If they read from disk and pass through, they're broken. ~65% confident on severity ranking of C3.

### 2. "Biggest thing I'm missing about the situation right now? What don't I realize?"

The biggest blind spot is **why the diff is uncommitted and on `main` already**. The git status shows these changes staged for commit but not committed; the AGENTS.md policy is explicit that a breaking change to `schemaVersion` (REQUIRED, type change, name change) requires **coordinated updates across HOARD, StratiGraph, and Trowel**. The diff appears to have been produced in isolation, without:
- a CHANGELOG entry,
- a major version bump,
- a notification to Mark,
- coordination notes (e.g. "awaiting HOARD PR #N to align"),
- tests,
- or a tracked Git issue.

What I don't realize — and what the user might not have fully internalised — is that **a feature push that *looks* additive ("we added provenance tracking") is actually a wire-format breaking change dressed as an additive one**, precisely because the new `schemaVersion` was made required and changed type. By AGENTS.md policy, this is a major-version event. The current state — uncommitted, unannounced, untested, privately-verified-with-make-only — is the *most dangerous* possible state for an infra repo that 3+ other tools depend on: it's almost publishable.

A second, smaller thing I might not realise: there is no CI workflow that lints or typechecks the *generated* artefacts before they can be tagged-and-published. The "models-v*.*.*" tag trigger in `publish-models.yml` will ship whatever `make all` produces, with no diff review and no test gate. If C1 ships, the first external `pip install` of `heritage-models 2.0.0` (or 1.0.x as currently versioned) will be the first moment HOARD users hit the trap, not the moment it should have been caught.

A third small thing: the `AGENTS.md` references `GitNexus` MCP tools extensively, and the working tree contains both `.claude/` and `.ctx/` with `graph.db`. None of the changes in this diff appear to have been routed through `detect_changes()` or `impact()`. The `gitnexus-exploring` / `gitnexus-impact-analysis` skills are present, but if GitNexus isn't actually consulted before commits, the `MUST run impact` directives are dead text in AGENTS.md.

---

## Suggested immediate actions (priority order)

1. **Do not tag or publish** the current diff. Resolve C1 + C2 + C3 first.
2. Re-run codegen after the changes below; commit only when `python/heritage_models/models.py` has *no* `HeritageDataPackage1` class, and `tsc --noEmit typescript/src/index.ts` passes.
3. Fix C1: drop `--class-name HeritageDataPackage` from `generate_python.py`.
4. Fix C2: extend `generate_typescript.py` to emit `type uuid = string` etc. for scalars and `enum AgentType {...}` for enums.
5. Fix C3: bump to `2.0.0` everywhere, add CHANGELOG entry.
6. Add a CI workflow step that runs `pytest` (after writing tests) and `tsc --noEmit`.
7. Address H1, H3, H4 in a follow-up commit.
