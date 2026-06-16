---
gsd_state_version: 1.0
milestone: v2.0.0
milestone_name: Standalone maccat — CLI Cleanup & Versioned Catalog
status: executing
stopped_at: Roadmap created — 3 phases defined (21-23), all 14 requirements mapped. Ready to plan Phase 21.
last_updated: "2026-06-16T13:58:40.280Z"
last_activity: 2026-06-16
progress:
  total_phases: 3
  completed_phases: 0
  total_plans: 2
  completed_plans: 1
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-16)

**Core value:** A single run produces one complete, restorable snapshot of a machine's software *and* tooling extensions — accurate enough to rebuild the environment from, degrading gracefully when any source isn't installed.
**Current focus:** Phase 21 — CLI Cleanup

## Current Position

Phase: 21 (CLI Cleanup) — EXECUTING
Plan: 2 of 2
Status: Ready to execute
Last activity: 2026-06-16

Progress: [█████░░░░░] 50%

## Performance Metrics

**Velocity:**

- Total plans completed: 29 (prior milestones)
- Average duration: - min
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 21. CLI Cleanup | 0/TBD | - | - |
| 22. Versioned Catalog | 0/TBD | - | - |
| 23. Retire the zsh Reference | 0/TBD | - | - |

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- **Roadmap (2026-06-16):** 3 phases (coarse), Phases 21-23. Order: CLI Cleanup first (independent, no deps), then Versioned Catalog (breaks parity goldens anyway), then zsh Retirement last (backfill tests written against final versioned collector behavior).
- **Phase 22 implementation notes:** Homebrew versions via `brew list --formula --versions` / `--cask --versions`. Setapp + web-installed via stdlib `plistlib` reading `Info.plist` CFBundleShortVersionString. Graceful degradation: name-only when version unavailable. Raw-write sections stay raw (no flush_section).
- **Phase 21 scope:** Remove from `cli.py`: `--personal`, `--office`, `--machine` args and the mutual-exclusion group. Remove from `identity.py`: the `personal`/`office`/`machine` parameters from `resolve_computer_selection`. Remove from `cli.py` step 3 guard and step 6 call. Update docstrings and `--help`.

### Pending Todos

None.

### Blockers/Concerns

None currently.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Browser state | CHR-02 / FF-02 — extension enabled/disabled state | v2+ | 2026-06-12 |
| Future tooling | CDX-02 — Codex plugins (arrived after v0.46.0) | v2+ | 2026-06-12 |
| Distribution | PKG-04 — pipx/PyPI as second distribution channel | future | 2026-06-14 |

## Session Continuity

Last session: 2026-06-16T13:58:40.271Z
Stopped at: Roadmap created — 3 phases defined (21-23), all 14 requirements mapped. Ready to plan Phase 21.
Resume file: None
