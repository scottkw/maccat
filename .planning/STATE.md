---
gsd_state_version: 1.0
milestone: v2.1.0
milestone_name: Reinstall from Catalog
status: executing
stopped_at: Roadmap created for v2.1.0 (Phases 24-26)
last_updated: "2026-06-16T21:21:05.118Z"
last_activity: 2026-06-16 -- Phase 26 execution started
progress:
  total_phases: 3
  completed_phases: 2
  total_plans: 4
  completed_plans: 3
  percent: 67
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-16)

**Core value:** A single run produces one complete, restorable snapshot of a machine's software *and* tooling extensions — accurate enough to rebuild the environment from, degrading gracefully when any source isn't installed.
**Current focus:** Phase 26 — picker-cli-wiring-integration

## Current Position

Phase: 26 (picker-cli-wiring-integration) — EXECUTING
Plan: 1 of 1
Status: Executing Phase 26
Last activity: 2026-06-16 -- Phase 26 execution started

```
[===========>                              ] Phase 0/3 complete (0%)
```

## Performance Metrics

**Velocity:**

- Total plans completed: 32 (prior milestones)
- Average duration: - min
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 24. Catalog Format Fix + Parser Foundation | 0/TBD | - | - |
| 25. Script Emitter | 0/TBD | - | - |
| 26. Picker + CLI Wiring + Integration | 0/TBD | - | - |
| 24 | 2 | - | - |
| 25 | 1 | - | - |

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- **Roadmap (2026-06-16):** 3 phases (coarse), Phases 24-26. Order: catalog format fix + parser first (MAS-01 is a hard prerequisite — mas ID must exist in catalog before emitter can use it; parser built against final line shapes), then emitter (all 5 render/safety requirements), then picker + CLI wiring last (protect the 13-step catalog-gen invariant in cli.py).
- **Phase 24 scope:** `MasCollector` changed to extract all three `mas list` columns and call `emit_item(name, version, id_)`; update collector tests. New `reinstall/` subpackage: `__init__.py`, `parser.py` with `ParsedItem`/`ParsedSection`/`ParsedCatalog` dataclasses, right-anchored regexes, section-boundary state machine. Round-trip contract test in `tests/reinstall/test_parser_contract.py`.
- **Phase 25 scope:** `reinstall/emitter.py` with `emit_reinstall_script()`, per-source renderers (`_brew_block`, `_editor_ext_block`, `_manual_checklist_block`), static `SECTION_SOURCE_MAP` (17 section titles), `shlex.quote()` via a `quote_for_script()` wrapper as the sole shell-interpolation path. File written at 0o644; zero subprocess calls.
- **Phase 26 scope:** `reinstall/picker.py` (`resolve_catalog_path`), `reinstall/cli.py` (`run_reinstall`), and wiring of `reinstall` subparser + one-liner dispatch into root `cli.py` after `validate_catalog_repo` and before the `--rename` short-circuit. Integration smoke test verifying `--rename` guard does not fire on reinstall args.
- **Key constraint:** `catalog/format.py:emit_item()` must NOT be changed except for the deliberate MAS-01 change (`MasCollector` now passes the numeric ID as the third argument). The parser inverts exactly the four line shapes `emit_item` already produces.
- **mas version de-parens:** `mas list` column 3 already wraps the version in parens (e.g., `(14.0)`). `MasCollector` must strip those parens before passing to `emit_item()` to avoid `AppName ((14.0)) [id]`.

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

Last session: 2026-06-16
Stopped at: Roadmap created for v2.1.0 (Phases 24-26)
Resume file: None

## Operator Next Steps

- Plan Phase 24 with `/gsd:plan-phase 24`
