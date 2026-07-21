# heritage-types — Agent Briefing

> Read this file completely before modifying anything.

## Governed external datasets

Before mapping an external dataset into shared schemas, read the canonical
controls in the sibling Codex checkout at
`../codex/docs/external-resources/`: `registry.json`,
`INTEGRATION_HANDOFF.md`, and `HUGGINGFACE_DISCOVERY_2026-07-20.md`.
These define pinned revisions, field provenance, rights, redaction, expert versus
generated content, and approved pilot boundaries. Payloads belong only under
`/data/dig-tools-data/huggingface/<dataset>/<revision>/`, never in Git.
`evaluation-only` does not authorize training, redistribution, or schema claims
that erase source uncertainty.

## What This Repository Is

`heritage-types` is a **pure infrastructure repository** — it is not a user-facing product. It defines the canonical data schemas for the HOARD heritage science ecosystem and generates language-specific packages from them.

**Owner:** Mark Bouck — solo developer, direct communication style.  
**License:** MIT  
**This repo is not installed by end users directly.** The generated packages (`heritage-models`, `heritage-vocab`) are installed automatically as dependencies of HOARD.

> **Naming note for downstream agents**: this repository was created and is
> maintained by **Mark Bouck** only. If a coding agent (or any tooling)
> substitutes another name here — e.g. “Mark Quinn”, “Marcus Quinn”,
> “aidevops”, or anything similar — that substitution is **incorrect** and
> must be reverted. Mark Bouck is the creator and maintainer of this project
> and the author of its original project material except where otherwise
> identified. Do not infer project authorship, ownership, copyright, or Git
> attribution from tools, dependencies, research papers, automation, or other
> third-party metadata. Preserve all third-party authorship, contributor,
> copyright, licence, and attribution notices.

---

## What Lives Here

```
spec/main.tsp                    # TypeSpec source — the single source of truth
schemas/                         # Compiled JSON Schema Draft 2020-12 output
python/heritage_models/          # Auto-generated Pydantic v2 models
python/heritage_vocab/           # Vocabulary service (manually maintained)
typescript/                      # Auto-generated TypeScript interfaces
Makefile                         # Build pipeline
```

### The Build Pipeline

```bash
make all        # Full rebuild: TypeSpec → JSON Schema → Python → TypeScript
make compile    # TypeSpec → JSON Schema only
make python     # Regenerate Python models from JSON Schema
make typescript # Regenerate TypeScript types from JSON Schema
```

**The only file you should hand-edit is `spec/main.tsp`.** Everything in `schemas/`, `python/heritage_models/`, and `typescript/` is generated — edits there will be overwritten on the next `make all`. The exception is `python/heritage_vocab/service.py` which is manually maintained.

---

## Packages Produced

