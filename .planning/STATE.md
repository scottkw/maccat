---
gsd_state_version: 1.0
milestone: v3.0.0
milestone_name: Markdown Catalog Format
status: executing
stopped_at: v3.0.0 ROADMAP created — 3 phases (30-32), coarse granularity, 12/12 requirements
last_updated: "2026-06-18T23:20:48.547Z"
last_activity: 2026-06-18 -- Phase 32 execution started
progress:
  total_phases: 3
  completed_phases: 2
  total_plans: 7
  completed_plans: 5
  percent: 67
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-18)

**Core value:** A single run produces one complete, restorable snapshot of a machine's software *and* tooling extensions — accurate enough to rebuild the environment from, degrading gracefully when any source isn't installed.
**Current focus:** Phase 32 — convert-command

## Current Position

Phase: 32 (convert-command) — EXECUTING
Plan: 1 of 2
Status: Executing Phase 32
Last activity: 2026-06-18 -- Phase 32 execution started

## Performance Metrics

**Velocity:**

- Total plans completed: 38 (prior milestones)
- Average duration: - min
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 30. Markdown Emitter & `.md` Plumbing | 0/TBD | - | - |
| 31. Markdown-Only Reinstall Parser | 0/TBD | - | - |
| 32. Convert Command | 0/TBD | - | - |

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- **Roadmap (2026-06-18):** v3.0.0 → 3 phases (coarse granularity), Phases 30-32. Order driven by
  the round-trip contract: the markdown emitter + `.md` plumbing land first (Phase 30) because both
  the reinstall parser and convert depend on it; then the markdown-only reinstall parser (Phase 31)
  which re-locks the parser↔emitter round-trip; then the convert command (Phase 32) which reuses the
  emitter and the retained legacy text parser.

- **Phase 30 (MD-01..05, FILE-01, FILE-02):** Shared markdown emitter in `catalog/format.py` —
  YAML frontmatter (computer / hostname / generated timestamp / maccat version) + `#` title + one
  `##` section per source rendering a uniform `Name | Version | ID` table; empty cell for missing
  version/ID, `(none found)` for empty sources. Deterministic + stably sorted (byte-stable across
  repeated runs, FMT-04), secret-clean (FMT-03, identity-only MCP/AI-CLI), FMT-01 upheld. Move the
  filename pattern, newest-per-computer retention glob, archive prune glob, and git add/commit
  discovery from `.txt` → `.md` (replace the glob, don't duplicate). Format-only: 22 sections + their
  collected data are UNCHANGED. Breaking format change (precedent: v2.0.0).

- **Phase 31 (RIN-01, RIN-02):** `reinstall/parser.py` parses the new markdown (frontmatter +
  per-section tables) into the typed `ParsedCatalog`; the parser↔emitter round-trip contract test is
  re-locked against the markdown emitter (replaces, not duplicates, the v2.1.0 plain-text lock).
  `maccat reinstall` consumes markdown only; a legacy `.txt` fails with a clear "convert it first"
  message — no silent partial parse, nothing executed.

- **Phase 32 (CONV-01..03):** `maccat convert --from PATH` reads ONE legacy `.txt` via the RETAINED
  legacy text parser (the existing `parse_catalog` stays as the legacy reader for convert input),
  rewrites the full contents through the Phase 30 markdown emitter, writes the `.md`, removes the old
  `.txt`, and stages both in a single commit (`--no-commit` does the file ops without git). Degrades
  gracefully on malformed/partial input (warn + skip, never abort or fabricate), never executes
  anything. Single-file only (bulk convert deferred → CONV-bulk).

- **Cross-cutting:** stdlib-only (no new pip deps), ruff + mypy --strict clean, output byte-stable
  across repeated runs. The shared markdown emitter is the SINGLE source of both catalog generation
  (MD-*) and convert output (CONV-*); RIN round-trips against that same emitter — keep the three in
  lockstep.

### Pending Todos

None.

### Blockers/Concerns

- **Round-trip contract is the central invariant:** the markdown emitter (`catalog/format.py`) and
  `reinstall/parser.py` must stay lossless against each other across all 22 sections + all
  `emit_item` line shapes. Re-lock the contract test in Phase 31; do not let convert (Phase 32) or
  generation (Phase 30) drift the emitter without updating the parser.

- **Two parsers coexist after this milestone:** the LEGACY plain-text `parse_catalog` (read-only,
  used by `convert` to read old `.txt`) and the NEW markdown parser (used by `reinstall`). Don't
  conflate them — reinstall must NOT accept `.txt`.

- **Breaking change:** existing `.txt` catalogs on disk become non-reinstallable until `convert`ed.
  FILE-01 retention now targets `.md` — a stray legacy `.txt` must be left untouched, not pruned.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Catalog/restore | DIFF-01 — catalog diffing / change reports | v2+ | 2026-06-18 |
| Convert scope | CONV-bulk — bulk / folder-wide convert (`--computer NAME` / all catalogs) | v2+ | 2026-06-18 |
| Browser state | CHR-02 / FF-02 / Edge / Brave — extension enabled/disabled state | v2+ | 2026-06-12 |
| Distribution | PKG-04 — pipx/PyPI as second distribution channel | future | 2026-06-14 |
| Restore | RST-03 — capture & restore Homebrew taps | v2+ | 2026-06-18 |
| Restore | RST-04 — best-effort AI-CLI tooling restore (beyond checklist) | v2+ | 2026-06-18 |
| Safari content blockers | SAF-02 — `com.apple.Safari.content-blocker` plugin point | v2+ | 2026-06-17 |
| Stale artifact | Quick task `260614-ckx-fix-interactive-machine-label-ux` (status: missing) — predates v2.0.0, not in scope | deferred | 2026-06-16 |
| Code hygiene | ~88 stale `update-list.sh:NNNN` code-comment cross-refs (out of ZSH-04 scope) | deferred | 2026-06-16 |
| Edge denylist | Complete Edge component ID denylist (beyond Chrome baseline) — requires real Edge install | v2+ | 2026-06-17 |

## Session Continuity

Last session: 2026-06-18
Stopped at: v3.0.0 ROADMAP created — 3 phases (30-32), coarse granularity, 12/12 requirements
  mapped (Phase 30: MD-01..05 + FILE-01/02; Phase 31: RIN-01/02; Phase 32: CONV-01..03). 100%
  coverage, no orphans/duplicates. ROADMAP.md + REQUIREMENTS.md traceability + STATE.md written.
Resume file: None.

## Operator Next Steps

1. **Plan Phase 30** — `/gsd:plan-phase 30` (Markdown Emitter & `.md` Plumbing). This is the keystone
   phase; the emitter it produces anchors the round-trip for Phases 31 and 32.

2. Then execute 30 → 31 → 32 in numeric order.

**Note (carried from v2.2.0):** tag `v2.2.0` push status — confirm whether v2.2.0 was published
before starting v3.0.0 release work. v3.0.0 is a breaking format change (major bump).
