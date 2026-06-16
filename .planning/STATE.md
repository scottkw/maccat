---
gsd_state_version: 1.0
milestone: v2.1.0
milestone_name: Reinstall from Catalog
status: planning
last_updated: "2026-06-16T16:51:04.157Z"
last_activity: 2026-06-16
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-16)

**Core value:** A single run produces one complete, restorable snapshot of a machine's software *and* tooling extensions — accurate enough to rebuild the environment from, degrading gracefully when any source isn't installed.
**Current focus:** Phase 23 — Retire the zsh Reference

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-06-16 — Milestone v2.1.0 started

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
| Phase 21-cli-cleanup P02 | 8 | 3 tasks | 2 files |
| Phase 22 P22-02 | 7 | 3 tasks | 3 files |
| Phase 22 P22-03 | 110s | 2 tasks | 1 files |
| Phase 23-retire-zsh-reference P23-01 | 5min | 1 tasks | 1 files |
| Phase 23-retire-zsh-reference P02 | 120 | 3 tasks | 43 files |
| Phase 23-retire-zsh-reference P03 | 5m | 2 tasks | 1 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- **Roadmap (2026-06-16):** 3 phases (coarse), Phases 21-23. Order: CLI Cleanup first (independent, no deps), then Versioned Catalog (breaks parity goldens anyway), then zsh Retirement last (backfill tests written against final versioned collector behavior).
- **Phase 22 implementation notes:** Homebrew versions via `brew list --formula --versions` / `--cask --versions`. Setapp + web-installed via stdlib `plistlib` reading `Info.plist` CFBundleShortVersionString. Graceful degradation: name-only when version unavailable. Raw-write sections stay raw (no flush_section).
- **Phase 21 scope:** Remove from `cli.py`: `--personal`, `--office`, `--machine` args and the mutual-exclusion group. Remove from `identity.py`: the `personal`/`office`/`machine` parameters from `resolve_computer_selection`. Remove from `cli.py` step 3 guard and step 6 call. Update docstrings and `--help`.
- [Phase ?]: test_naming.py confirmed unchanged — personal/office are filename fixture strings, not flag references
- [Phase ?]: Manually created _locales/en/ in test to write JSON array as messages.json — avoids _make_ext locales kwarg
- [Phase ?]: Retire zsh reference (ZSH-01, ZSH-02)
- [Phase ?]: Placed v1.0.0 history note above Troubleshooting section for natural placement

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
| Stale artifact | Quick task `260614-ckx-fix-interactive-machine-label-ux` (status: missing) — predates v2.0.0, not in scope; acknowledged at v2.0.0 close | deferred | 2026-06-16 |
| Code hygiene | ~88 stale `update-list.sh:NNNN` code-comment cross-refs (out of ZSH-04 scope) — future comment-cleanup pass | deferred | 2026-06-16 |

## Session Continuity

Last session: 2026-06-16T15:52:22.472Z
Stopped at: Completed 23-03-PLAN.md (ZSH-04: scrub README zsh refs)
Resume file: None

## Operator Next Steps

- Start the next milestone with /gsd-new-milestone