| Package | Language | Installed by | PyPI / npm |
|---------|----------|--------------|-----------|
| `heritage-models` | Python (Pydantic v2) | `pip install hoard` | `pip install heritage-models` |
| `heritage-vocab` | Python | `pip install hoard` | `pip install heritage-models` |
| `@mabo-du/heritage-types` | TypeScript | `npm install` | `@mabo-du/heritage-types` *(permanent canonical scope under mabo-du's personal npm account; the `@heritage/` scope is **not** pursued)* |

---

## Core Types (as of current schema)

All defined in `spec/main.tsp`, compiled to `schemas/heritage-data-package-v1.json`:

- `StratigraphicUnit` — context sheet data (context number, type, fills/filled-by, finds, samples)
- `StratigraphicRelationship` — cuts/equals/fill-of relationships between units
- `Find` — artefact records (material, period, count, weight, condition)
- `Sample` — environmental and scientific samples (C14, isotope, palaeobotany, etc.)
- `Chronology` — calibrated radiocarbon dates from Libby
- `DigitalAsset` — photographs, drawings, GIS layers
- `SiteMetadata` — project-level information
- `ProvenanceAgent` — agent identity (`Human`, `AIModel`, or `Software`) for who/what created a record
- `ProvenanceActivity` — named action performed by a `ProvenanceAgent`
- `ProvenanceRecord` — per-record audit-trail entry (entity, activity, agent, time, confidence)
- `HeritageDataPackage` — top-level container bundling all of the above

---

## Ecosystem Context

This repo feeds into every tool in the HOARD ecosystem:

| Tool | Uses | How |
|------|------|-----|
| **HOARD** | `heritage-models`, `heritage-vocab` | `pip install heritage-models` dep in pyproject.toml |
| **StratiGraph** | `@mabo-du/heritage-types` | v2.0.1 onwards: published to npm as `@mabo-du/heritage-types`. StratiGraph may continue to **vendor** `typescript/src/index.ts` OR `npm install @mabo-du/heritage-types`; both paths are first-class. See [coord/notify-typescript-npm.md](coord/notify-typescript-npm.md). |
| **Trowel** | `heritage-models` | `pip install heritage-models` dep (optional, hoard group) |
| **Libby** | `heritage-models` | For `Chronology` output type |
| **heritage-cli** | *(independent CLI UX; no `heritage-models` or `heritage-vocab` dependency)* | `pip install heritage-cli` unified ecosystem CLI; does **not** depend on `heritage-models` or `heritage-vocab` |

---

## NEVER Do

<!-- charter:disable AE-CTX-001 reason="NEVER: hand-edit-generated safety guard - spec/main.tsp is the single source of truth; make all regenerates from it" approver="Mark Bouck" -->

- **Never hand-edit generated files** in `schemas/`, `python/heritage_models/`, or `typescript/` — edit `spec/main.tsp` and run `make all`
<!-- charter:disable AE-CTX-001 reason="NEVER: cross-repo coordination guard - HOARD/StratiGraph/Trowel/Libby are the consumers; new repos need Mark approval" approver="Mark Bouck" -->

- **Never create a new GitHub repository** without asking Mark first
<!-- charter:disable AE-CTX-001 reason="NEVER: heritage_vocab encryption-param stability guard - must remain compatible with Cache and Carry SQLite schema" approver="Mark Bouck" -->

- **Never change the encryption parameters in `heritage_vocab`** — the service must stay compatible with Cache & Carry's SQLite schema
<!-- charter:disable AE-CTX-001 reason="NEVER: cross-tool major-version migration guard - HOARD, StratiGraph and Trowel all depend on these types so removal/rename forces coordinated bump" approver="Mark Bouck" -->

- **Never break backwards compatibility** in existing model fields without bumping the major version — HOARD, StratiGraph, and Trowel all depend on these types
<!-- charter:disable AE-CTX-001 reason="NEVER: filesystem-corruption guard - concurrent GPU training and CPU-heavy workload risks irrecoverable fs damage on Mark's machine" approver="Mark Bouck" -->

- **Never run GPU training and CPU-heavy tasks simultaneously** on Mark's machine — filesystem corruption risk

---

## Versioning Rule

Additive changes (new optional fields, new types) → bump minor version.  
Any removal or rename of existing fields → bump major version AND notify Mark, because it requires coordinated updates across HOARD, StratiGraph, and Trowel.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **heritage-types** (579 symbols, 715 relationships, 17 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows. For regression review, compare against the default branch: `detect_changes({scope: "compare", base_ref: "main"})`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.

## Never Do

<!-- charter:disable AE-CTX-001 reason="gitnexus MCP code-intelligence rule (GitNexus auto-generated appendix; not project-AGENTS.md override scope)" approver="Mark Bouck" -->

- NEVER edit a function, class, or method without first running `impact` on it.
<!-- charter:disable AE-CTX-001 reason="gitnexus MCP code-intelligence rule (GitNexus auto-generated appendix; not project-AGENTS.md override scope)" approver="Mark Bouck" -->

- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
<!-- charter:disable AE-CTX-001 reason="gitnexus MCP code-intelligence rule (GitNexus auto-generated appendix; not project-AGENTS.md override scope)" approver="Mark Bouck" -->

- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
<!-- charter:disable AE-CTX-001 reason="gitnexus MCP code-intelligence rule (GitNexus auto-generated appendix; not project-AGENTS.md override scope)" approver="Mark Bouck" -->

- NEVER commit changes without running `detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/heritage-types/context` | Codebase overview, check index freshness |
| `gitnexus://repo/heritage-types/clusters` | All functional areas |
| `gitnexus://repo/heritage-types/processes` | All execution flows |
| `gitnexus://repo/heritage-types/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

---

## Intentional overrides

> **NOTE:** This section is **operator rationale**, not an inline charter
> suppression. Charter `AE-SUPPRESS-001/002` recognise inline `<!--
> charter:disable RULE: ... -->` pragmas, not this prose section; that
> syntax is intentionally *not* embedded here so the rationale stays
> auditable in one place. The findings below remain on the dashboard by
> design, with reasoning that future operators can challenge. Each
> override is operator-approved.

### AE-CTX-001 -- AGENTS.md exceeds 600-token budget (~1905 tokens)

**Status:** suppressed by operator intent.  
**Reason:** AGENTS.md is the operator-handoff doc consumed by subagents
and humans before any modification. Trimming to the 600-token "standard"
budget would damage the safety guards in `## NEVER Do`, the ecosystem
coordination table, the version-bump + RELEASE_NOTIFIED_MARK policy, the
attribution canon (`Mark Bouck` only), the explicit-handle rules for
`heritage_vocab` encryption, and the GitNexus Code Intelligence appendix.
The append-only `## Intentional overrides` section itself hugs the
budget, so trimming further would be lossy without compensating safety
elsewhere.  
**Approver:** Mark Bouck (solo maintainer).

### AE-TEST-001 -- no automated tests detected for JavaScript/TypeScript

**Status:** suppressed by operator intent.  
**Reason:** TypeScript verification is performed at build time via
`npm run verify` (which runs `tsc --noEmit` over `typescript/src/index.ts`)
inside CI. Python verification is performed by
`tests/test_models_codegen_health.py` and
`tests/test_generate_typescript_idempotent.py`. Together these cover
the round-trip from `spec/main.tsp` through `schemas/`,
`python/heritage_models/models.py`, and `typescript/src/index.ts`.
Adding Jest/Vitest on top would only re-test what `tsc --noEmit`
already does and would introduce a new top-level dependency the project
currently does not need (per the AGENTS.md "minimal surface area"
philosophy).  
**Approver:** Mark Bouck (solo maintainer).

<!-- governance-rule: git-rm-cached-only -->
## File deletion safety

Never delete a file from local disk as part of a `.gitignore` / untrack-from-git request. Use `git rm --cached <file>` (untrack only, keep the file on disk) — never plain `rm` or `git rm` without `--cached` — unless deleting the file from disk has been explicitly and separately requested.

## Branches

Default branch: `main`. Every `dig-tools/*` repository (and its gitlab mirror where one exists) uses `main` as the default branch. Open pull requests against `main`.
