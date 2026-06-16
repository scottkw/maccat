---
gsd_state_version: 1.0
milestone: v1.1.0
milestone_name: Repo Separation & CI Build
status: planning
last_updated: "2026-06-15T23:55:00.000Z"
last_activity: 2026-06-15
progress:
  total_phases: 3
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-15)

**Core value:** A single run produces one complete, restorable snapshot of a machine's software *and* tooling extensions — accurate enough to rebuild the environment from, degrading gracefully when any source isn't installed.
**Current focus:** Phase 18 — Public Repo Migration (Genericized, Fresh History)

## Current Position

Phase: 18 of 20 (Public Repo Migration)
Plan: — (ready to plan)
Status: Ready to plan
Last activity: 2026-06-15 — Roadmap created for v1.1.0 (Phases 18-20, coarse granularity)

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 29 (prior milestones)
- Average duration: - min
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 18. Public Repo Migration | 0/? | - | - |
| 19. CI Build & Release Pipeline | 0/? | - | - |
| 20. Cut-Over & External-Catalog Verification | 0/? | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- **Roadmap (2026-06-15):** 3 phases (coarse), Phases 18-20. Order 18 → 19 → 20. Phase 18 = genericized clean tree + new public repo + fresh git history. Phase 19 = CI build + tag-gated Release in the new repo. Phase 20 = external-catalog verification, THEN reduce this repo to catalog-data-only (cut-over last, source tree stays intact until new repo proven).
- **Brownfield (2026-06-15):** Code, tests (`tests/`), build script (`scripts/build-pyz.sh`), and an existing CI test workflow (`.github/workflows/ci.yml`) already exist in this repo. This milestone MOVES them and ADDS build+release to CI — it does not re-create the test suite from scratch.
- **Fresh history (MIG-03):** New public repo via clean `git init` of a prepared/genericized tree — NOT a `git filter-branch` of this repo's history (saturated with personal catalog commits). Zero personal data in tree or log.
- **Genericization timing (2026-06-15):** GEN-01..04 happen as part of preparing the clean tree in Phase 18, so no personal data is ever committed to the new repo's first commit.
- **GEN-03 cleanup list:** remove committed `dist/maccat.pyz`, the three stray root test scripts (`test-parse-arguments-11-02.sh`, `test-rename-back-12-02.sh`, `test-rename-front-12-01.sh`), `venv/`, and any `personal`/`office` catalog folders.

### Pending Todos

- Phase 20 planning: MIG-05 verification MUST use an isolated/disposable external catalog dir (`mktemp -d`) — never the user's real `personal/`/`office/` trees. maccat/update-list.sh are destructive (prune/delete/move/commit) when run live.
- Phase 18 planning: confirm the new repo name and `gh repo create` visibility/flags before any push.

### Blockers/Concerns

None currently.

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Browser state | CHR-02 / FF-02 — extension enabled/disabled state | v2 | 2026-06-12 |
| Future tooling | CDX-02 — Codex plugins (arrived after installed v0.46.0) | v2 | 2026-06-12 |
| Distribution | PKG-04 — pipx/PyPI as second distribution channel | future | 2026-06-14 |

## Session Continuity

Last session: 2026-06-15T23:55:00.000Z
Stopped at: Created v1.1.0 roadmap (Phases 18-20); REQUIREMENTS.md traceability mapped 12/12
Resume file: None
