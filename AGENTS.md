# heritage-types — Agent Briefing

> Read this file completely before modifying anything.

## What This Repository Is

`heritage-types` is a **pure infrastructure repository** — it is not a user-facing product. It defines the canonical data schemas for the HOARD heritage science ecosystem and generates language-specific packages from them.

**Owner:** Mark Bouck — solo developer, direct communication style.  
**License:** MIT  
**This repo is not installed by end users directly.** The generated packages (`heritage-models`, `heritage-vocab`) are installed automatically as dependencies of HOARD.

> **Naming note for downstream agents**: this repository was created and is
> maintained by **Mark Bouck** only. If a coding agent (or any tooling)
> substitutes another name here — e.g. “Mark Quinn”, “Marcus Quinn”,
> “aidevops”, or anything similar — that substitution is **incorrect** and
> must be reverted. The sole authoritative attribution is to Mark Bouck;
> do not invent, infer, or assign authorship to anyone else. Citations,
> commits, package metadata, and changelogs derived from this repo should
> preserve that name verbatim.

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
| `@heritage/types` | TypeScript | — | *(internal-only; vendor `typescript/src/index.ts` directly — see [RELEASE.md](RELEASE.md))* |

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
| **StratiGraph** | `@heritage/types` *(vendored)* | Repository is **private**; StratiGraph vendors `typescript/src/index.ts` rather than installing from npm. See [RELEASE.md](RELEASE.md). |
| **Trowel** | `heritage-models` | `pip install heritage-models` dep (optional, hoard group) |
| **Libby** | `heritage-models` | For `Chronology` output type |

---

## NEVER Do

- **Never hand-edit generated files** in `schemas/`, `python/heritage_models/`, or `typescript/` — edit `spec/main.tsp` and run `make all`
- **Never create a new GitHub repository** without asking Mark first
- **Never change the encryption parameters in `heritage_vocab`** — the service must stay compatible with Cache & Carry's SQLite schema
- **Never break backwards compatibility** in existing model fields without bumping the major version — HOARD, StratiGraph, and Trowel all depend on these types
- **Never run GPU training and CPU-heavy tasks simultaneously** on Mark's machine — filesystem corruption risk

---

## Versioning Rule

Additive changes (new optional fields, new types) → bump minor version.  
Any removal or rename of existing fields → bump major version AND notify Mark, because it requires coordinated updates across HOARD, StratiGraph, and Trowel.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **heritage-types** (326 symbols, 363 relationships, 7 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows. For regression review, compare against the default branch: `detect_changes({scope: "compare", base_ref: "main"})`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
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
